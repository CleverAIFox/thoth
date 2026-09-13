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
             keep=[], terms=["throughput"])
    assert bench.check(u, "클라이언트가 여기서 예외를 받습니다.",
                       {"throughput": "처리량"}) == []


def test_복수형과_굴절형은_계속_본다():
    # 단어 경계만 걸면 records 가 record 에 안 걸려 검사가 조용히 약해진다.
    # 용어집(glossary._hits)과 같은 굴절 패턴을 쓴다.
    book = {"record": "레코드", "catalog": "카탈로그"}
    u = unit("The stream stores records for the configured window of time here.",
             keep=[], terms=["record"])
    assert bench.check(u, "스트림은 설정된 기간 동안 기록을 저장합니다.", book) \
        == ["term:record→레코드"]

    u = unit("The crawler is cataloging every partition of the bucket tonight.",
             keep=[], terms=["catalog"])
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
    if base.get("prompt_fingerprint") != bench.prompt_fingerprint():
        assert base.get("stale"), (
            "프롬프트·용어집이 기준선을 뜬 때와 다르다. 재측정하고 값을 채우거나 "
            "stale 로 표시한다")


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
    cond = bench.baseline_condition()
    assert isinstance(cond, str)
    assert "GPU" in cond


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
