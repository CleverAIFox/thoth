"""워커 계약 : POST /translate {texts[], target} -> {translations[], cached[], version}"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import cache, engine, guard

VERSION = "0.1.0"
app = FastAPI(title="site-translate worker", version=VERSION)

# 콘텐츠 스크립트의 fetch 는 페이지 오리진을 쓴다. CORS 없으면 전부 막힌다.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["POST"], allow_headers=["*"]
)


class Req(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=50)
    target: str = "ko"


@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION, "engine": engine.ENGINE,
            "cache": cache.MODE, "chars_used": guard.used()}


@app.post("/translate")
def translate(req: Req):
    hits = cache.get_many(req.texts)
    misses = [t for t in req.texts if t not in hits]

    if misses:
        try:
            guard.check_and_add(misses)
        except guard.QuotaExceeded:
            return JSONResponse({"error": "quota_exceeded"}, status_code=429)
        except guard.TooLong:
            return JSONResponse({"error": "too_long"}, status_code=413)

        fresh = engine.translate_batch(misses)
        cache.put_many(dict(zip(misses, fresh)))
        hits.update(dict(zip(misses, fresh)))

    return {
        "translations": [hits[t] for t in req.texts],
        "cached": [t not in misses for t in req.texts],
        "version": VERSION,
    }
