"""bench_golden 의 불변식 검사를 검사한다.

★ 검사도 코드이고 결함이 있다. 하루에 네 번 검사가 틀렸다(DECISIONS §21).
  일부러 위반을 만들어 잡히는지, 정상을 넣어 안 잡히는지 양쪽을 본다.
"""
import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "bench", pathlib.Path(__file__).resolve().parents[2] / "tools/bench_golden.py")
bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bench)

BOOK = {"record": "레코드", "consumer": "컨슈머",
        "consumer application": "컨슈머 애플리케이션", "catalog": "카탈로그"}


def unit(text, **kw):
    return {"text": text, "ratio_max": 0.75, "ratio_min": 0.30, **kw}


def test_정상은_통과한다():
    u = unit("The stream retains records for 168 hours in total here.",
             keep=[], terms=["record"])
    assert bench.check(u, "스트림은 레코드를 168시간 보관합니다.", BOOK) == []


def test_의문형_합니다체를_위반으로_보지_않는다():
    # 후처리가 만들어 내는 형태다. 검사가 이것을 잡으면 스스로를 부정한다.
    u = unit("Which condition must be confirmed?", keep=[], terms=[])
    assert bench.check(u, "어떤 조건을 확인해야 합니까?", BOOK) == []


def test_해요체는_잡는다():
    u = unit("Confirm the checkpoint position now please.", keep=[], terms=[])
    assert any("합니다체" in b for b in bench.check(u, "체크포인트를 확인하세요.", BOOK))


def test_원문에_없는_용어는_보지_않는다():
    u = unit("The shard count matches throughput.", keep=[], terms=["record"])
    assert not any("term" in b for b in bench.check(u, "샤드 수가 처리량과 맞습니다.", BOOK))


def test_긴_용어에_포함된_짧은_용어는_빼고_본다():
    u = unit("Every consumer application has checkpointed past the record.",
             keep=[], terms=["consumer", "consumer application"])
    ko = "모든 컨슈머 애플리케이션이 레코드를 지나 체크포인트했습니다."
    assert not any("term" in b for b in bench.check(u, ko, BOOK))


def test_길이가_과하면_덧붙임으로_잡는다():
    u = unit("Short source here.", keep=[], terms=[])
    bad = bench.check(u, "원문보다 훨씬 길게 늘어난 번역문을 여기에 넣습니다.", BOOK)
    assert any("덧붙임" in b for b in bad)


def test_길이가_모자라면_누락으로_잡는다():
    u = unit("A" * 200 + " records are retained for a long period of time.",
             keep=[], terms=[])
    assert any("누락" in b for b in bench.check(u, "짧습니다.", BOOK))


def test_물음표가_사라지면_잡는다():
    u = unit("Which condition must be confirmed?", keep=[], terms=[])
    assert any("물음표" in b for b in bench.check(u, "조건을 확인해야 합니다.", BOOK))


def test_keep_토큰이_번역되면_잡는다():
    u = unit("A Glue crawler populates the Data Catalog nightly here now.",
             keep=["Data Catalog"], terms=[])
    ko = "Glue 크롤러가 매일 밤 데이터 카탈로그를 채웁니다."
    assert any("keep" in b for b in bench.check(u, ko, BOOK))


def test_한글이_없으면_잡는다():
    u = unit("The stream retains records.", keep=[], terms=[])
    assert any("한글" in b for b in bench.check(u, "[KO] The stream retains records.", BOOK))


# ---------- 웜업 ----------

def test_웜업_문장은_매번_다르다(monkeypatch):
    # ★ 고정 문장이면 두 번째 실행부터 캐시 히트라 모델을 태우지 않는다.
    #   웜업이 조용히 아무것도 하지 않게 되고, 통과는 그것을 알려주지 않는다
    #   (DECISIONS §21).
    seen = []

    def fake(url, texts, timeout):
        seen.append(texts[0])
        return ["번역", 1.0]

    monkeypatch.setattr(bench, "translate", fake)
    for _ in range(5):
        bench.warmup("http://x", 10)
    assert len(set(seen)) == 5


def test_웜업은_골든셋_문장을_쓰지_않는다(monkeypatch):
    # 골든셋 문장을 태우면 그 문장이 캐시에 올라가 본 측정이 히트가 된다.
    # 캐시를 비우고 재는 규약(MASTER §11-4)이 웜업 때문에 무효가 된다.
    import json
    import pathlib
    cases = json.loads(
        (pathlib.Path(bench.__file__).resolve().parents[1]
         / "worker/tests/golden/cases.json").read_text(encoding="utf-8"))
    golden = {u["text"] for q in cases for u in q["units"]}

    seen = []
    monkeypatch.setattr(bench, "translate",
                        lambda url, texts, timeout: (seen.append(texts[0]), (["ko"], 1.0))[1])
    bench.warmup("http://x", 10)
    assert seen[0] not in golden


def test_웜업은_잰_시간을_돌려준다(monkeypatch):
    monkeypatch.setattr(bench, "translate",
                        lambda url, texts, timeout: (["ko"], 42.5))
    assert bench.warmup("http://x", 10) == 42.5


# ---------- 골든셋 구조 ----------
#
# ★ 케이스는 손으로 쓴다. 문항이 늘 때마다 사람이 규약을 기억해서 지키는
#   구조이고, 그 기억은 세션이 바뀌면 사라진다(DECISIONS §9). 여기서 잡는다.

import json as _json
import pathlib as _pathlib

_GOLDEN = (_pathlib.Path(bench.__file__).resolve().parents[1]
           / "worker/tests/golden/cases.json")
_CASES = _json.loads(_GOLDEN.read_text(encoding="utf-8"))
_UNITS = [u for q in _CASES for u in q["units"]]

# worker/tests/golden/README.md 의 실측 분포. 자릿수를 보는 것이지
# 중앙값에 맞추는 것이 아니다 — 표본이 문항 하나다.
_SHAPE = {"prompt": (400, 520), "choice": (130, 180), "explain": (350, 500)}


def test_문항은_아홉_유닛이다():
    # 낱개로 늘어놓으면 배치 번역의 용어 일관성을 잴 수 없다.
    for q in _CASES:
        assert len(q["units"]) == 9, q["qid"]


def test_문항_구성은_문제하나_보기넷_해설넷이다():
    for q in _CASES:
        kinds = [u["kind"] for u in q["units"]]
        assert kinds.count("prompt") == 1, q["qid"]
        assert kinds.count("choice") == 4, q["qid"]
        assert kinds.count("explain") == 4, q["qid"]


def test_id_가_유일하다():
    ids = [u["id"] for u in _UNITS]
    assert len(ids) == len(set(ids))
    qids = [q["qid"] for q in _CASES]
    assert len(qids) == len(set(qids))


def test_물음표는_문제에만_있다():
    # 환각(모델이 번역 뒤에 답을 이어 붙임)이 나오는 자리가 거기다.
    # 보기나 해설에 물음표가 있으면 그 검사가 엉뚱한 유닛에서 돈다.
    for u in _UNITS:
        if u["kind"] == "prompt":
            assert u["text"].rstrip().endswith("?"), u["id"]
        else:
            assert "?" not in u["text"], u["id"]


def test_길이가_실사용_분포_안에_있다():
    # 짧은 샘플로 재면 처리율을 잘못 본다(DECISIONS §6).
    for u in _UNITS:
        lo, hi = _SHAPE[u["kind"]]
        assert lo <= len(u["text"]) <= hi, f"{u['id']} {len(u['text'])}자"


def test_keep_토큰은_원문에_실제로_있다():
    # ★ 원문에 없는 토큰을 keep 에 적으면 번역문에도 없으므로 반드시 위반이
    #   된다. 검사가 모델이 아니라 케이스의 오타를 잡게 된다.
    for u in _UNITS:
        for tok in u.get("keep", []):
            assert tok in u["text"], f"{u['id']} keep={tok}"


def test_비율_경계가_모든_유닛에_있다():
    for u in _UNITS:
        assert 0 < u["ratio_min"] < u["ratio_max"], u["id"]


def test_기준선이_골든셋과_같은_규모를_가리킨다():
    """★ 숫자를 두 곳에 적으면 한쪽만 늙는다. PLAN 의 실측 요약이 기준선과
    어긋난 채로 남아 있던 것을 사람이 대조해서야 찾았다(DECISIONS §27).
    같은 일이 기준선과 골든셋 사이에서 일어나면 비교 자체가 무효가 된다.

    ★ `stale` 은 재측정 대기를 뜻한다. 문항을 늘린 커밋과 재측정 커밋은
      나뉠 수밖에 없으므로 — 측정은 기계 앞에서만 된다 — 그 사이 상태를
      거짓이 아니라 '표시된 불일치' 로 둔다. 값을 채우고 그 키를 지우는 것이
      재측정이 끝났다는 신호다.
    """
    base = _json.loads(
        (_pathlib.Path(bench.__file__).resolve().parents[1]
         / "docs/bench/baseline.json").read_text(encoding="utf-8"))
    if base.get("stale"):
        assert base["golden"]["units"] != len(_UNITS), \
            "stale 인데 규모가 맞는다. 재측정이 끝났으면 stale 을 지운다"
        return
    assert base["golden"]["cases"] == len(_CASES)
    assert base["golden"]["units"] == len(_UNITS)
    assert base["golden"]["chars"] == sum(len(u["text"]) for u in _UNITS)
