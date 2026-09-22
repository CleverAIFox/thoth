"""FastAPI 라우트. **계약은 `contract.py` 가 들고 있다.**

★ 이 파일에는 프레임워크 배선만 둔다 — 미들웨어, 경로, 응답 객체. 배포본은
  같은 계약을 `lambda_handler.py` 로 부르므로, 여기에 판단을 두면 두 경로가
  갈린다(DECISIONS §68).

★ 본문을 pydantic 으로 받지 않는다. 받으면 잘못된 본문이 여기서는 422, Lambda
  에서는 다른 코드가 되어 같은 입력에 두 답이 나온다. `Body` 로 날것을 받아
  `contract.validate` 하나가 판정한다.
"""
import logging

from fastapi import Body, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import contract

log = logging.getLogger("thoth")

app = FastAPI(title="thoth worker", version=contract.VERSION)

# 콘텐츠 스크립트의 fetch 는 페이지 오리진을 쓴다. CORS 없으면 전부 막힌다.
# 토큰 헤더는 단순 요청이 아니므로 preflight 가 돈다. allow_headers 가 이것을 덮는다.
#
# ★ 배포본에서는 Function URL 의 cors 설정이 같은 일을 한다. 코드가 아니라
#   설정이 하는 자리라 이 미들웨어는 로컬 전용이다.
#
# ★ **메서드를 배포본과 맞춘다**(DECISIONS §105). 팝업의 `연결 확인` 은 토큰 헤더를
#   달고 `GET /health` 를 부르고, 커스텀 헤더가 있으면 GET 도 프리플라이트를 탄다.
#   `POST` 만 열어 두어 로컬에서는 `OPTIONS /health` 가 400 이었고 배포본(`GET` ·
#   `POST`)에서는 됐다 — §68 이 없애려던 "같은 입력에 두 답" 이 CORS 층에 남아
#   있었다. `test_contract.py` 가 `infra/compute.tf` 와 대조한다.
CORS_METHODS = ["POST", "GET"]
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=CORS_METHODS, allow_headers=["*"]
)


def _respond(r: contract.Result) -> JSONResponse:
    return JSONResponse(r.body, status_code=r.status)


# ★ **깨진 JSON 은 FastAPI 가 422 로 가로챈다.** 본문을 날것으로 받아도 파싱은
#   프레임워크가 하므로 그 실패는 계약에 닿지 않는다. Lambda 쪽은 파싱 실패를
#   `None` 으로 넘겨 400 이 되므로, 두면 **같은 입력에 두 답**이 나온다 — §68 이
#   없애려던 바로 그것이다(DECISIONS §71).
@app.exception_handler(RequestValidationError)
def _bad_body(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _respond(contract.err(400, "bad_request", detail="invalid_json"))


@app.get("/health")
def health(request: Request):
    return _respond(contract.health(request.headers.get(contract.TOKEN_HEADER)))


@app.post("/translate")
def translate(request: Request, payload=Body(default=None)):
    return _respond(
        contract.translate(payload, request.headers.get(contract.TOKEN_HEADER))
    )
