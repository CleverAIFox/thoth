"""문서가 적은 건수를 실측과 대조한다.

  python3 tools/check_counts.py ext_tests=43 worker_tests=128

★ **정본은 실행이다.** 문서에 적힌 수는 파생물이고 이 검사가 둘을 묶는다.
  같은 숫자를 두 곳에 적으면 한쪽만 늙는다(DECISIONS §57). 늙지 않게 하는
  방법은 안 적는 것 아니면 **적되 묶는 것**이고, 여기는 후자를 택한다.

★ **표시된 것만 본다.** `<!--count:이름-->` 뒤의 정수만 주장으로 센다. PLAN 의
  ★ 문단은 과거 서술이라 옛 숫자가 있는 것이 정상이고, 표시가 없으므로 잡히지
  않는다. 검사 대상을 뭉뚱그리면 맞는 것을 위반으로 잡는다(DECISIONS §54).

★ **천 단위 쉼표를 받는다** — 문서는 `2,472` 로 쓴다(DECISIONS §202). 꼴이 어긋난
  `2,47` 은 **앞자리만 읽지 않고 못 읽었다고 말한다** — 앞자리를 값으로 쓰면
  「문서 2 · 실측 2472」 같은 **까닭이 거짓인 빨강**이 되고, 운 나쁘면 초록이 된다(§59).

★ **못 잰 것을 통과로 세지 않는다.** 실측이 넘어오지 않은 이름은 `못 잼` 이고
  종료 코드가 3 이다. 0 으로 끝내면 node 가 없는 기계에서 영영 통과한다
  (DECISIONS §47 · §59).

★ **모르는 이름은 실패다.** 표시를 오타내면 아무도 보지 않는 주장이 되어
  조용히 늙는다. 검사가 아무것도 하지 않는 것이 가장 위험하다(DECISIONS §21).

★ **밖 — 표시 없는 수는 안 본다.** `<!--count:이름-->` 뒤의 정수만 주장으로 세므로,
  문서가 **표시 없이** 적은 수가 틀려도 **안 잡는다.** 그것은 `docgen` 류의 일이다.
★ **밖 — 「그 수를 세는 법이 맞나」 는 안 묻는다.** 넘어온 실측이 옳다고 보고 대조만 한다.

  0  표시된 주장을 전부 대조했고 같다
  1  다르다 · 모르는 이름이 있다 · 수의 꼴이 어긋났다
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
    # ★ MASTER 0-8 의 표가 글자로 박은 수다. skip 하나를 더하면 세 수가 한꺼번에
    #   늙는다 — 하루 만에 그렇게 됐다(DECISIONS §152). 정본은 `check_skips.세기`.
    "skip_all": "doctor 의 skip 자리 전부 — check_skips.py --세기",
    "skip_seen": "그중 갈래가 참말인지까지 보는 것 (도구 + 범위)",
    "skip_tool": "갈래 '도구' 자리 수",
    "skip_scope": "갈래 '범위' 자리 수",
    "skip_cond": "갈래 '조건' 자리 수",
    "skip_debt": "갈래 '빚' 자리 수",
    # ★ **첫 줄은 `meta` 머리라 뺀다**(DECISIONS §201). 세는 자가 머리를 세면 늘 하나 많다 —
    #   문서는 2,472 로 옳았고 `wc -l` 은 2,473 이다. **둘 다 맞는 수인데 세는 것이 다르다.**
    "endings_corpus": "어미 코퍼스 줄 — corpus.jsonl 의 자료 줄(meta 머리 제외)",
}

# ★ **쉼표까지 한 덩어리로 집는다.** `([0-9]+)` 로 끊으면 `2,472` 에서 `2` 만 집고
#   그것이 **값으로 둔갑한다** — 2026-10-20 에 「문서 2 · 실측 2472」 로 났다.
#   덩어리로 집고 꼴은 `묶음` 이 따로 본다. **집는 일과 판정하는 일을 안 섞는다.**
MARK = re.compile(r"<!--count:(\w+)-->\s*([0-9][0-9,]*)")
묶음 = re.compile(r"^(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)$")
"""옳은 꼴. 세 자리마다 쉼표이거나, 쉼표가 아예 없다."""


def 읽는다(글자: str) -> int | None:
    """표시 뒤의 수. **꼴이 어긋나면 `None`** — 「못 읽었다」 는 값이 아니다(§59)."""
    return int(글자.replace(",", "")) if 묶음.match(글자) else None


def claims(root: Path) -> list[tuple[str, str, int, int | None]]:
    """(문서, 이름, 줄번호, 주장한 수). 같은 이름이 여러 곳에 있어도 전부 센다.
    **수가 `None` 이면 꼴이 어긋난 것**이고, 그 자리는 `compare` 가 실패로 만든다."""
    out = []
    files = [root / "README.md"] + sorted((root / "docs").glob("*.md"))
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in MARK.finditer(line):
                out.append((f.name, m.group(1), n, 읽는다(m.group(2))))
    return out


def compare(found: list[tuple[str, str, int, int | None]],
            measured: dict[str, int]) -> tuple[int, list[str]]:
    """(종료 코드, 줄). **판정만 한다** — 읽지도 재지도 않는다."""
    bad, skipped, okn = [], [], 0
    for doc, name, line, said in found:
        if said is None:
            bad.append(f"{doc}:{line} {name} 의 수가 꼴이 어긋났다 — "
                       f"세 자리마다 쉼표이거나 쉼표가 없어야 한다")
            continue
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



def 고친다(root: Path, measured: dict[str, int]) -> list[str]:
    """표시된 수를 실측으로 **갈아 쓴다**. 고친 자리를 돌려준다.

    ★ **doctor 는 실측을 아는데 문서는 사람이 고쳤다**(DECISIONS §180). 그래서 늙는다 —
      2026-10-10 하루에 `ext_tests` 와 `worker_tests` 가 **둘 다** 늙었고, 이 관문이 둘 다
      잡았다. **잡는 것과 고치는 것은 다른 일**이고, 잡기만 하면 사람이 손으로 옮겨 적는다.

    ★ **모르는 이름은 안 고친다.** 오타를 조용히 박제하면 그 주장은 영영 안 읽힌다.
    ★ **못 잰 이름도 안 고친다** — 「못 쟀다」 를 값으로 바꾸면 거짓이 된다(§59).
    """
    고침: list[str] = []
    files = [root / "README.md"] + sorted((root / "docs").glob("*.md"))
    for f in files:
        try:
            글 = f.read_text(encoding="utf-8")
        except OSError:
            continue
        def 바꾼다(m: re.Match) -> str:
            이름, 글자 = m.group(1), m.group(2)
            적힌 = 읽는다(글자)
            if 이름 not in KNOWN or 이름 not in measured:
                return m.group(0)
            잰것 = measured[이름]
            if 적힌 == 잰것:
                return m.group(0)
            # ★ **적힌 꼴을 지킨다.** 쉼표로 쓰던 자리를 `2472` 로 갈아 쓰면 **고치는 자가
            #   문서의 글꼴을 흐트러뜨린다** — 다음 사람이 손으로 쉼표를 되돌리고, 그러면
            #   이 자가 또 운다. 꼴이 어긋난 자리(`적힌` 이 `None`)는 쉼표 없이 쓴다.
            새글자 = f"{잰것:,}" if (적힌 is not None and "," in 글자) else str(잰것)
            고침.append(f"{f.name} {이름} {글자} → {새글자}")
            return m.group(0)[: m.start(2) - m.start(0)] + 새글자
        새 = MARK.sub(바꾼다, 글)
        if 새 != 글:
            f.write_text(새, encoding="utf-8")
    return 고침


def _canary() -> None:
    """★ **판별식이 사나.** 표시를 못 읽으면 **주장이 0 건**이 되고, 그러면 **아무것도 대조
    안 하고 초록**이 된다 — 0 이 목표인 검사의 가장 흔한 죽음이다."""
    import sys
    if MARK.findall("<!--count:x-->12 와 <!--count:y-->3") != [("x", "12"), ("y", "3")]:
        print("    ★ 카나리아가 죽었다 — 표시를 못 읽는다"); sys.exit(2)
    if MARK.findall("count:x 12"):
        print("    ★ 카나리아가 죽었다 — 표시 없는 수를 주장으로 센다"); sys.exit(2)
    # ★ **쉼표** — 덩어리로 집고 값으로 읽는다. 앞자리만 읽으면 2026-10-20 의 그 빨강이다
    if MARK.findall("<!--count:x-->2,472줄") != [("x", "2,472")]:
        print("    ★ 카나리아가 죽었다 — 쉼표에서 수를 끊는다"); sys.exit(2)
    if 읽는다("2,472") != 2472:
        print("    ★ 카나리아가 죽었다 — 천 단위 쉼표를 못 읽는다"); sys.exit(2)
    # 반대 통제 — **꼴이 어긋난 것을 값으로 읽지 않는다**. `247` 로 읽으면 조용히 틀린다
    if 읽는다("2,47") is not None:
        print("    ★ 카나리아가 죽었다 — 어긋난 꼴을 값으로 읽는다"); sys.exit(2)
    if 읽는다("1121") != 1121:
        print("    ★ 카나리아가 죽었다 — 쉼표 없는 수를 못 읽는다"); sys.exit(2)

def main(argv: list[str] | None = None) -> int:
    _canary()
    if "--selftest" in (sys.argv[1:] if argv is None else argv):
        print("  프로브 살아 있다 — 표시를 읽고, 표시 없는 수는 안 센다")
        return 0
    args = sys.argv[1:] if argv is None else argv
    measured = parse_args(args)
    if "--fix" in args:
        # ★ **고치고 나서 다시 센다.** 고쳤다고 말만 하고 안 보면, 안 고쳐진 자리가 남는다.
        for x in 고친다(ROOT, measured):
            print(f"    고쳤다 — {x}")
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
