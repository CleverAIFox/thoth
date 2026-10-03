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
#
# ★ **패치는 제 바탕을 선언한다**(DECISIONS §129). 2026-10-03 에 기획서 3.0 패치가
#   「thoth-126 이 붙은 트리」 를 가정하고 만들어졌는데 **실물에는 126 이 안 붙어
#   있었다.** 결과는 hunk 오류 다섯 줄이었고 **무엇이 틀렸는지는 거기 안 적혀 있다** —
#   읽는 사람이 다섯 파일을 뒤져 추측해야 했다. 바탕을 적어 두면 **붙이기 전에**
#   한 줄로 끝난다. 꼴은 이렇다 :
#
#     바탕 : 1885406cb68227561e5d350d7ce17162a2d9fe71
#
#   `---` 뒤 · 첫 `diff` 앞에 둔다. 거기는 `git apply` 가 **안 읽는 자리**라
#   패치의 뜻을 바꾸지 않는다. **적는 값은 `git rev-parse HEAD^{tree}` 다** —
#   커밋 sha 가 아니다(DECISIONS §130).
#
# ★ **선언이 없으면 막지 않는다.** 옛 패치가 다 막히면 이 검사를 꺼 버린다
#   (DECISIONS §46). 없다고 **말하고** 넘어간다 — 말없이 넘어가는 것과는 다르다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/tools/lib/env.sh"; load_env "$ROOT/.env"
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

# ★ **이미 붙은 패치인가.** 역적용이 되거나 영수증이 있으면 그렇다. 두 자리에서
#   같은 물음을 물으므로 함수로 둔다 — 두 벌이면 한쪽만 늙는다.
already_applied(){
  git apply --check -R -p1 "$TMP" 2>/dev/null && return 0
  local R="$ROOT/.cache/applied-patches.tsv"
  [ -f "$R" ] && grep -q "^$(sha256sum "$TMP" | cut -d' ' -f1)	" "$R"
}

# ★ **바탕을 먼저 본다 — 아무것도 건드리기 전에**(DECISIONS §129). 바탕이 다르면
#   hunk 오류는 **증상이고 까닭이 아니다.** 까닭을 뒤에 적으면 증상부터 고치게 된다.
#
# ★ **커밋이 아니라 나무로 본다**(DECISIONS §130). 첫 판은 커밋 sha 를 견줬는데,
#   **같은 패치를 양쪽이 다 붙여도 커밋 sha 는 다르다** — 적용한 사람 · 시각 · 메시지가
#   섞여 들어간다. 묻는 것은 「같은 역사인가」 가 아니라 **「같은 내용 위에 서 있나」**
#   이고, 그 답은 나무 하나다. seshat 이 2026-09-23 에 이미 그렇게 적어 뒀다
#   (seshat DECISIONS §30 의 `Seshat-Base-Tree`) — 여기는 그것을 넉 달 늦게 옮긴 것이다.
# ★ **그리고 나무로 봐야 잡히는 것이 있다.** 2026-10-03 에 양쪽이 같은 패치들을 다 붙였는데
#   **파일 이름 하나가 깨져서** 그 파일을 고치는 hunk 가 한쪽에만 닿았다. 커밋 로그는
#   똑같아 보였고 **나무만 달랐다.**
BASE="$(sed -n 's/^바탕 : \([0-9a-f]\{7,40\}\)$/\1/p' "$TMP" | head -1)"
if [ -z "$BASE" ]; then
  echo "       바탕 선언 없음 — 어느 나무에서 만든 패치인지 모른다"
elif ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "       git 저장소가 아니라 바탕을 못 본다"
else
  # ★ **나무와 커밋을 둘 다 받는다**(DECISIONS §130). 적는 값은 **나무**인데,
  #   이 검사를 나무로 바꾸는 패치 자체는 **커밋을 보던 옛 판**이 받아야 한다 —
  #   2026-10-03 에 실제로 그 패치가 제 손으로 거절당했다. **검사를 바꾸는 패치는
  #   옛 검사를 통과해야 한다**(부트스트랩). 둘 다 받으면 그 덫이 없어진다.
  TREE="$(git rev-parse "HEAD^{tree}")"
  HEADSHA="$(git rev-parse HEAD)"
  case "$TREE" in
    "$BASE"*) echo "       바탕 맞다 : 나무 $(echo "$BASE" | cut -c1-8)" ;;
  esac
  case "$HEADSHA" in
    "$BASE"*) echo "       바탕 맞다 : 커밋 $(echo "$BASE" | cut -c1-8) — **나무로 적는 쪽이 낫다**" ;;
  esac
  case "$TREE$HEADSHA" in
    *"$BASE"*) : ;;
    *)
      # ★ 이미 붙었으면 나무가 바탕보다 앞선 것이 **정상**이다. 그것부터 가른다.
      if already_applied; then
        echo "       이미 적용되어 있다. 아무것도 하지 않는다"
        exit 0
      fi
      echo "바탕이 다르다 :" >&2
      echo "       패치는 $(echo "$BASE" | cut -c1-8) 에서 만들었고" >&2
      echo "       지금 나무는 $(echo "$TREE" | cut -c1-8) · 커밋은 $(echo "$HEADSHA" | cut -c1-8) 다" >&2
      echo "       사이에 무엇이 들어왔거나, 들어왔어야 할 패치가 안 붙어 있다" >&2
      echo "       git log --oneline -5 와 git rev-parse HEAD^{tree} 를 보내면" >&2
      echo "       그 나무로 다시 만든다" >&2
      exit 1 ;;
  esac
fi

if ! git apply --check -p1 "$TMP" 2>/tmp/thoth-patch.err; then
  # ★ 역적용이 되면 이미 붙어 있는 패치다. 이것과 "저장소가 어긋났다" 를
  #   가르지 않으면 같은 오류 메시지를 보고 무엇을 해야 할지 알 수 없다.
  #   둘은 대응이 정반대다 — 전자는 아무것도 하지 않는 것이 맞다.
  # ★ **영수증이 있으면 역적용이 안 붙어도 적용된 것이다.** 붙은 뒤에 그
  #   파일을 다음 패치가 또 고치면 정방향도 역방향도 안 붙는다. 그때
  #   "저장소가 어긋났다" 로 적으면 맞는 상태를 사고로 읽는다(§61).
  if already_applied; then
    echo "       이미 적용되어 있다. 아무것도 하지 않는다"
    exit 0
  fi
  echo "붙지 않는다 :" >&2
  sed 's/^/       /' /tmp/thoth-patch.err >&2
  echo "       정방향도 역방향도 붙지 않고 영수증도 없다" >&2
  echo "       패치를 만든 시점과 다른 상태이거나, 붙은 뒤 같은 파일이 또 바뀌었다" >&2
  exit 1
fi
echo "       붙는다"

[ "$CHECK" = 1 ] && { echo "--check 이므로 적용하지 않는다"; exit 0; }

git apply -p1 "$TMP"
echo "적용 완료"

# ★ **적용했다는 사실을 여기서 적는다.** 이 스크립트는 지금 그것을 아는데,
#   전에는 버리고 `sweep` 이 나중에 역적용으로 되알아내게 했다. 역적용 성공은
#   "적용됐다" 의 증거지만 **역적용 실패는 "적용 안 됐다" 의 증거가 아니다** —
#   붙은 뒤에 그 파일이 또 바뀌면 양쪽 다 안 붙는다(DECISIONS §61).
#
# ★ 해시는 **줄끝을 벗긴 본문**으로 잡는다. `sweep` 이 같은 정규화를 하므로
#   브라우저를 거쳐 CRLF 가 된 사본도 같은 값이 된다.
#
# ★ `.cache/` 는 기계 상태다. 커밋되지 않으며 `doctor` 가 무시 여부를 본다.
RECEIPT="$ROOT/.cache/applied-patches.tsv"
mkdir -p "$(dirname "$RECEIPT")"
printf '%s\t%s\t%s\n' \
  "$(sha256sum "$TMP" | cut -d' ' -f1)" \
  "$(basename "$SRC")" \
  "$(date -Iseconds)" >> "$RECEIPT"

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
echo "       그 뒤 : bash tools/ship.sh \"메시지\""
