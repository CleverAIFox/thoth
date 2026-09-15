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

from app import cache, contract, engine, guard
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


# ---------- 접근 토큰 ----------

def test_토큰이_비면_열린다():
    # 로컬 개발의 기본값이다. 토큰을 강제하면 워커를 띄울 때마다 값이 필요하다.
    assert contract.TOKEN == ""
    assert post(["hello world"]).status_code == 200


def test_토큰이_설정되면_없는_요청은_401(monkeypatch):
    monkeypatch.setattr(contract, "TOKEN", "s3cret")
    r = post(["hello world"])
    assert r.status_code == 401 and r.json()["error"] == "unauthorized"


def test_틀린_토큰도_401(monkeypatch):
    monkeypatch.setattr(contract, "TOKEN", "s3cret")
    r = client.post(
        "/translate",
        json={"texts": ["hello world"], "target": "ko"},
        headers={"X-Thoth-Token": "wrong"},
    )
    assert r.status_code == 401


def test_맞는_토큰은_통과한다(monkeypatch):
    monkeypatch.setattr(contract, "TOKEN", "s3cret")
    r = client.post(
        "/translate",
        json={"texts": ["hello world"], "target": "ko"},
        headers={"X-Thoth-Token": "s3cret"},
    )
    assert r.status_code == 200


def test_401_에도_CORS_헤더가_있다(monkeypatch):
    # 인증 실패가 브라우저 콘솔에 CORS 위반으로 보이면 원인을 찾지 못한다.
    monkeypatch.setattr(contract, "TOKEN", "s3cret")
    r = client.post(
        "/translate",
        json={"texts": ["hello world"], "target": "ko"},
        headers={"Origin": "https://www.udemy.com"},
    )
    assert r.status_code == 401
    assert r.headers.get("access-control-allow-origin")


def test_인증_없는_health_는_잔여를_싣지_않는다(monkeypatch):
    # 기동 여부는 누구에게나 답한다. 남의 상한이 얼마나 닳았는지는 아니다.
    monkeypatch.setattr(contract, "TOKEN", "s3cret")
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["auth"] is True
    assert "chars_used" not in body and "chars_remaining" not in body

    body = client.get("/health", headers={"X-Thoth-Token": "s3cret"}).json()
    assert "chars_used" in body


# ---------- 부분 응답 ----------

def test_상한을_넘어도_캐시_히트는_돌려준다(monkeypatch):
    # 히트는 이미 손에 있고 과금이 0 이다. 상한에 걸렸다고 감출 이유가 없다.
    post(["cached text here"])
    monkeypatch.setattr(guard, "MAX_CHARS", 1)
    r = post(["cached text here", "brand new text here"])
    assert r.status_code == 200
    body = r.json()
    assert body["partial"] == "quota_exceeded"
    assert body["translations"][0] is not None
    assert body["translations"][1] is None
    assert body["cached"] == [True, False]


def test_히트가_하나도_없으면_부분_응답이_아니라_429(monkeypatch):
    # 돌려줄 것이 없으면 200 으로 내릴 이유가 없다. 확장이 사유를 상태 코드로
    # 읽는 경로가 그대로 살아 있어야 한다.
    monkeypatch.setattr(guard, "MAX_CHARS", 1)
    assert post(["brand new text here"]).status_code == 429


def test_카운터가_죽어도_캐시_히트는_돌려준다(monkeypatch):
    post(["cached text here"])

    def dead(texts):
        raise guard.GuardUnavailable("NoCredentialsError")
    monkeypatch.setattr(guard, "reserve", dead)
    r = post(["cached text here", "brand new text here"])
    assert r.status_code == 200 and r.json()["partial"] == "guard_unavailable"


def test_너무_긴_텍스트도_부분_응답을_탄다(monkeypatch):
    post(["cached text here"])
    monkeypatch.setattr(guard, "MAX_TEXT", 10)
    r = post(["cached text here", "w" * 50])
    assert r.status_code == 200 and r.json()["partial"] == "too_long"


def test_엔진_실패는_부분_응답이_아니다(monkeypatch):
    # 엔진 실패는 일시적이라 재시도가 맞다. 200 으로 내리면 확장이 그 자리를
    # 영구 실패로 버린다. 가드 실패와 반대 방향이다.
    post(["cached text here"])

    def boom(ts):
        raise RuntimeError("nope")
    monkeypatch.setattr(engine, "translate_batch", boom)
    r = post(["cached text here", "brand new text here"])
    assert r.status_code == 502


def test_전부_히트면_partial_키가_없다():
    post(["cached text here"])
    assert "partial" not in post(["cached text here"]).json()


# ---------- 엔진 분기 ----------

def test_llm_배치는_엔진마다_다시_만들지_않는다(monkeypatch):
    # 용어집 선택 · 배치 규약 · 폴백은 이 도구의 성질이지 엔진의 성질이 아니다.
    # local 과 bedrock 이 같은 경로를 타는지 본다.
    seen = []

    def fake(text, system):
        seen.append(system)
        return "\n\n".join(f"§ {i}\n번역{i}" for i in range(2))

    for name, fn in (("local", "_ollama"), ("bedrock", "_converse")):
        seen.clear()
        monkeypatch.setattr(engine, "ENGINE", name)
        monkeypatch.setattr(engine, fn, fake)
        out = engine._raw_batch(["A shard stores records.", "The partition key differs."])
        assert out == ["번역0", "번역1"], name
        assert len(seen) == 1, name            # 배치 한 번. 개별 폴백이 아니다
        assert "레코드" in seen[0], name        # 용어집이 실렸다


def test_배치_파싱이_깨지면_개별_호출로_되돌린다(monkeypatch):
    # 1번 보기에 2번 번역을 붙이는 것은 없는 것보다 나쁘다(DECISIONS §1).
    calls = []

    def broken(text, system):
        calls.append(text)
        return "번호가 없는 응답" if len(calls) == 1 else "개별 번역"

    monkeypatch.setattr(engine, "ENGINE", "bedrock")
    monkeypatch.setattr(engine, "_converse", broken)
    out = engine._raw_batch(["first text", "second text"])
    assert out == ["개별 번역", "개별 번역"]
    assert len(calls) == 3                     # 배치 1 + 개별 2


def _fake_bedrock(monkeypatch, usage, metrics=None):
    """converse 응답을 흉내낸다. **실제 호출 형태만 흉내내고 값은 시험값이다.**"""
    seen = {}

    class C:
        def converse(self, **kw):
            seen.update(kw)
            r = {"output": {"message": {"content": [{"text": "§ 0\n번역0\n\n§ 1\n번역1"}]}}}
            if usage is not None:
                r["usage"] = usage
            if metrics is not None:
                r["metrics"] = metrics
            return r

    monkeypatch.setattr(engine, "_bedrock_client", lambda: C())
    return seen


def _usage_lines(caplog):
    import json as _json
    return [_json.loads(r.message.split(" ", 1)[1])
            for r in caplog.records if r.message.startswith("usage ")]


def test_토큰_사용량을_호출마다_남긴다(monkeypatch, caplog):
    # ★ 상한은 원문만 세고 과금은 입력 토큰으로 매겨져 두 수가 7배 갈린다
    #   (DECISIONS §78). 비용을 판단할 단위가 어딘가에 남아야 한다.
    #
    # ★ **이 검사는 줄의 내용만 본다.** `caplog` 가 레벨을 올리고 자기 핸들러를
    #   걸므로 배선이 없어도 통과한다 — 실제로 그렇게 통과하면서 로그가 한 줄도
    #   안 나가는 것을 못 봤다(§79). 배선은 `test_logging.py` 가 본다.
    import logging
    _fake_bedrock(monkeypatch, {"inputTokens": 1234, "outputTokens": 567},
                  {"latencyMs": 890})
    monkeypatch.setattr(engine, "ENGINE", "bedrock")
    caplog.set_level(logging.INFO, logger="thoth")

    engine._raw_batch(["A shard stores records.", "The partition key differs."])

    lines = _usage_lines(caplog)
    assert len(lines) == 1
    u = lines[0]
    assert u["in_tok"] == 1234 and u["out_tok"] == 567
    assert u["latency_ms"] == 890
    # 배치 크기를 함께 적지 않으면 총액은 알아도 교환비를 모른다(#45).
    assert u["n"] == 2
    # 프롬프트 머리를 따로 적는다. 오버헤드가 요청마다 다시 실린다.
    assert u["sys_chars"] > 0 and u["in_chars"] > 0


def test_usage_가_없으면_0_이_아니라_null_로_적는다(monkeypatch, caplog):
    # ★ 못 잰 것과 0 은 다르다(DECISIONS §59). 0 으로 채우면 합계가 조용히
    #   틀리고, 그 합계가 비용 판단의 근거가 된다.
    import logging
    _fake_bedrock(monkeypatch, None)
    monkeypatch.setattr(engine, "ENGINE", "bedrock")
    caplog.set_level(logging.INFO, logger="thoth")

    out = engine._raw_batch(["A shard stores records.", "The partition key differs."])

    assert out == ["번역0", "번역1"]          # 계기가 없어도 번역은 돈다
    u = _usage_lines(caplog)[0]
    assert u["in_tok"] is None and u["out_tok"] is None


def test_모르는_엔진은_조용히_넘어가지_않는다(monkeypatch):
    monkeypatch.setattr(engine, "ENGINE", "gpt5")
    with pytest.raises(NotImplementedError):
        engine._raw_batch(["hello"])


# ---------- 항등 용어(영어 유지) ----------

def test_항등_항목은_번역_목록에_섞이지_않는다():
    # ★ `Data Catalog -> Data Catalog` 는 번역 지시 형식 그대로라, 나머지와
    #   같은 자리에 놓이면 무엇을 하라는 것인지 흐려진다(DECISIONS §30).
    from app import glossary

    p = glossary.as_prompt({"bucket": "버킷", "data catalog": "Data Catalog"})
    assert "bucket -> 버킷" in p
    assert "Data Catalog -> Data Catalog" not in p
    assert "data catalog -> Data Catalog" not in p
    assert "Data Catalog" in p.split(glossary.KEEP_HEADER)[1]


def test_항등_항목에_포함된_용어는_번역_목록에서_빠진다():
    """★ `catalog -> 카탈로그` 와 `Data Catalog 유지` 를 나란히 실으면
    프롬프트 자체가 모순이고 모델은 둘 중 하나를 고른다. 2026-09-13 실측에서
    `DynamoDB Streams` 는 이겼고 `Data Catalog` 는 졌다 — 같은 모순인데
    결과가 갈렸으므로 남겨 두면 어느 쪽이 나올지 정할 수 없다(DECISIONS §32).

    ★ `check()` 가 이미 같은 일을 한다. 검사만 그렇게 하고 프롬프트는 그러지
      않았다. 같은 질문에 두 답이 있으면 하나는 틀렸다(§28 · §30 의 재발).
    """
    from app import glossary

    p = glossary.as_prompt({"catalog": "카탈로그", "bucket": "버킷",
                            "data catalog": "Data Catalog"})
    assert "catalog -> 카탈로그" not in p     # 항등 항목 안에 들어 있다
    assert "bucket -> 버킷" in p              # 관계없는 용어는 남는다
    assert "Data Catalog" in p


def test_복수형_항등_항목도_짧은_용어를_덮는다():
    # DynamoDB Streams 의 stream. 굴절형을 보지 않으면 모순이 남는다(§28).
    from app import glossary

    p = glossary.as_prompt({"stream": "스트림", "record": "레코드",
                            "dynamodb streams": "DynamoDB Streams"})
    assert "stream -> 스트림" not in p
    assert "record -> 레코드" in p


def test_항등_판정은_대소문자를_무시한다():
    from app import glossary

    assert glossary.is_keep("data catalog", "Data Catalog")
    assert glossary.is_keep("EMR", "emr")
    assert not glossary.is_keep("catalog", "카탈로그")


def test_항등_항목만_있어도_번역_절은_나오지_않는다():
    from app import glossary

    p = glossary.as_prompt({"data catalog": "Data Catalog"})
    assert glossary.TRANS_HEADER not in p
    assert glossary.KEEP_HEADER in p


def test_용어가_없으면_빈_프롬프트다():
    from app import glossary

    assert glossary.as_prompt({}) == ""


def test_고유명사가_원문에_있으면_프롬프트에_실린다():
    # 규칙 1 의 예시는 모델이 목록으로 취급해 거기 없는 이름을 놓친다.
    # 예시가 아니라 데이터로 싣는다.
    from app import glossary

    _, terms = glossary.match([
        "The Glue crawler updates the Data Catalog with every new partition "
        "of the bucket so that the schema stays current for each object."])
    assert terms.get("data catalog") == "Data Catalog"
    assert "Data Catalog" in glossary.as_prompt(terms)


def test_용어집_키는_소문자다():
    # ★ _hits 가 blob.lower() 에서 찾는다. 대문자 키는 영영 매치되지 않으므로
    #   등재해도 조용히 아무것도 하지 않는다(DECISIONS §21).
    from app import glossary

    for book in glossary._load().values():
        for en in book:
            assert en == en.lower(), en


def test_ollama_타임아웃이_실측보다_길다():
    # ★ 실측 배치가 335초까지 갔다. 상한이 그보다 짧으면 느린 날에 번역이
    #   아니라 타임아웃이 결과가 된다.
    from app import engine

    assert engine.OLLAMA_TIMEOUT >= 700


# ---------- 계약 직접 호출 (DECISIONS §68) ----------
#
# ★ **뗀 덕에 생긴 자리다.** 전에는 검증도 토큰 비교도 `TestClient` 를 통해서만
#   닿았다. 배포본은 FastAPI 를 타지 않으므로, 프레임워크 없이 부르는 경로가
#   검사되지 않으면 Lambda 쪽이 통째로 사각이 된다.


@pytest.mark.parametrize("payload,name", [
    ("문자열", "bad_request"),
    (["리스트"], "bad_request"),
    ({}, "bad_request"),
    ({"texts": []}, "bad_request"),
    ({"texts": "hello"}, "bad_request"),
    ({"texts": ["a", 3]}, "bad_request"),
    ({"texts": ["a"] * (contract.MAX_TEXTS + 1)}, "bad_request"),
    ({"texts": ["a"], "target": 3}, "bad_request"),
    ({"texts": ["a"], "target": "ja"}, "unsupported_target"),
])
def test_검증이_모양과_내용을_함께_본다(payload, name):
    bad = contract.validate(payload)
    assert bad and bad[0] == name


def test_검증을_통과하는_최소_본문():
    assert contract.validate({"texts": ["hello"]}) is None
    assert contract.validate({"texts": ["hello"], "target": "ko"}) is None


def test_상한_경계는_통과한다():
    assert contract.validate({"texts": ["a"] * contract.MAX_TEXTS}) is None


def test_토큰이_비면_헤더가_없어도_통과(monkeypatch):
    monkeypatch.setattr(contract, "TOKEN", "")
    assert contract.authorized(None) and contract.authorized("아무거나")


def test_토큰이_있으면_같을_때만_통과(monkeypatch):
    monkeypatch.setattr(contract, "TOKEN", "s3cret")
    assert contract.authorized("s3cret")
    assert not contract.authorized("wrong")
    assert not contract.authorized(None)


def test_프레임워크_없이_번역이_돈다():
    r = contract.translate({"texts": ["hello world"]}, None)
    assert r.status == 200
    assert len(r.body["translations"]) == 1 and r.body["cached"] == [False]


def test_결과는_상태와_본문_두_칸이다():
    r = contract.err(429, "quota_exceeded")
    assert (r.status, r.body["error"]) == (429, "quota_exceeded")


@pytest.mark.parametrize("payload", [
    None, "문자열", {}, {"texts": []}, {"texts": ["a"], "target": "ja"},
    {"texts": ["hello world"]},
])
def test_라우트와_직접_호출이_같은_상태를_낸다(payload):
    """★ **이 검사가 두 경로를 묶는다.** 배포본은 FastAPI 를 타지 않으므로,
    같은 입력에 두 답이 나오기 시작해도 HTTP 쪽만 보면 모른다. 계약을 떼어
    놓고 양쪽을 대조하지 않으면 떼어 놓은 의미가 없다.
    """
    cache._mem.clear(); guard._mem.clear()
    direct = contract.translate(payload, None)
    cache._mem.clear(); guard._mem.clear()
    via_http = client.post("/translate", json=payload)
    assert direct.status == via_http.status_code
    assert direct.body.get("error") == via_http.json().get("error")
