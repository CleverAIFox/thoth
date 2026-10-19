#!/usr/bin/env python3
"""**Dependabot 이 지금 무엇을 들고 있는가**(DECISIONS §194).

    python3 tools/dependabot.py          막을 경보가 있으면 1
    python3 tools/dependabot.py --json   기계가 읽을 꼴

★ **`code_scanning.py` 도 `ci_status.py` 도 이것을 영영 못 본다.** 앞엣것은 CodeQL 경보만
  묻고, 뒤엣것은 `.github/workflows/*.yml` 에서 목록을 꺼내는데 **Dependabot 은 파일이
  없다.** 그래서 2026-10-15 에 `doctor` 가 「코드 스캐닝에 열린 경보 없음」 을 찍는 동안
  **High 한 건이 떠 있었다** — `source-map-js` 의 이벤트 루프 DoS. **참말이었고 모자랐다**
  (§171 과 같은 자리, 다른 눈).

★ **「못 쟀다」 를 초록으로 안 찍는다**(§59). `gh` 가 없거나 권한이 모자라면 **2** 로
  끝난다. 경보가 없는 것과 못 묻는 것은 다른 말이다.

★ **`development` 범위를 심각도로 안 뭉갠다 — 갈라서 적는다.** 그날 것은 `high` 인데
  `jsdom → css-tree` 가 끌어오는 **dev 의존**이었고, `sync_ext.sh` 가 `node_modules/` 를
  빼므로 **브라우저에 안 실린다.** 그렇다고 「dev 니까 무시」 로 숨기면 그 판단이
  **매번 사람 머릿속에서만** 일어난다. 막지는 않되 **줄에 적어** 눈에 둔다.
  막는 것은 `runtime` 뿐이다 — **사용자에게 닿는 것.**

★ **그래도 고쳐진 판이 있으면 적는다.** 그날 것은 `1.2.2` 가 `^1.2.1` 을 만족해서
  `package.json` 을 안 건드리고 잠금만 올리면 됐다 — **고치는 길이 한 줄인데 안 고치는
  것**과 「막을 값이 없다」 는 다른 말이다.

★ **종료 코드가 상태를 든다**(DECISIONS §127).
    0  막을 것 없음 (dev 범위만 남았거나 아예 없다)
    1  **runtime 범위에 열린 경보가 있다**
    2  묻지 못했다 (`gh` 없음 · 로그인 안 됨 · 권한 없음 · 꺼짐). **통과로 세지 않는다**
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ★ **면제는 경보 **번호**가 아니라 패키지 **이름**으로 적는다.** 번호로 적으면 같은
#   취약점이 다시 올라올 때 새 번호를 받아 그냥 통과한다. 비어 있는 것이 정상이다.
면제: dict[str, str] = {}


def 저장소(root: pathlib.Path | None = None) -> str | None:
    """`owner/repo`. **정본을 두 벌로 두지 않는다** — `code_scanning` 의 것을 읽어 쓴다."""
    import importlib.util
    뿌리 = root or ROOT
    s = importlib.util.spec_from_file_location("cs", 뿌리 / "tools/code_scanning.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m.저장소(뿌리)


def 판정(경보들: list[dict]) -> tuple[list[str], list[str]]:
    """`(막을 것, 알리기만 할 것)`.

    ★ **막는 것은 `runtime` 뿐이다.** 사용자에게 닿는 것만 커밋을 막을 자격이 있다.
    ★ **`development` 도 적는다.** 숨기면 그 판단이 매번 사람 머릿속에서만 일어난다.
    ★ **범위를 모르면 막는 쪽이다**(§59). 「모르겠으니 넘어간다」 가 §171 을 만들었다.
    """
    막을것, 알릴것 = [], []
    for a in 경보들:
        if (a.get("state") or "open") != "open":
            continue
        의존 = a.get("dependency") or {}
        이름 = ((의존.get("package") or {}).get("name")) or "?"
        if 이름 in 면제:
            continue
        조언 = a.get("security_advisory") or {}
        고친판 = ((a.get("security_vulnerability") or {})
                  .get("first_patched_version") or {}).get("identifier")
        범위 = 의존.get("scope") or "모름"
        줄글 = (f"#{a.get('number', '?')} [{조언.get('severity', '?')}/{범위}] {이름}"
                f" — {(조언.get('summary') or '?')[:70]}"
                f"\n        {의존.get('manifest_path', '?')}"
                + (f" · 고친 판 {고친판}" if 고친판 else " · **고친 판이 아직 없다**"))
        (알릴것 if 범위 == "development" else 막을것).append(줄글)
    return 막을것, 알릴것


def 묻는다(repo: str, 부른다=None) -> list[dict] | str:
    """경보 목록 또는 **왜 못 물었는지**를 적은 글."""
    부른다 = 부른다 or (lambda a: subprocess.run(a, capture_output=True, text=True))
    r = 부른다(["gh", "api", f"repos/{repo}/dependabot/alerts",
                "--paginate", "-X", "GET", "-f", "state=open", "-f", "per_page=100"])
    if r.returncode != 0:
        말 = (r.stderr or "").strip().splitlines()
        # ★ **404 는 「경보 없음」 이 아니다.** Dependabot 경보가 꺼져 있다는 뜻이고,
        #   그것은 **못 쟀다**이지 통과가 아니다(§59).
        return (f"`gh` 가 Dependabot 경보를 못 읽었다 — {말[-1] if 말 else '까닭 없음'}"
                "\n       권한이면 : gh auth refresh -h github.com -s security_events")
    try:
        것 = json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return "`gh` 가 Dependabot 경보에서 JSON 이 아닌 것을 줬다"
    return 것 if isinstance(것, list) else "`gh` 가 목록이 아닌 것을 줬다"


def _canary() -> None:
    """★ **판별식이 사나.** `판정` 이 아무것도 못 꺼내면 **경보가 몇 개든 0 건**이 되고,
    그러면 이 검사는 **꺼진 채 초록**이다 — §171 이 만들어진 모양 그대로다.
    ★ **합성으로 묻는다.** 네트워크가 없어도 돌아야 한다. 칸 이름은 2026-10-15 에
      실물을 찍어 **재서** 쓴 것이다(§194) — 추측한 꼴로 가드를 세우지 않는다."""
    실물 = {"state": "open", "number": 4,
            "security_advisory": {"summary": "x", "severity": "high"},
            "security_vulnerability": {"first_patched_version": {"identifier": "1.2.2"}},
            "dependency": {"scope": "runtime", "manifest_path": "m",
                           "package": {"name": "p"}}}
    막, 알 = 판정([실물])
    if len(막) != 1 or "p" not in 막[0] or "1.2.2" not in 막[0] or 알:
        print(f"    ★ 카나리아가 죽었다 — runtime 경보를 못 읽는다 : {막} / {알}")
        sys.exit(2)
    import copy
    dev = copy.deepcopy(실물)
    dev["dependency"]["scope"] = "development"
    막2, 알2 = 판정([dev])
    if 막2 or len(알2) != 1:
        print(f"    ★ 카나리아가 죽었다 — dev 와 runtime 을 못 가른다 : {막2} / {알2}")
        sys.exit(2)
    닫힘 = copy.deepcopy(실물)
    닫힘["state"] = "fixed"
    if 판정([닫힘]) != ([], []) or 판정([]) != ([], []):
        print("    ★ 카나리아가 죽었다 — 닫힌 경보나 빈 목록에서 경보를 만든다")
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _canary()
    if "--selftest" in args:
        print("  프로브 살아 있다 — runtime/dev 가름 · 닫힌 경보 거르기")
        return 0
    import shutil
    if not shutil.which("gh"):
        print("  `gh` 가 없다 — **못 보는 것은 통과가 아니다**")
        return 2
    repo = 저장소()
    if not repo:
        print("  origin 에서 owner/repo 를 못 읽었다")
        return 2
    것 = 묻는다(repo)
    if isinstance(것, str):
        print(f"  {것}")
        return 2
    막을것, 알릴것 = 판정(것)
    if "--json" in args:
        print(json.dumps({"막을것": 막을것, "알릴것": 알릴것}, ensure_ascii=False))
    else:
        for x in 막을것:
            print(f"    ✗ {x}")
        for x in 알릴것:
            print(f"    · {x}   ← 사용자에게 안 실린다(dev). 막지 않는다")
        if not 막을것 and not 알릴것:
            print(f"  Dependabot 에 열린 경보 없음 — {repo}")
        elif not 막을것:
            print(f"  Dependabot — 막을 것 없음 · dev 범위 {len(알릴것)}건 (위에 적었다)")
    return 1 if 막을것 else 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다(DECISIONS §21 · §127).
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("    ✗ 도구가 깨졌다 — 위 역추적이 자리를 든다", file=sys.stderr)
        raise SystemExit(2) from None
