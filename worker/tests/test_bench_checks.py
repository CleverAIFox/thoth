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
             keep=[])
    assert bench.check(u, "스트림은 레코드를 168시간 보관합니다.", BOOK) == []


def test_의문형_합니다체를_위반으로_보지_않는다():
    # 후처리가 만들어 내는 형태다. 검사가 이것을 잡으면 스스로를 부정한다.
    u = unit("Which condition must be confirmed?", keep=[])
    assert bench.check(u, "어떤 조건을 확인해야 합니까?", BOOK) == []


def test_해요체는_잡는다():
    u = unit("Confirm the checkpoint position now please.", keep=[])
    assert any("합니다체" in b for b in bench.check(u, "체크포인트를 확인하세요.", BOOK))


def test_원문에_없는_용어는_보지_않는다():
    u = unit("The shard count matches throughput.", keep=[])
    assert not any("term" in b for b in bench.check(u, "샤드 수가 처리량과 맞습니다.", BOOK))


def test_긴_용어에_포함된_짧은_용어는_빼고_본다():
    u = unit("Every consumer application has checkpointed past the record.",
             keep=[])
    ko = "모든 컨슈머 애플리케이션이 레코드를 지나 체크포인트했습니다."
    assert not any("term" in b for b in bench.check(u, ko, BOOK))


def test_길이가_과하면_덧붙임으로_잡는다():
    u = unit("Short source here.", keep=[])
    bad = bench.check(u, "원문보다 훨씬 길게 늘어난 번역문을 여기에 넣습니다.", BOOK)
    assert any("덧붙임" in b for b in bad)


def test_길이가_모자라면_누락으로_잡는다():
    u = unit("A" * 200 + " records are retained for a long period of time.",
             keep=[])
    assert any("누락" in b for b in bench.check(u, "짧습니다.", BOOK))


def test_물음표가_사라지면_잡는다():
    u = unit("Which condition must be confirmed?", keep=[])
    assert any("물음표" in b for b in bench.check(u, "조건을 확인해야 합니다.", BOOK))


def test_keep_토큰이_번역되면_잡는다():
    u = unit("A Glue crawler populates the Data Catalog nightly here now.",
             keep=["Data Catalog"])
    ko = "Glue 크롤러가 매일 밤 데이터 카탈로그를 채웁니다."
    assert any("keep" in b for b in bench.check(u, ko, BOOK))


def test_한글이_없으면_잡는다():
    u = unit("The stream retains records.", keep=[])
    assert any("한글" in b for b in bench.check(u, "[KO] The stream retains records.", BOOK))


# ---------- 웜업 ----------

def test_웜업_문장은_매번_다르다(monkeypatch):
    # ★ 고정 문장이면 두 번째 실행부터 캐시 히트라 모델을 태우지 않는다.
    #   웜업이 조용히 아무것도 하지 않게 되고, 통과는 그것을 알려주지 않는다
    #   (DECISIONS §21).
    seen = []

    def fake(url, texts, timeout):
        seen.append(texts[0])
        return ["번역"], 1.0, [False]

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
                        lambda url, texts, timeout: (seen.append(texts[0]),
                                                     (["ko"], 1.0, [False]))[1])
    bench.warmup("http://x", 10)
    assert seen[0] not in golden


def test_웜업은_잰_시간을_돌려준다(monkeypatch):
    monkeypatch.setattr(bench, "translate",
                        lambda url, texts, timeout: (["ko"], 42.5, [False]))
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
    """★ 숫자를 두 곳에 적으면 한쪽만 늙는다(DECISIONS §27).

    ★ `stale` 은 재측정 대기를 뜻한다. 처음에는 '골든셋 규모가 달라진 경우'
      로 좁게 정의했는데, 프롬프트나 후처리가 바뀌어도 기준선의 위반 수는
      그대로 무효가 된다. **규모가 같아도 값이 늙을 수 있다** — 정의가
      좁았다. 측정은 기계 앞에서만 되므로 코드를 고친 커밋과 재측정 커밋은
      나뉠 수밖에 없고, 그 사이를 거짓이 아니라 표시된 불일치로 둔다.

    ★ 사유를 필수로 둔다. 플래그만 있으면 왜 세웠는지 잊히고, 잊히면 지울
      수 없어 영영 남는다. 그때 이 검사는 조용히 아무것도 하지 않는다(§21).
    """
    base = _json.loads(
        (_pathlib.Path(bench.__file__).resolve().parents[1]
         / "docs/bench/baseline.json").read_text(encoding="utf-8"))
    if base.get("stale"):
        assert base.get("_stale_note"), "stale 인데 사유가 없다"
        return
    assert base["golden"]["cases"] == len(_CASES)
    assert base["golden"]["units"] == len(_UNITS)
    assert base["golden"]["chars"] == sum(len(u["text"]) for u in _UNITS)


def test_단어_내부에_박힌_용어는_보지_않는다():
    # ★ ProvisionedThroughputExceededException 안의 throughput 이 잡혀서
    #   원문에 단독으로 나오지도 않는 용어의 표기를 요구했다(DECISIONS §28).
    u = unit("The client receives ProvisionedThroughputExceededException here.",
             keep=[])
    assert bench.check(u, "클라이언트가 여기서 예외를 받습니다.",
                       {"throughput": "처리량"}) == []


def test_복수형과_굴절형은_계속_본다():
    # 단어 경계만 걸면 records 가 record 에 안 걸려 검사가 조용히 약해진다.
    # 용어집(glossary._hits)과 같은 굴절 패턴을 쓴다.
    book = {"record": "레코드", "catalog": "카탈로그"}
    u = unit("The stream stores records for the configured window of time here.",
             keep=[])
    assert bench.check(u, "스트림은 설정된 기간 동안 기록을 저장합니다.", book) \
        == ["term:record→레코드"]

    u = unit("The crawler is cataloging every partition of the bucket tonight.",
             keep=[])
    assert bench.check(u, "크롤러가 오늘 밤 모든 파티션을 목록화합니다.", book) \
        == ["term:catalog→카탈로그"]


def test_프롬프트가_바뀌면_기준선이_stale_이어야_한다():
    """★ 앞 검사는 사람이 `stale` 을 세워야만 돈다. 세우지 않은 날은 아무도
    모르고, 그때 검사는 조용히 아무것도 하지 않는다(DECISIONS §21).

    ★ 프롬프트와 용어집의 해시를 기준선에 박아 두면 코드가 스스로 늙었다고
      말한다. 사람의 성실성에 기대지 않는 유일한 방법이다.
    """
    base = _json.loads(
        (_pathlib.Path(bench.__file__).resolve().parents[1]
         / "docs/bench/baseline.json").read_text(encoding="utf-8"))
    for name, blk in base["engines"].items():
        if blk.get("prompt_fingerprint") != bench.prompt_fingerprint(blk["batch"]):
            assert blk.get("stale") or base.get("stale"), (
                f"engines.{name} 의 프롬프트·용어집이 기준선을 뜬 때와 다르다. "
                "재측정하고 값을 채우거나 stale 로 표시한다")


def test_지문은_모델이_보는_것만_담는다(monkeypatch):
    # 후처리나 배치 파싱을 고쳐도 흔들리면 관계없는 재측정을 요구하게 된다.
    from app import engine

    before = bench.prompt_fingerprint()
    monkeypatch.setattr(engine, "_ENDINGS", [])
    monkeypatch.setattr(engine, "BATCH_MARK", "#")
    assert bench.prompt_fingerprint() == before

    monkeypatch.setattr(engine, "SYSTEM", engine.SYSTEM + "\n7. Extra rule.")
    assert bench.prompt_fingerprint() != before


def test_지문은_프롬프트_조립_로직도_본다(monkeypatch):
    """★ 데이터만 해시하면 `as_prompt` 의 변경을 놓친다. 2026-09-13 에 항등
    항목이 짧은 용어를 덮도록 로직을 고쳤는데 지문이 흔들리지 않았다
    (DECISIONS §33). 모델이 보는 것에는 값뿐 아니라 배치도 들어간다.
    """
    from app import glossary

    before = bench.prompt_fingerprint()
    real = glossary.as_prompt
    monkeypatch.setattr(glossary, "as_prompt",
                        lambda terms: real(terms) + "\nExtra line.")
    assert bench.prompt_fingerprint() != before


# ---------- 환경 스냅샷 ----------

def test_도구가_없어도_측정이_죽지_않는다(monkeypatch):
    # ★ 이 기록은 측정을 돕는 부속이지 측정의 전제가 아니다. nvidia-smi 가
    #   없는 기계에서 벤치가 못 돌면 부속이 본체를 막는 것이다.
    def missing(*a, **kw):
        raise FileNotFoundError("nvidia-smi")
    monkeypatch.setattr(bench.subprocess, "run", missing)
    snap = bench.env_snapshot()
    assert isinstance(snap, dict)
    assert "vram_used" not in snap


def test_명령이_실패해도_측정이_죽지_않는다(monkeypatch):
    import subprocess as sp
    monkeypatch.setattr(bench.subprocess, "run",
                        lambda *a, **kw: (_ for _ in ()).throw(sp.TimeoutExpired("x", 5)))
    assert isinstance(bench.env_snapshot(), dict)


def test_오프로딩이_기록에_남는다(monkeypatch):
    # ★ 측정이 끝난 뒤에 재면 모델이 이미 언로드되어 있다. 그때의 환경은
    #   측정 중 환경이 아니다(DECISIONS §34). 배치마다 찍어 남긴다.
    class R:
        def __init__(self, out): self.stdout = out

    def fake(cmd, **kw):
        if cmd[0] == "ollama":
            return R("NAME  ID  SIZE  PROCESSOR  CONTEXT  UNTIL\n"
                     "exaone  abc  4.6GB  38%/62% CPU/GPU  4096  5m\n")
        return R("512, 6144, 51, 1455\n")

    monkeypatch.setattr(bench.subprocess, "run", fake)
    snap = bench.env_snapshot()
    # ★ 비율은 PROCESSOR 앞 칸에 따로 있다. 칸 하나만 집으면 `38%/62%` 를
    #   잃고 `CPU/GPU` 만 남는다. 2026-09-13 실측에서 실제로 그랬다.
    assert snap["processor"] == "38%/62% CPU/GPU"
    assert snap["offloaded"] is True
    assert snap["vram_used"] == "512" and snap["vram_total"] == "6144"


def test_온전히_GPU_면_오프로딩이_아니다(monkeypatch):
    class R:
        def __init__(self, out): self.stdout = out
    monkeypatch.setattr(
        bench.subprocess, "run",
        lambda cmd, **kw: R("NAME  ID  SIZE  PROCESSOR  CONTEXT  UNTIL\n"
                            "exaone  abc  6.0 GB  100% GPU  4096  5m\n")
        if cmd[0] == "ollama" else R(""))
    snap = bench.env_snapshot()
    assert snap["processor"] == "100% GPU"
    assert snap["offloaded"] is False


def test_모델이_안_올라가_있으면_그것도_기록한다(monkeypatch):
    class R:
        def __init__(self, out): self.stdout = out
    monkeypatch.setattr(bench.subprocess, "run",
                        lambda cmd, **kw: R("NAME  ID  SIZE  PROCESSOR\n")
                        if cmd[0] == "ollama" else R(""))
    assert bench.env_snapshot()["processor"] == "모델 없음"


def test_환경_기록은_지문을_흔들지_않는다(monkeypatch):
    # 모델이 보는 것이 아니므로 재측정을 요구해서는 안 된다(DECISIONS §22).
    before = bench.prompt_fingerprint()
    monkeypatch.setattr(bench, "env_snapshot", lambda: {"vram_used": "9999"})
    assert bench.prompt_fingerprint() == before


def test_컨텍스트도_함께_남긴다(monkeypatch):
    # ★ VRAM 이 남아 있는데도 오프로딩되는 이유가 여기 있다. 가중치만이 아니라
    #   KV 캐시와 컴퓨트 버퍼도 VRAM 을 쓴다(DECISIONS §36).
    class R:
        def __init__(self, out): self.stdout = out
    monkeypatch.setattr(
        bench.subprocess, "run",
        lambda cmd, **kw: R("NAME  ID  SIZE  PROCESSOR  CONTEXT  UNTIL\n"
                            "exaone  abc  6.0 GB  24%/76% CPU/GPU  4096  5m\n")
        if cmd[0] == "ollama" else R(""))
    assert bench.env_snapshot()["context"] == "4096"


def test_기준선의_배치_조건을_읽는다():
    # 러너가 이번 실행의 배치를 기준선과 대조한다. 조건이 없으면 빈 문자열이고
    # 그때는 대조하지 않는다 — 없는 것을 틀렸다고 보고하면 안 된다.
    assert "GPU" in bench.baseline_condition("local")
    # ★ 호스팅 엔진에는 그 축이 없다. 없는 것을 틀렸다고 보고하면 안 된다.
    assert bench.baseline_condition("bedrock") == ""


# ---------- 실패 안내 ----------

def test_502_는_워커가_아니라_엔진을_가리킨다():
    """★ HTTPError 는 URLError 의 하위 클래스라 같은 except 에 걸린다. 둘을
    뭉뚱그리면 502 에도 "워커에 닿지 못했다" 가 나가고, 시킨 대로 워커를 다시
    띄우면 502 가 또 난다(DECISIONS §37).
    """
    import io
    import urllib.error

    e = urllib.error.HTTPError(
        "http://x", 502, "Bad Gateway", {},
        io.BytesIO(b'{"error":"engine_failed","detail":"URLError"}'))
    msg = bench.explain_failure(e)
    assert "워커는 살아 있다" in msg
    assert "run_ollama.sh" in msg
    assert "run_worker.sh" not in msg


def test_401_은_토큰을_가리킨다():
    import io
    import urllib.error

    e = urllib.error.HTTPError("http://x", 401, "Unauthorized", {},
                               io.BytesIO(b'{"error":"unauthorized"}'))
    assert "WORKER_TOKEN" in bench.explain_failure(e)


def test_닿지_못한_경우에만_워커를_가리킨다():
    import urllib.error

    msg = bench.explain_failure(urllib.error.URLError("Connection refused"))
    assert "run_worker.sh" in msg
    assert "run_ollama.sh" not in msg


def test_본문이_깨져도_안내가_나간다():
    import io
    import urllib.error

    e = urllib.error.HTTPError("http://x", 502, "Bad Gateway", {},
                               io.BytesIO(b"<html>not json</html>"))
    assert "502" in bench.explain_failure(e)


# ---------- 검사 대상 목록 ----------

def test_케이스의_terms_를_보지_않는다():
    """★ 그 필드는 사람이 손으로 적는데 프롬프트는 원문에서 자동으로 고른다.
    두 목록이 다르면 차이나는 자리는 지시만 하고 검사하지 않는다 — 실측에서
    15개 유닛이 그랬고 위반 3건이 그 그늘에 있었다(DECISIONS §49).
    """
    u = unit("The stream stores records for the configured window of time.")
    u["terms"] = []            # 비어 있어도 원문에서 골라 검사한다
    assert bench.check(u, "스트림은 설정된 기간 동안 기록을 저장합니다.", BOOK) \
        == ["term:record→레코드"]


def test_원문에_없는_용어는_검사하지_않는다():
    # 용어집이 커져도 관계없는 용어를 요구하지 않는다.
    u = unit("The crawler updates the table every night without fail here.")
    assert bench.check(u, "크롤러가 매일 밤 테이블을 갱신합니다.", BOOK) == []


def test_프롬프트와_같은_함수로_고른다():
    """★ 같은 질문에 답이 둘이면 하나는 틀렸다(§28 · §30 · §32 의 재발).
    `glossary._hits` 가 고른 것과 검사 대상이 같아야 한다.
    """
    import sys, pathlib as _p
    sys.path.insert(0, str(_p.Path(__file__).resolve().parents[1]))
    from app import glossary

    src = "The consumer application reads records from the stream today."
    picked = set(glossary._hits(BOOK, src.lower()))
    # consumer 는 consumer application 에 포함되므로 검사에서 빠진다
    assert "consumer application" in picked
    assert "record" in picked


# ── 캐시 히트 · 배치 기본값 (DECISIONS §64) ──────────────────────────────


class _Resp:
    def __init__(self, payload):
        self._b = __import__("json").dumps(payload).encode()
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _patch_urlopen(monkeypatch, payload):
    monkeypatch.setattr(bench.urllib.request, "urlopen",
                        lambda *a, **k: _Resp(payload))


def test_translate_가_캐시_플래그를_돌려준다(monkeypatch):
    _patch_urlopen(monkeypatch, {"translations": ["가", "나"], "cached": [True, False]})
    out, _dt, cached = bench.translate("http://x/translate", ["a", "b"], 5)
    assert out == ["가", "나"] and cached == [True, False]


def test_cached_가_없으면_히트로_세지_않는다(monkeypatch):
    # 옛 워커와 붙어도 죽지 않는다. 없는 것을 True 로 읽으면 멀쩡한 측정이 무효가 된다.
    _patch_urlopen(monkeypatch, {"translations": ["가"]})
    _out, _dt, cached = bench.translate("http://x/translate", ["a"], 5)
    assert cached == [False]


def test_부분_응답은_여전히_멈춘다(monkeypatch):
    import pytest
    _patch_urlopen(monkeypatch, {"translations": ["가"], "partial": "quota"})
    with pytest.raises(SystemExit):
        bench.translate("http://x/translate", ["a"], 5)


def test_배치_기본값을_엔진별_기준선에서_읽는다():
    import json as _json
    d = _json.loads((bench.ROOT / "docs/bench/baseline.json").read_text(encoding="utf-8"))
    for name, blk in d["engines"].items():
        assert bench.baseline_batch(name) == blk["batch"], \
            "러너 기본값과 기준선이 갈리면 --batch 를 빠뜨린 실행이 다른 조건에서 잰다"


def test_기준선을_못_읽으면_None(monkeypatch, tmp_path):
    monkeypatch.setattr(bench, "ROOT", tmp_path)
    assert bench.baseline_batch("local") is None


def test_모르는_엔진은_None(monkeypatch):
    # ★ 조용히 다른 엔진 값으로 떨어지면 안 된다. 없으면 없다고 해야 --batch 를 요구한다.
    assert bench.baseline_batch("없는엔진") is None


def test_기준선이_엔진마다_지문과_배치를_갖는다():
    import json as _json
    d = _json.loads((bench.ROOT / "docs/bench/baseline.json").read_text(encoding="utf-8"))
    assert d["engines"], "engines 블록이 비었다"
    for name, blk in d["engines"].items():
        for k in ("batch", "prompt_fingerprint", "speed", "violations", "model"):
            assert k in blk, f"engines.{name} 에 {k} 가 없다"


def test_말뭉치는_엔진_블록_밖에_있다():
    import json as _json
    d = _json.loads((bench.ROOT / "docs/bench/baseline.json").read_text(encoding="utf-8"))
    assert "golden" in d and "units" in d["golden"]
    for name, blk in d["engines"].items():
        assert "golden" not in blk, f"engines.{name} 이 말뭉치를 따로 들고 있다"


def test_로컬_엔진만_로컬_환경을_잰다():
    assert "local" in bench.LOCAL_ENGINES
    assert "bedrock" not in bench.LOCAL_ENGINES


def test_엔진을_못_물으면_빈_문자열(monkeypatch):
    def boom(*a, **k):
        raise bench.urllib.error.URLError("no")
    monkeypatch.setattr(bench.urllib.request, "urlopen", boom)
    assert bench.worker_engine("http://x/translate", 5) == ""


def test_엔진을_health_에서_읽는다(monkeypatch):
    _patch_urlopen(monkeypatch, {"engine": "bedrock"})
    assert bench.worker_engine("http://x/translate", 5) == "bedrock"


def test_흉내가_실제_translate_와_같은_모양을_돌려준다():
    """★ `warmup` 이 3-튜플로 바뀌었는데 테스트의 흉내는 2-튜플 그대로였다.

    그래서 실제 코드가 깨진 채로 테스트가 통과했고, CI 의 골든셋 스텝이 러너를
    끝까지 돌리고 나서야 잡혔다. 흉내가 계약을 따라가지 않으면 검사가 검사를
    하지 않는다(DECISIONS §48 · §65).
    """
    import inspect
    src = inspect.getsource(bench.translate)
    assert "return data[\"translations\"], time.monotonic() - t0, cached" in src
    # warmup 이 그 모양을 그대로 받는지
    assert "_, dt, _cached = translate(" in inspect.getsource(bench.warmup)


# ── 어간·어미 결합 (DECISIONS §93) ─────────────────────────────────────────
#
# ★ 실사용에서 `사용해야 할습니까?` 가 나왔는데 골든셋 45유닛은 위반 3으로
#   조용했다. **재는 자가 없으면 유닛을 늘려도 안 잡힌다.**

def test_모음_어간에_습니다는_비문이다():
    assert bench.bad_conjugation("되습니다") == ["어미:되습니다"]


def test_ㄹ_어간에_습니까는_비문이다():
    # 하+ㄹ. 실제로 난 것이다 — "사용해야 할습니까?"
    assert bench.bad_conjugation("사용해야 할습니까?") == ["어미:할습니까"]
    assert bench.bad_conjugation("만들습니다") == ["어미:들습니다"]


def test_자음_어간은_통과한다():
    for ok in ["있습니다", "좋습니다", "확인했습니다", "기록되었습니다."]:
        assert bench.bad_conjugation(ok) == [], ok


def test_ㅂ니다_꼴은_건드리지_않는다():
    # 합니다 · 만듭니다 는 올바른 활용이고 검사 대상이 아니다.
    for ok in ["사용해야 합니까?", "만듭니다", "입니다"]:
        assert bench.bad_conjugation(ok) == [], ok


def test_한글이_아니면_판정하지_않는다():
    # ★ 못 잴 자리에 결과를 적지 않는다(§59).
    assert bench.bad_conjugation("Glue습니다") == []


def test_한_문장에_둘이면_둘_다_적는다():
    assert len(bench.bad_conjugation("되습니다. 할습니까?")) == 2


def test_check_가_이_축을_부른다():
    bad = bench.check(unit("Does it work?"), "동작해야 할습니까?", BOOK)
    assert any(b.startswith("어미:") for b in bad)
