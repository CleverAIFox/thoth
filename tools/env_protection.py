"""배포 게이트가 GitHub 에 실제로 걸려 있는지 본다(DECISIONS §98 · §110).

  python3 tools/env_protection.py                 gh 로 읽어 판정한다
  python3 tools/env_protection.py ENV.json POL.json   읽어 둔 응답으로 판정한다

★ **게이트는 저장소 밖에 산다.** `production` Environment 의 required reviewers 와
  `v*` 태그 제한은 GitHub 설정이라 `doctor` 도 CI 도 코드로는 보지 못했다. 문서가
  "승인을 거친다" 고 적은 채 게이트 없이 배포가 돈 날이 있었다(§98).

★ **판정과 수집을 나눈다.** `judge` 는 순수 함수이고 테스트가 본다. `gh` 는 이
  파일의 `main` 만 부른다 — 인증이 없는 기계에서는 못 쟀다(3)로 끝난다.

  0  게이트가 걸려 있다
  1  빠진 것이 있다
  3  재지 못했다 (gh 가 없거나 인증이 없다)
"""
import json
import subprocess
import sys

REPO = "CleverAIFox/thoth"
ENV = "production"
TAG = "v*"


def judge(env: dict, policies: dict) -> list[str]:
    """빠진 것 목록. 비면 통과다."""
    bad = []
    rules = env.get("protection_rules") or []
    reviewers = [r for r in rules if r.get("type") == "required_reviewers"]
    if not reviewers or not any(r.get("reviewers") for r in reviewers):
        bad.append("required reviewers 가 없다 — 태그만 밀면 승인 없이 apply 가 돈다")
    dbp = env.get("deployment_branch_policy") or {}
    if not dbp.get("custom_branch_policies"):
        bad.append("배포 브랜치 정책이 custom 이 아니다 — 아무 ref 에서나 production 에 닿는다")
    tags = [p.get("name") for p in (policies.get("branch_policies") or []) if p.get("type") == "tag"]
    if TAG not in tags:
        bad.append(f"태그 정책 {TAG} 가 없다 (있는 것 {tags})")
    return bad


def _gh(path: str) -> dict | None:
    try:
        r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 2:
        env = json.load(open(args[0], encoding="utf-8"))
        pol = json.load(open(args[1], encoding="utf-8"))
    else:
        env = _gh(f"repos/{REPO}/environments/{ENV}")
        pol = _gh(f"repos/{REPO}/environments/{ENV}/deployment-branch-policies")
        if env is None or pol is None:
            print("gh api 로 읽지 못했다 — gh auth status")
            return 3
    bad = judge(env, pol)
    for b in bad:
        print(b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
