#!/usr/bin/env bash
# 윈도우 다운로드 폴더에 받은 패치를 저장소에 적용한다.
#   bash tools/apply_patch.sh              가장 최근 thoth-*.patch
#   bash tools/apply_patch.sh 이름.patch    다운로드 폴더 안의 특정 파일
#   bash tools/apply_patch.sh /경로/x.patch 절대경로도 받는다
#   bash tools/apply_patch.sh --check ...   붙는지만 보고 적용하지 않는다
#
# ★ 경로의 정본은 .env 다. 기계마다 다른 값을 스크립트가 들면 두 곳이
#   조용히 어긋난다(sync_ext.sh 와 같은 이유).
#
# ★ **브라우저를 거친 패치는 줄끝이 CRLF 가 되어 있을 수 있다.** 저장소는
#   전부 LF 이므로 그대로 적용하면 문맥이 한 줄도 맞지 않아 "patch does not
#   apply" 로 죽는다. 원인이 내용이 아니라 줄끝이라는 것을 오류 메시지가
#   알려주지 않으므로, 여기서 먼저 벗겨 놓는다.
#
# ★ DrvFs 위의 파일을 직접 적용하지 않는다. 사본을 /tmp 에 두고 거기서
#   적용한다 — 줄끝 정리가 원본을 건드리지 않아야 다시 받을 필요가 없다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$ROOT/.env" ] && { set -a; . "$ROOT/.env"; set +a; }
: "${WIN_DOWNLOADS:?.env 에 WIN_DOWNLOADS 가 없다}"

CHECK=0
[ "${1:-}" = "--check" ] && { CHECK=1; shift; }
ARG="${1:-}"

if [ -z "$ARG" ]; then
  # ls -t 는 파일명에 공백이 있으면 깨진다. 패치 이름은 공백을 쓰지 않지만
  # 다운로드 폴더에 무엇이 들어올지는 정하지 못하므로 find 로 고른다.
  SRC="$(find "$WIN_DOWNLOADS" -maxdepth 1 -name 'thoth-*.patch' -printf '%T@ %p\n' 2>/dev/null \
         | sort -rn | head -1 | cut -d' ' -f2-)"
  [ -n "$SRC" ] || { echo "$WIN_DOWNLOADS 에 thoth-*.patch 가 없다" >&2; exit 1; }
elif [ -f "$ARG" ]; then
  SRC="$ARG"
else
  SRC="$WIN_DOWNLOADS/$ARG"
  [ -f "$SRC" ] || { echo "없는 파일 : $SRC" >&2; exit 1; }
fi

echo "패치 : $SRC"
echo "       $(stat -c '%s 바이트, %y' "$SRC" | cut -d. -f1)"

TMP="$(mktemp /tmp/thoth-patch.XXXXXX)"
trap 'rm -f "$TMP"' EXIT
sed 's/\r$//' "$SRC" > "$TMP"
if ! cmp -s "$SRC" "$TMP"; then
  echo "       줄끝 CRLF 를 LF 로 벗겼다"
fi

cd "$ROOT"

# ★ 적용 전에 작업 트리가 깨끗한지 본다. 더러운 상태에서 반쯤 적용되면
#   무엇이 패치이고 무엇이 원래 작업이었는지 가를 수 없다.
if git rev-parse --git-dir >/dev/null 2>&1; then
  if [ -n "$(git status --porcelain)" ]; then
    echo "경고 : 작업 트리에 커밋되지 않은 변경이 있다" >&2
    git status --short | sed 's/^/       /' >&2
    echo "       git stash 로 치우고 적용하는 것을 권한다" >&2
  fi
fi

if ! git apply --check -p1 "$TMP" 2>/tmp/thoth-patch.err; then
  # ★ 역적용이 되면 이미 붙어 있는 패치다. 이것과 "저장소가 어긋났다" 를
  #   가르지 않으면 같은 오류 메시지를 보고 무엇을 해야 할지 알 수 없다.
  #   둘은 대응이 정반대다 — 전자는 아무것도 하지 않는 것이 맞다.
  if git apply --check -R -p1 "$TMP" 2>/dev/null; then
    echo "       이미 적용되어 있다. 아무것도 하지 않는다"
    exit 0
  fi
  echo "붙지 않는다 :" >&2
  sed 's/^/       /' /tmp/thoth-patch.err >&2
  echo "       저장소가 패치를 만든 시점과 다른 상태일 수 있다" >&2
  exit 1
fi
echo "       붙는다"

[ "$CHECK" = 1 ] && { echo "--check 이므로 적용하지 않는다"; exit 0; }

git apply -p1 "$TMP"
echo "적용 완료"

# 적용 직후 상태를 보여 준다. 다음에 무엇을 해야 하는지가 여기서 갈린다.
echo
echo "== 바뀐 파일 =="
if git rev-parse --git-dir >/dev/null 2>&1; then
  git status --short | sed 's/^/  /'
fi

echo
echo "== .env 키 정합 =="
keys(){ grep -oE '^[A-Z_][A-Z0-9_]*=' "$1" 2>/dev/null | tr -d '=' | sort -u; }
if [ -f .env ]; then
  MISS="$(comm -23 <(keys .env.example) <(keys .env))"
  if [ -n "$MISS" ]; then
    echo "  .env 에 없는 키 : $(echo $MISS)"
    echo "  넣지 않으면 doctor.sh 가 FAIL 한다"
  else
    echo "  이상 없음"
  fi
else
  echo "  .env 가 없다"
fi

echo
echo "다음 : bash tools/doctor.sh"
