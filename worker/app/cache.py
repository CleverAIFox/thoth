"""번역 캐시. 키는 sha256(text) — 사이트를 섞지 않는다(PLAN §2-3).

같은 문장이 여러 사이트에 나오므로 사이트를 키에 넣으면 중복 과금된다.
사이트가 늘수록 히트율이 올라가는 구조로 둔다.

CACHE=memory  프로세스 메모리. 재시작하면 사라진다
CACHE=file    로컬 JSON 파일. 재시작을 견딘다
CACHE=ddb     DynamoDB

★ 재시작마다 캐시가 비면 전량 재번역이다. 로컬 엔진에서는 시간이지만
  과금 엔진에서는 그대로 재과금이다. 개발 중에도 영속 캐시를 쓴다.

★ 항목마다 get_item 을 돌면 왕복이 항목 수만큼 난다. Lambda 는 실행 시간이
  곧 과금이므로 batch_get_item(최대 100건)으로 묶는다.

★ **`UnprocessedKeys` 를 사이 없이 다시 던지면 조름 속에서 제자리 회전이다**
  (DECISIONS §181). 180 전까지 `while pending:` 이 **횟수도 사이도 없이** 돌았고
  `batch_writer` 도 같은 모양이었다 — `PAY_PER_REQUEST` 에서는 조름이 드물어
  한 번도 안 드러났지만, 2026-10-11 에 테이블을 `PROVISIONED` 25/25 로 내리면서
  **조름이 정상 상태**가 됐다. Lambda 는 벽시계로 과금되므로 제자리 회전은
  **무료 몫을 아끼려고 다른 무료 몫을 태우는 짓**이다.

★ **다 못 받으면 빈 쪽으로 끝낸다.** 캐시 미스는 재번역(시간·돈)이고 멈춤은
  요청 실패다. 둘 다 나쁘지만 **둘 중 하나는 돌아온다** — 안 돌아오는 쪽을 고르지
  않는다. 못 받은 건수는 로그에 남겨 조름을 볼 수 있게 한다.
"""
import hashlib
import json
import logging
import os
import pathlib
import time

MODE = os.environ.get("CACHE", "memory")
TABLE = os.environ.get("CACHE_TABLE", "thoth-translations")
BATCH = 100
# ★ `batch_write_item` 은 25건이 상한이다 — 읽기(100)와 **다르다**. 한 수로 묶어
#   쓰면 쓰기가 조용히 거절된다.
쓰기묶음 = 25
재시도 = 5
사이 = 0.05        # 배로 늘린다 — 합이 최대 1.55초. 25 RCU 는 초마다 다시 찬다
FILE = pathlib.Path(os.environ.get("CACHE_FILE", ".cache/translations.json"))

log = logging.getLogger("thoth")

_mem: dict[str, str] = {}
_res = None


def key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resource():
    global _res
    if _res is None:
        import boto3
        from botocore.config import Config
        # ★ **재시도를 물려받지 않고 적는다.** botocore 의 기정값은 판마다 바뀌고,
        #   `PROVISIONED` 에서는 **요청째로 조름을 맞는 일**이 정상이라 이 수가
        #   동작을 정한다. `standard` 는 지터를 넣어 되던진다.
        _res = boto3.resource(
            "dynamodb", config=Config(retries={"max_attempts": 5, "mode": "standard"}))
    return _res


def _사이두기(번: int) -> None:
    time.sleep(사이 * (2 ** 번))


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def _file_load() -> dict[str, str]:
    if not _mem and FILE.exists():
        _mem.update(json.loads(FILE.read_text(encoding="utf-8")))
    return _mem


def get_many(texts: list[str]) -> dict[str, str]:
    if not texts:
        return {}
    if MODE == "file":
        m = _file_load()
        return {t: m[key(t)] for t in texts if key(t) in m}
    if MODE == "memory":
        return {t: _mem[key(t)] for t in texts if key(t) in _mem}

    by_hash = {key(t): t for t in texts}   # 중복 원문은 자동으로 합쳐진다
    found: dict[str, str] = {}
    res = _resource()

    for group in _chunks(list(by_hash), BATCH):
        pending = {TABLE: {"Keys": [{"h": h} for h in group]}}
        for 번 in range(재시도 + 1):
            r = res.batch_get_item(RequestItems=pending)
            for item in r["Responses"].get(TABLE, []):
                found[by_hash[item["h"]]] = item["ko"]
            pending = r.get("UnprocessedKeys") or {}
            if not pending:
                break
            if 번 < 재시도:
                _사이두기(번)
        if pending:
            남 = len((pending.get(TABLE) or {}).get("Keys") or [])
            log.warning("ddb 읽기 %d건을 %d번 만에 못 받았다 — 캐시 미스로 둔다 "
                        "(조르고 있다)", 남, 재시도 + 1)
    return found


def put_many(pairs: dict[str, str]) -> None:
    if not pairs:
        return
    if MODE == "file":
        m = _file_load()
        m.update({key(k): v for k, v in pairs.items()})
        FILE.parent.mkdir(parents=True, exist_ok=True)
        FILE.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        return
    if MODE == "memory":
        _mem.update({key(k): v for k, v in pairs.items()})
        return

    # ★ `batch_writer` 를 안 쓴다. 그것의 `__exit__` 가 `while self._items_buffer:` 로
    #   **횟수도 사이도 없이** 다시 던진다 — 읽기 쪽과 같은 병이다(DECISIONS §181).
    # ★ 같은 해시가 한 배치에 두 번 들어가면 DynamoDB 가 **요청째로** 거절한다.
    #   `overwrite_by_pkeys=["h"]` 가 해 주던 일이라 여기서 먼저 합친다.
    묶음 = {key(k): v for k, v in pairs.items()}
    res = _resource()
    못넣음 = 0
    for group in _chunks([{"PutRequest": {"Item": {"h": h, "ko": v}}}
                          for h, v in 묶음.items()], 쓰기묶음):
        pending = {TABLE: group}
        for 번 in range(재시도 + 1):
            r = res.batch_write_item(RequestItems=pending)
            pending = r.get("UnprocessedItems") or {}
            if not pending:
                break
            if 번 < 재시도:
                _사이두기(번)
        if pending:
            못넣음 += len(pending.get(TABLE) or [])
    if 못넣음:
        log.warning("ddb 쓰기 %d건을 %d번 만에 못 넣었다 — 다음 요청이 그만큼 "
                    "다시 번역한다 (조르고 있다)", 못넣음, 재시도 + 1)
