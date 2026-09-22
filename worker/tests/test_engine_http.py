"""`ENGINE=http` — 자체 모델을 끼우는 자리(DECISIONS §109).

★ 가짜 번역 서버를 실제 소켓으로 띄운다. `urlopen` 을 흉내내면 헤더 · 상태 코드 ·
  JSON 직렬화가 검사 밖으로 빠진다 — 끼울 때 깨지는 자리가 바로 거기다.
"""
import importlib.util
import json
import os
import pathlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ["ENGINE"] = "echo"
os.environ["CACHE"] = "memory"

import pytest
from fastapi.testclient import TestClient

from app import cache, engine, guard, preflight
from app.main import app

_spec = importlib.util.spec_from_file_location(
    "engine_conformance",
    pathlib.Path(__file__).resolve().parents[2] / "tools/engine_conformance.py")
conf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(conf)


class Stub:
    """행동을 바꿔 가며 계약 위반을 흉내낸다."""
    mode = "good"
    model = "seshat-test"
    token = ""
    seen: list = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, status, body):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _authed(self):
        return not Stub.token or self.headers.get("Authorization") == f"Bearer {Stub.token}"

    def do_GET(self):
        if self.path != "/health":
            return self._send(404, {})
        if not self._authed():
            return self._send(401, {})
        body = {"status": "ok"} if Stub.mode == "no_model" else {"status": "ok", "model": Stub.model}
        self._send(200, body)

    def do_POST(self):
        if not self._authed():
            return self._send(401, {})
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Stub.seen.append(req)
        texts = req["texts"]
        if Stub.mode == "short":
            return self._send(200, {"translations": [f"번역 {t}" for t in texts[:-1]]})
        if Stub.mode == "not_str":
            return self._send(200, {"translations": [1 for _ in texts]})
        if Stub.mode == "reversed":
            return self._send(200, {"translations": [f"번역 {t}" for t in reversed(texts)]})
        self._send(200, {"translations": [f"  번역 {t}  " for t in texts], "model": Stub.model})


@pytest.fixture(scope="module")
def server():
    s = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{s.server_address[1]}"
    s.shutdown()


@pytest.fixture(autouse=True)
def reset(monkeypatch, server):
    Stub.mode, Stub.token, Stub.model, Stub.seen = "good", "", "seshat-test", []
    cache._mem.clear()
    guard._mem.clear()
    monkeypatch.setattr(engine, "ENGINE", "http")
    monkeypatch.setattr(engine, "HTTP_URL", server)
    monkeypatch.setattr(engine, "HTTP_TOKEN", "")
    monkeypatch.setattr(engine, "HTTP_MODEL", "seshat-test")


# ---------- 엔진 ----------

def test_번역을_받아_후처리를_건다():
    ko, raw = engine.translate_detail(["What is a shard?", "Pick one."])
    assert raw == ["번역 What is a shard?", "번역 Pick one."]   # 앞뒤 공백은 벗긴다
    assert len(ko) == 2


def test_프롬프트가_아니라_용어집만_싣는다():
    engine._raw_batch(["A shard stores records.", "The partition key differs."])
    req = Stub.seen[-1]
    assert set(req) == {"texts", "source", "target", "terms"}
    assert req["terms"].get("record") == "레코드"
    assert "Translate English" not in json.dumps(req)


def test_길이가_다르면_계약_위반이다():
    Stub.mode = "short"
    with pytest.raises(engine.EngineContractError):
        engine._raw_batch(["a", "b"])


def test_문자열이_아니면_계약_위반이다():
    Stub.mode = "not_str"
    with pytest.raises(engine.EngineContractError):
        engine._raw_batch(["a"])


def test_토큰을_베어러로_싣는다(monkeypatch):
    Stub.token = "s3cret"
    with pytest.raises(Exception):
        engine._raw_batch(["a"])               # 토큰 없이 401
    monkeypatch.setattr(engine, "HTTP_TOKEN", "s3cret")
    assert engine._raw_batch(["a"]) == ["번역 a"]


def test_모델명은_선언을_쓴다(monkeypatch):
    assert engine.model_name() == "seshat-test"
    monkeypatch.setattr(engine, "HTTP_MODEL", "")
    assert engine.model_name() == "http:undeclared"


def test_워커_계약이_그대로_돈다():
    # ★ 확장이 보는 것은 워커다. 엔진을 바꿔도 이 응답 모양은 같아야 한다.
    r = TestClient(app).post("/translate", json={"texts": ["What is a shard?"], "target": "ko"})
    assert r.status_code == 200
    assert r.json()["translations"][0].startswith("번역")


def test_서버가_계약을_어기면_502_다():
    Stub.mode = "short"
    r = TestClient(app).post("/translate", json={"texts": ["a b c d", "e f g h"], "target": "ko"})
    assert r.status_code == 502
    assert r.json()["error"] == "engine_failed"


# ---------- 전검사 ----------

def test_전검사가_통과한다():
    f = preflight.run("http")
    assert f.ok and f.code == "ok", f


def test_선언과_서버가_다르면_막는다(monkeypatch):
    monkeypatch.setattr(engine, "HTTP_MODEL", "seshat-old")
    f = preflight.run("http")
    assert not f.ok and f.code == "model_mismatch"


def test_선언이_없으면_막지_않고_알린다(monkeypatch):
    monkeypatch.setattr(engine, "HTTP_MODEL", "")
    f = preflight.run("http")
    assert f.ok and f.code == "undeclared"
    assert f.hints == ("HTTP_MODEL=seshat-test",)


def test_health_에_모델이_없으면_실패다():
    Stub.mode = "no_model"
    assert preflight.run("http").code == "http_no_model"


def test_서버가_없으면_http_down(monkeypatch):
    monkeypatch.setattr(engine, "HTTP_URL", "http://127.0.0.1:1")
    assert preflight.run("http").code == "http_down"


def test_cheap_이면_나가지_않는다():
    assert preflight.run("http", remote=False).code == "not_measured"


# ---------- 적합성 도구 ----------

def test_적합성_도구가_계약을_지키는_서버를_통과시킨다(server):
    res = conf.run(server, model="seshat-test")
    assert all(ok for _, ok, _ in res), res
    assert {n for n, _, _ in res} == {"health", "single", "batch", "order", "terms", "newline"}


def test_적합성_도구가_순서_뒤집힘을_잡는다(server):
    Stub.mode = "reversed"
    res = dict((n, ok) for n, ok, _ in conf.run(server))
    assert res["batch"] and not res["order"]


def test_적합성_도구가_길이_위반을_잡는다(server):
    Stub.mode = "short"
    res = dict((n, ok) for n, ok, _ in conf.run(server))
    assert not res["batch"]


def test_적합성_도구가_토큰을_본다(server):
    Stub.token = "t"
    res = dict((n, ok) for n, ok, _ in conf.run(server, token="t"))
    assert res["auth"] and res["single"]
