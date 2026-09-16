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
