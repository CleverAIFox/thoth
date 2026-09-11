"""번역 캐시. 키는 sha256(text) — 사이트를 섞지 않는다(PLAN §2-3).

같은 문장이 여러 사이트에 나오므로 사이트를 키에 넣으면 중복 과금된다.
사이트가 늘수록 히트율이 올라가는 구조로 둔다.

CACHE=memory  로컬 개발
CACHE=ddb     DynamoDB

★ 항목마다 get_item 을 돌면 왕복이 항목 수만큼 난다. Lambda 는 실행 시간이
  곧 과금이므로 batch_get_item(최대 100건)으로 묶는다.
"""
import hashlib
import os

MODE = os.environ.get("CACHE", "memory")
TABLE = os.environ.get("CACHE_TABLE", "thoth-translations")
BATCH = 100

_mem: dict[str, str] = {}
_res = None


def key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resource():
    global _res
    if _res is None:
        import boto3
        _res = boto3.resource("dynamodb")
    return _res


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def get_many(texts: list[str]) -> dict[str, str]:
    if not texts:
        return {}
    if MODE == "memory":
        return {t: _mem[key(t)] for t in texts if key(t) in _mem}

    by_hash = {key(t): t for t in texts}   # 중복 원문은 자동으로 합쳐진다
    found: dict[str, str] = {}
    res = _resource()

    for group in _chunks(list(by_hash), BATCH):
        pending = {TABLE: {"Keys": [{"h": h} for h in group]}}
        while pending:
            r = res.batch_get_item(RequestItems=pending)
            for item in r["Responses"].get(TABLE, []):
                found[by_hash[item["h"]]] = item["ko"]
            pending = r.get("UnprocessedKeys") or {}
    return found


def put_many(pairs: dict[str, str]) -> None:
    if not pairs:
        return
    if MODE == "memory":
        _mem.update({key(k): v for k, v in pairs.items()})
        return

    table = _resource().Table(TABLE)
    with table.batch_writer(overwrite_by_pkeys=["h"]) as b:
        for k, v in pairs.items():
            b.put_item(Item={"h": key(k), "ko": v})
