"""문서 규약 검사 — 2판(DECISIONS §111).

  python3 tools/check_docs.py          검사한다. 위반이면 1, 도구 고장이면 2
  python3 tools/check_docs.py --list   무엇을 보는지 찍는다

★ 단독 작업이라 강제자가 불필요하다는 초기 판단은 틀렸다. 세션이 바뀌면
  문맥이 초기화되므로 실제로는 여러 손이 같은 문서를 업서트하는 상황이고,
  그것이 강제자가 존재하는 조건이다(DECISIONS §9).

★ **2판은 파이어레인 · 하토르에서 옮겼다**(DECISIONS §111). 1판은 문체와 PLAN 전건만
  보았고, PLAN 표가 다섯 절에 흩어지고 절 번호 `## 6.` 이 두 번 나오고 해결된 경위가
  ★ 문단 102줄로 쌓이는 동안 초록이었다.

검사 대상은 **구조**다. 내용의 옳고 그름은 사람이 본다. 규약 본문은 MASTER §0 이고
규약마다 이 파일의 어느 검사가 강제자인지 거기 적혀 있다.

| 검사 | 무엇을 잡는가 |
|---|---|
| `check_style` | 1·2인칭 · 경어체 종결 · 대화체 |
| `check_headings` | `##` 에 번호가 없다 · 번호가 겹친다 · 연속이 아니다 |
| `check_plan` | 표가 §1 밖에 있다 · 제목의 행 수가 틀리다 · 번호가 겹치거나 역순이다 · 상태가 어휘 밖이다 · ⏳ 인데 막고 있는 것이 비었다 · 전건이 없는 번호다 |
| `check_refs` | `PLAN #N` · `PLAN §N` · `MASTER §x` · `DECISIONS §N` 이 없는 것을 가리킨다 |
| `check_master` | 미래형. 계획은 PLAN 에 적는다 |
| `check_decisions` | `배운 것` · 날짜가 없다 · 번호가 연속이 아니다 · §108 부터 `강제자` 가 없다 |

★ **정규식마다 카나리아가 있다**(`_canary`). 0건이 목표인 검사는 0건을 성공으로만 읽으면
  안 된다 — 깨끗해서인지 정규식이 죽어서인지 가를 수 없다. 1판의 `check_plan` 이 `^` 를
  MULTILINE 없이 써서 거의 아무것도 못 찾은 적이 있다(아래 `check_plan` 주석).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# ★ README 는 서술 규약에서 뺀다. 나머지 셋은 미래의 나를 향하고 README 는
#   처음 읽는 사람을 향한다. 대상이 다르면 문체도 다르다. 빠진 것이 아니라
#   뺀 것이다. **참조 검사는 README 도 본다** — 처음 읽는 사람이 죽은 링크를 만난다.
DOCS = ["docs/MASTER.md", "docs/PLAN.md", "docs/DECISIONS.md"]

# 1·2인칭. 문서는 3인칭으로 쓴다.
PERSON = re.compile(r"(?<![가-힣])(우리|저희|여러분|당신|제가|내가|너희)(?![가-힣])")
# 경어체 종결. 평어체 -다 로 쓴다.
POLITE = re.compile(r"(습니다|입니다|하세요|해요|합시다)\s*[.!?]?\s*$")
# 대화체·은어. 읽는 사람이 이 저장소만 보고도 이해해야 한다.
SLANG = ["딸깍", "개꿀", "ㅋㅋ", "ㅇㅋ", "에바", "싸개", "빡세", "쩐다", "개많", "노답"]
FUTURE = re.compile(r"(할 것이다|하겠다|예정이다|할 예정|계획이다)")

H2 = re.compile(r"^## (?!#)(.*)$", re.M)
H2_NUM = re.compile(r"^(\d+)\.\s")            # PLAN · MASTER
H2_DEC = re.compile(r"^§(\d+)\.\s")           # DECISIONS
HEAD_ANY = re.compile(r"^#{2,4} (\d+(?:-\d+[a-z]?)*)\.\s", re.M)

ROW = re.compile(r"^\| *(\d+) *\|")           # PLAN 항목 행
PLAN_S1 = re.compile(r"^## 1\. 남은 일 — (\d+)행\s*$", re.M)
# ★ **상태 어휘는 닫혀 있다**(파이어레인 PLAN §0-2). 닫힘 표식을 만들면 사람은 행을
#   지우는 대신 표식을 단다. `✅` · `⬛` 는 어휘 밖이다.
STATUS = {"📄", "🟡", "⏳", "⚠"}
CLOSED_MARKS = ("✅", "⬛", "해결됨", "완료")
PLAN_REF = re.compile(r"(?<![\w§-])#(\d+)(?!\d)")

# 다른 문서를 가리키는 참조. 문서명을 앞에 적는 것이 이 저장소의 규약이다(MASTER §0-2).
# ★ **이어 적은 번호도 본다.** `DECISIONS §98 · §110` 의 뒤쪽은 문서명 없이 온다.
#   앞만 보면 뒤쪽 오타가 검사 밖으로 빠진다. 사슬은 `§` 가 끊기면 멈춘다 —
#   `DECISIONS §98 · MASTER §7` 의 7 은 MASTER 몫이다.
REF_DEC = re.compile(r"DECISIONS\s*((?:§\s*\d+(?:\s*[·,]\s*)?)+)")
REF_MASTER = re.compile(r"MASTER(?:\.md)?\s*((?:§\s*\d+(?:-\d+[a-z]?)*(?:\s*[·,]\s*)?)+)")
SEC_NUM = re.compile(r"§\s*(\d+(?:-\d+[a-z]?)*)")
REF_PLAN_ROW = re.compile(r"PLAN(?:\.md)?\s*(?:§\s*[\d-]+\s*)?#\s*(\d+)")
REF_PLAN_SEC = re.compile(r"PLAN(?:\.md)?\s*§\s*(\d+)(?![\d-]*\s*#)")
DATE = re.compile(r"^\*\*20\d\d-\d\d-\d\d\*\*", re.M)
ENFORCER = re.compile(r"^강제자( 없음)? — ", re.M)

# ★ **강제자 줄은 §108 부터 요구한다.** 옛 절에 지금 강제자를 적으면 그때 하지 않은
#   판단을 사후에 지어내는 것이다(하토르 D-0081 — 내용은 신규만, 표기는 전수).
ENFORCER_FROM = 108

# ★ **남의 저장소를 가리키는 참조는 저장소 이름을 앞에 적는다.** `파이어레인 DECISIONS §205`
#   · `하토르 D-0117` · `seshat PLAN #2`. 이름이 붙은 참조는 이 저장소의 절이 아니므로
#   보지 않는다. 이름 없이 적으면 이 저장소의 것으로 읽고 검사한다.
SELF = "thoth"
REPOS = {"thoth": ("thoth", "토트"), "seshat": ("seshat", "세샤트"),
         "fire-lane": ("fire-lane", "파이어레인"), "hathor": ("hathor", "하토르")}
FOREIGN = tuple(a for k, v in REPOS.items() if k != SELF for a in v)


def _foreign(line: str, start: int) -> bool:
    head = line[max(0, start - 14):start].rstrip()
    return head.endswith(FOREIGN)


# 참조를 찾는 파일. 코드 주석도 문서다.
REF_DIRS = ("worker", "tools", "extension", "infra", ".github")
REF_SUFFIX = {".py", ".js", ".sh", ".md", ".json", ".tf", ".yml", ".html"}


def body_lines(text: str):
    """코드 블록과 인용 밖의 본문 줄만 돌려준다."""
    fence = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence or line.lstrip().startswith(">"):
            continue
        yield n, line


def check_style(name: str, text: str, fails: list) -> None:
    for n, line in body_lines(text):
        if m := PERSON.search(line):
            fails.append(f"{name}:{n} 1·2인칭 '{m.group(1)}'")
        # '합니다체' 처럼 문체 자체를 가리키는 표기는 검사에서 뺀다.
        if "합니다체" in line or "평어체" in line or "<!--voice-ok-->" in line:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line.strip()):
            if POLITE.search(sentence):
                fails.append(f"{name}:{n} 경어체 종결")
                break
        for word in SLANG:
            if word in line:
                fails.append(f"{name}:{n} 대화체 '{word}'")


def check_eof(name: str, text: str, fails: list) -> None:
    """파일 끝은 줄바꿈 하나다(DECISIONS §118). 빈 줄이 붙으면 `git apply` 가 경고를 낸다."""
    if not text.endswith("\n"):
        fails.append(f"{name} 끝에 줄바꿈이 없다")
    elif text.endswith("\n\n"):
        fails.append(f"{name} 끝에 빈 줄이 있다")


def _h2(text: str) -> list[tuple[int, str]]:
    """코드 블록 밖의 `## ` 제목. (줄 번호, 제목)."""
    return [(n, line[3:]) for n, line in body_lines(text) if line.startswith("## ")]


def check_headings(name: str, text: str, fails: list) -> None:
    """모든 `##` 에 번호가 있고, 겹치지 않고, 연속이다(파이어레인 MASTER §0-2).

    ★ 번호 없는 절은 밖에서 인용할 수 없다. 겹치는 번호는 인용이 두 곳을 가리킨다 —
      PLAN 이 한동안 `## 6. 이후 후보` 와 `## 6. 위험` 을 함께 들고 있었다.
    """
    pat = H2_DEC if name.endswith("DECISIONS.md") else H2_NUM
    nums = []
    for n, title in _h2(text):
        m = pat.match(title)
        if not m:
            fails.append(f"{name}:{n} 번호 없는 절 '## {title[:30]}'")
            continue
        nums.append(int(m.group(1)))
    seen = set()
    for x in nums:
        if x in seen:
            fails.append(f"{name} 절 번호 {x} 이 두 번 나온다")
        seen.add(x)
    if nums and sorted(set(nums)) != list(range(min(nums), max(nums) + 1)):
        fails.append(f"{name} 절 번호가 연속이 아니다: {nums}")
    if nums and nums != sorted(nums):
        fails.append(f"{name} 절 번호가 순서대로가 아니다: {nums}")


def plan_rows(text: str) -> tuple[list[tuple[int, list[str]]], list[int]]:
    """(§1 안의 행, §1 밖에서 찾은 행 번호).

    ★ finditer 로 훑지 않는다. `^` 는 MULTILINE 없이는 문자열 전체의 시작만 가리켜
      거의 매치되지 않는다. 1판의 `check_plan` 이 한 자리만 그렇게 깨져, 실재하는
      전건이 전부 없는 것으로 보고됐다. 줄 단위로 `ROW.match` 한다.
    """
    inside, outside, in_s1 = [], [], False
    for _, line in body_lines(text):
        if line.startswith("## "):
            in_s1 = line.startswith("## 1. ")
            continue
        m = ROW.match(line)
        if not m:
            continue
        if in_s1:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            inside.append((int(m.group(1)), cells))
        else:
            outside.append(int(m.group(1)))
    return inside, outside


def check_plan(text: str, fails: list) -> None:
    """PLAN §1 은 **남은 일의 유일한 표**다(파이어레인 PLAN §1 · DECISIONS §205).

    ★ **행 번호는 영구 식별자다.** 결번이 정상이고 지운 번호는 다시 쓰지 않는다. 당기면
      DECISIONS(append-only)의 인용이 조용히 다른 행을 가리킨다. 그래서 **오름차순 ·
      유일** 만 요구하고 연속은 요구하지 않는다.

    열: `| # | 상태 | 항목 | 전건 · 막고 있는 것 |`
    """
    rows, outside = plan_rows(text)
    if outside:
        fails.append(f"PLAN 표 행이 §1 밖에 있다: {outside} — 남은 일은 §1 하나에 둔다")
    m = PLAN_S1.search(text)
    if not m:
        fails.append("PLAN 에 '## 1. 남은 일 — N행' 제목이 없다")
    elif int(m.group(1)) != len(rows):
        fails.append(f"PLAN §1 제목은 {m.group(1)}행인데 표는 {len(rows)}행이다")
    nums = [n for n, _ in rows]
    if len(nums) != len(set(nums)):
        fails.append(f"PLAN 번호가 겹친다: {nums}")
    if nums != sorted(nums):
        fails.append(f"PLAN 번호가 오름차순이 아니다: {nums}")
    known = set(nums)
    for n, cells in rows:
        if len(cells) < 4:
            fails.append(f"PLAN #{n} 의 열이 넷이 아니다")
            continue
        status, item, deps = cells[1], cells[2], cells[3]
        marks = set(status.split())
        if not marks or not marks <= STATUS:
            fails.append(f"PLAN #{n} 의 상태 '{status}' 가 어휘 밖이다 — {' '.join(sorted(STATUS))}")
        if any(c in item or c in status for c in CLOSED_MARKS):
            fails.append(f"PLAN #{n} 에 닫힘 표시가 있다 — 닫힌 행은 지운다")
        if "⏳" in marks and not deps:
            fails.append(f"PLAN #{n} 이 ⏳ 인데 막고 있는 것이 비었다")
        for tok in PLAN_REF.findall(deps):
            if int(tok) not in known:
                fails.append(f"PLAN #{n} 의 전건 #{tok} 이 존재하지 않는다")
    # ★ **PLAN 본문의 `#N` 도 살아 있는 행을 가리켜야 한다.** 1판은 ★ 문단을 경위
    #   서술로 보고 뺐다. 그 틈으로 해결된 경위가 102줄 쌓였다. 닫힌 행의 행선지는
    #   DECISIONS 가 적는다 — PLAN 은 그것을 가리키지 않는다.
    for ln, line in body_lines(text):
        for m in PLAN_REF.finditer(line):
            head = line[:m.start()].rstrip()
            head = head[:-4].rstrip() if head.endswith("PLAN") else head
            if _foreign(head, len(head)):
                continue                # `seshat PLAN #2` 는 남의 행이다
            if int(m.group(1)) not in known:
                fails.append(f"PLAN.md:{ln} 가 없는 #{m.group(1)} 을 가리킨다")


def _targets(root: Path) -> list[Path]:
    out = [root / "README.md", root / "docs/MASTER.md", root / "docs/PLAN.md"]
    out += sorted((root / "docs/bench").glob("*")) if (root / "docs/bench").exists() else []
    for d in REF_DIRS:
        base = root / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if (p.is_file() and p.suffix in REF_SUFFIX and "__pycache__" not in p.parts
                    and "node_modules" not in p.parts and ".cache" not in p.parts):
                out.append(p)
    return out


def check_refs(root: Path, fails: list) -> None:
    """다른 문서를 가리키는 참조가 실재하는가.

    ★ **DECISIONS 본문은 보지 않는다.** 그때를 적는 문서이고 그때 있던 PLAN 행은 지금
      없는 것이 정상이다. 대신 **DECISIONS 를 가리키는 참조**는 어디서든 본다 —
      DECISIONS 는 지우지 않으므로 없는 절을 가리키면 오타다.
    ★ 1판은 `PLAN §x #N` 꼴만 보았다. `MASTER §x` 와 `DECISIONS §N` 은 아무도 보지 않았다.
    """
    plan = (root / "docs/PLAN.md").read_text(encoding="utf-8")
    master = (root / "docs/MASTER.md").read_text(encoding="utf-8")
    dec = (root / "docs/DECISIONS.md").read_text(encoding="utf-8")
    rows = {n for n, _ in plan_rows(plan)[0]}
    plan_secs = {int(m.group(1)) for _, t in _h2(plan) if (m := H2_NUM.match(t))}
    master_secs = set(HEAD_ANY.findall(master))
    dec_secs = {m.group(1) for m in re.finditer(r"^## §(\d+)\.", dec, re.M)}
    # ★ 이 파일과 그 검사의 예시 문자열은 참조가 아니다. 목록으로 못 박는다 —
    #   여기에 파일이 늘면 그만큼 검사 밖이 늘어난다.
    skip = {Path(__file__).resolve(), (root / "worker/tests/test_doc_enforcers.py").resolve()}
    for p in _targets(root):
        if p.resolve() in skip:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # ★ **다른 저장소에서 복사해 온 파일은 그 저장소의 참조를 든다.** 머리 세 줄에
        #   `사본이다` 를 적은 파일은 보지 않는다 — 고치면 사본이 원본과 갈린다.
        if "사본이다" in "\n".join(text.splitlines()[:3]):
            continue
        rel = p.relative_to(root)
        for n, line in enumerate(text.splitlines(), 1):
            for m in REF_DEC.finditer(line):
                if _foreign(line, m.start()):
                    continue
                for x in SEC_NUM.findall(m.group(1)):
                    if x not in dec_secs:
                        fails.append(f"{rel}:{n} 가 없는 DECISIONS §{x} 을 가리킨다")
            for m in REF_MASTER.finditer(line):
                if _foreign(line, m.start()):
                    continue
                for x in SEC_NUM.findall(m.group(1)):
                    if x not in master_secs:
                        fails.append(f"{rel}:{n} 가 없는 MASTER §{x} 을 가리킨다")
            for m in REF_PLAN_ROW.finditer(line):
                if _foreign(line, m.start()):
                    continue
                if int(m.group(1)) not in rows:
                    fails.append(f"{rel}:{n} 가 없는 PLAN #{m.group(1)} 을 가리킨다")
            for m in REF_PLAN_SEC.finditer(line):
                if _foreign(line, m.start()):
                    continue
                if int(m.group(1)) not in plan_secs:
                    fails.append(f"{rel}:{n} 가 없는 PLAN §{m.group(1)} 을 가리킨다")


def check_master(text: str, fails: list) -> None:
    """MASTER 는 완료된 사실만 담는다. 계획은 PLAN 이 담는다(DECISIONS §9)."""
    for i, line in body_lines(text):
        if FUTURE.search(line):
            fails.append(f"MASTER.md:{i} 미래형. 계획은 PLAN 에 적는다")


def check_decisions(text: str, fails: list) -> None:
    blocks = re.split(r"^## §", text, flags=re.M)[1:]
    if not blocks:
        fails.append("DECISIONS.md 에 '## §' 절이 없다")
    nums = []
    for b in blocks:
        num = b.splitlines()[0].split(".")[0].strip()
        if not num.isdigit():
            fails.append(f"DECISIONS §{num} 의 번호가 숫자가 아니다")
            continue
        nums.append(int(num))
        if "### 배운 것" not in b:
            fails.append(f"DECISIONS §{num} 에 '### 배운 것' 이 없다")
        if not DATE.search(b[:400]):
            fails.append(f"DECISIONS §{num} 에 날짜 줄(**YYYY-MM-DD**)이 없다")
        if int(num) >= ENFORCER_FROM and not ENFORCER.search(b):
            fails.append(f"DECISIONS §{num} 에 '강제자 — ' 또는 '강제자 없음 — 사유' 줄이 없다")
    if nums != list(range(1, len(nums) + 1)):
        fails.append(f"DECISIONS 절 번호가 연속이 아니다: {nums[:5]}…")


def _canary() -> None:
    """정규식이 살아 있는가. **양성 대조다.** 죽었으면 2 로 끝난다 — 위반(1)과 가른다."""
    plan = ("## 0. 규약\n\n## 1. 남은 일 — 2행\n\n| # | 상태 | 항목 | 전건 |\n|---|---|---|---|\n"
            "| 3 | 📄 | a | |\n| 7 | ⏳ | b | #3 |\n\n## 2. 범위 밖\n\n본문 #7\n")
    rows, out = plan_rows(plan)
    probes = {
        "ROW": [n for n, _ in rows] == [3, 7] and out == [],
        "PLAN_S1": PLAN_S1.search(plan) is not None,
        "PLAN_REF": PLAN_REF.findall("보라 #63 과 `#45`. a#9 · 1#2") == ["63", "45"],
        "REF_DEC": [SEC_NUM.findall(g) for g in REF_DEC.findall("(DECISIONS §98 · §110 · MASTER §7)")]
        == [["98", "110"]],
        "REF_MASTER": [SEC_NUM.findall(g) for g in REF_MASTER.findall("MASTER §7-4 · §7-0-2, DECISIONS §3")]
        == [["7-4", "7-0-2"]],
        "REF_PLAN_ROW": REF_PLAN_ROW.findall("PLAN §2-4 #25 · PLAN #59") == ["25", "59"],
        "REF_PLAN_SEC": REF_PLAN_SEC.findall("PLAN §4 · PLAN §2-4 #25") == ["4"],
        "HEAD_ANY": HEAD_ANY.findall("## 7. a\n### 7-4. b\n#### 11-18a. c\n") == ["7", "7-4", "11-18a"],
        "ENFORCER": bool(ENFORCER.search("x\n강제자 — `a.py`\n")),
        "FOREIGN": _foreign("(파이어레인 DECISIONS §199)", 7) and not _foreign("(DECISIONS §9)", 1),
    }
    f: list = []
    check_plan(plan, f)
    probes["check_plan 깨끗"] = f == []
    f = []
    check_plan(plan.replace("2행", "3행").replace("| 7 | ⏳ | b | #3 |", "| 7 | ✅ | b | |"), f)
    probes["check_plan 잡음"] = len(f) >= 3          # 행 수 · 어휘 · 닫힘 · ⏳ 빈 칸
    dead = [k for k, ok in probes.items() if not ok]
    if dead:
        print(f"    ★ 카나리아가 죽었다 — {dead}. 검사가 아무것도 못 찾는 상태다")
        sys.exit(2)


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _canary()
    if "--list" in args:
        print(__doc__)
        return 0
    fails: list[str] = []
    texts = {}
    for rel in DOCS:
        p = ROOT / rel
        if not p.exists():
            fails.append(f"{rel} 가 없다")
            continue
        texts[rel] = p.read_text(encoding="utf-8")
        check_style(p.name, texts[rel], fails)
        check_headings(p.name, texts[rel], fails)
        check_eof(p.name, texts[rel], fails)
    if len(texts) == len(DOCS):
        check_plan(texts["docs/PLAN.md"], fails)
        check_master(texts["docs/MASTER.md"], fails)
        check_decisions(texts["docs/DECISIONS.md"], fails)
        check_refs(ROOT, fails)
    for f in fails:
        print(f"    {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다. 같은 코드면 검사가
    #   깨진 것을 문서가 틀린 것으로 읽는다(DECISIONS §21).
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
