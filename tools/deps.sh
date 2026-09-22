#!/usr/bin/env bash
# 의존성 봇의 PR 을 치운다(DECISIONS §122).
#   bash tools/deps.sh          본다. 초록인 PR 과 빨간 PR 을 가른다
#   bash tools/deps.sh --merge  초록인 것만 squash 로 합치고 가지를 지운 뒤 main 을 당긴다
#
# ★ **이 저장소는 로컬이 먼저다.** 패치 → ship → push 로 main 이 움직인다. 봇의 PR 을 GitHub 에서
#   합치면 원격 main 이 앞서가고, 다음 ship 의 push 가 거절된다. 그래서 합친 직후 여기서 당긴다.
# ★ **빨간 PR 은 합치지 않는다.** 이름만 대고 멈춘다. 고치는 것은 사람이 한다.
# ★ **가지를 남기지 않는다.** 합칠 때 원격 가지를 지우고(`--delete-branch`), 로컬의 원격 추적 가지는
#   `fetch --prune` 으로 지운다. 저장소 설정 `delete_branch_on_merge` 는 doctor 가 본다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MERGE=0
[ "${1:-}" = "--merge" ] && MERGE=1

command -v gh >/dev/null 2>&1 || { echo "gh 가 없다" >&2; exit 2; }

# 봇 PR 과 검사 결과. 검사가 하나라도 실패 · 진행 중이면 초록이 아니다
ROWS="$(gh pr list --author 'app/dependabot' --state open \
  --json number,title,statusCheckRollup \
  --jq '.[] | [.number, .title, ([.statusCheckRollup[]? | (.conclusion // .status)] | if length == 0 then "NONE" elif all(. == "SUCCESS" or . == "SKIPPED" or . == "NEUTRAL") then "GREEN" else "RED" end)] | @tsv')"

if [ -z "$ROWS" ]; then
  echo "  봇 PR 없음"
else
  printf '%s\n' "$ROWS" | while IFS=$'\t' read -r num title state; do
    case "$state" in
      GREEN) mark="초록" ;;
      NONE)  mark="검사 없음" ;;
      *)     mark="빨강 · 진행 중" ;;
    esac
    printf '  #%-5s %-12s %s\n' "$num" "$mark" "$title"
    if [ "$MERGE" = 1 ] && [ "$state" = GREEN ]; then
      gh pr merge "$num" --squash --delete-branch >/dev/null && echo "         합쳤다 · 가지를 지웠다"
    fi
  done
fi

git fetch --prune --quiet
if [ "$MERGE" = 1 ]; then
  git pull --ff-only --quiet && echo "  main 을 당겼다 — 다음: bash tools/doctor.sh"
else
  echo "  합치려면: bash tools/deps.sh --merge"
fi
