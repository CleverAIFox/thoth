"""푸시하거나 `apply` 한 뒤에야 드러나는 것을 앞으로 당긴다.

  python3 tools/check_static.py

★ 두 검사가 한 파일에 있는 이유는 같은 성질이라서다. **문법은 맞는데 받는
  쪽이 거절한다.** `terraform validate` 는 HCL 을 보지 AWS API 의 값 제약을
  보지 않고, git 은 YAML 을 보지 않는다. 그래서 둘 다 원격에 나간 다음에야
  안다 — 2026-09-15 에 하나씩 걸렸다(DECISIONS §87).

## 1. 워크플로 YAML

깨진 워크플로는 **조용히 사라진다.** `gh workflow run` 이 "could not find any
workflows named ..." 를 내는데, 그 문구는 파일이 없을 때와 같다.

★ `yaml` 이 없으면 `SKIP` 이다. `doctor` 의 린터 취급과 같고, **CI 는 그것을
  넘어가지 못하게 따로 본다**(§54).

## 2. `.tf` 의 인용 문자열

AWS 는 `description` 같은 필드에 ASCII 만 받는다. 이 저장소는 주석도 문서도
전부 한글이라 **섞여 들어가기 쉽고**, `terraform validate` 는 통과시킨다.

★ **`resource` 블록 안만 본다.** `variable` 과 `output` 의 설명은 terraform
  안에서 끝나고 API 로 나가지 않는다. 거기까지 막으면 한글 문서를 쓰지 말라는
  말이 되고, **검사가 넓으면 끄는 방법부터 찾게 된다**(§46).

★ 주석(`#`)과 히어독(`<<-EOT`)도 건너뛴다. 나가는 것은 인용 문자열이다.

## 3. Node 20 액션

러너가 Node 20 액션을 Node 24 로 **강제로** 돌리고 경고만 남긴다. 강제가 끝나는
날 워크플로 셋이 한꺼번에 멈추고, 그때까지는 초록불이다(DECISIONS §100).

★ **아는 옛 메이저만 막는다.** 액션의 `action.yml` 을 받아 `runs.using` 을 보면
  정확하지만 네트워크가 든다. 이 저장소가 실제로 쓰는 액션의 Node 20 메이저를
  적어 두고, 올린 뒤 되돌아가는 것만 막는다. 새 액션을 들이면 그때 여기에 적는다.

★ `gitleaks/gitleaks-action` 은 처음에 빠졌다. Node 24 판을 확인하지 않고
  "모른다" 로 두었는데 v3 이 이미 있었다(DECISIONS §101).

## 4. 액션 고정과 시간 상한

메이저 태그는 업스트림이 옮긴다. `uses:` 가 전부 SHA 로 고정됐는지 본다
(DECISIONS §125). 러너를 `ubuntu-24.04` 로 못 박은 것과 같은 규율이고, **가장
값진 축**(배포 자격증명과 같은 잡에서 도는 액션)에만 그것이 없었다.

★ **판 주석(`# v7.0.1`)도 요구한다.** SHA 만 있으면 사람이 무엇을 쓰는지 못 읽고,
  §3 의 Node 20 검사가 **메이저를 읽을 자리를 잃는다.**

그리고 **작업마다 `timeout-minutes`** 를 요구한다. 없으면 GitHub 기본 **6시간**까지
매달린다 — `deploy.yml` 의 `apply` 는 배포 자격증명을 든 작업이라 그 세션까지 같이 태운다.
재사용 워크플로를 부르는 작업은 뺀다(GitHub 가 거기 상한을 거부한다).

## 5. 번역 캐시 삭제 지시

`rm … translations.json` 을 적은 문서 · 스크립트를 막는다. 과금 엔진에서는
재과금이다(MASTER §11-4). `CACHE_FILE` 로 딴 파일을 가리키는 것이 맞는 길이다.

  0  이상 없음
  1  위반
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def tf_bad_strings(text: str) -> list[tuple[int, str]]:
    """`resource` 블록 안 인용 문자열의 비ASCII 를 찾는다.

    ★ 중괄호 깊이로 블록을 따라간다. HCL 파서를 붙이지 않는 이유는 의존성
      하나가 이 검사 하나보다 비싸서다 — 틀리면 `apply` 가 여전히 잡는다.
    """
    bad, in_heredoc, depth, res_at = [], False, 0, None
    for n, line in enumerate(text.split("\n"), 1):
        if in_heredoc:
            if re.match(r"^\s*EOT\s*$", line):
                in_heredoc = False
            continue
        if "<<-EOT" in line or "<<EOT" in line:
            in_heredoc = True
            continue
        code = "" if line.lstrip().startswith("#") else line.split("#", 1)[0]

        if res_at is None and re.match(r'^\s*resource\s+"', code):
            res_at = depth
        elif res_at is not None:
            for lit in re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', code):
                if any(ord(c) > 127 for c in lit):
                    bad.append((n, lit))

        depth += code.count("{") - code.count("}")
        if res_at is not None and depth <= res_at:
            res_at = None
    return bad


# 액션 → Node 20 인 메이저. 이 번호 이하를 막는다.
NODE20 = {
    "actions/checkout": 4,
    "actions/setup-python": 5,
    "actions/setup-node": 4,
    "astral-sh/setup-uv": 6,
    "hashicorp/setup-terraform": 3,
    "aws-actions/configure-aws-credentials": 5,
    "gitleaks/gitleaks-action": 2,
    # 2026-09-22 seshat GPU 평가 실행의 주석이 짚었다. 이 저장소는 쓰지 않지만 같은 목록이다(DECISIONS §120)
    "actions/upload-artifact": 4,
}
USES = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)@v(\d+)\b")
# ★ **SHA 로 고정한 줄의 판은 주석에 산다.** 그래서 이 검사는 주석을 벗기면
#   아무것도 못 본다 — 2026-10-03 에 `uses:` 를 전부 SHA 로 바꾼 순간
#   `check_node20` 이 조용히 0건이 됐다(DECISIONS §125). **고정이 검사를 껐다.**
#   꼴을 바꾸는 고침이 **그 꼴을 읽던 검사를 같이 고쳐야 한다**는 자리다.
USES_PINNED = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)@[0-9a-f]{40}\s*#\s*v(\d+)\b")
# `uses:` 가 가리킬 수 있는 꼴 — 저장소 액션 · 같은 저장소의 경로 · 도커 이미지.
USES_ANY = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)")


def _액션들(line: str) -> list[tuple[str, int]]:
    """한 줄에서 (액션 이름, 메이저). 맨 태그 꼴과 SHA 고정 꼴을 다 읽는다."""
    것 = [(m.group(1), int(m.group(2))) for m in USES.finditer(line.split("#", 1)[0])]
    것 += [(m.group(1), int(m.group(2))) for m in USES_PINNED.finditer(line)]
    return 것


def node20_uses(text: str) -> list[tuple[int, str]]:
    """(줄번호, `액션@vN`). 빈 리스트가 통과다."""
    bad = []
    for n, line in enumerate(text.split("\n"), 1):
        for name, major in _액션들(line):
            if name in NODE20 and major <= NODE20[name]:
                bad.append((n, f"{name}@v{major}"))
    return bad


# ★ **메이저 태그는 업스트림이 언제든 옮긴다.** `@v7` 은 가리키는 커밋이 바뀌어도
#   이름이 같아서, 침해된 액션이 들어오는 것을 저장소 쪽에서는 아무것도 못 본다.
#   가장 무거운 자리가 `deploy.yml` 이다 — `configure-aws-credentials` 가
#   `production` 승인으로 받은 OIDC 토큰을 배포 역할로 바꾸고, 같은 잡의 다른
#   액션들이 **그 자격증명과 함께 돈다.**
#
# ★ **고정의 사고방식은 이미 있었다.** 러너는 `ubuntu-24.04` 로 고정하고
#   `check_runner` 가 강제한다. Node 20 액션도 목록으로 막는다. **가장 값진 축에만
#   그 규율이 없었다**(DECISIONS §125).
#
# ★ 운영 비용은 안 는다. `dependabot.yml` 의 `github-actions` 생태계가 SHA 핀도
#   갱신 PR 로 올린다 — 태그를 쓸 때와 같은 월 1회 PR 하나다.
#
# ★ **판을 주석으로 적는다.** SHA 만 있으면 사람이 무엇을 쓰는지 못 읽는다.
#   `# v7.0.1` 은 장식이 아니라 `node20_uses` 가 읽는 자료다.
def unpinned_uses(text: str) -> list[tuple[int, str]]:
    """SHA 로 고정하지 않은 `uses:`. 같은 저장소 경로(`./`)와 도커는 밖이다."""
    bad = []
    for n, line in enumerate(text.split("\n"), 1):
        code = line.split("#", 1)[0]
        m = USES_ANY.match(code)
        if not m:
            continue
        ref = m.group(1)
        if ref.startswith(("./", ".\\", "docker://")):
            continue
        손, _, 가리키는것 = ref.partition("@")
        if not re.fullmatch(r"[0-9a-f]{40}", 가리키는것):
            bad.append((n, ref))
            continue
        if not re.search(r"#\s*v\d+", line):
            bad.append((n, f"{손}@{가리키는것[:12]}… 판 주석이 없다"))
    return bad


def check_pinned() -> list[str]:
    return [f"{p.relative_to(ROOT)}:{n} `uses:` 가 SHA 로 안 고정됐다 — {ref}"
            for p in sorted(ROOT.glob(".github/workflows/*.yml"))
            for n, ref in unpinned_uses(p.read_text(encoding="utf-8"))]


# ★ **작업마다 시간 상한을 적는다**(파이어레인 `tools/actionpin.py` · DECISIONS §126).
#   없으면 GitHub 기본 **6시간**까지 매달린다. 2026-10-03 까지 이 저장소의 작업 여섯이
#   전부 상한이 없었고, 그중 `deploy.yml` 의 `apply` 는 **배포 자격증명을 든 작업**이다 —
#   매달리면 러너 시간과 그 OIDC 세션을 같이 태운다.
#
# ★ **족 가드다.** 「이 작업에 상한이 있나」 를 하나씩 묻지 않고 「상한 없는 작업이
#   있나」 를 묻는다. 새 작업이 생기는 순간 자동으로 물린다 — 파이어레인이 인스턴스
#   가드와 족 가드를 가르는 그 자리다.
#
# ★ **재사용 워크플로를 부르는 작업은 뺀다.** GitHub 가 그 작업에 `timeout-minutes` 를
#   거부한다 — 넣으면 워크플로가 통째로 안 돈다. 상한은 불려가는 쪽이 각자 든다.
작업머리 = re.compile(r"^  ([\w-]+):\s*$")


def jobs(text: str) -> dict[str, list[str]]:
    """`jobs:` 아래의 (작업 이름 → 그 블록의 줄들)."""
    것, 이름, 안 = {}, None, False
    for 줄 in text.split("\n"):
        if 줄.startswith("jobs:"):
            안 = True
            continue
        if not 안:
            continue
        if 줄 and not 줄.startswith(" "):
            break                      # 최상위 키로 돌아왔다
        if m := 작업머리.match(줄):
            이름 = m.group(1)
            것[이름] = []
            continue
        if 이름:
            것[이름].append(줄)
    return 것


def timeout_faults(text: str) -> list[str]:
    난것 = []
    for 이름, 블록 in jobs(text).items():
        if any(re.match(r"^    uses:\s*\S", x) for x in 블록):
            continue                   # 재사용 워크플로 호출
        if not any(re.match(r"^    timeout-minutes:\s*\d+", x) for x in 블록):
            난것.append(이름)
    return 난것


def check_timeouts() -> list[str]:
    return [f"{p.relative_to(ROOT)} 의 작업 `{이름}` 에 `timeout-minutes` 가 없다 — "
            f"매달리면 **기본 6시간**을 태운다"
            for p in sorted(ROOT.glob(".github/workflows/*.yml"))
            for 이름 in timeout_faults(p.read_text(encoding="utf-8"))]


# ★ **번역 캐시를 지우라고 적은 글을 막는다**(MASTER §11-4 · DECISIONS §125).
#   지우면 번역이 버려지고 과금 엔진에서는 **재과금**이다. 2026-10-02 에
#   하위 README 둘이 정확히 그 줄을 들고 있었다 — MASTER 는 정반대를 적는데
#   **같은 절차가 두 곳에 살아서 한쪽만 고쳐졌다.** 대신 `CACHE_FILE` 로 딴
#   파일을 가리킨다.
캐시삭제 = re.compile(r"\brm\b[^\n]*\b(?:translations\.json|\.cache/translations)")


def cache_rm(text: str) -> list[int]:
    return [n for n, line in enumerate(text.split("\n"), 1) if 캐시삭제.search(line)]


# ── 로컬 전용 검사의 선언 ──────────────────────────────────────────────────
#
# ★ **CI 가 안 보는 검사는 선언돼 있어야 한다**(파이어레인 `tools/gate_parity.py` ·
#   DECISIONS §127). CI 의 `verify` 작업은 `doctor.sh --repo` 를 돌고, `--repo` 는
#   기계 설정에 기대는 검사를 건너뛴다. **건너뛰는 것 자체는 옳다** — CI 에는 SSD 도
#   `.env` 도 `gh` 도 없다. 위험한 것은 **건너뛰는데 아무 말도 안 하는 것**이다.
#   그러면 「그 기계에서 사람이 doctor 를 돌렸을 때만」 도는 검사가 되고, 안 돌리면
#   아무도 모른다.
#
# ★ **지금은 일곱 자리가 전부 사유를 적고 있다**(2026-10-03 실측) — `.env 존재` ·
#   `SSD 비밀` · `워커 노출` · `기계 설정 묶음` · `인프라 적용 시차` · `배포 게이트` ·
#   `가지 자동 삭제`. 그래서 파이어레인처럼 선언 표를 새로 만들지 않았다.
#   **없는 병에 관문을 세우지 않는다.**
#
# ★ **일곱째가 이 래칫이 실제로 문 첫 자리다**(DECISIONS §133). `tf.sh apply` 의 도장을
#   `doctor` 가 보게 하면서 `--repo` 가지를 하나 더 만들었고, **사유를 적었는데도** 이 수가
#   울었다 — 그래서 수를 고치며 위 목록도 같이 고쳤다. **세는 자와 적는 자가 같이 움직인다.**
#
# ★ **다만 수는 못 박는다.** 다음 사람이 `if [ "$SCOPE" != "--repo" ]` 가지를 하나 더
#   만들고 `skip` 을 안 적으면 **조용히 CI 밖이 는다.** 이 수가 그것을 잡는다 — 늘어도
#   줄어도 운다(양방향 래칫). 사유를 적으면서 늘리는 것은 **여기 수를 같이 고치는 일**이다.
SCOPE_BRANCHES = 7


def scope_branches(text: str) -> list[int]:
    """`$SCOPE` 를 `--repo` 와 견주는 줄. 그 자리가 CI 와 이 기계를 가른다."""
    return [n for n, line in enumerate(text.split("\n"), 1)
            if re.search(r'"\$\{?SCOPE\}?"\s*(?:=|!=)\s*"--repo"', line.split("#", 1)[0])]


def check_scope_declared() -> list[str]:
    글 = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    줄들 = 글.split("\n")
    자리 = scope_branches(글)
    fails = []
    if len(자리) != SCOPE_BRANCHES:
        fails.append(f"tools/doctor.sh 의 `--repo` 가지가 {len(자리)}개다 — 선언은 "
                     f"{SCOPE_BRANCHES}개다. **CI 밖이 늘었거나 줄었다.** "
                     f"사유를 적고 `check_static.py` 의 `SCOPE_BRANCHES` 를 같이 고친다")
    # 각 가지가 세 줄 안에 사유 딸린 `skip` 을 내는가.
    for n in 자리:
        창 = "\n".join(줄들[n - 1:n + 3])
        if not re.search(r'skip "[^"]*\(', 창):
            fails.append(f"tools/doctor.sh:{n} `--repo` 가지가 사유 딸린 `skip` 을 안 낸다 — "
                         f"CI 가 왜 이것을 안 보는지 아무 데도 안 적힌다")
    return fails


# 이 검사와 그 시험의 예시 문자열은 지시가 아니다. **목록으로 못 박는다** —
# 여기에 파일이 늘면 그만큼 검사 밖이 는다.
캐시검사밖 = {"tools/check_static.py", "worker/tests/test_check_static.py"}


def check_cache_rm() -> list[str]:
    fails = []
    for d in ("docs", "worker/tests", "tools"):
        for p in sorted((ROOT / d).rglob("*")):
            if not p.is_file() or p.suffix not in {".md", ".sh", ".py"}:
                continue
            if p.relative_to(ROOT).as_posix() in 캐시검사밖:
                continue
            for n in cache_rm(p.read_text(encoding="utf-8", errors="replace")):
                fails.append(f"{p.relative_to(ROOT)}:{n} 번역 캐시를 지우라고 적었다 — "
                             f"`CACHE_FILE=/tmp/…` 로 딴 파일을 가리킨다(MASTER §11-4)")
    return fails


def check_node20() -> list[str]:
    fails = []
    for p in sorted(ROOT.glob(".github/workflows/*.yml")):
        for n, use in node20_uses(p.read_text(encoding="utf-8")):
            fails.append(f"{p.relative_to(ROOT)}:{n} Node 20 액션 — {use}")
    return fails


# ★ **러너 이미지를 고정한다**(DECISIONS §105). `ubuntu-latest` 는 날짜가 되면 저절로
#   다음 판으로 넘어간다 — 2026-10-19 에 26 으로. 패키지 구성이 바뀌어도 그날까지
#   초록불이고, 그날 이후 실패는 "이미지가 바뀌었다" 가 아니라 엉뚱한 단계의 오류로
#   보인다. 올리는 것을 사람이 하는 일로 둔다.
LATEST = re.compile(r"runs-on:\s*ubuntu-latest\b")


def latest_runners(text: str) -> list[int]:
    return [n for n, line in enumerate(text.split("\n"), 1)
            if LATEST.search(line.split("#", 1)[0])]


def check_runner() -> list[str]:
    return [f"{p.relative_to(ROOT)}:{n} 러너가 ubuntu-latest 다 — 판을 고정한다"
            for p in sorted(ROOT.glob(".github/workflows/*.yml"))
            for n in latest_runners(p.read_text(encoding="utf-8"))]


def check_tf() -> list[str]:
    fails = []
    for p in sorted(ROOT.glob("infra/*.tf")):
        for n, lit in tf_bad_strings(p.read_text(encoding="utf-8")):
            fails.append(f"{p.relative_to(ROOT)}:{n} 인용 문자열에 비ASCII — {lit!r}")
    return fails


def check_workflows() -> tuple[list[str], str | None]:
    try:
        import yaml
    except ImportError:
        return [], "yaml 이 없다 (pip install pyyaml)"
    fails = []
    for p in sorted(ROOT.glob(".github/workflows/*.yml")):
        try:
            yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            # ★ 위치를 적는다. 판정만 남기면 어디를 볼지 모른다(§70).
            fails.append(f"{p.relative_to(ROOT)} 가 YAML 이 아니다 — {str(e).splitlines()[-1].strip()}")
    return fails, None


def py_warnings(src: str, name: str) -> list[str]:
    """컴파일 경고를 실패로 읽는다.

    ★ **지금은 경고지만 나중에는 오류다.** 문자열 안의 `\\d` 같은 잘못된 이스케이프는
      Python 3.12 부터 `SyntaxWarning` 이고 앞으로 `SyntaxError` 가 된다. 테스트는 모듈을 이미
      컴파일된 채로 불러 경고를 삼키고, `package_lambda.sh` 만 한 줄 찍고 지나갔다
      (2026-09-22, `pairs.py` 의 docstring). 런타임을 올리는 날 워커가 import 에서 죽는다.
    """
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        try:
            compile(src, name, "exec")
        except SyntaxError as e:
            return [f"{name}:{e.lineno} {e.msg}"]
    return []


def check_python() -> list[str]:
    fails = []
    for d in ("worker/app", "worker/tests", "tools"):
        for p in sorted((ROOT / d).rglob("*.py")):
            if ".venv" in p.parts or "__pycache__" in p.parts:
                continue
            fails += py_warnings(p.read_text(encoding="utf-8"), str(p.relative_to(ROOT)))
    return fails


def main() -> int:
    fails = (check_tf() + check_node20() + check_runner() + check_python()
             + check_pinned() + check_cache_rm() + check_timeouts()
             + check_scope_declared())
    wf, skip = check_workflows()
    fails += wf
    for f in fails:
        print(f"  {f}", file=sys.stderr)
    if skip:
        print(f"  건너뜀 : {skip}", file=sys.stderr)
    if not fails:
        print("  인용 문자열이 ASCII 다 · Node 20 액션 없음 · 러너 고정 · 파이썬 컴파일 경고 없음"
              " · 액션이 SHA 로 고정됐다 · 작업마다 시간 상한 · 캐시 삭제 지시 없음"
              " · CI 밖이 전부 선언됐다"
              + ("" if skip else " · 워크플로가 YAML 이다"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
