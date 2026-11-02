# ★ **세샤트의 `tools/check_gh.py` 에서 왔다. 정본은 세샤트다**(seshat DECISIONS §331).
#   고칠 것이 있으면 거기서 고치고 다시 옮긴다. 이 저장소에서 갈린 자리는 둘이다 — **둘을 여기 적는다**
#     · `ROOT` 를 `tools/check_gh.py` 의 부모에서 잡는다(같다). 글자가 갈린 곳은 **`선언` 표뿐**이다
#     · `선언` 이 **비어 있다** — 이 저장소의 워크플로(`ci` · `deploy` · `drift` · `proposal`)에는 PR 을 열거나
#       설정을 쓰는 `gh` 호출이 **하나도 없다**(재서 확인했다). 배포 게이트(`env_protection.py`)와 합친 가지
#       자동 삭제는 `doctor` 가 따로 읽는다. 이 자의 값은 **새 워크플로가 `gh pr create` 를 쓰는 순간
#       선언을 강제하는 것**이다 — 비어 있어도 장식이 아니다.
#   아래 `§N` 은 세샤트의 절 번호다.
r"""**워크플로가 기대는 GitHub 설정이 선언돼 있고, 실제 값이 그것인가**(seshat DECISIONS §331).

  python3 tools/check_gh.py            선언 전수 + 실제 설정을 읽어 견준다(이 기계에서만 쓴다)
  python3 tools/check_gh.py --static   선언 전수만 — 망 없이 돈다(CI 도 돈다)
  python3 tools/check_gh.py --selftest 판별식이 살아 있나
  python3 tools/check_gh.py --list     선언표를 찍는다

★ **2026-11-01 `보안설정.sh` 가 `can_approve_pull_request_reviews` 를 `true → false` 로 조였고 다음
  `papers` 가 죽었다.** 이름엔 approve 만 있지만 **한 체크박스가 PR 을 만드는 것과 승인하는 것을 같이
  지배한다.** 워크플로가 설정에 기댄다는 사실은 **어디에도 안 적혔고 아무도 안 쟀다** — `doctor` 의
  `SKIP (GitHub 설정이다)` 는 선언만 하고 영원히 안 재는 자리였다. **못 쟀다는 없다와 같아진다**(§59).
★ **이 관문의 값어치는 ② 에 있다.** 새 워크플로가 PR 을 열면(`gh pr create` …) **선언표에 줄이 없는 순간
  운다.** 선언이 있으면 설정을 조일 때 **조이기 전에** 울 수 있다.
★ **종료 코드를 가른다**(§59).
  0  전부 맞다
  1  어긋났다 — 선언이 없는 쓰임 · 실제 값이 기대와 다름 · 쓰임 없는 낡은 선언
  2  도구 고장
  3  **못 쟀다** — `gh` 가 없다 · 로그인이 안 됐다 · 토큰에 권한이 없다
★ **CI 에서는 3 이 정상이다.** `actions/permissions/workflow` 는 admin 권한을 요구하고 `GITHUB_TOKEN`
  은 admin 이 아니다. 그래서 **실측은 CI 밖이다** — `verify.sh` 가 「CI 밖 — 권한이다」 라고 적고,
  CI 는 `--static` 만 돈다. **CI 에서 영원히 3 인 관문을 초록으로 보이게 만들지 않는다.**
★ **밖 — 쓰임을 못 뽑는 꼴은 안 본다.** 아래 `쓰임무늬` 에 든 꼴만 센다. 스크립트 파일로 빼 부르거나
  `gh` 대신 `curl` 로 API 를 치면 **안 잡힌다** — 무늬를 늘려도 알려진 목록은 언젠가 하나를 빠뜨린다
  (thoth §43). 새 꼴이 보이면 무늬에 더한다.
★ **밖 — 기대값이 옳은지는 못 본다.** 선언과 실물이 같은가만 본다. 그 설정을 켜 두는 것이 맞는가
  (§332 가 PAT 를 안 쓰기로 한 까닭)는 읽는 사람이 판정한다.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLOWS = ROOT / ".github/workflows"

#: **쓰임 → 무늬.** GitHub 설정에 기대는 워크플로의 손짓. 주석은 이미 뗀 글에 건다.
쓰임무늬 = {
    "gh pr create": re.compile(r"\bgh\s+pr\s+create\b"),
    "gh pr merge": re.compile(r"\bgh\s+pr\s+merge\b"),
    "gh issue (create|comment)": re.compile(r"\bgh\s+issue\s+(?:create|comment)\b"),
    "peter-evans/create-pull-request": re.compile(r"\buses:\s*peter-evans/create-pull-request@"),
    "gh api -X (PUT|PATCH|POST|DELETE)":
        re.compile(r"\bgh\s+api\b[^\n]*?(?:-X|--method)[ =]+(?:PUT|PATCH|POST|DELETE)\b"),
}

#: **(워크플로, 쓰임) → [(끝점, 필드, 기대값, 까닭)].** 끝점은 `repos/{owner}/{repo}/` 뒤의 몫이다.
선언: dict[tuple[str, str], list[tuple[str, str, object, str]]] = {}


class 못쟀다(Exception):
    """망 · 로그인 · 권한 · 응답 꼴 — **값을 못 읽었다.** 어긋남이 아니다."""


def 코드줄(글: str) -> str:
    """주석을 떼고 `\\` 로 이은 줄을 합친다. **주석에 적힌 `gh pr create` 는 쓰임이 아니다.**"""
    줄 = [x for x in 글.splitlines() if not x.lstrip().startswith("#")]
    return re.sub(r"\\\n\s*", " ", "\n".join(줄))


def 쓰임들(글: str) -> list[str]:
    코드 = 코드줄(글)
    return [이름 for 이름, 무늬 in 쓰임무늬.items() if 무늬.search(코드)]


def 선언_점검(워크플로: dict[str, str], 표: dict | None = None) -> list[str]:
    """① 쓰임마다 선언이 있나 ② 쓰임 없는 낡은 선언은 없나. `워크플로` 는 `{상대경로: 글}`."""
    표 = 선언 if 표 is None else 표
    난것: list[str] = []
    본 = {(자리, 쓰임) for 자리, 글 in 워크플로.items() for 쓰임 in 쓰임들(글)}
    for 자리, 쓰임 in sorted(본 - set(표)):
        난것.append(f"{자리} 가 `{쓰임}` 을 쓰는데 GitHub 설정 선언이 없다 — tools/check_gh.py 의 `선언` 에 더한다")
    for 자리, 쓰임 in sorted(set(표) - 본):
        난것.append(f"선언 ({자리}, `{쓰임}`) 에 해당하는 쓰임이 없다 — 낡은 선언이다. 지운다")
    return 난것


def 견준다(표: dict, 읽는다) -> tuple[int, list[str]]:
    """(종료 코드, 할 말). `읽는다(끝점) -> dict` 를 밖에서 받는다 — 이 함수는 망을 안 탄다."""
    말: list[str] = []
    어긋남 = 0
    for (자리, 쓰임), 줄들 in sorted(표.items()):
        for 끝점, 필드, 기대, 까닭 in 줄들:
            try:
                값 = 읽는다(끝점)
            except 못쟀다 as e:
                return 3, [f"못 쟀다 — {끝점}: {e}"]
            if not isinstance(값, dict) or 필드 not in 값:
                return 3, [f"못 쟀다 — {끝점} 응답에 `{필드}` 가 없다(API 가 바뀌었나)"]
            if 값[필드] != 기대 or type(값[필드]) is not type(기대):
                어긋남 += 1
                말.append(f"{자리} 의 `{쓰임}` 이 기댄다 — {끝점} {필드} = {기대!r} 인데 실제는 {값[필드]!r}\n"
                        f"        까닭: {까닭}")
            else:
                말.append(f"  맞다 — {끝점 or "(저장소)"} {필드} = {기대!r} ({pathlib.PurePath(자리).name} 의 `{쓰임}`)")
    return (1 if 어긋남 else 0), 말


def _저장소() -> str:
    r = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0 or "/" not in r.stdout:
        raise 못쟀다(f"저장소 이름을 못 읽었다 — {r.stderr.strip()[:120] or '빈 응답'}")
    return r.stdout.strip()


def 읽는다(끝점: str) -> dict:
    if shutil.which("gh") is None:
        raise 못쟀다("`gh` 가 없다")
    r = subprocess.run(["gh", "api", f"repos/{_저장소()}" + (f"/{끝점}" if 끝점 else "")], capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        # 401 · 403 · 404 는 **권한이 없다는 말**이다 — 값이 틀렸다는 말이 아니다
        raise 못쟀다(r.stderr.strip().splitlines()[0][:160] if r.stderr.strip() else f"gh rc {r.returncode}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError as e:
        raise 못쟀다(f"응답이 JSON 이 아니다({e.msg})") from e


def 워크플로들() -> dict[str, str]:
    return {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(FLOWS.glob("*.yml"))}


def _selftest() -> int:
    """판별식이 살아 있나 — 합성 응답으로 **틀린 값을 먹여** 우는 것을 본다. 없으면 장식이다."""
    글 = "      - run: |\n          gh pr create --base main\n"
    주석글 = "      # gh pr create 가 실패했다\n      - run: echo\n"
    이은글 = "      - run: |\n          gh api \\\n            -X PUT repos/x/y\n"
    표 = {("a.yml", "gh pr create"): [("e", "f", True, "까닭")]}
    검 = []

    def 묻는다(이름: str, 참: bool) -> None:
        if not 참:
            검.append(이름)

    묻는다("쓰임을 못 뽑는다", 쓰임들(글) == ["gh pr create"])
    묻는다("주석의 쓰임을 센다", 쓰임들(주석글) == [])
    묻는다("이은 줄의 -X 를 못 뽑는다", 쓰임들(이은글) == ["gh api -X (PUT|PATCH|POST|DELETE)"])
    묻는다("선언 없는 쓰임을 못 잡는다", len(선언_점검({"a.yml": 글}, {})) == 1)
    묻는다("낡은 선언을 못 잡는다", len(선언_점검({"a.yml": 주석글}, 표)) == 1)
    묻는다("선언이 맞는데 운다", 선언_점검({"a.yml": 글}, 표) == [])
    묻는다("맞는 값을 어긋남이라 한다", 견준다(표, lambda e: {"f": True})[0] == 0)
    묻는다("틀린 값을 통과시킨다", 견준다(표, lambda e: {"f": False})[0] == 1)
    묻는다("1 과 True 를 같다고 한다", 견준다(표, lambda e: {"f": 1})[0] == 1)

    def 권한없음(e: str) -> dict:
        raise 못쟀다("HTTP 403")
    묻는다("권한이 없는데 0/1 로 끝난다", 견준다(표, 권한없음)[0] == 3)
    묻는다("필드가 없는데 통과시킨다", 견준다(표, lambda e: {})[0] == 3)
    if 검:
        print("check_gh: 판별식이 거꾸로다 — " + " · ".join(검), file=sys.stderr)
        return 2
    print("  판별식이 산다 — 틀린 값 1 · 권한 없음 3 · 선언 없는 쓰임 1")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--selftest" in args:
        return _selftest()
    if "--list" in args:
        for (자리, 쓰임), 줄들 in sorted(선언.items()):
            for 끝점, 필드, 기대, 까닭 in 줄들:
                print(f"  {자리} · `{쓰임}` → {끝점} {필드} = {기대!r}\n      {까닭}")
        return 0
    난것 = 선언_점검(워크플로들())
    for x in 난것:
        print(f"    {x}")
    if 난것:
        return 1
    if "--static" in args:
        n = sum(len(v) for v in 선언.values())
        print(f"  선언 {n} — 쓰임마다 줄이 있고 낡은 줄이 없다(실측은 CI 밖)")
        return 0
    rc, 말 = 견준다(선언, 읽는다)
    for x in 말:
        print(f"    {x}" if rc else x)
    if rc == 3:
        print("    ※ **못 쟀다는 통과가 아니다**(§59). 이 기계에서 `gh auth login` 한 admin 토큰으로 돈다",
              file=sys.stderr)
    return rc


if __name__ == "__main__":
    # ★ 위반(1)과 못 쟀다(3)와 도구 고장(2)을 다른 코드로 끝낸다(seshat DECISIONS §21 · §232 · §59)
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("    ✗ 도구가 깨졌다 — 위 역추적이 자리를 든다\n"
              "      고치고 다시 돌린다 : python3 tools/check_gh.py --selftest", file=sys.stderr)
        sys.exit(2)
