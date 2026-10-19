#!/usr/bin/env python3
"""화면 그림을 **건너뛸 수 있는가** — 그 그림이 찍은 원본이 그대로인가(DECISIONS §185).

사용 :
    python3 tools/shot_stale.py            건너뛰어도 되나 묻는다

종료 코드 (DECISIONS §59) :
    0  건너뛰어도 된다 — 옛 그림이 **지금 원본을 찍은 것**이다
    1  건너뛰면 안 된다 — 원본이 바뀌었다. 옛 그림은 **다른 화면**이다
    2  **못 쟀다** — 곁파일이 없다. 통과가 아니다

★ **왜 있나.** `build_proposal.sh` 의 건너뛰기는 「옛 **파일이** 있나」 만 봤다.
  **「옛 그림이 지금 원본을 찍은 것인가」 는 아무도 안 봤다.** 2026-10-12 에 183 이
  `popup.html` 에 버튼을 달았는데, 크로미움 없는 기계에서 구우면 **버튼 없는 옛
  그림**이 그대로 실리고 `doctor` 는 「기획서가 정본과 맞다」 로 **초록**이었다.
  §126 과 같은 족속이다 — 그때는 **생성기**가 뒤진 것을 못 봤고, 이번엔 **그림이
  찍은 대상**이 뒤진 것을 못 봤다.

★ **사실 선언으로는 못 잡는다.** `*.facts.json` 은 「이 글자가 그 파일에 있나」 를
  묻는다. 버튼을 **더해도** 옛 글자는 그대로 있으므로 선언은 참이다. 선언은 **빠진
  것**을 잡지 **더한 것**을 못 잡는다. 그래서 지문을 따로 든다.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

뿌리 = pathlib.Path(__file__).resolve().parent.parent

# ★ playwright 판은 `tools/lib/pw.sh` 하나가 들고 **여기서 읽어 쓴다**(DECISIONS §194).
#   두 곳에 수를 적으면 한쪽만 늙는다(§91).
import importlib.util as _il

_몫pw = _il.spec_from_file_location("pwpin", pathlib.Path(__file__).resolve().parent / "lib/pw.py")
_pw = _il.module_from_spec(_몫pw)
_몫pw.loader.exec_module(_pw)
핀 = _pw.핀()

# ★ **자리를 바꿔 끼울 수 있게 둔다.** `main` 의 종료 코드 셋은 **건너뛰는 기계에서만**
#   밟히므로, 바꿔 끼우지 못하면 영영 안 재진다 — 「한 번도 안 돌아 본 가지」(§182).
곁 = pathlib.Path(os.environ.get("THOTH_SHOT_FIG") or (뿌리 / "docs/proposal/.build/fig"))

# ★ **그림마다 무엇을 찍었는지 여기 적는다.** `shots.py` 가 같은 목록으로 지문을
#   남기고, 여기서 **같은 목록으로** 되읽는다 — 한쪽만 늘면 `원본이 늘었다` 로 막는다.
찍은것 = {
    "f_popup": [
        "extension/popup.html",
        "extension/popup.css",
        "extension/src/popup.js",
        "extension/src/state.js",
    ],
    "f_preview_a": [
        "extension/preview.html",
        "extension/content.css",
    ],
}


def _보일(p: pathlib.Path) -> str:
    """저장소 안이면 짧게, 밖이면 그대로. **밖이라고 터지면 안 된다** — 바꿔 끼운
    자리를 쓰는 검사가 그 터짐을 「통과가 아니다」 로 못 읽는다(§59)."""
    try:
        return str(p.relative_to(뿌리))
    except ValueError:
        return str(p)


def 지문(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def 지금() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for 이름, 것들 in 찍은것.items():
        out[이름] = {f: 지문(뿌리 / f) for f in 것들}
    return out


def 흠(적힌: dict[str, dict[str, str]] | None,
      이제: dict[str, dict[str, str]]) -> tuple[list[str], list[str]]:
    """(막, 못쟀다). **「다르다」 와 「못 쟀다」 를 가른다**(§59)."""
    막: list[str] = []
    못: list[str] = []
    for 이름, 이제것 in 이제.items():
        그때 = (적힌 or {}).get(이름)
        if not 그때:
            못.append(f"`{이름}` 이 무엇을 찍었는지 안 적혀 있다")
            continue
        for f, h in 이제것.items():
            if f not in 그때:
                못.append(f"`{이름}` 의 원본 목록에 `{f}` 가 없다 — 목록이 늘었다")
            elif 그때[f] != h:
                막.append(f"`{이름}` 이 찍은 `{f}` 가 바뀌었다 ({그때[f]} → {h})")
        for f in 그때:
            if f not in 이제것:
                못.append(f"`{이름}` 의 원본 목록에서 `{f}` 가 빠졌다")
    return 막, 못


def main(argv: list[str]) -> int:
    적힌: dict[str, dict[str, str]] = {}
    없는것 = []
    for 이름 in 찍은것:
        p = 곁 / f"{이름}.원본.json"
        if not p.exists():
            없는것.append(_보일(p))
            continue
        try:
            적힌[이름] = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            없는것.append(f"{_보일(p)} ({e})")

    if 없는것:
        print("  **못 쟀다** — 옛 그림이 무엇을 찍은 것인지 적혀 있지 않다")
        for x in 없는것:
            print(f"      {x}")
        print(f"  그림을 다시 찍는다 : uv run --with {핀} python -m playwright install chromium")
        return 2

    막, 못 = 흠(적힌, 지금())
    if 못:
        print("  **못 쟀다** — 그림과 원본 목록이 어긋난다")
        for x in 못:
            print(f"      {x}")
        return 2
    if 막:
        print("  건너뛸 수 없다 — **옛 그림은 지금 화면이 아니다**")
        for x in 막:
            print(f"      {x}")
        print(f"  깔고 다시 돌린다 : uv run --with {핀} python -m playwright install chromium")
        return 1
    print("  옛 그림이 지금 원본을 찍은 것이다 — 건너뛴다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
