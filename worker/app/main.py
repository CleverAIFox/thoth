"""워커 계약 : POST /translate {texts[], target} -> {translations[], cached[], version}"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import logging

from . import cache, engine, guard

log = logging.getLogger("thoth")

VERSION = "0.1.0"
TARGETS = {"ko"}
app = FastAPI(title="thoth worker", version=VERSION)

# 콘텐츠 스크립트의 fetch 는 페이지 오리진을 쓴다. CORS 없으면 전부 막힌다.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["POST"], allow_headers=["*"]
)


class Req(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=50)
    target: str = "ko"


def _err(code: int, name: str, **extra):
    """계약 형태의 에러. 예외를 그대로 올리면 미들웨어를 건너뛰어 CORS 헤더가
    빠지고 브라우저 콘솔에는 CORS 위반으로 보고된다(DECISIONS §2)."""
    return JSONResponse({"error": name, **extra}, status_code=code)


@app.get("/health")
def health():
    body = {
        "status": "ok",
        "version": VERSION,
        "engine": engine.ENGINE,
        "cache": cache.MODE,
    }
    # 카운터 저장소가 죽어도 /health 자체는 답한다. 무엇이 죽었는지 알려주는
    # 것이 이 엔드포인트의 일이다.
    try:
        body["chars_used"] = guard.used()
        body["chars_remaining"] = guard.remaining()
    except guard.GuardUnavailable as e:
        body["status"] = "degraded"
        body["guard_error"] = str(e)
    return body


@app.post("/translate")
def translate(req: Req):
    if req.target not in TARGETS:
        return _err(400, "unsupported_target", detail=req.target)

    hits = cache.get_many(req.texts)
    # 중복 제거. 같은 배치에 같은 문장이 두 번 오면 한 번만 번역한다.
    misses = list(dict.fromkeys(t for t in req.texts if t not in hits))

    if misses:
        try:
            guard.reserve(misses)          # 번역 '전에' 예약한다
        except guard.QuotaExceeded:
            return _err(429, "quota_exceeded")
        except guard.TooLong:
            return _err(413, "too_long")
        except guard.GuardUnavailable as e:
            # 세지 못하는 상태로 번역하면 상한이 없는 것과 같다. 닫는다.
            log.error("guard unavailable: %s", e)
            return _err(503, "guard_unavailable", detail=str(e))

        try:
            fresh = engine.translate_batch(misses)
        except Exception as e:
            log.exception("engine failed")
            return _err(502, "engine_failed", detail=type(e).__name__)

        # 엔진을 믿지 않는다. zip 은 짧은 쪽에 맞춰 조용히 자르고, 잘린 결과는
        # 아래에서 KeyError 로 터져 500 이 된다. 여기서 계약으로 잡는다.
        if len(fresh) != len(misses) or any(not isinstance(x, str) for x in fresh):
            log.error("engine returned %d for %d inputs", len(fresh), len(misses))
            return _err(502, "engine_failed", detail="length_mismatch")

        cache.put_many(dict(zip(misses, fresh)))
        hits.update(dict(zip(misses, fresh)))

    missed = set(misses)
    return {
        "translations": [hits[t] for t in req.texts],
        "cached": [t not in missed for t in req.texts],
        "version": VERSION,
    }
