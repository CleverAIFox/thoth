"""워커 계약. **프레임워크를 모른다.**

  POST /translate {texts[], target, source?} -> {translations[], cached[], version}
  GET  /health                      -> {status, version, engine, cache, auth}

★ **FastAPI 라우트와 Lambda 핸들러가 같은 함수를 부른다.** 배포본을 Lambda 로
  옮기면서 CORS · 토큰 비교 · 요청 검증 · 응답 형태를 핸들러에 다시 쓰면 같은
  계약이 두 곳에 살고 한쪽만 고쳐질 때 조용히 어긋난다(DECISIONS §14). 엔진이
  "한 프롬프트를 처리하는 함수" 만 다른 것(`_llm_batch`)과 같은 모양이다.

★ **ASGI 어댑터를 쓰지 않는다.** Mangum 을 끼우면 이 파일이 필요 없지만 Lambda
  패키지에 FastAPI 와 pydantic 이 들어가고 콜드스타트가 1초 넘게 붙는다. 첫
  문항 5.2초에 얹히는 시간이라 사용자가 체감한다. 계약을 떼는 쪽이 중복도 0 이고
  느려지지도 않는다(DECISIONS §68).

★ **검증을 pydantic 에 맡기지 않는다.** 맡기면 잘못된 본문이 FastAPI 에서는
  422, Lambda 에서는 다른 코드가 되어 **같은 입력에 두 답이 나온다.** 여기서
  검증하면 두 경로가 같은 400 을 낸다.

★ CORS 헤더는 이 파일이 만들지 않는다. 로컬은 FastAPI 미들웨어, 배포본은
  Function URL 의 `cors` 설정이 붙인다. 프리플라이트(OPTIONS)도 그쪽이 답하므로
  핸들러가 볼 일이 없다.
"""
import logging
import os
import secrets
from typing import NamedTuple

from . import cache, engine, glossary, guard, pairs

log = logging.getLogger("thoth")

VERSION = "0.1.0"
TARGETS = {"ko"}
MAX_TEXTS = 50
# ★ **`source` 는 선택이다.** 옛 확장 · 벤치 · smoke 는 보내지 않고 그래도 번역은
#   된다. 보내면 모양을 본다 — 쌍 로그의 열이 되므로 아무 값이나 받으면 Athena
#   에서 사이트별로 가를 수 없다. 길이 상한은 호스트명 규격(253)과 어댑터 이름이다.
SOURCE_KEYS = {"site": 253, "adapter": 32}

# ★ 토큰이 비면 열린다. 로컬 개발의 기본값이고, 배포에서는 doctor 가 막는다.
#   확장에 심는 토큰은 사용자가 꺼내볼 수 있으므로 이것은 비밀이 아니라
#   '엔드포인트를 주운 사람' 을 거르는 장치다(MASTER §12).
TOKEN = os.environ.get("WORKER_TOKEN", "")
TOKEN_HEADER = "x-thoth-token"


class Result(NamedTuple):
    """(상태 코드, 본문). 호출부가 이것을 자기 프레임워크의 응답으로 옮긴다."""

    status: int
    body: dict


def err(code: int, name: str, **extra) -> Result:
    """계약 형태의 에러.

    ★ 예외를 그대로 올리면 미들웨어를 건너뛰어 CORS 헤더가 빠지고 브라우저
      콘솔에는 CORS 위반으로 보고된다(DECISIONS §2). 에러도 본문으로 낸다.
    """
    return Result(code, {"error": name, **extra})


def authorized(token_header: str | None) -> bool:
    """상수 시간 비교.

    ★ 문자열 `==` 는 앞에서부터 끊어 길이와 접두사가 새어 나간다.
    """
    if not TOKEN:
        return True
    return secrets.compare_digest(token_header or "", TOKEN)


def validate(payload: object) -> tuple[str, dict] | None:
    """본문 모양 검사. 통과하면 None, 아니면 (에러 이름, 추가 필드).

    ★ **모양과 내용을 한 곳에서 본다.** 전에는 개수·타입을 pydantic 이,
      대상 언어를 라우트가 보았다. 나누면 Lambda 쪽에서 절반만 옮겨 간다.
    """
    if not isinstance(payload, dict):
        return "bad_request", {"detail": "body_not_object"}
    texts = payload.get("texts")
    if not isinstance(texts, list) or not texts:
        return "bad_request", {"detail": "texts_missing"}
    if len(texts) > MAX_TEXTS:
        return "bad_request", {"detail": f"texts_over_{MAX_TEXTS}"}
    if any(not isinstance(t, str) for t in texts):
        return "bad_request", {"detail": "texts_not_strings"}
    target = payload.get("target", "ko")
    if not isinstance(target, str):
        return "bad_request", {"detail": "target_not_string"}
    if target not in TARGETS:
        return "unsupported_target", {"detail": target}
    source = payload.get("source")
    if source is not None:
        if not isinstance(source, dict):
            return "bad_request", {"detail": "source_not_object"}
        for k, v in source.items():
            if k not in SOURCE_KEYS:
                return "bad_request", {"detail": f"source_unknown_{k}"[:64]}
            if not isinstance(v, str) or len(v) > SOURCE_KEYS[k]:
                return "bad_request", {"detail": f"source_bad_{k}"}
    return None


def health(token_header: str | None) -> Result:
    body = {
        "status": "ok",
        "version": VERSION,
        "engine": engine.ENGINE,
        "cache": cache.MODE,
        "auth": bool(TOKEN),
    }
    # ★ 기동 여부는 누구에게나 답한다. 배포 뒤 살아 있는지 보는 데 토큰을
    #   요구하면 헬스체크가 비밀을 들고 다녀야 한다. 다만 잔여 문자는 싣지
    #   않는다 — 남의 상한이 얼마나 닳았는지는 공개할 정보가 아니다.
    if not authorized(token_header):
        return Result(200, body)
    # 카운터 저장소가 죽어도 /health 자체는 답한다. 무엇이 죽었는지 알려주는
    # 것이 이 엔드포인트의 일이다.
    try:
        body["chars_used"] = guard.used()
        body["chars_remaining"] = guard.remaining()
    except guard.GuardUnavailable as e:
        body["status"] = "degraded"
        body["guard_error"] = str(e)
    return Result(200, body)


# 가드 예외 → (상태 코드, 계약상의 이름). 세 갈래가 같은 처리를 타므로
# 분기를 세 번 적지 않는다.
_GUARD_FAIL = {
    guard.QuotaExceeded: (429, "quota_exceeded"),
    guard.TooLong: (413, "too_long"),
    guard.GuardUnavailable: (503, "guard_unavailable"),
}


def translate(payload: object, token_header: str | None) -> Result:
    if not authorized(token_header):
        return err(401, "unauthorized")
    bad = validate(payload)
    if bad:
        name, extra = bad
        return err(400, name, **extra)

    texts = payload["texts"]          # validate 가 모양을 보장한다
    hits = cache.get_many(texts)
    # 중복 제거. 같은 배치에 같은 문장이 두 번 오면 한 번만 번역한다.
    misses = list(dict.fromkeys(t for t in texts if t not in hits))

    partial = ""
    if misses:
        try:
            guard.reserve(misses)          # 번역 '전에' 예약한다
        except tuple(_GUARD_FAIL) as e:
            code, name = _GUARD_FAIL[type(e)]
            detail = str(e) if isinstance(e, guard.GuardUnavailable) else ""
            if isinstance(e, guard.GuardUnavailable):
                log.error("guard unavailable: %s", e)
            # ★ 캐시 히트까지 버리지 않는다. 히트는 이미 손에 있고 과금이 0
            #   이므로, 상한에 걸렸다고 보여줄 수 있는 것까지 감출 이유가 없다.
            #   못 채운 자리만 null 로 두고 왜 못 채웠는지를 실어 보낸다.
            if not hits:
                return err(code, name, **({"detail": detail} if detail else {}))
            partial = name
        else:
            try:
                fresh, raw = engine.translate_detail(misses)
            except Exception as e:
                # ★ 엔진 실패는 부분 응답으로 내리지 않는다. 일시적이라 재시도가
                #   맞는데 200 으로 내리면 확장이 그 자리를 영구 실패로 버린다.
                #   가드 실패는 재시도로 풀리지 않으므로 반대다.
                log.exception("engine failed")
                return err(502, "engine_failed", detail=type(e).__name__)

            # 엔진을 믿지 않는다. zip 은 짧은 쪽에 맞춰 조용히 자르고, 잘린 결과는
            # 아래에서 KeyError 로 터져 500 이 된다. 여기서 계약으로 잡는다.
            if (len(fresh) != len(misses) or len(raw) != len(misses)
                    or any(not isinstance(x, str) for x in fresh)):
                log.error("engine returned %d for %d inputs", len(fresh), len(misses))
                return err(502, "engine_failed", detail="length_mismatch")

            cache.put_many(dict(zip(misses, fresh)))
            hits.update(dict(zip(misses, fresh)))
            _log_pairs(misses, raw, fresh, payload.get("source") or {})

    missed = set(misses)
    body = {
        "translations": [hits.get(t) for t in texts],
        "cached": [t not in missed for t in texts],
        "version": VERSION,
    }
    if partial:
        body["partial"] = partial
    return Result(200, body)


def _log_pairs(src: list[str], raw: list[str], ko: list[str], source: dict) -> None:
    """캐시에 쓴 **뒤에** 적는다. 캐시 쓰기가 죽으면 요청이 500 이고 그 번역은
    사용자에게 가지 않았으므로 쌍으로 남길 이유도 없다.

    ★ 용어집 이름을 다시 고른다. `glossary.match` 는 결정적이라 엔진 안에서
      고른 것과 같은 값이고, 엔진 반환값을 늘리면 엔진마다 그것을 들고 다녀야 한다.

    ★ **어떤 예외도 올리지 않는다.** 번역은 이미 끝났고 이것은 부산물이다.
    """
    site = source.get("site")
    # ★ **픽스처와 개발 번역은 쌓지 않는다**(DECISIONS §104). 막지 않으면 사람이
    #   지어낸 표본이 실사용 코퍼스에 섞이고 Parquet 에서 골라낼 수 없다.
    if pairs.is_local(site):
        return
    try:
        book, _ = glossary.match(src)
        pairs.emit(pairs.records(
            src, raw, ko,
            engine=engine.ENGINE, model=engine.model_name(),
            prompt=engine.prompt_fingerprint(), book=book,
            site=site, adapter=source.get("adapter"), ver=VERSION,
        ))
    except Exception:
        log.exception("pair 로그 실패")
