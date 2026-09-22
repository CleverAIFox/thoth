"""후처리 평가 코퍼스와 그것을 재는 도구(DECISIONS §107).

★ **코퍼스가 낡았는지를 코드가 말한다.** 코퍼스 첫 줄에 용언 목록의 지문이 있다.
  `lexicon.json` 을 고치고 `gen_endings.py` 를 다시 돌리지 않으면 여기서 멈춘다 —
  기준선 지문과 같은 장치다(§57).

★ **틀림은 늘면 안 된다.** 후처리를 분석기로 바꾸기 전까지 틀림이 0 이 아니므로
  게이트 대신 **톱니**를 건다. 지금 값보다 늘면 실패하고, 줄이면 아래 수를 같이
  줄인다. 교체가 끝나면 0 으로 두고 `bench_endings.py --gate` 로 넘긴다.
"""
import hashlib
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIR = ROOT / "worker/tests/endings"

_spec = importlib.util.spec_from_file_location("bench_endings", ROOT / "tools/bench_endings.py")
be = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(be)

# ★ 2026-09-22 실측. 106 이전 규칙은 476, 106 규칙이 218 이다.
WRONG_CEILING = 218


def lines(name):
    return [json.loads(x) for x in (DIR / name).read_text(encoding="utf-8").splitlines() if x.strip()]


def test_코퍼스가_용언_목록과_같은_판이다():
    meta = lines("corpus.jsonl")[0]
    assert meta.get("meta") is True
    now = hashlib.sha256((DIR / "lexicon.json").read_bytes()).hexdigest()[:16]
    assert meta["lexicon_sha"] == now, (
        "lexicon.json 이 코퍼스를 만든 뒤에 바뀌었다 — "
        "uv run --with kiwipiepy python tools/gen_endings.py")


def test_줄마다_필수_칸이_있고_id_가_겹치지_않는다():
    rows = be.load()
    assert len(rows) > 2000, "코퍼스가 조용히 비면 벤치가 전부 통과한 척한다(§21)"
    for r in rows:
        assert r["src"] and r["tgt"] and r["id"], r
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))


def test_부류마다_줄이_있다():
    # 한 부류가 통째로 빠지면 그 부류의 결함은 영영 안 보인다.
    lex = json.loads((DIR / "lexicon.json").read_text(encoding="utf-8"))
    seen = {r["class"] for r in be.load()}
    assert set(lex["classes"]) <= seen, set(lex["classes"]) - seen


def test_합쇼체_원문은_정답이_원문이다():
    # 바뀌면 안 되는 줄이 코퍼스에 있어야 과잉 교정을 잰다.
    same = [r for r in be.load() if r.get("type", "").startswith("합쇼")]
    assert same and all(r["src"] == r["tgt"] for r in same)


def test_판정이_셋으로_갈린다():
    r = {"src": "가요.", "tgt": "갑니다.", "ambiguous": ["가옵니다."]}
    assert be.judge(r, "갑니다.") == "맞음"
    assert be.judge(r, "가옵니다.") == "맞음", "겹치는 줄은 다른 정답도 맞음이다"
    assert be.judge(r, "가요.") == "그대로"
    assert be.judge(r, "가습니다.") == "틀림"


def test_후처리의_틀림이_늘지_않는다():
    wrong = [r["id"] for r, _, v in be.run(be.load()) if v == "틀림"]
    assert len(wrong) <= WRONG_CEILING, (
        f"틀림 {len(wrong)} > {WRONG_CEILING} — python3 tools/bench_endings.py --fails 20")


def test_검수_표본이_코퍼스에_있는_줄이다():
    ids = {r["id"] for r in be.load()}
    rows = (DIR / "review.tsv").read_text(encoding="utf-8").splitlines()[1:]
    assert rows
    for line in rows:
        assert line.split("\t")[0] in ids, line


def test_검수_판정은_정해진_값만_쓴다():
    # 미정 · O · X. 그 밖의 값은 오타이고, 오타는 조용히 "봤다" 로 읽힌다.
    rows = (DIR / "review.tsv").read_text(encoding="utf-8").splitlines()[1:]
    bad = [r for r in rows if r.split("\t")[5] not in ("미정", "O", "X")]
    assert not bad, bad[:3]
