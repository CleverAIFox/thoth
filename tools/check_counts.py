"""문서가 적은 건수를 실측과 대조한다.

  python3 tools/check_counts.py ext_tests=43 worker_tests=128

★ **정본은 실행이다.** 문서에 적힌 수는 파생물이고 이 검사가 둘을 묶는다.
  같은 숫자를 두 곳에 적으면 한쪽만 늙는다(DECISIONS §57). 늙지 않게 하는
  방법은 안 적는 것 아니면 **적되 묶는 것**이고, 여기는 후자를 택한다.

★ **표시된 것만 본다.** `<!--count:이름-->` 뒤의 정수만 주장으로 센다. PLAN 의
  ★ 문단은 과거 서술이라 옛 숫자가 있는 것이 정상이고, 표시가 없으므로 잡히지
  않는다. 검사 대상을 뭉뚱그리면 맞는 것을 위반으로 잡는다(DECISIONS §54).

★ **못 잰 것을 통과로 세지 않는다.** 실측이 넘어오지 않은 이름은 `못 잼` 이고
  종료 코드가 3 이다. 0 으로 끝내면 node 가 없는 기계에서 영영 통과한다
  (DECISIONS §47 · §59).

★ **모르는 이름은 실패다.** 표시를 오타내면 아무도 보지 않는 주장이 되어
  조용히 늙는다. 검사가 아무것도 하지 않는 것이 가장 위험하다(DECISIONS §21).

  0  표시된 주장을 전부 대조했고 같다
  1  다르다 · 모르는 이름이 있다
  2  도구가 죽었다
  3  일부를 재지 못했다
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 무엇을 재는 이름인지 여기에 적는다. 여기 없는 이름은 문서에 쓸 수 없다.
KNOWN = {
    "ext_tests": "확장 테스트 건수 — node --test 의 '# tests'",
    "worker_tests": "워커 테스트 건수 — pytest 통과 수",
}

MARK = re.compile(r"<!--count:(\w+)-->\s*([0-9]+)")


def claims(root: Path) -> list[tuple[str, str, int, int]]:
    """(문서, 이름, 줄번호, 주장한 수). 같은 이름이 여러 곳에 있어도 전부 센다."""
    out = []
    files = [root / "README.md"] + sorted((root / "docs").glob("*.md"))
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in MARK.finditer(line):
                out.append((f.name, m.group(1), n, int(m.group(2))))
    return out


def compare(found: list[tuple[str, str, int, int]],
            measured: dict[str, int]) -> tuple[int, list[str]]:
    """(종료 코드, 줄). **판정만 한다** — 읽지도 재지도 않는다."""
    bad, skipped, okn = [], [], 0
    for doc, name, line, said in found:
        if name not in KNOWN:
            bad.append(f"{doc}:{line} 모르는 이름 '{name}' — tools/check_counts.py 의 KNOWN 에 없다")
            continue
        if name not in measured:
            skipped.append(f"{doc}:{line} {name} 을 재지 못해 대조하지 않았다")
            continue
        if said != measured[name]:
            bad.append(f"{doc}:{line} {name} 문서 {said} · 실측 {measured[name]}")
        else:
            okn += 1

    if bad:
        return 1, bad + skipped
    if skipped:
        return 3, skipped
    return 0, ([f"주장 {okn}건이 실측과 같다"] if okn else ["표시된 주장이 없다"])


def parse_args(argv: list[str]) -> dict[str, int]:
    out = {}
    for a in argv:
        k, _, v = a.partition("=")
        # ★ 빈 값은 '재지 못했다' 로 본다. 셸에서 변수가 비면 `이름=` 이 그대로
        #   넘어오는데, 그것을 0 으로 읽으면 못 잰 것이 0건으로 둔갑한다.
        if not v.strip():
            continue
        out[k.strip()] = int(v)
    return out


def main(argv: list[str] | None = None) -> int:
    measured = parse_args(sys.argv[1:] if argv is None else argv)
    code, lines = compare(claims(ROOT), measured)
    for line in lines:
        print(f"    {line}")
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
