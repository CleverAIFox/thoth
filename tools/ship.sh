#!/usr/bin/env bash
# 커밋부터 위생까지의 순서. 한 줄로 묶는다.
#
#   bash tools/ship.sh "커밋 메시지"
#   bash tools/ship.sh --dry "메시지"    푸시 직전까지만
#
# ★ **순서를 사람 머리에서 코드로 옮긴다.** 알고 있는 목록은 언젠가 하나를
#   빠뜨린다. 2026-09-13 세션에서 문서 대조를 두 번, 위생을 한 번 빠뜨렸고
#   **세 번 다 '무조건' 단계였다**(DECISIONS §43).
#
# ★ **푸시는 자동으로 하지 않는다.** 무엇이 나가는지 보여주고 사람이 친다.
#   자동으로 미는 도구는 사고가 난다.
#
# ★ **`--no-verify` 를 받지 않는다.** 급할 때 넘기는 문을 만들면 급할 때
#   넘긴다.
#
# ★ **커밋 메시지를 지어내지 않는다.** 인자로 받는다.
#
# ★ `doctor` 는 이 스크립트를 모른다. 상위 도구가 하위 검사 사슬에 들어가면
#   순환이 된다 — `doctor` 에 `--ship` 같은 인자를 두지 않는 이유다.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
. "$ROOT/tools/lib/env.sh"; load_env "$ROOT/.env"

DRY=0
[ "${1:-}" = "--dry" ] && { DRY=1; shift; }
MSG="${1:-}"
[ -n "$MSG" ] || { echo "커밋 메시지가 없다 — bash tools/ship.sh \"메시지\"" >&2; exit 1; }

step(){ printf '\n\033[1m%s\033[0m\n' "$1"; }
die(){ printf '\033[31m멈춘다 — %s\033[0m\n' "$1" >&2; exit 1; }

# ── 0. 바꿀 것이 있는가 ──────────────────────────────────
#
# ★ **없으면 시작하지 않는다.** 패치를 받지 못한 채 이 스크립트를 부르면
#   doctor 를 다 돌리고 3 단계에서야 "nothing to commit" 으로 멈춘다. 4분을
#   쓰고 아무것도 하지 않는다 — 실패는 그것이 일어난 자리에서 알린다
#   (DECISIONS §37 · §52).
if [ -z "$(git status --porcelain)" ]; then
  echo "바꿀 것이 없다 — 작업 트리가 깨끗하다"
  echo "  패치를 받았는가 : bash tools/apply_patch.sh"
  exit 1
fi

# ── 1. 검사 ──────────────────────────────────────────────
step "1/4  doctor"
bash tools/doctor.sh || die "doctor 가 FAIL 했다"

# ── 2. 문서 대조 ─────────────────────────────────────────
#
# ★ 내용이 코드와 맞는지는 사람이 본다(`check_docs.py` 머리말). 기계가 볼 수
#   있는 것은 **안 봤다는 사실**이다. 코드가 바뀌었는데 문서가 그대로면 묻는다.
step "2/4  문서 대조"
STAGED_ALL="$(git status --porcelain | awk '{print $NF}')"
CODE="$(printf '%s\n' "$STAGED_ALL" | grep -E '^(tools|worker|extension)/' || true)"
DOCS="$(printf '%s\n' "$STAGED_ALL" | grep -E '^(docs/|README\.md)' || true)"

if [ -n "$CODE" ] && [ -z "$DOCS" ]; then
  echo "  코드가 바뀌었는데 문서가 그대로다."
  printf '%s\n' "$CODE" | sed 's/^/    /'
  echo
  echo "  docs/MASTER.md · docs/PLAN.md · docs/DECISIONS.md · README.md 넷을"
  echo "  대조했는가. 손댈 것이 정말 없으면 --dry 로 확인하고 직접 커밋한다."
  die "문서를 보지 않았다"
fi
if [ -n "$DOCS" ]; then
  echo "  문서 변경 있음"
  printf '%s\n' "$DOCS" | sed 's/^/    /'
else
  echo "  코드 변경 없음 — 대조할 것이 없다"
fi

# ── 3. 커밋 ──────────────────────────────────────────────
step "3/4  커밋"
# ★ **새 바이너리를 묻지 않고 싣지 않는다**(DECISIONS §115). `git add -A` 는 작업 트리에
#   떨어진 것을 전부 담는다 — 2026-09-22 에 `infra/tfplan`(토큰이 평문으로 든 plan 파일)이
#   그렇게 공개 저장소로 나갔다. 패치가 들이는 새 파일은 텍스트이고, 바이너리는 기획서처럼
#   `docs/` 에만 산다. 그 밖의 새 바이너리는 멈춘다.
NEW_BIN=""
while IFS= read -r f; do
  [ -n "$f" ] && [ -s "$f" ] || continue
  case "$f" in docs/*) continue ;; esac
  LC_ALL=C grep -qI . "$f" 2>/dev/null || NEW_BIN="$NEW_BIN $f"
done <<< "$(git ls-files --others --exclude-standard)"
[ -z "$NEW_BIN" ] || die "새 바이너리가 있다:$NEW_BIN — 산출물이면 지우거나 .gitignore 에 넣는다"
git add -A
git diff --cached --stat | tail -1
# ★ **실패 이유를 단정하지 않는다.** 훅이 막은 것과 git 이 거부한 것은 대응이
#   다르다. 시킨 대로 훅을 보면 아무것도 없는 경우가 있다(DECISIONS §37 의
#   재발).
if ! COMMIT_OUT="$(git commit -m "$MSG" 2>&1)"; then
  printf '%s\n' "$COMMIT_OUT" | sed 's/^/  /'
  case "$COMMIT_OUT" in
    *"nothing to commit"*|*"no changes added"*)
      die "커밋할 것이 없다" ;;
    *"Please tell me who you are"*|*"unable to auto-detect"*)
      die "git 신원이 없다 (git config --global user.email · user.name)" ;;
    *)
      die "커밋이 거부됐다 — 위 출력을 본다" ;;
  esac
fi
printf '%s\n' "$COMMIT_OUT" | tail -2 | sed 's/^/  /'

# ── 4. 푸시 안내 · 위생 ──────────────────────────────────
step "4/4  푸시"
if [ "$DRY" = 1 ]; then
  echo "  --dry 라 밀지 않는다. 나갈 것 :"
  git log --oneline "@{u}..HEAD" 2>/dev/null | sed 's/^/    /' || git log --oneline -1 | sed 's/^/    /'
  echo
  echo "  밀려면 : git push && python3 tools/sweep.py --fix"
  exit 0
fi

echo "  나갈 것 :"
git log --oneline "@{u}..HEAD" 2>/dev/null | sed 's/^/    /' || git log --oneline -1 | sed 's/^/    /'
echo
echo "  git push        ← 직접 친다. 이 도구는 밀지 않는다"
echo "  그 뒤 : python3 tools/sweep.py --fix"
