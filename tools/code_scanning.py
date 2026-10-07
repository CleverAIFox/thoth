#!/usr/bin/env python3
"""**코드 스캐닝이 지금 무엇을 들고 있는가**(DECISIONS §171).

    python3 tools/code_scanning.py          열린 경보가 있으면 1
    python3 tools/code_scanning.py --json   기계가 읽을 꼴

★ **`ci_status.py` 가 이것을 영영 못 본다.** 그쪽은 `.github/workflows/*.yml` 에서 물을
  목록을 꺼내는데(세샤트 §293), **CodeQL 은 GitHub 기본 설정으로 돌아 파일이 없다.**
  그래서 `doctor` 가 「CI 가 이 커밋을 초록으로 봤다 — 워크플로 3 전부」 를 찍는 동안
  `docs/proposal/html.js` 의 경보 둘이 **이틀** 떠 있었다. 참말이었고, 모자랐다.

★ **「못 쟀다」 를 초록으로 안 찍는다**(DECISIONS §59). `gh` 가 없거나 권한이 모자라면
  **2** 로 끝난다 — 0 이 아니다. 경보가 없는 것과 못 묻는 것은 다른 말이다.

★ **심각도로 안 거른다.** 「medium 은 나중에」 가 이틀을 만들었다. 열려 있으면 막는다.
  시끄러운 규칙이 생기면 그때 **그 규칙 이름을 적어** 빼고, 왜 뺐는지를 함께 적는다 —
  **수를 낮추는 것이 아니라 이름을 적는 것**이 갚는 길이다(§167 의 갈래와 같은 처방).

★ **종료 코드가 상태를 든다**(DECISIONS §127).
    0  열린 경보 없음
    1  열린 경보가 있다
    2  묻지 못했다 (`gh` 없음 · 로그인 안 됨 · 권한 없음). **통과로 세지 않는다**
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ★ **면제는 규칙 **이름**으로 적는다.** 수로 적으면 「스물둘 중 스물하나」 가 통과가 되고,
#   어느 하나가 새 것인지 아무도 모른다. 비어 있는 것이 정상이다.
면제: dict[str, str] = {}

_원격 = re.compile(r"github\.com[:/]([^/]+)/([^/.]+)")


def 저장소(root: pathlib.Path | None = None) -> str | None:
    """`owner/repo`. **이름을 코드에 안 박는다** — 포크에서도 제 것을 묻는다."""
    r = subprocess.run(["git", "-C", str(root or ROOT), "remote", "get-url", "origin"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    m = _원격.search(r.stdout.strip())
    return f"{m.group(1)}/{m.group(2)}" if m else None


def 바뀌었나(sha: str, 길: str, root: pathlib.Path | None = None,
             부른다=None) -> bool | None:
    """**스캔된 커밋 이후로 이 파일이 작업 트리에서 바뀌었나.** 못 재면 `None`.

    ★ **코드 스캐닝은 「스캔된 커밋」 에 대해 답한다 — 네 나무가 아니다**(DECISIONS §172).
      고친 것을 아직 안 밀었으면 그 답은 **과거의 나무**에 관한 것이다.
    ★ **「나무가 더럽다」 로 묻지 않는다.** 그러면 패치를 붙인 모든 판에서 관문이
      통째로 꺼진다 — **관문을 끄는 가장 쉬운 길**이 거기 생긴다. 묻는 것은
      **그 경보가 가리킨 파일 하나**가 그 커밋 이후로 바뀌었나다.
    """
    if not sha or not 길:
        return None
    부른다 = 부른다 or (lambda a: subprocess.run(a, capture_output=True, text=True))
    r = 부른다(["git", "-C", str(root or ROOT), "diff", "--quiet", sha, "--", 길])
    # 0 = 같다(안 바뀜) · 1 = 다르다 · 그 밖 = 그 커밋이 여기 없다 등 **못 잼**
    return {0: False, 1: True}.get(r.returncode)


def 판정(경보들: list[dict], 바뀜=None) -> tuple[list[str], list[str]]:
    """`(막을 것, 이 나무에서 그 파일이 바뀐 것)`.

    ★ **DOM 도 네트워크도 안 읽는다** — 합성으로 전부 먹여 볼 수 있다(§132 와 같은 꼴).
    ★ **고치는 커밋을 제가 막으면 안 된다**(DECISIONS §172). `ship.sh` 는 `doctor` 가
      FAIL 이면 죽는다 — 열려 있다는 이유만으로 막으면 **경보를 고친 커밋이 영영 못
      나간다.** 2026-10-07 에 실제로 그 교착에 빠졌다.
    ★ **그렇다고 「바뀌었으면 통과」 가 아니다.** 바뀐 것은 **못 쟀다**이고, 다음
      스캔이 답한다. 초록이 아니라 건너뜀으로 적는다(§59).
    """
    바뀜 = 바뀜 or 바뀌었나
    막을것, 바뀐것 = [], []
    for a in 경보들:
        규칙 = ((a.get("rule") or {}).get("id")
                or (a.get("rule") or {}).get("name") or "?")
        if 규칙 in 면제:
            continue
        최근 = a.get("most_recent_instance") or {}
        위치 = 최근.get("location") or {}
        어디 = 위치.get("path") or "?"
        줄 = 위치.get("start_line")
        심각 = ((a.get("rule") or {}).get("security_severity_level")
                or (a.get("rule") or {}).get("severity") or "?")
        줄글 = (f"#{a.get('number', '?')} [{심각}] {규칙} — {어디}"
                + (f":{줄}" if 줄 else ""))
        # ★ **못 쟀으면 막는 쪽이다.** 「모르겠으니 넘어간다」 가 §171 을 만들었다.
        if 바뀜(최근.get("commit_sha") or "", 위치.get("path") or "") is True:
            바뀐것.append(줄글 + "  ← 이 나무에서 그 파일이 바뀌었다")
        else:
            막을것.append(줄글)
    return 막을것, 바뀐것


def 묻는다(repo: str, 부른다=None) -> list[dict] | str:
    """경보 목록 또는 **왜 못 물었는지**를 적은 글."""
    부른다 = 부른다 or (lambda a: subprocess.run(a, capture_output=True, text=True))
    r = 부른다(["gh", "api", f"repos/{repo}/code-scanning/alerts",
                "--paginate", "-X", "GET", "-f", "state=open", "-f", "per_page=100"])
    if r.returncode != 0:
        말 = (r.stderr or "").strip().splitlines()
        # ★ **404 는 「경보 없음」 이 아니다.** 코드 스캐닝이 꺼져 있다는 뜻이고,
        #   그것은 **이 검사가 지켜 주지 않는다**는 말이라 초록으로 찍으면 안 된다.
        return f"`gh` 가 코드 스캐닝을 못 읽었다 — {말[-1] if 말 else '까닭 없음'}"
    try:
        것 = json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return "`gh` 가 JSON 이 아닌 것을 줬다"
    return 것 if isinstance(것, list) else "`gh` 가 목록이 아닌 것을 줬다"


def _canary() -> None:
    """★ **판별식이 사나.** `판정` 이 아무것도 못 꺼내면 **경보가 몇 개든 0 건**이 되고,
    그러면 이 검사는 **꺼진 채 초록**이다 — 그것이 §171 을 만든 모양 그대로다.
    ★ **합성으로 묻는다.** 네트워크가 없어도 돌아야 한다."""
    합성 = {"number": 9, "rule": {"id": "x/y", "security_severity_level": "medium"},
            "most_recent_instance": {"location": {"path": "a.js", "start_line": 1}}}
    막, 바뀜 = 판정([합성], 바뀜=lambda *_: False)
    if len(막) != 1 or "x/y" not in 막[0] or "a.js:1" not in 막[0] or 바뀜:
        print(f"    ★ 카나리아가 죽었다 — 경보를 못 읽는다 : {막} / {바뀜}")
        sys.exit(2)
    if 판정([], 바뀜=lambda *_: False) != ([], []):
        print("    ★ 카나리아가 죽었다 — 빈 목록에서 경보를 만든다")
        sys.exit(2)
    # ★ **가름이 사는가.** 「바뀌었다」 를 늘 거짓으로 읽으면 §172 의 교착이 돌아오고,
    #   늘 참으로 읽으면 **관문이 통째로 꺼진다.** 양쪽을 다 먹여 본다.
    if 판정([합성], 바뀜=lambda *_: True)[0]:
        print("    ★ 카나리아가 죽었다 — 파일이 바뀌어도 막는다")
        sys.exit(2)
    if not 판정([합성], 바뀜=lambda *_: None)[0]:
        print("    ★ 카나리아가 죽었다 — 못 쟀는데 넘긴다")
        sys.exit(2)


def main() -> int:
    _canary()
    if "--selftest" in sys.argv[1:]:
        print("  프로브 살아 있다 — 경보 읽기 · 빈 목록 거르기")
        return 0
    if not shutil.which("gh"):
        print("`gh` 가 없다 — `sudo apt install gh && gh auth login`. "
              "**못 보는 것은 통과가 아니다**")
        return 2
    repo = 저장소()
    if not repo:
        print("`origin` 에서 owner/repo 를 못 읽었다")
        return 2
    것 = 묻는다(repo)
    if isinstance(것, str):
        print(것)
        print("  권한이면 : gh auth refresh -h github.com -s security_events")
        return 2
    if "--json" in sys.argv:
        print(json.dumps(것, ensure_ascii=False, indent=2))
    막을것, 바뀐것 = 판정(것)
    if 막을것:
        print(f"코드 스캐닝에 열린 경보 {len(막을것)}건 — {repo}"
              + (f" (그 밖에 {len(바뀐것)}건은 파일이 바뀌었다)" if 바뀐것 else ""))
        for x in 막을것:
            print(f"    {x}")
        return 1
    if 바뀐것:
        # ★ **초록이 아니라 건너뜀이다**(§59). 스캔된 커밋 이후로 그 파일이 바뀌었으니
        #   **이 답은 이 나무에 관한 것이 아니다.** 고쳤는지는 **다음 스캔이 말한다.**
        print(f"경보 {len(바뀐것)}건이 열려 있으나 그 파일이 이 나무에서 바뀌었다 — {repo}")
        for x in 바뀐것:
            print(f"    {x}")
        print("    밀고 나면 다음 스캔이 답한다. 안 닫히면 그때 이 자리가 막는다")
        return 2
    면 = f" (면제 {len(면제)})" if 면제 else ""
    print(f"코드 스캐닝에 열린 경보 없음 — {repo}{면}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
