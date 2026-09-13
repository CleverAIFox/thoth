"""문서 서술 규약 검사.

★ 단독 작업이라 강제자가 불필요하다는 초기 판단은 틀렸다. 세션이 바뀌면
  문맥이 초기화되므로 실제로는 여러 손이 같은 문서를 업서트하는 상황이고,
  그것이 강제자가 존재하는 조건이다(DECISIONS §9).

검사 대상은 문체와 구조뿐이다. 내용의 옳고 그름은 사람이 본다.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# ★ README 는 서술 규약에서 뺀다. 나머지 셋은 미래의 나를 향하고 README 는
#   처음 읽는 사람을 향한다. 대상이 다르면 문체도 다르다. 빠진 것이 아니라
#   뺀 것이다.
DOCS = ["docs/MASTER.md", "docs/PLAN.md", "docs/DECISIONS.md"]

# 문서마다 불변식이 다르므로 검사도 다르다. 아래는 문서별 고유 검사다.
ROW = re.compile(r"^\| *(\d+) *\|")           # PLAN 항목 행
DEPS = re.compile(r"^\| *\d+ *\|[^|]*\|[^|]*\| *([^|]*?) *\|")
FUTURE = re.compile(r"(할 것이다|하겠다|예정이다|할 예정|계획이다)")

# 1·2인칭. 문서는 3인칭으로 쓴다.
PERSON = re.compile(r"(?<![가-힣])(우리|저희|여러분|당신|제가|내가|너희)(?![가-힣])")

# 경어체 종결. 평어체 -다 로 쓴다.
POLITE = re.compile(r"(습니다|입니다|하세요|해요|합시다)\s*[.!?]?\s*$")

# 대화체·은어. 읽는 사람이 이 저장소만 보고도 이해해야 한다.
SLANG = ["딸깍", "개꿀", "ㅋㅋ", "ㅇㅋ", "에바", "싸개", "빡세", "쩐다", "개많", "노답"]


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


def check_style(path: Path, fails: list):
    text = path.read_text(encoding="utf-8")
    for n, line in body_lines(text):
        if m := PERSON.search(line):
            fails.append(f"{path.name}:{n} 1·2인칭 '{m.group(1)}'")
        # '합니다체' 처럼 문체 자체를 가리키는 표기는 검사에서 뺀다.
        if "합니다체" in line or "평어체" in line:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line.strip()):
            if POLITE.search(sentence):
                fails.append(f"{path.name}:{n} 경어체 종결")
                break
        for word in SLANG:
            if word in line:
                fails.append(f"{path.name}:{n} 대화체 '{word}'")


def check_plan(path: Path, fails: list):
    """전건은 존재하는 번호를 가리켜야 한다.

    ★ 해결된 항목을 행째로 지우면(DECISIONS §18) 그것을 전건으로 걸어 둔
      항목이 없는 번호를 가리키게 된다. 2026-09-13 에 #7 을 지우고 #41 · #43
      이 실제로 깨졌으며 사람이 지적할 때까지 아무도 몰랐다.
    """
    # ★ finditer 로 훑지 않는다. ROW 의 ^ 는 MULTILINE 없이는 문자열 전체의
    #   시작만 가리켜 거의 매치되지 않는다. 아래 루프는 ROW.match(line) 이라
    #   정상인데 여기만 깨져, 실재하는 전건이 전부 없는 것으로 보고됐다.
    #   같은 정규식을 두 방식으로 쓰지 않는다.
    lines = path.read_text(encoding="utf-8").splitlines()
    nums = {int(m.group(1)) for line in lines if (m := ROW.match(line))}
    seen = set()
    for line in lines:
        m = ROW.match(line)
        if not m:
            continue
        n = int(m.group(1))
        if n in seen:
            fails.append(f"PLAN #{n} 이 두 번 나온다. 번호는 재사용하지 않는다")
        seen.add(n)
        d = DEPS.match(line)
        if not d:
            continue
        # ★ '§3 #24' 는 다른 절의 항목을 가리킨다. 이 표의 번호가 아니므로
        #   빼고 본다. 절 참조까지 검사하려면 문서 전체의 번호를 모아야 하는데,
        #   PLAN 의 번호는 절 안에서만 유일하다.
        deps = re.sub(r"§\s*\d+\s*#\s*\d+", "", d.group(1))
        for tok in re.findall(r"\d+", deps):
            if int(tok) not in nums:
                fails.append(f"PLAN #{n} 의 전건 {tok} 이 존재하지 않는다")


def check_master(path: Path, fails: list):
    """MASTER 는 완료된 사실만 담는다.

    ★ 계획은 PLAN 이 담는다. 같은 사실이 두 곳에 살면 한쪽만 고쳐질 때
      정본을 알 수 없다(DECISIONS §9).
    """
    for i, line in body_lines(path.read_text(encoding="utf-8")):
        if FUTURE.search(line):
            fails.append(f"{path.name}:{i} 미래형. 계획은 PLAN 에 적는다")


def check_decisions(path: Path, fails: list):
    """각 절이 '배운 것' 을 가져야 한다. 없으면 이 문서에 올 항목이 아니다."""
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"^## §", text, flags=re.M)[1:]
    if not blocks:
        fails.append("DECISIONS.md 에 '## §' 절이 없다")
    seen = []
    for b in blocks:
        head = b.splitlines()[0]
        num = head.split(".")[0].strip()
        seen.append(num)
        if "### 배운 것" not in b:
            fails.append(f"DECISIONS §{num} 에 '### 배운 것' 이 없다")
    nums = [int(x) for x in seen if x.isdigit()]
    if nums != list(range(1, len(nums) + 1)):
        fails.append(f"DECISIONS 절 번호가 연속이 아니다: {nums}")


def check_refs(root: Path, fails: list):
    """코드와 부속 문서가 가리키는 PLAN 번호가 실재하는지 본다.

    ★ PLAN 은 해결된 항목을 행째로 지우고 번호를 재사용하지 않는다(§18).
      그러면 그 번호를 인용해 둔 코드 주석은 영영 빈 곳을 가리킨다.
      `check_plan` 은 PLAN 안의 전건만 보므로 바깥에서 들어오는 참조는
      아무도 보지 않았고, 실제로 `#13` 을 지운 뒤 `broker.js` 와
      `udemy.js` 가 깨진 채로 남아 있었다(DECISIONS §29).

    ★ 절 참조(`PLAN §4`)는 검사하지 않는다. 절은 주제로 나뉘어 안정적이고,
      번호가 사라지는 것은 항목뿐이다. 대상을 뭉뚱그리면 맞는 것을 위반으로
      잡는다(§22).
    """
    plan = (root / "docs/PLAN.md").read_text(encoding="utf-8").splitlines()
    nums = {int(m.group(1)) for line in plan if (m := ROW.match(line))}

    targets = ["README.md"]
    for d in ("worker", "tools", "extension"):
        for p in sorted((root / d).rglob("*")):
            if p.is_file() and p.suffix in {".py", ".js", ".sh", ".md", ".json"} \
               and "__pycache__" not in p.parts and ".cache" not in p.parts:
                targets.append(str(p.relative_to(root)))

    ref = re.compile(r"PLAN\s+§[\d-]+\s*#\s*(\d+)")
    for rel in targets:
        p = root / rel
        if not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in ref.finditer(line):
                if int(m.group(1)) not in nums:
                    fails.append(f"{rel}:{n} 가 없는 PLAN #{m.group(1)} 을 가리킨다")


def main() -> int:
    fails: list[str] = []
    for rel in DOCS:
        p = ROOT / rel
        if not p.exists():
            fails.append(f"{rel} 가 없다")
            continue
        check_style(p, fails)
    check_plan(ROOT / "docs/PLAN.md", fails)
    check_refs(ROOT, fails)
    check_master(ROOT / "docs/MASTER.md", fails)
    d = ROOT / "docs/DECISIONS.md"
    if d.exists():
        check_decisions(d, fails)

    for f in fails:
        print(f"    {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다. 같은 코드면 검사가
    #   깨진 것을 문서가 틀린 것으로 읽는다(DECISIONS §21).
    try:
        sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
