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
