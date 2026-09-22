"""원문 · 번역 쌍 로그. **자체 번역 모델의 학습 데이터가 여기서 난다**(DECISIONS §97).

  캐시 미스 한 건 → stdout 한 줄(JSON) → CloudWatch Logs → 구독 필터
  → Firehose(해제 · 추출 · Parquet) → S3 → Glue 테이블 `pairs`

★ **줄 전체가 JSON 이다.** 접두사(`INFO thoth ...`)를 붙이면 Firehose 가 메시지를
  추출한 뒤 JSON 으로 읽지 못해 Parquet 변환이 전부 오류 버킷으로 간다. 그래서
  `usage` 와 다른 로거를 쓰고 포맷터가 메시지만 낸다(배선은 `__init__.py`).

★ **`k` 가 구독 필터의 판별자다.** `{ $.k = "pair" }` 로 이 줄만 Firehose 로
  간다. 필드명을 바꾸면 `infra/analytics.tf` 의 필터가 조용히 0건이 된다 —
  `SCHEMA` 와 함께 `test_pairs.py` 가 묶는다.

★ **한 줄에 한 쌍이다.** 요청 하나를 한 줄에 담으면 50문장 × 5,000자에서
  CloudWatch 이벤트 상한에 닿고, Glue 스키마가 배열이 되어 Athena 에서 매번
  `UNNEST` 해야 한다.

★ **캐시 히트는 적지 않는다.** 같은 원문의 쌍은 처음 번역될 때 한 번이면 된다.
  히트율(#24)은 별도 계기로 잰다 — 여기에 섞으면 학습 데이터에 중복이 쌓인다.

★ **검사 축을 여기서 돌리지 않는다.** 위반 판정은 읽을 때 한다. 축은 늘어나고
  (§93 에서 어미 축이 뒤늦게 생겼다) 쓸 때 박은 판정은 새 축을 모른다. 날것을
  남기면 **옛 데이터에 새 자를 댈 수 있다.**

★ **사이트는 호스트만 받는다.** 경로에는 강의 · 사용자 식별자가 섞인다.
"""
import json
import logging
import re
import time

from . import cache

log = logging.getLogger("thoth.pair")

SCHEMA = 1
KIND = "pair"

# Glue 테이블의 열과 같은 순서 · 같은 이름이다. `analytics.tf` 가 정본을 따로
# 들 수 없으므로(HCL 은 파이썬을 못 읽는다) 검사가 둘을 대조한다.
COLUMNS = (
    ("k", "string"),
    ("v", "int"),
    ("ts", "bigint"),
    ("h", "string"),
    ("src", "string"),
    ("raw", "string"),
    ("ko", "string"),
    ("engine", "string"),
    ("model", "string"),
    ("prompt", "string"),
    ("book", "string"),
    ("n", "int"),
    ("site", "string"),
    ("adapter", "string"),
    ("ver", "string"),
)


# ★ **로컬에서 온 것은 학습 데이터가 아니다**(DECISIONS §104). 픽스처와 개발 중
#   번역이 같은 경로로 들어오는데, 픽스처의 영어 문장은 사람이 지어낸 표본이라
#   실사용 코퍼스에 섞이면 되돌릴 수 없다 — Parquet 는 한 줄만 지우지 못한다.
#
# ★ **호스트로 가른다.** 확장은 `location.hostname` 을 보내고 픽스처가 Udemy 인
#   척해도 그 값은 `127.0.0.1` 이다. 흉내낸 주소를 보내면 이 구별이 사라진다.
#
# ★ `site` 가 없는 것(`None`)은 막지 않는다. 벤치 · smoke · 배포 확인이 그렇게
#   들어오고, 그 쌍은 실제 엔진을 지난 것이다.
LOCAL_SUFFIX = (".localhost", ".local", ".test")
LOCAL_HOSTS = {"localhost", "0.0.0.0", "::1"}
# ★ **접두사로 보지 않는다.** `startswith("127.")` 는 `127.0.0.1.evil.com` 도 로컬로
#   읽는다. 이 검사는 버리는 쪽으로 틀리므로 조용히 데이터가 사라진다 — 틀린 방향이
#   안전하다는 것과 틀려도 된다는 것은 다르다.
LOOPBACK = re.compile(r"^127(\.\d{1,3}){3}$")


def _host(site: str) -> str:
    """`host:port` 에서 호스트만. **IPv6 를 포트로 자르지 않는다** — `::1` 을 무턱대고
    `:\d+$` 로 벗기면 `:` 하나가 남아 로컬이 아닌 것이 된다."""
    s = site.strip().lower()
    if s.startswith("[") and "]" in s:          # [::1]:8000
        return s[1:s.index("]")]
    return s.split(":")[0] if s.count(":") == 1 else s


def is_local(site: str | None) -> bool:
    """로컬 호스트에서 온 쌍인가. `None` 은 로컬이 아니다 — 벤치와 smoke 가 그렇다."""
    if not site:
        return False
    host = _host(site)
    return host in LOCAL_HOSTS or bool(LOOPBACK.match(host)) or host.endswith(LOCAL_SUFFIX)


def records(src: list[str], raw: list[str], ko: list[str], *, engine: str,
            model: str, prompt: str, book: str | None, site: str | None,
            adapter: str | None, ver: str, now_ms: int | None = None) -> list[dict]:
    """쌍 레코드를 만든다. **판단만 한다** — 쓰지 않는다."""
    ts = int(time.time() * 1000) if now_ms is None else now_ms
    return [
        {
            "k": KIND,
            "v": SCHEMA,
            "ts": ts,
            "h": cache.key(s),            # 캐시 키와 같다 — 둘을 조인한다
            "src": s,
            "raw": r,
            "ko": t,
            "engine": engine,
            "model": model,
            "prompt": prompt,
            "book": book,
            "n": len(src),
            "site": site,
            "adapter": adapter,
            "ver": ver,
        }
        for s, r, t in zip(src, raw, ko)
    ]


def emit(recs: list[dict]) -> None:
    """★ **실패해도 번역을 막지 않는다.** 이 줄은 부산물이고 사용자는 번역을
    기다린다. 직렬화가 죽으면 `usage` 로거로 경고만 남긴다(§70: 관측을 남긴다).
    """
    for r in recs:
        try:
            log.info(json.dumps(r, ensure_ascii=False, separators=(",", ":")))
        except (TypeError, ValueError) as e:
            logging.getLogger("thoth").warning("pair 직렬화 실패: %s", e)
