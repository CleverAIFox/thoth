#!/usr/bin/env python3
"""가드를 망가뜨려 시험이 우는지 본다 — **선언된 돌연변이를 전부 돌린다**.

    python3 tools/mutate_gate.py              전부
    python3 tools/mutate_gate.py --only pkg   한 가드만
    python3 tools/mutate_gate.py --list       무엇이 선언돼 있나

★ **「검사를 더했다」 와 「검사가 문다」 는 다른 말이다**(DECISIONS §152). 2026-10-04
  하루에 가드 일곱을 세우면서 돌연변이를 손으로 돌렸는데, **세 번은 첫 판이 안 물었다**
  (§145 · §147 · §150). 저장소가 깨끗하면 **검사를 꺼도 조용하기** 때문이다 —
  시험이 가드를 붙들고 있지 않아도 초록이 뜬다.

★ **그런데 그 돌연변이가 전부 휘발됐다.** 손으로 돌리면 다음 사람이 안 돌리고,
  안 돌린 줄도 모른다. 하토르가 `tools/mutate_gate.py` 를 가진 까닭이 이것이다.

★ **자동 생성이 아니라 선언이다.** `mutmut` 류는 모든 토막을 뒤집어 보므로 느리고
  시끄럽다. 오늘 물린 돌연변이는 전부 **가드의 하중을 받는 한 줄**을 겨눈 것이었다.
  겨냥은 사람이 하고, **빠뜨리지 않는 일만 기계가 한다.**

★ **시험을 좁혀 부른다.** 돌연변이마다 「어느 시험이 울어야 하나」 를 선언하므로
  한 건이 0.5초 안쪽이다. 전부 돌려도 `doctor` 안에서 돌 만하다.

★ **양방향 톱니다.** 살아남은 것이 **0 이 아니면** 울고, 선언이 **줄어도** 운다 —
  안 그러면 안 무는 돌연변이를 지워서 초록을 만들 수 있다.

★ **덮는 가드를 선언한다.** 「선언 안 된 가드가 있나」 를 묻는다(족 가드). 아직 안
  덮은 것은 `미선언` 에 적어 두고 **그 수가 늘면 운다** — 못 보는 자리를 좁히고
  그 자리를 적는다(§73).
"""
import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
선언파일 = ROOT / "tools" / "mutations.json"

# ★ **덮은 가드가 줄면 운다.** 돌연변이를 지워서 초록을 만드는 길을 막는다.
MIN_돌연변이 = 50
MIN_가드 = 8


def 읽기() -> dict:
    raw = json.loads(선언파일.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def 가드들(선언: dict) -> dict:
    """★ **「가드란 무엇인가」 를 한 곳이 정한다.** 여기와 시험이 각각 정하면
    시험이 세는 수와 관문이 도는 수가 갈린다(§132 · §145 가 같은 모양이었다)."""
    return {k: v for k, v in 선언.items() if k != "미선언"}


def 한건(파일: pathlib.Path, 전: str, 후: str, 시험: list[str]) -> tuple[bool, str]:
    """한 줄을 바꾸고 선언된 시험을 돌린다. (물었나, 까닭)."""
    원 = 파일.read_text(encoding="utf-8")
    if 전 not in 원:
        return False, "바꿀 자리를 못 찾았다 — 코드가 바뀌었으면 선언도 고친다"
    if 원.count(전) > 1:
        return False, f"바꿀 자리가 {원.count(전)}곳이다 — 겨냥이 흐리다"
    파일.write_text(원.replace(전, 후, 1), encoding="utf-8")
    try:
        r = subprocess.run(시험, cwd=ROOT, capture_output=True, text=True, timeout=300)
    finally:
        파일.write_text(원, encoding="utf-8")
    return r.returncode != 0, "" if r.returncode else "시험이 통과했다 — 가드를 안 붙들고 있다"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="가드 이름 하나만")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    선언 = 읽기()
    가드 = 가드들(선언)
    미선언 = 선언.get("미선언", [])

    if a.list:
        for 이름, g in 가드.items():
            print(f"{이름:<14} {g['파일']:<42} 돌연변이 {len(g['돌연변이'])}")
        print(f"\n미선언 가드 {len(미선언)} : " + " ".join(미선언))
        return 0

    셈 = {"돌": 0, "산것": 0}
    난것: list[str] = []
    for 이름, g in 가드.items():
        if a.only and a.only != 이름:
            continue
        파일 = ROOT / g["파일"]
        for m in g["돌연변이"]:
            셈["돌"] += 1
            물었나, 까닭 = 한건(파일, m["전"], m["후"], g["시험"])
            if not 물었나:
                셈["산것"] += 1
                난것.append(f'  LIVE [{이름}] {m["이름"]} — {까닭}')
            print(f'  {"OK  " if 물었나 else "LIVE"} [{이름}] {m["이름"]}')

    print(f'\n돌연변이 {셈["돌"]}건 · 살아남음 {셈["산것"]}건')
    for x in 난것:
        print(x)

    # ★ 양방향 — 선언이 줄면 운다
    전체 = sum(len(g["돌연변이"]) for g in 가드.values())
    if not a.only:
        if 전체 < MIN_돌연변이:
            난것.append(f"선언된 돌연변이가 {전체}건으로 바닥 {MIN_돌연변이} 아래다 — "
                        f"안 무는 돌연변이를 지워 초록을 만드는 길이다")
        if len(가드) < MIN_가드:
            난것.append(f"덮는 가드가 {len(가드)}개로 바닥 {MIN_가드} 아래다")
        if 전체 > MIN_돌연변이 or len(가드) > MIN_가드:
            print(f"\n※ 좋아졌다 — MIN_돌연변이 를 {전체} 로, MIN_가드 를 {len(가드)} 로 올린다")
    return 1 if 난것 else 0


if __name__ == "__main__":
    sys.exit(main())
