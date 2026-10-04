r"""**관문이 제 밖과 생사를 선언하나**(DECISIONS §157).

  python3 tools/check_scope.py            장부보다 늘면 1
  python3 tools/check_scope.py --list     지금 자리를 전부 찍는다
  python3 tools/check_scope.py --selftest 판별식이 살아 있나

★ **검사는 제가 못 보는 것을 적어야 한다.** 안 적으면 다음 사람이 **이름이 약속하는 만큼**
  본다고 믿는다 — §152 가 「`skip` 16곳만 보는데 33곳으로 읽힌다」 로 겪은 자리이고,
  §155 가 「표와 그림의 수는 안 본다」 를 적어 둔 까닭이다.

★ **0건이 목표인 검사는 깨끗해서 0 인지 죽어서 0 인지 못 가른다.** 그래서 **생사**도
  묻는다 — `_canary` 든 `--selftest` 든, **제가 사는지 스스로 아는 자리**가 있어야 한다.

★ **관문만 본다**(DECISIONS §133). `tools/` 전부가 아니라 **`doctor.sh` 가 부르는 것**이다 —
  손으로 돌리는 조사 도구는 사슬에 없으므로 그 약속을 아무도 안 읽는다. **목록을 안 만든다** :
  `doctor.sh` 에서 뽑으므로 새 관문이 늘면 **자동으로 걸린다**(족 가드).

★ **장부다.** 지금 못 지키는 자리를 이름으로 적고 **늘면 막는다.** 갚으면 찍어 준다 —
  **줄지 않는 장부는 영구 면제**가 된다(§152 · §156 과 같은 꼴).

★ **밖 — 「무엇을 안 보는지」 가 맞는 말인지는 안 본다.** 한 줄이 있는지만 본다. 뜻은 사람이
  읽는다 — 그것이 `docseal` 의 일이고 이 자의 일이 아니다.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
장부파일 = ROOT / "tools" / "scope_debt.json"

# ★ **제 한계를 말하는 낱말.** 늘려도 되지만 **넓히면 거짓 초록**이 된다.
밖말 = ("안 본다", "못 본다", "완전하지 않다", "안 잡는다", "보지 않는다", "안 센다",
       "거짓 양성", "안 가른다", "안 잰다", "안 묻는다")
생사말 = ("_canary", "--selftest", "selftest")
_부름 = re.compile(r"tools/([a-z_][a-z0-9_]*\.py)")


def 관문들(root: Path | None = None) -> list[str]:
    """`doctor.sh` 가 부르는 `tools/*.py`. **손 목록을 안 만든다** — 실물에서 뽑는다."""
    root = root or ROOT
    글 = (root / "tools/doctor.sh").read_text(encoding="utf-8")
    return sorted({n for n in _부름.findall(글) if (root / "tools" / n).exists()})


def 흠(root: Path | None = None) -> list[str]:
    """`파일:밖` · `파일:생사` 꼴. **장부의 열쇠다.**"""
    root = root or ROOT
    out = []
    for n in 관문들(root):
        글 = (root / "tools" / n).read_text(encoding="utf-8")
        if not any(w in 글 for w in 밖말):
            out.append(f"{n}:밖")
        if not any(w in 글 for w in 생사말):
            out.append(f"{n}:생사")
    return out


def 장부(path: Path | None = None) -> set[str]:
    raw = json.loads((path or 장부파일).read_text(encoding="utf-8"))
    return {x for k, v in raw.items() if not k.startswith("_") for x in v}


def 견준다(지금: list[str], 적힌: set[str]) -> tuple[list[str], list[str]]:
    """(장부에 없는 것, 장부에 있는데 이제 흠이 아닌 것). **둘 다 낸다.**"""
    return [x for x in 지금 if x not in 적힌], [x for x in sorted(적힌) if x not in set(지금)]


def _canary() -> None:
    """★ **판별식이 사나.** 이 자 자신이 제 규칙을 어기면 안 된다."""
    가짜 = "이 도구는 아무것도 안 본다"
    if not any(w in 가짜 for w in 밖말):
        print("    ★ 카나리아가 죽었다 — 밖말을 못 읽는다"); sys.exit(2)
    if any(w in "그냥 글" for w in 밖말):
        print("    ★ 카나리아가 죽었다 — 아무 글이나 밖으로 읽는다"); sys.exit(2)
    if 견준다(["a"], {"b"}) != (["a"], ["b"]):
        print("    ★ 카나리아가 죽었다 — 장부를 못 견준다"); sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    a = argv if argv is not None else sys.argv[1:]
    _canary()
    if "--selftest" in a:
        print("  프로브 살아 있다 — 밖말 읽기 · 아닌 것 거르기 · 장부 견주기")
        return 0
    지금 = 흠()
    문 = 관문들()
    if "--list" in a:
        적힌 = 장부()
        for n in 문:
            상태 = [x.split(":")[1] for x in 지금 if x.startswith(f"{n}:")]
            print(f"    {n:<24}{'·'.join(상태) + ' 없음' if 상태 else '밖·생사 둘 다 있다'}"
                  f"{'  (장부)' if all(f'{n}:{s}' in 적힌 for s in 상태) and 상태 else ''}")
        return 0
    새것, 갚음 = 견준다(지금, 장부())
    if 갚음:
        print(f"  ※ 갚았다 {len(갚음)} — 장부에서 지운다 : " + " ".join(갚음))
    print(f"  관문 {len(문)} · 흠 {len(지금)} / 장부 {len(장부())}")
    for x in 새것:
        파일, _, 갈래 = x.partition(":")
        말 = ("머리말이 **안 보는 것**을 안 적는다 — 「… 는 안 본다」 를 한 줄 넣는다"
              if 갈래 == "밖" else
              "**제가 사는지** 묻는 자리가 없다 — `_canary` 나 `--selftest` 를 둔다")
        print(f"    {파일} — {말}")
    return 1 if 새것 else 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다(DECISIONS §153).
    sys.exit(main())
