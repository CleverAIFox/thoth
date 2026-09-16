"""쌍 로그. **학습 데이터가 실제로 나가는 모양**을 본다(PLAN #23).

★ **배선을 검사가 만들지 않는다**(§79). `test_logging.py` 와 같이 레벨도 핸들러도
  건드리지 않고 패키지가 놓은 핸들러의 스트림만 바꿔 읽는다.

★ **줄을 문자열이 아니라 JSON 으로 읽는다.** Firehose 가 그렇게 읽는다. 접두사
  하나가 붙으면 여기서 `json.loads` 가 죽는다 — 그것이 배포본에서 Parquet 변환이
  전부 실패하는 것과 같은 사건이다.

★ **HCL 과 파이썬을 대조한다.** 열 목록과 필터 판별자는 두 언어에 따로 산다.
"""
import io
import json
import logging
import os
import pathlib
import re

os.environ["ENGINE"] = "echo"
os.environ["CACHE"] = "memory"

import pytest  # noqa: E402

from app import cache, contract, engine, guard, pairs  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
TF = ROOT / "infra/analytics.tf"


@pytest.fixture(autouse=True)
def clean():
    cache._mem.clear()
    guard._mem.clear()
    yield


def capture(monkeypatch) -> io.StringIO:
    buf = io.StringIO()
    monkeypatch.setattr(logging.getLogger("thoth.pair").handlers[0], "stream", buf)
    return buf


def lines(buf: io.StringIO) -> list[dict]:
    return [json.loads(x) for x in buf.getvalue().splitlines() if x.strip()]


def call(texts, source=None):
    body = {"texts": texts, "target": "ko"}
    if source is not None:
        body["source"] = source
    return contract.translate(body, None)


# ---------- 배선 ----------

def test_쌍_줄은_접두사가_없는_JSON_이다(monkeypatch):
    buf = capture(monkeypatch)
    assert call(["A shard stores records here."]).status == 200
    out = buf.getvalue().splitlines()
    assert len(out) == 1
    assert out[0].startswith("{"), "접두사가 붙으면 Firehose 가 JSON 으로 못 읽는다"
    assert json.loads(out[0])["k"] == pairs.KIND


def test_쌍_줄이_부모_핸들러로_두_번_나가지_않는다(monkeypatch):
    parent = io.StringIO()
    monkeypatch.setattr(logging.getLogger("thoth").handlers[0], "stream", parent)
    capture(monkeypatch)
    call(["Only once please here."])
    assert '"k":"pair"' not in parent.getvalue()
    assert logging.getLogger("thoth.pair").propagate is False


# ---------- 무엇이 실리는가 ----------

def test_모델_출력과_후처리_결과를_둘_다_싣는다(monkeypatch):
    # ★ 후처리가 고친 자리가 모델이 틀린 자리다. 둘이 같으면 학습 신호가 없다.
    monkeypatch.setattr(engine, "_raw_batch", lambda ts: ["확인하세요" for _ in ts])
    buf = capture(monkeypatch)
    call(["Check the settings now."])
    (rec,) = lines(buf)
    assert rec["raw"] == "확인하세요"
    assert rec["ko"] == "확인합니다"
    assert rec["h"] == cache.key("Check the settings now.")


def test_열이_스키마와_같은_순서다(monkeypatch):
    buf = capture(monkeypatch)
    call(["Column order matters here."])
    (rec,) = lines(buf)
    assert list(rec) == [c for c, _ in pairs.COLUMNS]
    assert rec["v"] == pairs.SCHEMA


def test_지문은_벤치와_같은_계산이다(monkeypatch):
    # 기준선과 운영 로그를 한 조건으로 묶는 열이다.
    buf = capture(monkeypatch)
    call(["Fingerprint joins baseline."])
    (rec,) = lines(buf)
    assert rec["prompt"] == engine.prompt_fingerprint()
    assert rec["engine"] == "echo" and rec["model"] == "echo"


def test_캐시_히트는_적지_않는다(monkeypatch):
    call(["Seen before text here."])
    buf = capture(monkeypatch)
    call(["Seen before text here."])
    assert buf.getvalue() == "", "학습 데이터에 중복이 쌓인다"


def test_같은_요청_안의_중복도_한_번이다(monkeypatch):
    buf = capture(monkeypatch)
    call(["Twice in one batch.", "Twice in one batch."])
    assert len(lines(buf)) == 1


def test_엔진이_실패하면_적지_않는다(monkeypatch):
    def boom(ts):
        raise RuntimeError("nope")
    monkeypatch.setattr(engine, "translate_detail", boom)
    buf = capture(monkeypatch)
    assert call(["Engine fails here."]).status == 502
    assert buf.getvalue() == ""


def test_쌍_로그가_죽어도_번역은_나간다(monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("log down")
    monkeypatch.setattr(pairs, "records", boom)
    r = call(["Translation still ships."])
    assert r.status == 200 and r.body["translations"][0]


# ---------- source ----------

def test_source_를_열로_싣는다(monkeypatch):
    buf = capture(monkeypatch)
    call(["Site column lands."], source={"site": "www.udemy.com", "adapter": "udemy"})
    (rec,) = lines(buf)
    assert (rec["site"], rec["adapter"]) == ("www.udemy.com", "udemy")


def test_source_가_없어도_번역된다(monkeypatch):
    # 옛 확장 · 벤치 · smoke 는 보내지 않는다.
    buf = capture(monkeypatch)
    assert call(["No source given."]).status == 200
    (rec,) = lines(buf)
    assert rec["site"] is None and rec["adapter"] is None


@pytest.mark.parametrize("source, detail", [
    ("udemy", "source_not_object"),
    ({"url": "https://x.test/course/123"}, "source_unknown_url"),
    ({"site": 3}, "source_bad_site"),
    ({"site": "a" * 254}, "source_bad_site"),
    ({"adapter": "x" * 33}, "source_bad_adapter"),
])
def test_source_모양이_틀리면_400(source, detail):
    r = call(["Bad source shape."], source=source)
    assert r.status == 400 and r.body["detail"] == detail


# ---------- HCL 대조 ----------

def test_Glue_열이_COLUMNS_와_같다():
    text = TF.read_text(encoding="utf-8")
    block = text[text.index("pairs_columns = ["):]
    block = block[: block.index("\n  ]")]
    cols = re.findall(r'name = "(\w+)", type = "(\w+)"', block)
    assert tuple(cols) == pairs.COLUMNS


def test_구독_필터가_KIND_를_본다():
    text = TF.read_text(encoding="utf-8")
    m = re.search(r'filter_pattern\s*=\s*"\{ \$\.k = \\"(\w+)\\" \}"', text)
    assert m, "필터 패턴을 못 찾았다 — 모양이 바뀌었으면 이 검사도 고친다"
    assert m.group(1) == pairs.KIND
