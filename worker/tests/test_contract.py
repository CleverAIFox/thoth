"""워커 계약과 비용 가드.

★ 이전 판은 전부 CACHE=memory 로만 돌았다. 실제 기본값은 file 이고, 그 경로가
  guard 에서 DynamoDB 로 새는 결함을 테스트가 통째로 가리고 있었다
  (DECISIONS §10). 기본값과 다른 설정으로만 검증하지 않는다.
"""
import os

# 계약 테스트는 엔진·백엔드와 무관하다. 셸에 ENGINE 이 export 돼 있어도
# 여기서 강제로 덮는다(setdefault 로는 못 이긴다).
os.environ["ENGINE"] = "echo"
os.environ["CACHE"] = "memory"

import pytest
from fastapi.testclient import TestClient

from app import cache, engine, guard
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean():
    cache._mem.clear()
    guard._mem.clear()
    yield


def post(texts, target="ko"):
    return client.post("/translate", json={"texts": texts, "target": target})


# ---------- 계약 ----------

def test_길이가_보존된다():
    r = post(["a" * 30, "b" * 30, "c" * 30])
    assert r.status_code == 200
    assert len(r.json()["translations"]) == 3


def test_두번째_호출은_캐시_히트다():
    post(["hello world"])
    assert post(["hello world"]).json()["cached"] == [True]


def test_지원하지_않는_대상언어는_400():
    r = post(["hello"], target="ja")
    assert r.status_code == 400 and r.json()["error"] == "unsupported_target"


def test_엔진이_짧게_돌려주면_502_다(monkeypatch):
    # zip 은 짧은 쪽에 맞춰 조용히 자른다. 잘린 채로 나가면 확장이 1번 보기에
    # 2번 번역을 붙인다. 없는 것보다 나쁘다(DECISIONS §1).
    monkeypatch.setattr(engine, "translate_batch", lambda ts: ["하나만"])
    r = post(["first text here", "second text here"])
    assert r.status_code == 502 and r.json()["detail"] == "length_mismatch"


def test_엔진_예외는_502_로_감싼다(monkeypatch):
    def boom(ts):
        raise RuntimeError("nope")
    monkeypatch.setattr(engine, "translate_batch", boom)
    r = post(["hello world"])
    assert r.status_code == 502 and r.json()["error"] == "engine_failed"


def test_에러응답에도_CORS_헤더가_있다(monkeypatch):
    # 예외가 미들웨어를 건너뛰면 브라우저는 원인을 CORS 로 오인한다.
    monkeypatch.setattr(engine, "translate_batch", lambda ts: ["짧다"])
    r = client.post(
        "/translate",
        json={"texts": ["a" * 25, "b" * 25], "target": "ko"},
        headers={"Origin": "https://www.udemy.com"},
    )
    assert r.status_code == 502
    assert r.headers.get("access-control-allow-origin")


# ---------- 비용 가드 ----------

def test_캐시_히트는_문자를_소모하지_않는다():
    post(["x" * 100])
    before = guard.used()
    post(["x" * 100])
    assert guard.used() == before


def test_한_배치의_중복은_한_번만_과금된다():
    post(["same text here"] * 5)
    assert guard.used() == len("same text here")


def test_상한을_넘으면_429(monkeypatch):
    monkeypatch.setattr(guard, "MAX_CHARS", 50)
    r = post(["y" * 40, "z" * 40])
    assert r.status_code == 429 and r.json()["error"] == "quota_exceeded"


def test_누적이_상한에_닿으면_429(monkeypatch):
    # 단일 요청이 아니라 '누적' 이 걸리는지. 이전 판은 이걸 안 봤다.
    monkeypatch.setattr(guard, "MAX_CHARS", 100)
    assert post(["a" * 60]).status_code == 200
    assert post(["b" * 60]).status_code == 429


def test_너무_긴_텍스트는_413(monkeypatch):
    monkeypatch.setattr(guard, "MAX_TEXT", 10)
    assert post(["w" * 50]).status_code == 413


def test_카운터_저장소가_죽으면_503_이다(monkeypatch):
    # 세지 못하는 상태로 번역하면 상한이 없는 것과 같다. 열지 않고 닫는다.
    def dead(texts):
        raise guard.GuardUnavailable("NoCredentialsError")
    monkeypatch.setattr(guard, "reserve", dead)
    r = post(["hello world"])
    assert r.status_code == 503 and r.json()["error"] == "guard_unavailable"


def test_guard_백엔드는_ddb_일_때만_원격이다():
    # CACHE 는 memory · file · ddb 세 값이다. 'memory 가 아니면 DynamoDB' 로
    # 분기하면 CACHE=file 에서 카운터만 AWS 로 샌다(DECISIONS §10).
    assert guard.REMOTE is (guard.MODE == "ddb")


def test_file_모드는_카운터가_재시작을_견딘다(tmp_path, monkeypatch):
    monkeypatch.setattr(guard, "MODE", "file")
    monkeypatch.setattr(guard, "REMOTE", False)
    monkeypatch.setattr(guard, "FILE", tmp_path / "quota.json")
    monkeypatch.setattr(guard, "_loaded", False)
    guard._mem.clear()
    guard.reserve(["x" * 30])

    guard._mem.clear()                      # 워커 재시작
    monkeypatch.setattr(guard, "_loaded", False)
    assert guard.used() == 30


# ---------- 용어집 ----------

def test_용어집은_원문이_고른다():
    from app import glossary

    name, terms = glossary.match(["A shard stores records with a partition key."])
    assert name == "aws"
    assert terms["record"] == "레코드"

    name, terms = glossary.match(["The cat sat on the mat and slept all day."])
    assert name is None and terms == {}


def test_평범한_낱말_몇_개로는_도메인이_되지_않는다():
    # object · policy · role · node 는 등재어지만 AWS 신호가 아니다.
    from app import glossary

    name, _ = glossary.match(
        ["The policy role of the node was reviewed by the object owner."]
    )
    assert name is None


def test_여러_낱말_용어는_강한_신호다():
    from app import glossary

    name, _ = glossary.match(["The retention period and the partition key differ."])
    assert name == "aws"


def test_맞은_용어만_프롬프트에_실린다():
    from app import glossary

    _, terms = glossary.match(["A shard stores records with a partition key."])
    prompt = glossary.as_prompt(terms)
    assert "레코드" in prompt
    assert "장애 조치" not in prompt      # failover 는 원문에 없다
