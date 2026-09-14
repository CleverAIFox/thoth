"""Lambda Function URL 핸들러.

★ **배포본이 타는 경로다.** 로컬 워커는 FastAPI 를 타고 배포본은 이 파일을
  타므로, 여기가 검사되지 않으면 배포 뒤에야 결함을 안다(DECISIONS §17).

★ **판정은 계약이 한다.** 이 파일의 검사는 '이벤트를 계약 인자로 옳게 옮기는가'
  하나이고, 검증·토큰·응답 형태는 `test_contract.py` 가 본다. 같은 것을 두 번
  검사하면 한쪽만 고쳐질 때 갈린다(DECISIONS §14).
"""
import base64
import json
import os

os.environ["ENGINE"] = "echo"
os.environ["CACHE"] = "memory"

import pytest
from fastapi.testclient import TestClient

from app import cache, contract, guard
from app import lambda_handler as lh
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean():
    cache._mem.clear()
    guard._mem.clear()
    yield


def ev(method, path, body=None, headers=None, b64=False):
    return {
        "rawPath": path,
        "requestContext": {"http": {"method": method, "path": path}},
        "headers": headers or {},
        "body": body,
        "isBase64Encoded": b64,
    }


def body_of(resp):
    return json.loads(resp["body"])


# ── 배선 ─────────────────────────────────────────────────────────────────


def test_health_가_돈다():
    r = lh.handler(ev("GET", "/health"))
    assert r["statusCode"] == 200
    assert body_of(r)["engine"] == "echo"


def test_translate_가_돈다():
    r = lh.handler(ev("POST", "/translate", json.dumps({"texts": ["hello"]})))
    assert r["statusCode"] == 200
    assert body_of(r)["cached"] == [False]


def test_응답은_Function_URL_모양이다():
    r = lh.handler(ev("GET", "/health"))
    assert set(r) == {"statusCode", "headers", "body"}
    assert r["headers"]["content-type"] == "application/json"
    assert isinstance(r["body"], str)


def test_CORS_헤더를_만들지_않는다():
    # Function URL 의 cors 설정이 붙인다. 코드가 붙이면 두 곳에서 정하게 된다.
    r = lh.handler(ev("POST", "/translate", json.dumps({"texts": ["hi"]})))
    assert not [k for k in r["headers"] if k.lower().startswith("access-control")]


def test_모르는_경로는_404_에_보낸_곳을_적는다():
    r = lh.handler(ev("GET", "/nope"))
    assert r["statusCode"] == 404
    assert "GET /nope" in body_of(r)["detail"]


def test_메서드가_다르면_404():
    assert lh.handler(ev("GET", "/translate"))["statusCode"] == 404
    assert lh.handler(ev("POST", "/health"))["statusCode"] == 404


def test_이벤트가_이상해도_죽지_않는다():
    # ★ 예외를 올리면 Lambda 가 502 를 내고 원인이 로그에만 남는다.
    for bad in ({}, {"headers": None}, {"requestContext": {}}, "문자열", None):
        r = lh.handler(bad)
        assert r["statusCode"] == 404


# ── 헤더 ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("name", ["x-thoth-token", "X-Thoth-Token", "X-THOTH-TOKEN"])
def test_토큰_헤더는_대소문자를_가리지_않는다(monkeypatch, name):
    # Function URL 이 소문자로 준다고 적혀 있으나, 틀리면 토큰이 조용히 안 걸린다.
    monkeypatch.setattr(contract, "TOKEN", "s3cret")
    r = lh.handler(ev("POST", "/translate",
                      json.dumps({"texts": ["hello"]}), {name: "s3cret"}))
    assert r["statusCode"] == 200


def test_토큰이_틀리면_401(monkeypatch):
    monkeypatch.setattr(contract, "TOKEN", "s3cret")
    r = lh.handler(ev("POST", "/translate",
                      json.dumps({"texts": ["hello"]}), {"x-thoth-token": "wrong"}))
    assert r["statusCode"] == 401


def test_본문이_깨져도_토큰을_먼저_본다(monkeypatch):
    # 인증 실패를 400 으로 내리면 토큰 없이도 본문 파싱 결과를 알려주게 된다.
    monkeypatch.setattr(contract, "TOKEN", "s3cret")
    assert lh.handler(ev("POST", "/translate", "{"))["statusCode"] == 401


# ── 본문 ─────────────────────────────────────────────────────────────────


def test_base64_본문을_푼다():
    raw = base64.b64encode(json.dumps({"texts": ["b64"]}).encode()).decode()
    r = lh.handler(ev("POST", "/translate", raw, b64=True))
    assert r["statusCode"] == 200 and body_of(r)["cached"] == [False]


def test_깨진_base64_는_invalid_json():
    r = lh.handler(ev("POST", "/translate", "!!!아님!!!", b64=True))
    assert r["statusCode"] == 400 and body_of(r)["detail"] == "invalid_json"


def test_없는_본문과_깨진_본문을_가른다():
    # 둘 다 400 이지만 원인이 다르다. 같이 적으면 로그를 보고 다른 것을 고친다.
    assert body_of(lh.handler(ev("POST", "/translate")))["detail"] == "body_not_object"
    assert body_of(lh.handler(ev("POST", "/translate", "{")))["detail"] == "invalid_json"


# ── 두 경로가 같은 답을 내는가 ───────────────────────────────────────────


@pytest.mark.parametrize("raw", [
    '{"texts":["hello world"]}',
    '{"texts":[]}',
    '{"texts":["a"],"target":"ja"}',
    '{"nope":1}',
    '{"texts":',
    '"문자열"',
])
def test_라우트와_람다가_같은_답을_낸다(raw):
    """★ **§68 의 약속을 여기서 지킨다.** 계약을 떼어 놓은 이유가 두 경로의
    답을 같게 하는 것이었고, 대조하지 않으면 약속이 문서에만 남는다.

    ★ 상태 코드와 에러 이름만이 아니라 `detail` 까지 본다. 원인을 다르게 적으면
      같은 입력에 다른 진단이 나가고, 그것은 §37 이 말한 틀린 원인이다.
    """
    cache._mem.clear(); guard._mem.clear()
    lam = lh.handler(ev("POST", "/translate", raw))
    cache._mem.clear(); guard._mem.clear()
    http = client.post("/translate", content=raw,
                       headers={"Content-Type": "application/json"})

    assert lam["statusCode"] == http.status_code
    a, b = body_of(lam), http.json()
    assert a.get("error") == b.get("error")
    assert a.get("detail") == b.get("detail")


def test_health_도_같은_답을_낸다():
    lam = body_of(lh.handler(ev("GET", "/health")))
    http = client.get("/health").json()
    assert lam == http
