"""문서 강제자의 검사(DECISIONS §111). **강제자가 죽으면 문서는 조용히 늙는다.**

★ 양성과 음성을 함께 본다. 깨끗한 합성 문서가 통과하는가, 그리고 **규칙마다 하나씩 어긴
  문서가 그 규칙으로 걸리는가.** 음성만 있으면 무엇이든 잡는 검사가, 양성만 있으면 아무것도
  못 잡는 검사가 초록이다.
"""
import importlib.util
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"tools/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cd = _load("check_docs")
fsck = _load("doc_fsck")

PLAN = """# t

## 0. 다음 한 수

#7 을 본다.

## 1. 남은 일 — 2행

| # | 상태 | 항목 | 전건 · 막고 있는 것 |
|---|---|---|---|
| 3 | 📄 | 가 | |
| 7 | ⏳ | 나 | #3 |

## 2. 범위 밖

없다.
"""


def plan_fails(text):
    f = []
    cd.check_plan(text, f)
    return f


# ---------- 카나리아 ----------

def test_카나리아가_산다():
    cd._canary()
    fsck._canary()


def test_실제_저장소가_통과한다():
    # ★ 도구를 CLI 로 돌려 종료 코드를 본다. 위반은 1, 고장은 2 다.
    for tool in ("check_docs", "doc_fsck"):
        r = subprocess.run(["python3", str(ROOT / f"tools/{tool}.py")], capture_output=True, text=True)
        assert r.returncode == 0, (tool, r.stdout[-800:], r.stderr[-800:])


# ---------- PLAN ----------

def test_깨끗한_PLAN_은_통과한다():
    assert plan_fails(PLAN) == []


@pytest.mark.parametrize("change,want", [
    (("2행", "3행"), "제목은 3행인데"),
    (("| 3 | 📄 | 가 | |\n| 7 |", "| 7 | 📄 | 가 | |\n| 3 |"), "오름차순"),
    (("| 7 | ⏳ | 나 | #3 |", "| 3 | ⏳ | 나 | #3 |"), "겹친다"),
    (("| 3 | 📄 |", "| 3 | ✅ |"), "어휘 밖"),
    (("| 3 | 📄 | 가 |", "| 3 | 📄 | 가 해결됨 |"), "닫힘 표시"),
    (("| 7 | ⏳ | 나 | #3 |", "| 7 | ⏳ | 나 | |"), "막고 있는 것이 비었다"),
    (("| 7 | ⏳ | 나 | #3 |", "| 7 | ⏳ | 나 | #4 |"), "전건 #4"),
    (("#7 을 본다.", "#9 을 본다."), "없는 #9"),
    (("없다.", "| 9 | 📄 | 다 | |"), "§1 밖"),
    (("## 1. 남은 일 — 2행", "## 1. 남은 일"), "제목이 없다"),
])
def test_PLAN_규칙마다_걸린다(change, want):
    bad = PLAN.replace(*change)
    assert bad != PLAN, "치환이 먹지 않았다 — 검사의 검사가 빈손이다"
    assert any(want in f for f in plan_fails(bad)), plan_fails(bad)


def test_결번은_정상이다():
    # ★ 행 번호는 영구 식별자다. 3 다음이 7 이어도 통과한다.
    assert not any("연속" in f for f in plan_fails(PLAN))


# ---------- 절 번호 ----------

def test_절_번호가_겹치면_걸린다():
    f = []
    cd.check_headings("PLAN.md", "## 0. a\n## 1. b\n## 1. c\n", f)
    assert any("두 번" in x for x in f)


def test_번호_없는_절이_걸린다():
    f = []
    cd.check_headings("MASTER.md", "## 1. a\n## 부록\n", f)
    assert any("번호 없는" in x for x in f)


def test_DECISIONS_는_기호가_붙은_번호를_본다():
    f = []
    cd.check_headings("DECISIONS.md", "## §1. a\n## §2. b\n", f)
    assert f == []


# ---------- DECISIONS ----------

def _dec(n, body):
    return f"## §{n}. 제목\n\n**2026-09-22**\n\n{body}\n\n### 배운 것\n\n무엇.\n"


def test_강제자는_108_부터_요구한다():
    old = "".join(_dec(i, "본문") for i in range(1, 108))
    f = []
    cd.check_decisions(old, f)
    assert f == [], "옛 절에 소급하면 안 된다"
    f = []
    cd.check_decisions(old + _dec(108, "본문"), f)
    assert any("§108" in x and "강제자" in x for x in f)
    f = []
    cd.check_decisions(old + _dec(108, "강제자 없음 — 설계 판단이다"), f)
    assert f == []


def test_날짜_없는_절이_걸린다():
    f = []
    cd.check_decisions("## §1. a\n\n본문\n\n### 배운 것\n", f)
    assert any("날짜" in x for x in f)


# ---------- 참조 ----------

def _tree(tmp_path, plan=PLAN, master="# m\n\n## 1. a\n\n### 1-1. b\n", dec=None, extra=None):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/PLAN.md").write_text(plan, encoding="utf-8")
    (tmp_path / "docs/MASTER.md").write_text(master, encoding="utf-8")
    (tmp_path / "docs/DECISIONS.md").write_text(dec or _dec(1, "본문"), encoding="utf-8")
    (tmp_path / "README.md").write_text(extra or "", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("line,bad", [
    ("(DECISIONS §1)", False),
    ("(DECISIONS §1 · §2)", True),          # 사슬의 뒤쪽도 본다
    ("(MASTER §1-1)", False),
    ("(MASTER §1-2)", True),
    ("PLAN #7", False),
    ("PLAN #8", True),
    ("PLAN §2", False),
    ("PLAN §9", True),
    ("(파이어레인 DECISIONS §205)", False),  # 남의 저장소
    ("(seshat PLAN #2)", False),
])
def test_참조가_실재해야_한다(tmp_path, line, bad):
    f = []
    cd.check_refs(_tree(tmp_path, extra=line), f)
    assert bool(f) is bad, f


# ---------- 실물 ----------

def test_없는_경로와_테스트가_걸린다(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/a.py").write_text("def check_x():\n    pass\n", encoding="utf-8")
    _tree(tmp_path, master="# m\n\n## 1. a\n\n`tools/a.py::check_x` · `tools/a.py::check_y` · `tools/b.py`\n")
    f = []
    fsck.check_paths(tmp_path, f)
    assert any("check_y" in x for x in f)
    assert any("tools/b.py" in x for x in f)
    assert not any("check_x" in x for x in f)


def test_어디서도_안_불리는_도구가_걸린다(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / "tools/used.py").write_text("", encoding="utf-8")
    (tmp_path / "tools/dead.py").write_text("", encoding="utf-8")
    (tmp_path / "README.md").write_text("python3 tools/used.py", encoding="utf-8")
    f = []
    fsck.check_tools(tmp_path, f)
    assert f == ["tools/dead.py 가 어디서도 불리지 않는다 — README 에 적거나 지운다"]
