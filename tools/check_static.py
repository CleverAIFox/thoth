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
}
USES = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)@v(\d+)\b")


def node20_uses(text: str) -> list[tuple[int, str]]:
    """(줄번호, `액션@vN`). 빈 리스트가 통과다."""
    bad = []
    for n, line in enumerate(text.split("\n"), 1):
        code = line.split("#", 1)[0]
        for m in USES.finditer(code):
            name, major = m.group(1), int(m.group(2))
            if name in NODE20 and major <= NODE20[name]:
                bad.append((n, f"{name}@v{major}"))
    return bad


def check_node20() -> list[str]:
    fails = []
    for p in sorted(ROOT.glob(".github/workflows/*.yml")):
        for n, use in node20_uses(p.read_text(encoding="utf-8")):
            fails.append(f"{p.relative_to(ROOT)}:{n} Node 20 액션 — {use}")
    return fails


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


def main() -> int:
    fails = check_tf() + check_node20()
    wf, skip = check_workflows()
    fails += wf
    for f in fails:
        print(f"  {f}", file=sys.stderr)
    if skip:
        print(f"  건너뜀 : {skip}", file=sys.stderr)
    if not fails:
        print("  인용 문자열이 ASCII 다 · Node 20 액션 없음" + ("" if skip else " · 워크플로가 YAML 이다"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
