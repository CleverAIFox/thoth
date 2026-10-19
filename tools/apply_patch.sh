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
#
# ★ **「더럽다」 에 두 가지가 있고, 되돌리는 명령이 다르다**(DECISIONS §195).
#   `git status --short` 의 **첫 칸은 색인**이고 **둘째 칸은 작업 트리**다 :
#
#       ` M file`   작업 트리만 바뀌었다        → git restore <file>
#       `M  file`   **색인에 올라가 있다**       → git reset --hard HEAD
#       `AD file`   색인엔 올렸고 작업 트리엔 없다
#
#   앞판은 둘을 한 줄로 뭉개고 「git stash 로 치우는 것을 권한다」 만 적었다.
#   2026-10-19 에 그 값을 치렀다 : `ship.sh` 가 **`git add -A` 를 한 뒤 훅에 막혀**
#   194 전체가 **색인에 올라간 채** 남았고, 내가 「`git restore .` 로 되돌려라」 고
#   말했다. **`git restore .` 는 색인을 안 건드린다** — 작업 트리를 **색인에서**
#   되돌리므로 194 가 그대로 복원됐고, 그 위에 패치를 붙이려다 **18 개가 전부
#   거절**됐다. 오류 열여덟 줄은 「바탕이 틀렸나」 로 읽혔다. 바탕은 맞았다.
# ★ **색인이 더러우면 멈춘다.** 작업 트리만 더러운 것은 경고로 족하다 —
#   `git apply` 가 겹치면 거기서 운다. 색인은 다르다 : **거기 있는 것은 `git apply`
#   의 눈에 안 보이면서 커밋에는 들어간다.** 「다음 사람이 스스로 알아차리게」 두면
#   안 되는 자리다.
# ★ **`git add -N` 은 여기 안 걸린다 — 재서 확인했다.** 의도만 올린 항목은
#   색인↔HEAD 차이에 **안 뜬다**. 그래서 이 저장소가 권하는 `git add -N` 뒤에도
#   조용하다(거짓 빨강 아님 · §126).
if git rev-parse --git-dir >/dev/null 2>&1; then
  if ! git diff --cached --quiet 2>/dev/null; then
    echo "색인에 올라간 변경이 있다 — 멈춘다 :" >&2
    git diff --cached --name-status | sed 's/^/       /' >&2
    echo "       **git restore . 는 이것을 안 지운다.** 색인에서 작업 트리를" >&2
    echo "       되돌릴 뿐이라 같은 내용이 그대로 돌아온다." >&2
    echo "       버릴 것이면 :  git reset --hard HEAD" >&2
    echo "       둘 것이면   :  git stash --include-untracked" >&2
    exit 1
  fi
  if [ -n "$(git status --porcelain)" ]; then
    echo "경고 : 작업 트리에 커밋 안 된 변경이 있다 (색인은 깨끗하다)" >&2
    git status --short | sed 's/^/       /' >&2
    echo "       겹치면 git apply 가 거기서 운다. 치우려면 : git restore ." >&2
  fi
fi

# ★ **이미 붙은 패치인가.** 역적용이 되거나 영수증이 있으면 그렇다. 두 자리에서
#   같은 물음을 물으므로 함수로 둔다 — 두 벌이면 한쪽만 늙는다.
already_applied(){
  git apply --check -R -p1 "$TMP" 2>/dev/null && return 0
  local R="$ROOT/.cache/applied-patches.tsv"
  [ -f "$R" ] && grep -q "^$(sha256sum "$TMP" | cut -d' ' -f1)	" "$R"
}

# ★ **「이미 적용되어 있다」 는 저장소 상태에 대한 말인데, 영수증은 역사에 대한 말이다**
#   (DECISIONS §195). 2026-10-16 에 앞판을 붙인 뒤 **그 판이 만든 새 파일 여섯을
#   이름으로 지우고** 같은 패치를 다시 돌렸더니 이 스크립트가 **「이미 적용되어 있다.
#   아무것도 하지 않는다」 를 찍고 0 으로 끝났다.** 그때 저장소는 **반쯤 붙은 상태**였고,
#   뒤이은 `build_proposal.sh` 가 없는 `tools/lib/pw.sh` 를 들이려다 죽었다.
# ★ **이것은 메시지 흠이 아니라 틀린 초록이다.** 영수증은 「언젠가 붙였다」 를 알고,
#   역방향 검사는 「되돌릴 수 있나」 를 아는데 **둘 다 「지금 다 있나」 를 모른다.**
#   패치가 만드는 파일 목록은 패치 안에 적혀 있다 — **묻기만 하면 된다.**
# ★ **git 은 비 ASCII 경로를 따옴표로 싸서 escape 한다 — 재서 알았다.** `diff --git`
#   줄이 `"b/\354\203\210.txt"` 꼴이 되므로 그대로 `[ -e ]` 에 넣으면 **있는 파일을
#   없다고 읽는다**(거짓 빨강 · §126). 이 저장소의 추적 경로는 **전부 ASCII** 이고
#   `test_apply_patch.py` 가 그것을 관문으로 든다. 그래도 **못 보는 것은 말한다**(§59) —
#   따옴표 경로는 세기만 하고 아래에서 「이 눈 밖」 으로 찍는다.
new_files(){
  awk '/^diff --git /{p=$4} /^new file mode /{sub(/^b\//,"",p); if (p !~ /^"/) print p}' "$TMP"
}

quoted_new(){
  awk '/^diff --git /{p=$4} /^new file mode /{if (p ~ /^"/) n++} END{print n+0}' "$TMP"
}

missing_new(){
  local f out=""
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    [ -e "$ROOT/$f" ] || out="$out$f
"
  done <<EOF
$(new_files)
EOF
  printf '%s' "$out"
}

# ★ **「붙었다」 고 말하기 전에 「다 있나」 를 묻는다.** 하나라도 없으면 **반쯤**이다.
#   하나도 안 만드는 패치면 목록이 비고 이 자리는 **아무 일도 안 한다**(§133).
# ★ **이 눈 밖** : 패치가 **고치는** 파일이 그 뒤 따로 바뀐 것은 여기서 못 가른다 —
#   그것은 아래 「정방향도 역방향도 안 붙는다」 가지가 든다.
#
# ★ **셸에서는 함수 이름도 ASCII 다 — 재서 알았다**(DECISIONS §195). §186 · §188 은
#   「배시는 **함수 이름**에 한글을 받지만 **변수**에는 안 받는다」 고 적었다. 참말인데
#   **모자랐다** : 이 저장소는 `shellcheck` 에 관문을 걸어 뒀고, **shellcheck 는 한글
#   함수 이름을 파싱하지 못한다** — `새파일들(){` 에 SC1036 · SC1088(둘 다 error)을 내고
#   **거기서 파싱을 멈춘다.** 멈춘 뒤로는 아무것도 안 보므로, 뒤쪽 셸 코드 전체가
#   **조용히 검사 밖**이 된다(SC2034 가 엉뚱한 줄에 뜨는 것이 그 증상이었다).
#   이 저장소의 셸 함수 **전부가 이미 ASCII** 였다 — 규약이었는데 적혀 있지 않았다.
# ★ **변수 이름도 ASCII 다**(§123). `MISS=...` 가 한글이면 대입이 아니라 **명령**으로
#   읽히고 `bash -n` 은 그것을 문법 오류로 안 본다.
warn_if_partial(){
  local GONE QN
  GONE="$(missing_new)"
  QN="$(quoted_new)"
  [ "$QN" = 0 ] || echo "       이 눈 밖 : 따옴표로 싸인 경로 $QN개 — 비 ASCII 이름은 못 본다" >&2
  [ -n "$GONE" ] || return 0
  echo "반쯤 붙어 있다 :" >&2
  printf '%s' "$GONE" | sed 's/^/         /' >&2
  echo "       영수증과 역방향 검사는 「붙었다」 고 하는데 **위 파일이 없다.**" >&2
  echo "       앞판을 붙인 뒤 누가 지웠거나, 뒤 패치가 지운 자리다." >&2
  echo "       되돌리고 처음부터 붙인다 — 추적되는 변경을 되돌린 뒤" >&2
  echo "       **남아 있는** 새 파일을 이름으로 지우고 다시 이 명령을 돌린다 :" >&2
  echo "           git restore . && git status --porcelain" >&2
  exit 1
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
  # ★ **둘 다 앞에서부터 맞춘다**(DECISIONS §132). 첫 판은 「어느 쪽에도 안 맞으면」 을
  #   `case "$TREE$HEADSHA" in *"$BASE"*` 로 적었는데 그것은 **가운데서도 맞는다** —
  #   짧게 적은 바탕(7글자)이 나무 해시 **안쪽**에 우연히 들어 있으면 **틀린 바탕이
  #   통과한다.** 맞는지를 먼저 깃발에 담고, 깃발이 비었을 때만 운다.
  TREE="$(git rev-parse "HEAD^{tree}")"
  HEADSHA="$(git rev-parse HEAD)"
  MATCH=""
  case "$TREE" in "$BASE"*) MATCH="나무" ;; esac
  case "$HEADSHA" in "$BASE"*) MATCH="${MATCH:-커밋}" ;; esac
  if [ -n "$MATCH" ]; then
    echo "       바탕 맞다 : $MATCH $(echo "$BASE" | cut -c1-8)"
  else
    # ★ 이미 붙었으면 나무가 바탕보다 앞선 것이 **정상**이다. 그것부터 가른다.
    if already_applied; then
      warn_if_partial
      echo "       이미 적용되어 있다. 아무것도 하지 않는다"
      exit 0
    fi
    echo "바탕이 다르다 :" >&2
    echo "       패치는 $(echo "$BASE" | cut -c1-8) 에서 만들었고" >&2
    echo "       지금 나무는 $(echo "$TREE" | cut -c1-8) · 커밋은 $(echo "$HEADSHA" | cut -c1-8) 다" >&2
    echo "       사이에 무엇이 들어왔거나, 들어왔어야 할 패치가 안 붙어 있다" >&2
    echo "       git log --oneline -5 와 git rev-parse HEAD^{tree} 를 보내면" >&2
    echo "       그 나무로 다시 만든다" >&2
    exit 1
  fi
fi

if ! git apply --check -p1 "$TMP" 2>/tmp/thoth-patch.err; then
  # ★ 역적용이 되면 이미 붙어 있는 패치다. 이것과 "저장소가 어긋났다" 를
  #   가르지 않으면 같은 오류 메시지를 보고 무엇을 해야 할지 알 수 없다.
  #   둘은 대응이 정반대다 — 전자는 아무것도 하지 않는 것이 맞다.
  # ★ **영수증이 있으면 역적용이 안 붙어도 적용된 것이다.** 붙은 뒤에 그
  #   파일을 다음 패치가 또 고치면 정방향도 역방향도 안 붙는다. 그때
  #   "저장소가 어긋났다" 로 적으면 맞는 상태를 사고로 읽는다(§61).
  if already_applied; then
    warn_if_partial
    echo "       이미 적용되어 있다. 아무것도 하지 않는다"
    exit 0
  fi
  # ★ **git 이 정확히 말해 준 것을 덮어쓰지 않는다**(DECISIONS §195). 2026-10-16 에
  #   `error: tools/dependabot.py: already exists in working directory` 가 다섯 줄
  #   찍혔는데, 그 **바로 아래**에 「패치를 만든 시점과 다른 상태이거나」 를 붙였다.
  #   바탕은 바로 위에서 **맞다고 찍었는데도** 읽는 사람은 바탕을 의심하게 된다.
  #   세 갈래는 대응이 다르다(§59) : 바탕이 다르다 · 이미 붙었다 · **앞판 찌꺼기가 남았다.**
  if grep -q "already exists in working directory" /tmp/thoth-patch.err; then
    echo "앞판이 만든 파일이 남아 있다 :" >&2
    sed -n 's/^error: \(.*\): already exists in working directory$/         \1/p' \
      /tmp/thoth-patch.err >&2
    echo "       이 패치가 만들려는 파일이 **이미 있다** — 앞판을 반쯤 붙였다 되돌린" >&2
    echo "       자리다. git reset --hard 는 **추적 안 되는 파일을 안 지운다.**" >&2
    echo "       위 파일을 이름으로 지운 뒤 다시 이 명령을 돌린다." >&2
    echo "       git clean 으로 쓸지 않는다 — 지울 것을 정확히 아는 자리다." >&2
    exit 1
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
# ★ **기획서 산출물은 패치에 안 들어온다**(DECISIONS §182). `docs/proposal.docx` ·
#   `build.lock.json` · `site/proposal.html` 은 바이너리이거나 3MB 짜리라 패치를
#   통째로 삼킨다. 그래서 **생성기만** 패치로 오고 산출물은 받는 쪽이 굽는다.
# ★ 2026-10-11 에 그 한 줄을 안 알려 줬고, `doctor` 가 「기획서가 생성기보다 낡았다」 로
#   WARN 했다 — **도구가 말해 줄 수 있는 것을 사람이 기억하게 뒀다**(§152).
if git rev-parse --git-dir >/dev/null 2>&1 \
   && git status --short -- docs/proposal 2>/dev/null | grep -q .; then
  echo "== 기획서 =="
  echo "  생성기가 바뀌었다 — 산출물은 패치에 안 들어온다. 먼저 굽는다 :"
  echo "      bash tools/build_proposal.sh"
  echo
fi
echo "다음 : bash tools/doctor.sh"
echo "       그 뒤 : bash tools/ship.sh \"메시지\""
