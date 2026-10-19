"""playwright 판의 **정본을 읽는다 — 적지 않는다**(DECISIONS §194).

★ **정본은 `tools/lib/pw.sh` 하나다.** 셸과 파이썬이 각자 수를 들면 한쪽만 늙는다(§91).
  셸은 그 파일을 `.` 로 읽고, 파이썬은 여기서 읽는다.
★ **못 읽으면 `playwright` 로 떨어진다 — 그리고 그 사실이 명령에 드러난다.** 핀 없는
  명령이 찍히면 사람이 「왜 핀이 없지」 를 묻게 된다. 조용히 최신을 쓰는 것보다 낫다.
"""
from __future__ import annotations

import pathlib
import re

_정규 = re.compile(r'PW_PIN="([^"]+)"')


def 핀(root: pathlib.Path | str | None = None) -> str:
    뿌리 = pathlib.Path(root) if root else pathlib.Path(__file__).resolve().parent.parent.parent
    try:
        글 = (뿌리 / "tools/lib/pw.sh").read_text(encoding="utf-8")
    except OSError:
        return "playwright"
    m = _정규.search(글)
    return m.group(1) if m else "playwright"
