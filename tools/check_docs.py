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
DOCS = ["docs/MASTER.md", "docs/PLAN.md", "docs/DECISIONS.md"]

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


def main() -> int:
    fails: list[str] = []
    for rel in DOCS:
        p = ROOT / rel
        if not p.exists():
            fails.append(f"{rel} 가 없다")
            continue
        check_style(p, fails)
    d = ROOT / "docs/DECISIONS.md"
    if d.exists():
        check_decisions(d, fails)

    for f in fails:
        print(f"    {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
