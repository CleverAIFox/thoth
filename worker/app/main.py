"""워커 계약 : POST /translate {texts[], target} -> {translations[], cached[], version}"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import logging

from . import cache, engine, guard

log = logging.getLogger("thoth")

VERSION = "0.1.0"
app = FastAPI(title="thoth worker", version=VERSION)

# 콘텐츠 스크립트의 fetch 는 페이지 오리진을 쓴다. CORS 없으면 전부 막힌다.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["POST"], allow_headers=["*"]
)


class Req(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=50)
    target: str = "ko"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": VERSION,
        "engine": engine.ENGINE,
        "cache": cache.MODE,
        "chars_used": guard.used(),
        "chars_remaining": guard.remaining(),
    }


@app.post("/translate")
def translate(req: Req):
    hits = cache.get_many(req.texts)
    # 중복 제거. 같은 배치에 같은 문장이 두 번 오면 한 번만 번역한다.
    misses = list(dict.fromkeys(t for t in req.texts if t not in hits))

    if misses:
        try:
            guard.reserve(misses)          # 번역 '전에' 예약한다
        except guard.QuotaExceeded:
            return JSONResponse({"error": "quota_exceeded"}, status_code=429)
        except guard.TooLong:
            return JSONResponse({"error": "too_long"}, status_code=413)

        try:
            fresh = engine.translate_batch(misses)
        except Exception as e:
            # 엔진 실패를 500 으로 흘리면 CORS 헤더가 빠져 브라우저에서
            # 원인이 CORS 로 오인된다. 계약대로 에러를 돌려준다.
            log.exception("engine failed")
            return JSONResponse(
                {"error": "engine_failed", "detail": type(e).__name__},
                status_code=502,
            )
        cache.put_many(dict(zip(misses, fresh)))
        hits.update(dict(zip(misses, fresh)))

    missed = set(misses)
    return {
        "translations": [hits[t] for t in req.texts],
        "cached": [t not in missed for t in req.texts],
        "version": VERSION,
    }
