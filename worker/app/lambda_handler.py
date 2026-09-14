"""Lambda Function URL 핸들러. **계약은 `contract.py` 가 들고 있다.**

  이벤트 → (메서드, 경로, 토큰 헤더, 본문) → contract → Function URL 응답

★ **여기에 판단을 두지 않는다.** 검증 · 토큰 비교 · 응답 형태는 전부 계약이
  한다. 이 파일이 아는 것은 Lambda 이벤트의 모양뿐이고, 그래서 로컬 FastAPI 와
  같은 입력에 같은 답이 나온다(DECISIONS §68).

★ **서드파티를 import 하지 않는다.** `boto3` 와 `botocore` 는 `cache` · `guard`
  · `engine` 이 함수 안에서 늦게 부르고 Lambda 런타임이 제공한다. 그래서 배포
  패키지에 의존성이 하나도 들어가지 않는다 — 우리 코드와 용어집 JSON 뿐이다.
  콜드스타트가 짧은 이유가 이것이다.

★ **CORS 헤더를 만들지 않는다.** Function URL 의 `cors` 설정이 프리플라이트
  (OPTIONS)까지 답한다. 코드가 아니라 설정이 하는 자리다.

★ Function URL 은 페이로드 형식 2.0 만 쓴다. `requestContext.http` 에 메서드와
  경로가 있고 헤더 키는 소문자로 온다. **그래도 소문자로 한 번 더 낮춘다** —
  '온다고 적혀 있다' 와 '왔다' 는 다르고, 틀리면 토큰이 조용히 안 걸린다.
"""
import base64
import json

from . import contract


def _headers(event: dict) -> dict:
    raw = event.get("headers") or {}
    return {str(k).lower(): v for k, v in raw.items()}


def _route(event: dict) -> tuple[str, str]:
    """(메서드, 경로). 형식이 이상하면 빈 문자열을 돌려준다."""
    http = (event.get("requestContext") or {}).get("http") or {}
    method = str(http.get("method", "")).upper()
    path = event.get("rawPath") or http.get("path") or ""
    return method, str(path)


# ★ **'본문이 없다' 와 '파싱을 못 했다' 를 가른다.** 둘 다 None 으로 넘기면
#   계약이 `body_not_object` 로 받는데, 로컬 FastAPI 는 깨진 JSON 을
#   `invalid_json` 으로 적는다. 상태와 에러 이름이 같아도 **원인을 다르게 적으면
#   로그를 보고 다른 것을 고치게 된다**(DECISIONS §71).
UNPARSEABLE = object()


def _body(event: dict) -> object:
    """본문을 파이썬 값으로. 없으면 None, 파싱 실패면 `UNPARSEABLE`."""
    raw = event.get("body")
    if raw is None:
        return None
    if event.get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return UNPARSEABLE
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return UNPARSEABLE


def _respond(result: contract.Result) -> dict:
    return {
        "statusCode": result.status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(result.body, ensure_ascii=False),
    }


def handler(event, context=None):
    method, path = _route(event if isinstance(event, dict) else {})
    token = _headers(event if isinstance(event, dict) else {}).get(contract.TOKEN_HEADER)

    if method == "GET" and path.endswith("/health"):
        return _respond(contract.health(token))
    if method == "POST" and path.endswith("/translate"):
        payload = _body(event)
        if payload is UNPARSEABLE:
            # 토큰 검사가 먼저다. 본문이 깨졌다고 인증을 건너뛰지 않는다.
            if not contract.authorized(token):
                return _respond(contract.err(401, "unauthorized"))
            return _respond(contract.err(400, "bad_request", detail="invalid_json"))
        return _respond(contract.translate(payload, token))

    # ★ 모르는 경로를 500 으로 두지 않는다. 어디로 보냈는지가 원인이므로
    #   그것을 실어 보낸다(DECISIONS §37).
    return _respond(
        contract.err(404, "not_found", detail=f"{method or '?'} {path or '?'}")
    )
