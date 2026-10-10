"""문서 건수 대조를 검사한다.

★ 검사도 코드이고 결함이 있다(DECISIONS §21). 판정을 순수 함수로 떼어 두었으니
  그쪽만 본다 — 읽는 것과 재는 것은 이 파일의 관심이 아니다.
"""
import importlib.util
import pathlib

import pytest

_spec = importlib.util.spec_from_file_location(
    "check_counts", pathlib.Path(__file__).resolve().parents[2] / "tools/check_counts.py")
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)

ROOT = pathlib.Path(__file__).resolve().parents[2]


def found(*rows):
    return list(rows)


def test_같으면_통과한다():
    code, _ = cc.compare(found(("PLAN.md", "ext_tests", 10, 43)), {"ext_tests": 43})
    assert code == 0


def test_다르면_실패하고_양쪽을_적는다():
    code, lines = cc.compare(found(("PLAN.md", "ext_tests", 10, 41)), {"ext_tests": 43})
    assert code == 1
    assert "41" in lines[0] and "43" in lines[0] and "PLAN.md:10" in lines[0]


def test_재지_못한_것은_통과가_아니다():
    # ★ 0 으로 끝내면 node 가 없는 기계에서 영영 통과한다(§59).
    code, lines = cc.compare(found(("PLAN.md", "ext_tests", 10, 43)), {})
    assert code == 3
    assert "재지 못해" in lines[0]


def test_모르는_이름은_실패다():
    # 표시를 오타내면 아무도 보지 않는 주장이 된다.
    code, lines = cc.compare(found(("PLAN.md", "ext_tset", 10, 43)), {"ext_tests": 43})
    assert code == 1
    assert "모르는 이름" in lines[0]


def test_불일치가_못_잼을_이긴다():
    code, _ = cc.compare(
        found(("PLAN.md", "ext_tests", 10, 41), ("MASTER.md", "worker_tests", 5, 128)),
        {"ext_tests": 43})
    assert code == 1


def test_주장이_없으면_통과한다():
    code, lines = cc.compare([], {"ext_tests": 43})
    assert code == 0 and "표시된 주장이 없다" in lines[0]


# ── 표시 읽기 ────────────────────────────────────────────────────────────


def test_표시된_숫자만_읽는다(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    (tmp_path / "docs" / "PLAN.md").write_text(
        "★ 그때는 41건이었다\n"
        "확장 테스트 <!--count:ext_tests-->43건이며 doctor 가 함께 돌린다\n",
        encoding="utf-8")
    got = cc.claims(tmp_path)
    # ★ 문단의 41 은 표시가 없으므로 주장이 아니다(§54).
    assert got == [("PLAN.md", "ext_tests", 2, 43)]


def test_한_줄에_둘이어도_둘_다_센다(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(
        "<!--count:ext_tests-->43 · <!--count:worker_tests-->128\n", encoding="utf-8")
    assert len(cc.claims(tmp_path)) == 2


# ── 인자 ─────────────────────────────────────────────────────────────────


def test_빈_값은_못_잼이다():
    # 셸에서 변수가 비면 `이름=` 이 그대로 넘어온다. 0 으로 읽으면 안 된다.
    assert cc.parse_args(["ext_tests=", "worker_tests=128"]) == {"worker_tests": 128}


def test_숫자가_아니면_죽는다():
    with pytest.raises(ValueError):
        cc.parse_args(["ext_tests=많음"])


# ── 실제 문서 ────────────────────────────────────────────────────────────


def test_저장소_문서의_표시가_전부_아는_이름이다():
    unknown = {n for _, n, _, _ in cc.claims(cc.ROOT) if n not in cc.KNOWN}
    assert not unknown, f"KNOWN 에 없는 표시: {unknown}"


# ── 고치기 (DECISIONS §180) ───────────────────────────────────────────────
#
# ★ **잡는 것과 고치는 것은 다른 일이다.** `doctor` 는 실측을 손에 들고 있는데 문서는
#   사람이 옮겨 적었다 — 그래서 늙는다. 2026-10-10 하루에 `ext_tests` 와 `worker_tests`
#   가 **둘 다** 늙었고 이 관문이 둘 다 잡았다. 잡기만 하면 사람이 손으로 옮긴다.

def _모래밭(tmp_path, 글: str) -> pathlib.Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text(글, encoding="utf-8")
    return tmp_path


def test_실측으로_갈아_쓴다(tmp_path):
    d = _모래밭(tmp_path, "확장 <!--count:ext_tests-->176건 · 워커 <!--count:worker_tests-->828건\n")
    고침 = cc.고친다(d, {"ext_tests": 187, "worker_tests": 885})
    글 = (d / "README.md").read_text(encoding="utf-8")
    assert "<!--count:ext_tests-->187건" in 글 and "<!--count:worker_tests-->885건" in 글
    assert len(고침) == 2


def test_같은_수는_안_건드린다(tmp_path):
    d = _모래밭(tmp_path, "확장 <!--count:ext_tests-->187건\n")
    assert cc.고친다(d, {"ext_tests": 187}) == []


def test_못_잰_이름은_안_고친다(tmp_path):
    """★ **「못 쟀다」 를 값으로 바꾸면 거짓이 된다**(DECISIONS §59)."""
    d = _모래밭(tmp_path, "확장 <!--count:ext_tests-->176건\n")
    assert cc.고친다(d, {}) == []
    assert "176건" in (d / "README.md").read_text(encoding="utf-8")


def test_모르는_이름은_안_고친다(tmp_path):
    """★ 오타를 조용히 박제하면 그 주장은 영영 안 읽힌다."""
    d = _모래밭(tmp_path, "<!--count:오타-->5건\n")
    assert cc.고친다(d, {"오타": 9}) == []
    assert "5건" in (d / "README.md").read_text(encoding="utf-8")


def test_같은_줄의_다른_수를_안_건드린다(tmp_path):
    """★ `176건 · 워커 176` 처럼 같은 수가 줄에 또 있으면 **표시된 쪽만** 바꾼다."""
    d = _모래밭(tmp_path, "확장 <!--count:ext_tests-->176건 (전에도 176이었다)\n")
    cc.고친다(d, {"ext_tests": 187})
    assert (d / "README.md").read_text(encoding="utf-8") == \
        "확장 <!--count:ext_tests-->187건 (전에도 176이었다)\n"


def test_doctor_가_고치는_길을_적는다():
    """★ **길을 안 적으면 사람이 손으로 옮긴다** — 그것이 이 빚의 모양이었다."""
    sh = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    본문 = "\n".join(l for l in sh.split("\n") if not l.lstrip().startswith("#"))
    assert "check_counts.py --fix" in 본문, "doctor 가 고치는 명령을 안 알려 준다"


def test_fix_가_고치고_다시_센다(tmp_path, monkeypatch):
    """★ **고쳤다고 말만 하고 안 보면, 못 고친 자리가 남는데 초록이 된다.**
    모르는 이름은 안 고치므로 `--fix` 뒤에도 **울어야 한다.**"""
    가 = _모래밭(tmp_path / "가", "확장 <!--count:ext_tests-->176건 · <!--count:오타-->5건\n")
    monkeypatch.setattr(cc, "ROOT", 가)
    assert cc.main(["--fix", "ext_tests=187"]) == 1, "못 고친 이름이 있는데 통과했다"
    assert "187건" in (가 / "README.md").read_text(encoding="utf-8"), "고칠 수 있는 것도 안 고쳤다"

    나 = _모래밭(tmp_path / "나", "확장 <!--count:ext_tests-->176건\n")
    monkeypatch.setattr(cc, "ROOT", 나)
    assert cc.main(["--fix", "ext_tests=187"]) == 0, "다 고쳤는데 안 통과한다"
