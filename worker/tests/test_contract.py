"""워커 계약과 비용 가드. 로컬(memory) 모드에서 검증한다."""
import os

# 계약 테스트는 엔진·백엔드와 무관하다. 셸에 ENGINE 이 export 돼 있어도
# 여기서 강제로 덮는다(setdefault 로는 못 이긴다).
os.environ["ENGINE"] = "echo"
os.environ["CACHE"] = "memory"

import pytest
from fastapi.testclient import TestClient

from app import cache, guard
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean():
    cache._mem.clear()
    guard._mem.clear()
    yield


def post(texts):
    return client.post("/translate", json={"texts": texts, "target": "ko"})


def test_길이가_보존된다():
    r = post(["a" * 30, "b" * 30, "c" * 30])
    assert r.status_code == 200
    assert len(r.json()["translations"]) == 3


def test_두번째_호출은_캐시_히트다():
    post(["hello world"])
    r = post(["hello world"])
    assert r.json()["cached"] == [True]


def test_캐시_히트는_문자를_소모하지_않는다():
    post(["x" * 100])
    before = guard.used()
    post(["x" * 100])
    assert guard.used() == before


def test_한_배치의_중복은_한_번만_과금된다():
    post(["same text here"] * 5)
    assert guard.used() == len("same text here")


def test_상한을_넘으면_429():
    guard.MAX_CHARS = 50
    r = post(["y" * 40, "z" * 40])
    assert r.status_code == 429
    assert r.json()["error"] == "quota_exceeded"
    guard.MAX_CHARS = int(os.environ.get("MAX_CHARS_PER_MONTH", "2000000"))


def test_너무_긴_텍스트는_413():
    guard.MAX_TEXT = 10
    r = post(["w" * 50])
    assert r.status_code == 413
    guard.MAX_TEXT = int(os.environ.get("MAX_TEXT_LEN", "5000"))


def test_용어집은_원문이_고른다():
    from app import glossary

    name, terms = glossary.match(["A shard stores records with a partition key."])
    assert name == "aws"
    assert terms["record"] == "레코드"

    # 관련 없는 원문에는 어떤 용어집도 걸리지 않는다.
    name, terms = glossary.match(["The cat sat on the mat and slept all day."])
    assert name is None and terms == {}


def test_맞은_용어만_프롬프트에_실린다():
    from app import glossary

    _, terms = glossary.match(["A shard stores records with a partition key."])
    prompt = glossary.as_prompt(terms)
    assert "레코드" in prompt
    assert "장애 조치" not in prompt      # failover 는 원문에 없다
