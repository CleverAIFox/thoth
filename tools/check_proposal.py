r"""**기획서 본문이 제 자리를 지키나** — 틀린 모양이 **존재할 수 없게** 한다(DECISIONS §155).

  python3 tools/check_proposal.py            본다. 위반이면 1, 도구 고장이면 2
  python3 tools/check_proposal.py --list     지금 블록과 수를 찍는다
  python3 tools/check_proposal.py --selftest 판별식이 살아 있나

★ **「틀린 걸 잡는다」 와 「틀린 모양이 존재할 수 없다」 는 다른 말이다.** 본문(`part*.js`)이
  `docx` 를 직접 만질 수 있으면 **렌더러를 하나 더 붙일 수 없다** — 두 번째 렌더러가 그
  줄을 못 읽는다. 셋을 본다.

| | 묻는 것 |
|---|---|
| **문** | `part*.js` 가 `./lib` 말고 다른 것을 부르는가 · 렌더러의 것(`D` · `t` · `W` …)을 가져가는가 |
| **블록** | 가짜 `lib` 으로 끝까지 도는가 · 선언 밖 블록을 쓰는가 · `docx` 를 만지는가 |
| **수** | 산문에 든 **단위를 가진 수**가 장부에 있는가 — **늘면 막는다** |

★ **「문」 은 글자가 아니라 `require` 와 구조분해로 본다.** 첫 판은 정규식으로 `\bD\b\.` 를
  찾았는데 **표 칸의 `"D. 호스팅 LLM …"` 이 걸렸다** — 글자로는 뜻이 안 갈린다.

★ **「블록」 은 실행으로 본다.** `docs/proposal/extract.js` 가 `lib` 자리에 **기록만 하는
  가짜**를 끼워 `part*.js` 를 그대로 읽는다. 본문이 `docx` 를 만지면 그 프록시가 **기록을
  남긴다** — 주장이 아니라 실행이 가른다.

★ **「수」 는 장부다.** 지금 든 수를 이름으로 적고 **늘면 막는다.** 갈래(치환 · 밖 · 면제)로
  가르는 것은 **분류기를 만드는 일**이고 그것은 PLAN 이다 — 분류기를 합성 입력에 안 물리고
  세우면 그 비율이 자의 잡음이다(thoth §152 가 네 번 당한 자리).

★ **밖 — 뜻은 안 본다.** 산문이 맞는 말인지, 표가 옳은지는 **사람이 읽는다.** 이 자는
  **모양**만 본다.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROP = ROOT / "docs/proposal"
장부파일 = PROP / "numbers.json"

# 본문이 가져가도 되는 것 — **블록과 색뿐이다.** `D` · `t` · `runs` · `W` · `FONT` 는 렌더러의 것이다
허용 = {"P", "GAP", "BR", "PART", "H1", "H2", "H3", "B", "NOTE", "CODE", "TBL", "KV",
       "FIGURE", "COVER", "TOC", "NAVY", "RED", "GRAY", "secs", "ROOT", "RNG"}
본문 = ("part1.js", "part2.js", "part3.js")
_구조분해 = re.compile(r"const\s*\{([^}]*)\}\s*=\s*require\(\"([^\"]+)\"\)")
_require = re.compile(r"require\(\"([^\"]+)\"\)")
산문갈래 = {"P", "NOTE", "B", "H1", "H2", "H3", "PART", "COVER"}
단위 = r"(?:유닛|초|자|항목|개|건|%|MB|ms|배|쪽|줄|점|회|종|구간|시간|분|문항)"
# ★ **소수점 뒤에 공백이 오면 수가 아니다.** 첫 판은 `\d+\.?\d*\s*단위` 로 적었고 목차의
#   「12. 개발 환경」 이 **`12. 개`** 로 잡혔다 — 자를 먼저 의심한다.
수 = re.compile(r"(?:\$\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?" + 단위 + r")")


def 문(root: Path | None = None) -> list[str]:
    """본문이 `./lib` 만 부르고 **블록만** 가져가는가."""
    root = root or ROOT
    난것 = []
    for f in 본문:
        글 = (root / "docs/proposal" / f).read_text(encoding="utf-8")
        for 자리 in set(_require.findall(글)):
            if 자리 != "./lib":
                난것.append(f"{f} 가 `{자리}` 를 부른다 — 본문은 `./lib` 만 부른다")
        for 이름들, 자리 in _구조분해.findall(글):
            if 자리 != "./lib":
                continue
            for n in (x.strip() for x in 이름들.split(",")):
                if n and n not in 허용:
                    난것.append(f"{f} 가 `{n}` 을 가져간다 — 렌더러의 것이다. "
                                f"블록이 모자라면 `lib.js` 에 블록을 연다")
    return 난것


def 나무(root: Path | None = None) -> dict:
    """가짜 `lib` 으로 읽은 블록 나무. **도구가 깨지면 2 로 끝낸다.**"""
    root = root or ROOT
    r = subprocess.run(["node", "extract.js"], cwd=root / "docs/proposal",
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    ★ extract.js 가 {r.returncode} 로 죽었다\n{r.stderr[-600:]}", file=sys.stderr)
        raise SystemExit(2)
    return json.loads(r.stdout)


def 블록(t: dict) -> list[str]:
    난것 = [f"본문이 끝까지 안 돈다 — {x}" for x in t["난것"]]
    안다 = set(t["블록이름"])
    for b in t["블록"]:
        if b["종류"] == "DOCX직접":
            난것.append("본문이 `docx` 를 직접 만진다 — 렌더러를 하나 더 붙일 수 없게 된다")
        elif b["종류"] not in 안다:
            난것.append(f"선언 밖 블록 `{b['종류']}` — `lib.js` 가 내보내는 것만 쓴다")
    return 난것


def 수들(t: dict) -> list[str]:
    """산문 블록에 든 **단위를 가진 수**. 자리마다 한 번씩."""
    out = []
    for b in t["블록"]:
        if b["종류"] not in 산문갈래:
            continue
        for 글 in b["글"]:
            out += [m.strip() for m in 수.findall(글)]
    return sorted(set(out))


def 장부(root: Path | None = None) -> set[str]:
    p = (root or ROOT) / "docs/proposal/numbers.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    return {x for k, v in raw.items() if not k.startswith("_") for x in v}


def 견준다(지금: list[str], 적힌: set[str]) -> tuple[list[str], list[str]]:
    """(장부에 없는 것, 장부에 있는데 이제 안 쓰는 것). **둘 다 낸다** — 늘면 막고 줄면 알린다."""
    return [x for x in 지금 if x not in 적힌], [x for x in sorted(적힌) if x not in set(지금)]


def _canary() -> None:
    """★ **판별식이 사나.** 0건이 목표인 검사는 **깨끗해서 0 인지 죽어서 0 인지** 못 가른다."""
    t = {"블록이름": ["P"], "블록": [{"종류": "DOCX직접", "글": []}], "난것": []}
    if not 블록(t):
        print("    ★ 카나리아가 죽었다 — `docx` 직접 사용을 안 잡는다"); sys.exit(2)
    if not 블록({"블록이름": ["P"], "블록": [{"종류": "몰라", "글": []}], "난것": []}):
        print("    ★ 카나리아가 죽었다 — 선언 밖 블록을 안 잡는다"); sys.exit(2)
    t2 = {"블록": [{"종류": "P", "글": ["45유닛 과 $0.59 · 12. 개발 환경"]},
                  {"종류": "TBL", "글": ["99건"]}]}
    if 수들(t2) != ["$0.59", "45유닛"]:
        print(f"    ★ 카나리아가 죽었다 — 수를 못 읽는다 : {수들(t2)}"); sys.exit(2)
    if 견준다(["a"], {"b"}) != (["a"], ["b"]):
        print("    ★ 카나리아가 죽었다 — 장부를 못 견준다"); sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    a = argv if argv is not None else sys.argv[1:]
    _canary()
    if "--selftest" in a:
        print("  프로브 살아 있다 — docx 직접 · 선언 밖 블록 · 수 읽기 · 장부 견주기")
        return 0
    t = 나무()
    지금 = 수들(t)
    if "--list" in a:
        import collections
        c = collections.Counter(b["종류"] for b in t["블록"])
        print(f"  블록 {len(t['블록'])} — " + " · ".join(f"{k} {v}" for k, v in sorted(c.items())))
        print(f"  산문 속 단위를 든 수 {len(지금)}")
        for x in 지금:
            print(f"    {x}")
        return 0
    난것 = 문() + 블록(t)
    새것, 안쓰는것 = 견준다(지금, 장부())
    난것 += [f"장부에 없는 수 `{x}` — `docs/proposal/numbers.json` 에 적는다" for x in 새것]
    if 안쓰는것:
        print(f"  ※ 안 쓰게 된 수 {len(안쓰는것)} — 장부에서 지운다 : " + " ".join(안쓰는것))
    print(f"  블록 {len(t['블록'])} · 산문 속 수 {len(지금)} · 장부 {len(장부())}")
    for x in 난것:
        print(f"    {x}")
    return 1 if 난것 else 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다 — 같은 코드면 **도구가 깨진 것을
    #   검사가 실패한 것으로 읽는다**(DECISIONS §153 과 같은 자리).
    sys.exit(main())
