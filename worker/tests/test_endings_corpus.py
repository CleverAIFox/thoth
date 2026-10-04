"""후처리 평가 코퍼스와 그것을 재는 도구(DECISIONS §107).

★ **코퍼스가 낡았는지를 코드가 말한다.** 코퍼스 첫 줄에 용언 목록의 지문이 있다.
  `lexicon.json` 을 고치고 `gen_endings.py` 를 다시 돌리지 않으면 여기서 멈춘다 —
  기준선 지문과 같은 장치다(§57).

★ **틀림은 늘면 안 된다.** 후처리는 땜질에서 멈췄고(DECISIONS §108) 틀림이 0 이
  아니므로 게이트 대신 **톱니**를 건다. 지금 값보다 늘면 실패하고, 줄이면 아래 수를
  같이 줄인다. 규칙 후처리를 더 키우지 않는다 — 문체는 자체 모델이 배운다.
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

# ★ 2026-09-22 실측. 106 이전 규칙은 476, 106 규칙이 218 이다. 생성기가 만든
#   오답 줄(명령이 아닌 낱말의 `하십시오` · `것 같겠어요`)을 빼고 214 다(generator 2).
# ★ **2026-10-04 — 214 중 164 가 규칙 셋의 결함이었다**(DECISIONS §151). 명령을
#   평서로 바꾸고 있었고(`먹으세요` → `먹으십니다`), `하십시오 → 합니다` 는 **이미
#   맞는 합쇼 명령을 망가뜨렸다.** 셋을 하나로 줄여 50 이 됐다. 남은 50 은 불규칙
#   어간 복원이고 **규칙을 키우는 쪽이라 §108 의 경계 밖이다.**
WRONG_CEILING = 50


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


def test_후처리의_틀림이_상한과_같다():
    """★ **양방향이다**(DECISIONS §108). 늘면 실패하고, **줄어도 실패한다** — 줄었는데
    상한을 안 내리면 되돌아갈 자리가 남는다. 느슨한 톱니는 초록으로 위장한다
    (하토르 D-0117 · 파이어레인 DECISIONS §199 에서 옮겼다)."""
    wrong = [r["id"] for r, _, v in be.run(be.load()) if v == "틀림"]
    assert len(wrong) <= WRONG_CEILING, (
        f"틀림 {len(wrong)} > {WRONG_CEILING} — python3 tools/bench_endings.py --fails 20")
    assert len(wrong) == WRONG_CEILING, (
        f"틀림 {len(wrong)} < {WRONG_CEILING} — 좋아졌다. WRONG_CEILING 을 {len(wrong)} 로 내린다")


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


# ★ **톱니가 수만 보면 결함이 기대값으로 언다**(DECISIONS §151). 214 중 164 가 규칙
#   셋의 결함이었는데, 「214 이하」 라는 수만 보는 톱니는 **그 164 를 정상으로 셌다.**
#   수가 같아도 **구성이 바뀌면** 울어야 한다 — 하나가 고쳐지고 다른 하나가 생겨도
#   수는 그대로이기 때문이다.
WRONG_SHAPE = {"어간복원": 50}


def 갈래(r: dict) -> str:
    """틀린 줄 하나의 갈래. **순수 함수라 가짜 입력으로 물을 수 있다.**

    ★ **`나요` 는 안 넣는다.** 남은 50 은 전부 `~ㄹ까요` 이고 `나요` 실패는 0건이다 —
      없는 갈래를 미리 만들면 **`나요` 가 나중에 틀려도 조용히 같은 칸으로 들어간다.**
      안 넣으면 `부류/문형` 칸으로 떨어져 **구성 검사가 문다**(§133 · §151).
    """
    if r["src"].rstrip("?. ").endswith("까요"):
        return "어간복원"
    return f"{r['class']}/{r['type']}"


def _wrong_shape():
    """남은 틀림을 갈래로 나눈다. `~ㄹ까요`·`~나요` 의 불규칙 어간 복원뿐이어야 한다."""
    import collections
    return dict(collections.Counter(
        갈래(r) for r, got, v in be.run(be.load()) if v == "틀림"))


def test_남은_틀림의_구성이_선언과_같다():
    assert _wrong_shape() == WRONG_SHAPE, (
        "틀림의 **구성**이 바뀌었다 — 수가 같아도 다른 결함이다. "
        "python3 tools/bench_endings.py --fails 20")


def test_구성의_합이_천장과_같다():
    # ★ 둘이 갈리면 한쪽이 거짓말이다. 같은 수를 두 곳이 들면 언젠가 갈린다(§132).
    assert sum(WRONG_SHAPE.values()) == WRONG_CEILING


def test_갈래가_어간복원을_가른다():
    # ★ **분류기에 시험이 없으면 「무엇이든 어간복원」 으로 바꿔도 조용하다** —
    #   돌연변이가 그렇게 살아 돌아왔다.
    assert 갈래({"src": "도울까요?", "class": "ㅂ불규칙", "type": "의문"}) == "어간복원"
    assert 갈래({"src": "그럴까요?", "class": "ㅎ불규칙", "type": "의문"}) == "어간복원"


def test_갈래가_나머지를_안_뭉친다():
    # ★ 음성 대조 — 전부 어간복원으로 세면 구성 검사가 아무것도 안 잰다.
    assert 갈래({"src": "먹으세요.", "class": "규칙-자음", "type": "명령"}) == "규칙-자음/명령"
    assert 갈래({"src": "확인하십시오.", "class": "하다", "type": "합쇼-명령"}) == "하다/합쇼-명령"
    # ★ `나요` 는 일부러 안 가른다 — 지금 0건이고, 나중에 나면 울어야 한다
    assert 갈래({"src": "남나요?", "class": "규칙-자음", "type": "의문"}) == "규칙-자음/의문"


def test_구성_검사가_다른_갈래를_문다():
    # ★ 수가 같아도 **구성이 바뀌면** 울어야 한다. 가짜 셈으로 그 자리를 묻는다.
    가짜 = {"어간복원": 49, "하다/명령": 1}
    assert sum(가짜.values()) == WRONG_CEILING
    assert 가짜 != WRONG_SHAPE, "수가 같은데 구성이 다른 것을 같다고 본다"
