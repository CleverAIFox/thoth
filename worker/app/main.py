"""워커 계약 : POST /translate {texts[], target} -> {translations[], cached[], version}"""
import logging
import os
import secrets

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import cache, engine, guard

log = logging.getLogger("thoth")

VERSION = "0.1.0"
TARGETS = {"ko"}

# ★ 토큰이 비면 열린다. 로컬 개발의 기본값이고, 배포에서는 doctor 가 막는다.
#   확장에 심는 토큰은 사용자가 꺼내볼 수 있으므로 이것은 비밀이 아니라
#   '엔드포인트를 주운 사람' 을 거르는 장치다(MASTER §12).
TOKEN = os.environ.get("WORKER_TOKEN", "")
TOKEN_HEADER = "x-thoth-token"

app = FastAPI(title="thoth worker", version=VERSION)

# 콘텐츠 스크립트의 fetch 는 페이지 오리진을 쓴다. CORS 없으면 전부 막힌다.
# 토큰 헤더는 단순 요청이 아니므로 preflight 가 돈다. allow_headers 가 이것을 덮는다.
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


def authorized(request: Request) -> bool:
    """상수 시간 비교. 문자열 == 는 앞에서부터 끊어 길이·접두사가 새어 나간다."""
    if not TOKEN:
        return True
    return secrets.compare_digest(request.headers.get(TOKEN_HEADER, ""), TOKEN)


@app.get("/health")
def health(request: Request):
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
    if not authorized(request):
        return body
    # 카운터 저장소가 죽어도 /health 자체는 답한다. 무엇이 죽었는지 알려주는
    # 것이 이 엔드포인트의 일이다.
    try:
        body["chars_used"] = guard.used()
        body["chars_remaining"] = guard.remaining()
    except guard.GuardUnavailable as e:
        body["status"] = "degraded"
        body["guard_error"] = str(e)
    return body


# 가드 예외 → (상태 코드, 계약상의 이름). 세 갈래가 같은 처리를 타므로
# 분기를 세 번 적지 않는다.
_GUARD_FAIL = {
    guard.QuotaExceeded: (429, "quota_exceeded"),
    guard.TooLong: (413, "too_long"),
    guard.GuardUnavailable: (503, "guard_unavailable"),
}


@app.post("/translate")
def translate(req: Req, request: Request):
    if not authorized(request):
        return _err(401, "unauthorized")
    if req.target not in TARGETS:
        return _err(400, "unsupported_target", detail=req.target)

    hits = cache.get_many(req.texts)
    # 중복 제거. 같은 배치에 같은 문장이 두 번 오면 한 번만 번역한다.
    misses = list(dict.fromkeys(t for t in req.texts if t not in hits))

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
                return _err(code, name, **({"detail": detail} if detail else {}))
            partial = name
        else:
            try:
                fresh = engine.translate_batch(misses)
            except Exception as e:
                # ★ 엔진 실패는 부분 응답으로 내리지 않는다. 일시적이라 재시도가
                #   맞는데 200 으로 내리면 확장이 그 자리를 영구 실패로 버린다.
                #   가드 실패는 재시도로 풀리지 않으므로 반대다.
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
    body = {
        "translations": [hits.get(t) for t in req.texts],
        "cached": [t not in missed for t in req.texts],
        "version": VERSION,
    }
    if partial:
        body["partial"] = partial
    return body
