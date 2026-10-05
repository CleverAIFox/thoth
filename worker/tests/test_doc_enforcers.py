"""문서 강제자의 검사(DECISIONS §111). **강제자가 죽으면 문서는 조용히 늙는다.**

★ 양성과 음성을 함께 본다. 깨끗한 합성 문서가 통과하는가, 그리고 **규칙마다 하나씩 어긴
  문서가 그 규칙으로 걸리는가.** 음성만 있으면 무엇이든 잡는 검사가, 양성만 있으면 아무것도
  못 잡는 검사가 초록이다.
"""
import importlib.util
import pathlib
import subprocess

import pytest

# ★ 저장소 뿌리를 위치로 찾지 않는다. 이 파일은 seshat 에 사본으로 가고 거기서는 깊이가 다르다.
ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/check_docs.py").exists())


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
    (("#7 을 본다.", "#7 과 파이어레인 PLAN #9 · 하토르 #8 을 본다. #9"), "없는 #9"),
    (("없다.", "| 9 | 📄 | 다 | |"), "§1 밖"),
    (("## 1. 남은 일 — 2행", "## 1. 남은 일"), "제목이 없다"),
])
def test_PLAN_규칙마다_걸린다(change, want):
    bad = PLAN.replace(*change)
    assert bad != PLAN, "치환이 먹지 않았다 — 검사의 검사가 빈손이다"
    assert any(want in f for f in plan_fails(bad)), plan_fails(bad)


def test_남의_저장소_행은_보지_않는다():
    # ★ 예시 이름은 파이어레인 · 하토르다. 이 파일은 seshat 에 사본으로 가고, 거기서
    #   `seshat` 은 자기 이름이다.
    assert plan_fails(PLAN.replace("#7 을 본다.", "파이어레인 PLAN #9 · 하토르 #8 을 본다.")) == []


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


# ---------- 파일 끝 ----------

@pytest.mark.parametrize("tail,want", [("끝.\n", None), ("끝.\n\n", "빈 줄"), ("끝.", "줄바꿈이 없다")])
def test_파일_끝은_줄바꿈_하나다(tail, want):
    f = []
    cd.check_eof("X.md", "# t\n\n" + tail, f)
    assert (f == []) if want is None else any(want in x for x in f), f


# ---------- DECISIONS ----------

def _dec(n, body):
    return f"## §{n}. 제목\n\n**2026-09-22**\n\n{body}\n\n### 배운 것\n\n무엇.\n"


def test_강제자는_정한_절부터_요구한다():
    n = cd.ENFORCER_FROM
    old = "".join(_dec(i, "본문") for i in range(1, n))
    if old:
        f = []
        cd.check_decisions(old, f)
        assert f == [], "옛 절에 소급하면 안 된다"
    f = []
    cd.check_decisions(old + _dec(n, "본문"), f)
    assert any(f"§{n}" in x and "강제자" in x for x in f)
    f = []
    cd.check_decisions(old + _dec(n, "강제자 없음 — 설계 판단이다"), f)
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
    ("(하토르 PLAN #2)", False),       # 이 사본이 어느 저장소에 있든 남의 것인 이름
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


def test_사본은_원본의_참조를_들어도_된다(tmp_path):
    # ★ 다른 저장소에서 복사한 파일을 고치면 원본과 갈린다. 머리에 `사본이다` 가 있으면 뺀다.
    root = _tree(tmp_path)
    (root / "tools").mkdir()
    (root / "tools/copy.py").write_text("# ★ 저쪽의 사본이다.\n# (DECISIONS §999)\n", encoding="utf-8")
    (root / "tools/mine.py").write_text("# (DECISIONS §999)\n", encoding="utf-8")
    f = []
    cd.check_refs(root, f)
    assert [x for x in f if "copy.py" in x] == []
    assert any("mine.py" in x for x in f)


# ── 강제자 바닥 — 내려가기만 한다 (DECISIONS §158) ────────────────────────

def test_강제자_바닥이_실제와_맞다():
    """★ **이 수는 손으로 못 올린다.** 실제로 **연속해서** 강제자를 든 가장 낮은 번호와
    맞댄다 — 묶음을 채우면 **내려가야 하고**, 올리면 운다.

    ★ 「강제자 — X」 는 **「지금 이 결정을 지키는 자가 누구인가」** 다. 그때의 판단이 아니라
      지금의 사실이므로 **표기**이고 소급해야 한다(하토르 D-0081 — 「표기는 전수 강제하고
      내용만 신규에 건다」). `강제자 없음 — 까닭` 이라는 꼴이 따로 있는 것이 그 증거다.

    ★ **바닥이 1 이다**(2026-10-05 · DECISIONS §159). 한 판에 §1~§89 를 쓰고 22줄이 틀렸고
      `doc_fsck.check_enforcer_quotes` 가 전부 잡았다. 이제 이 수가 움직이는 유일한 길은
      **강제자 줄을 지우는 것**이고, 그러면 이 시험이 운다.
    """
    import importlib.util
    import re
    s = importlib.util.spec_from_file_location("cd2", ROOT / "tools/check_docs.py")
    CD2 = importlib.util.module_from_spec(s)
    s.loader.exec_module(CD2)
    글 = (ROOT / "docs/DECISIONS.md").read_text(encoding="utf-8")
    절 = [(int(m.group(1)), m.start()) for m in re.finditer(r"^## §(\d+)\. ", 글, re.M)]
    번호 = [n for n, _ in 절]
    든다 = set()
    for i, (n, st) in enumerate(절):
        끝 = 절[i + 1][1] if i + 1 < len(절) else len(글)
        if CD2.ENFORCER.search(글[st:끝]):
            든다.add(n)
    바닥 = max(번호) + 1
    for n in sorted(번호, reverse=True):
        if n not in 든다:
            break
        바닥 = n
    assert CD2.ENFORCER_FROM == 바닥, (
        f"`ENFORCER_FROM` 이 {CD2.ENFORCER_FROM} 인데 실제로 연속해서 든 가장 낮은 번호는 "
        f"{바닥} 이다 — 채웠으면 내리고, 올렸으면 되돌린다")


# ── 강제자 줄의 인용(DECISIONS §159) ──────────────────────────────────────────
#
# ★ **건초가 「그 줄이 적은 파일」 이라는 것이 이 검사의 전부다.** 저장소 전체를 보면
#   §159 의 25건 중 **한 건도 안 잡힌다** — 전부 저장소 안에는 있었다.

def _절(강제자: str, n: int | None = None) -> str:
    n = fsck.ENFORCER_FROM if n is None else n
    return (f"## §{n}. 제목\n\n**2026-10-05**\n\n본문\n\n### 배운 것\n\n무엇.\n\n"
            f"---\n\n{강제자}\n")


def _심는다(tmp_path, 강제자: str, n: int | None = None):
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "tools").mkdir(exist_ok=True)
    (tmp_path / "docs/DECISIONS.md").write_text(_절(강제자, n), encoding="utf-8")
    f: list = []
    fsck.check_enforcer_quotes(tmp_path, f)
    return f


def test_인용이_그_파일_안을_본다(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/a.py").write_text(
        "def test_있다():\n    pass\n# 레이블 가\n", encoding="utf-8")
    assert _심는다(tmp_path, "강제자 — `tools/a.py` 의 `test_있다` · `레이블 가`") == []
    f = _심는다(tmp_path, "강제자 — `tools/a.py` 의 `test_없다` · `레이블 나`")
    assert any("test_없다" in x for x in f), f
    assert any("레이블 나" in x for x in f), f


def test_저장소_어딘가에_있는_것으로는_안_통한다(tmp_path):
    # ★ §159 의 실제 꼴이다 — 이름은 실재하고 **다른 파일**에 있었다.
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/a.py").write_text("# 비었다\n", encoding="utf-8")
    (tmp_path / "tools/b.py").write_text("def test_있다():\n    pass\n", encoding="utf-8")
    f = _심는다(tmp_path, "강제자 — `tools/a.py` 의 `test_있다`")
    assert any("test_있다" in x for x in f), "저장소 안에 있다고 통과시키면 §159 가 재발한다"


def test_이어진_강제자_줄도_본다(tmp_path):
    # ★ §158 의 강제자는 세 줄이고 **시험 이름이 둘째 줄에 있다.**
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/a.py").write_text("def test_있다():\n    pass\n", encoding="utf-8")
    f = _심는다(tmp_path, "강제자 — `tools/a.py` 의\n`test_없다`")
    assert any("test_없다" in x for x in f), "둘째 줄의 인용이 검사 밖이면 안 된다"


def test_강제자_없음_줄도_인용을_본다(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/a.py").write_text("# 비었다\n", encoding="utf-8")
    f = _심는다(tmp_path, "강제자 없음 — `tools/a.py` 의 `test_없다` 가 그 일을 한다")
    assert any("test_없다" in x for x in f)


def test_파일을_안_적은_줄은_안_본다(tmp_path):
    # ★ 맞댈 자리가 없다. 저장소 전체로 넓히면 그것이 §159 의 거짓 초록이다.
    assert _심는다(tmp_path, "강제자 없음 — `pgrep` 이 무엇을 찾는지는 그 기계가 정한다") == []


def test_파일처럼_안_생긴_토막은_파일로_안_센다(tmp_path):
    # ★ `.env.example` 은 `TOP/` 밖이지만 파일이다. 못 보면 레이블이 **엉뚱한 파일**과
    #   맞대져 거짓 빨강이 난다(§124).
    파일, 시험, 레이블 = fsck.인용("강제자 — `.env.example` 의 `KEY_A` · `output -raw`")
    assert 파일 == [".env.example"]
    assert 시험 == []
    assert 레이블 == ["KEY_A"], 레이블


def test_실제_저장소의_강제자_인용이_전부_참말이다():
    f: list = []
    fsck.check_enforcer_quotes(ROOT, f)
    assert f == [], "\n".join(f)


# ── 표기는 전수 · 본문은 추가만(DECISIONS §159) ────────────────────────────────

def test_강제자_줄은_고쳐도_본문_수정이_아니다():
    옛 = _dec(1, "본문") + "\n---\n\n강제자 — `tools/a.py` 의 `옛 레이블`\n"
    새 = _dec(1, "본문") + "\n---\n\n강제자 — `tools/a.py` 의 `새 레이블`\n"
    assert cd.본문_수정(옛, 새) == []


def test_본문을_고치면_걸린다():
    옛 = _dec(1, "본문 가") + "\n---\n\n강제자 — `tools/a.py`\n"
    새 = _dec(1, "본문 나") + "\n---\n\n강제자 — `tools/a.py`\n"
    f = cd.본문_수정(옛, 새)
    assert any("본문 가" in x for x in f), f


def test_이어진_강제자_줄도_표기로_센다():
    # ★ §158 의 강제자는 세 줄이다. 둘째 줄을 본문으로 세면 그것만 고쳐도 운다.
    옛 = _dec(1, "본문") + "\n---\n\n강제자 — `tools/a.py` 의\n`옛것` · `또`\n"
    새 = _dec(1, "본문") + "\n---\n\n강제자 — `tools/a.py` 의\n`새것`\n"
    assert cd.본문_수정(옛, 새) == []


def test_절을_더하는_것은_수정이_아니다():
    옛 = _dec(1, "본문")
    assert cd.본문_수정(옛, 옛 + _dec(2, "본문")) == []


def test_실제_저장소의_본문이_추가만_되었다():
    r = subprocess.run(["git", "show", "HEAD:docs/DECISIONS.md"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        pytest.skip("조건 — HEAD 에 DECISIONS 가 없다 (얕은 사본 · 첫 커밋)")
    f = cd.본문_수정(r.stdout, (ROOT / "docs/DECISIONS.md").read_text(encoding="utf-8"))
    assert f == [], "\n".join(f)


def test_대조할_옛것이_없으면_3_이다():
    # ★ **못 잼을 통과로 세지 않는다**(DECISIONS §47 · §59). 0 으로 끝내면 얕은 사본에서
    #   영영 통과하고, 그 초록은 「본문이 안 고쳐졌다」 를 뜻하지 않는다.
    r = subprocess.run(["python3", str(ROOT / "tools/check_docs.py"), "--추가만"],
                       input="", capture_output=True, text=True)
    assert r.returncode == 3, (r.returncode, r.stdout, r.stderr)
