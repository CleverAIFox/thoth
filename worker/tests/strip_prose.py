"""**글을 코드로 읽는 검사는 글부터 지운다** — 그 지우개의 정본(DECISIONS §196).

★ **파일 이름은 ASCII 다.** 처음엔 `글지움.py` 로 뒀다가 `git ls-files` 쓰는 검사 셋이
  깨졌다 — git 이 비 ASCII 경로를 `"worker/tests/\\352\\270\\200…"` 로 **따옴표로 싸서**
  내놓고, 그 글자를 그대로 경로로 쓰면 **없는 파일**이 된다. §195 가 이 사실을 적고
  「추적 경로가 전부 ASCII 인 것을 관문으로 들었다」 고 썼는데 **그 관문이 없었다** —
  그래서 내가 바로 어겼다. 관문은 `test_endings_oracle.py` 가 든다.

★ **이 저장소에 「`#` 줄을 지운다」 가 스무 벌 있었다.** 전부 같은 구멍을 안고 있다 —
  **글귀(docstring)는 `#` 이 아니다.** §195 가 `test_pw_pin.py` 에서 그 구멍에 걸렸고,
  §196 이 `test_endings_oracle.py` 에서 **같은 구멍에 또** 걸렸다. 두 번 걸린 것은
  고칠 자리가 코드가 아니라 **정본이 없다는 사실**이라는 뜻이다(§91).
★ **지우는 것은 줄 머리에서 열리는 세겹 따옴표뿐이다.** 값으로 쓰는 세겹
  문자열(`MOCK = \"\"\"…`)은 **글이 아니라 데이터**이고 거기 든 명령은 실제로 돈다 —
  그것까지 지우면 **검사가 조용히 꺼진다.**
★ **옮기는 것은 한 번에 하나씩.** 나머지 열여덟 벌은 제자리에 둔다 — 한꺼번에 바꾸면
  **무엇이 깨졌는지 못 가른다.** 새로 쓰는 검사는 여기를 쓴다.
"""
from __future__ import annotations

import pathlib
import re

_연다 = re.compile(r"""[rbuRBU]{0,2}("{3}|'{3})""")


def 본문(p: pathlib.Path | str) -> str:
    """주석과 글귀를 걷어낸 코드."""
    글 = pathlib.Path(p).read_text(encoding="utf-8", errors="ignore")
    줄, 안 = [], ""
    for x in 글.splitlines():
        s = x.strip()
        if 안:                                   # 글귀 안이다
            if 안 in s:
                안 = ""
            continue
        if s.startswith("#") or s.startswith("//"):
            continue
        m = _연다.match(s)
        if m:
            if m.group(1) not in s[m.end():]:    # 한 줄로 안 닫힌다
                안 = m.group(1)
            continue
        줄.append(x)
    return "\n".join(줄)


def 추적파일(*무늬: str, root: pathlib.Path | None = None) -> list[pathlib.Path]:
    """`git ls-files -z` 로 고른 추적 파일 — **구분자는 NUL 이다**(DECISIONS §196).

    ★ **`-z` 없이 부르면 git 이 비 ASCII 경로를 따옴표로 싼다.** `"worker/tests/
      \\352\\270\\200…"` 를 그대로 경로로 쓰면 **없는 파일**이 되고, 검사는 통과가
      아니라 **터진다.** 이 저장소엔 `docs/proposal/수.js` · `extension/src/지문.js`
      가 이미 있었고 `.js` 라 아무 목록에도 안 걸렸을 뿐이다.
    ★ **§195 는 「추적 경로가 전부 ASCII 인 것을 관문으로 들었다」 고 적었다.** 관문은
      없었고 **주장도 거짓이었다.** 이름을 묶는 대신 **목록 뽑는 자리를 하나로 모은다** —
      이름은 사람이 짓고 구분자는 도구가 고른다.
    ★ **못 읽으면 터진다.** 빈 목록을 돌려주면 그것을 쓰는 검사가 **0건을 통과로**
      센다(§59).
    """
    import subprocess
    뿌리 = root or pathlib.Path(__file__).resolve().parents[2]
    r = subprocess.run(["git", "ls-files", "-z", *무늬], cwd=뿌리,
                       capture_output=True, text=True)
    assert r.returncode == 0, "`git ls-files` 를 못 읽었다 — 못 쟀다는 뜻이다"
    return [뿌리 / x for x in r.stdout.split("\0") if x]
