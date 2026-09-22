#!/usr/bin/env bash
# 저장소·환경 불변식 점검.
#   bash tools/doctor.sh          전부 본다. FAIL 이 있으면 1 로 끝난다
#   bash tools/doctor.sh --repo   저장소 안의 불변식만 본다 (커밋 훅 · CI 용)
#
# ★ 기계 설정 검사(홈 규약 · 셸 오염 · 전역 훅 · SSD 경로)는 이 저장소의
#   불변식이 아니라 한 작업 기계의 불변식이다. 커밋을 막는 자리에 두면
#   다른 기계에서 관계없는 이유로 커밋이 막힌다. --repo 에서 뺀다.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
. ./tools/lib/env.sh; load_env ./.env
SCOPE="${1:-all}"
FAIL=0
skip(){ printf '  \033[33mSKIP\033[0m %s\n' "$1"; }
ok(){ printf '  \033[32mOK\033[0m   %s\n' "$1"; }
no(){ printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAIL=1; }
# ★ **등급이 하나뿐이면 모든 검사가 최악의 검사와 같은 힘을 갖는다.** 문서 세
#   줄을 고치는 커밋이 ollama 미기동으로 막혔다 — 번역을 돌릴 일이 없는데도
#   그랬다. `no` 는 커밋을 막고 `warn` 은 알리고 넘어간다. 새 검사를 넣을 때
#   "이것이 커밋을 막을 일인가" 를 묻게 하는 것이 이 구분의 목적이다
#   (DECISIONS §46).
warn(){ printf '  \033[33mWARN\033[0m %s\n' "$1"; }

echo "== 비밀값 =="
git check-ignore -q .env && ok ".env 가 무시된다" || no ".env 가 추적될 수 있다"
# ★ .env 존재는 기계 설정이지 저장소 불변식이 아니다. .env 는 커밋되지
#   않으므로 CI 에는 언제나 없고, 없다고 저장소가 틀린 것이 아니다.
#   검사가 무엇을 금지하는지만 정하고 어디에 적용되는지를 정하지 않으면
#   맞는 상태를 위반으로 잡는다(DECISIONS §22).
[ "$SCOPE" = "--repo" ] && skip ".env 존재 (기계 설정이다)" \
                        || { [ -f .env ] && ok ".env 가 있다" \
                                         || no ".env 가 없다 (.env.example 을 복사한다)"; }
# ★ `tfplan` 도 비밀 파일이다. plan 파일은 변수 값을 평문으로 든다 — 2026-09-22 에
#   `infra/tfplan` 이 공개 저장소에 올라갔다(DECISIONS §115).
git ls-files | grep -qE '(^|/)\.env$|credential|\.pem$|(^|/)tfplan$|\.tfplan$|\.tfstate' \
  && no "추적 중인 비밀 파일" || ok "추적 중인 비밀 파일 없음"

# ★ 위 셋은 전부 git 에 묻는다. **저장소 밖은 구조적으로 시야 밖이다.**
#   2026-09-13 에 `$THOTH_SSD_ROOT/.aws/credentials` 가 장기 액세스 키를 담은
#   채 남아 있었고 아무도 보지 않았다. DrvFs 는 유닉스 권한이 붙지 않아
#   `-rwxrwxrwx` 로 보이고 윈도우 탐색기에서 그대로 열린다 — **거기서는 600 을
#   줄 수 없으므로 "권한을 고쳐라" 가 아니라 "두지 마라" 가 맞는 검사다**
#   (DECISIONS §43).
#
# ★ 경로를 박지 않는다. `.env` 의 `THOTH_SSD_ROOT` 를 쓴다. 기계 설정이므로
#   `--repo` 범위 밖이다 — CI 에는 그 마운트가 없다.
if [ "$SCOPE" = "--repo" ]; then
  skip "SSD 비밀 검사 (기계 설정이다)"
elif [ -z "${THOTH_SSD_ROOT:-}" ] || [ ! -d "${THOTH_SSD_ROOT:-/nonexistent}" ]; then
  skip "SSD 에 닿지 못해 재지 못했다"
else
  # 이름으로 찾는다. 내용을 읽지 않는다 — 검사가 비밀을 읽을 이유가 없다.
  SSD_HITS="$(find "$THOTH_SSD_ROOT" \
    \( -name 'credentials' -o -name '*.pem' -o -name '*.key' -o -name '.env' \
       -o -name 'id_rsa*' -o -name 'id_ed25519' -o -name '*.p12' \) \
    -type f 2>/dev/null | head -20)"
  if [ -n "$SSD_HITS" ]; then
    no "SSD 에 비밀 파일이 있다 — DrvFs 는 권한이 붙지 않아 윈도우에서 열린다"
    printf '%s\n' "$SSD_HITS" | sed 's|^|       |'
    echo "       옮기거나 지운다. 키가 살아 있으면 먼저 회수한다"
  else
    ok "SSD 에 비밀 파일 없음"
  fi
fi

echo "== .env 키 정합 =="
if [ ! -f .env ]; then skip ".env 가 없어 비교하지 않는다"; else
# 키 목록의 정본은 .env.example 이다. 한쪽만 늘면 조용히 어긋난다.
keys(){ grep -oE '^[A-Z_][A-Z0-9_]*=' "$1" 2>/dev/null | tr -d '=' | sort -u; }
MISS="$(comm -23 <(keys .env.example) <(keys .env))"
EXTRA="$(comm -13 <(keys .env.example) <(keys .env))"
[ -z "$MISS" ]  && ok ".env 에 빠진 키 없음"         || no ".env 에 없는 키: $(echo $MISS)"
[ -z "$EXTRA" ] && ok ".env.example 에 빠진 키 없음" || no ".env.example 에 없는 키: $(echo $EXTRA)"
fi

echo "== .env 로더 =="
# ★ 일회성 지정이 먹는지 본다. 전에는 `set -a; . .env` 가 무조건 덮어써서
#   `ENGINE=echo bash tools/run_worker.sh` 가 조용히 무시됐다(DECISIONS §40).
#   셸이라 pytest 가 보지 못하는 자리다.
LOADER_TMP="$(mktemp -d)"
printf 'ENGINE=local\nCACHE=file\n' > "$LOADER_TMP/.env"
# shellcheck disable=SC2209  # ENGINE 의 값이 문자열 'echo' 다. 명령 치환이 아니다
LOADER_OUT="$(ENGINE=echo bash -c '. tools/lib/env.sh; load_env "$1/.env"; echo "$ENGINE $CACHE"' _ "$LOADER_TMP" 2>/dev/null)"
rm -rf "$LOADER_TMP"
[ "$LOADER_OUT" = "echo file" ] \
  && ok "셸 지정이 .env 를 이긴다" \
  || no ".env 로더가 일회성 지정을 덮어쓴다 (받은 값: $LOADER_OUT)"

echo "== 워커 노출 =="
# ★ 토큰이 비면 엔드포인트를 주운 사람이 그대로 쓴다. 로컬 전용 설정에서는
#   문제가 아니지만, 원격에 닿는 설정(과금 엔진 · DynamoDB)에서 무인증이면
#   상한만이 유일한 방어가 되고 그 상한은 남이 태운다(MASTER §12).
if [ "${SCOPE}" = "--repo" ] || [ ! -f .env ]; then
  skip "토큰 검사 (기계 설정이다)"
elif [ "${ENGINE:-echo}" = "bedrock" ] || [ "${ENGINE:-echo}" = "translate" ] \
     || [ "${CACHE:-memory}" = "ddb" ]; then
  [ -n "${WORKER_TOKEN:-}" ] && ok "원격 설정에 토큰이 있다" \
                             || no "ENGINE=${ENGINE:-} CACHE=${CACHE:-} 인데 WORKER_TOKEN 이 비었다"
else
  ok "로컬 전용 설정 (토큰 없어도 된다)"
fi

if [ "$SCOPE" = "--repo" ]; then
  echo "== 기계 설정 =="
  skip "셸 오염 · 훅 · 홈 규약 · 산출물 · 모델 (--repo 범위 밖)"
else

echo "== 셸 오염 (D-0066) =="
# 프로젝트 설정을 셸에 export 하면 .env 가 조용히 무시된다.
POL="$(grep -cE '^\s*export\s+(AWS_PROFILE|ENGINE|CACHE|OLLAMA_|MAX_CHARS|TERMINOLOGY)' ~/.bashrc 2>/dev/null || true)"
# shellcheck disable=SC2088  # 경로가 아니라 사람이 읽는 문구다. 확장할 이유가 없다
[ "$POL" = "0" ] && ok "~/.bashrc 에 프로젝트 변수 없음" || no "~/.bashrc 에 프로젝트 변수 ${POL}건"

echo "== 훅 =="
[ -z "$(git config --local --get core.hooksPath)" ] \
  && ok "로컬 hooksPath 없음 (전역 훅이 돈다)" \
  || no "로컬 hooksPath 가 전역 자격증명 검사를 가린다"
[ -x "$HOME/.githooks/pre-commit" ] && ok "전역 pre-commit 있음" || no "전역 pre-commit 없음"
[ -f "$(git config --global --get core.excludesFile 2>/dev/null)" ] \
  && ok "전역 gitignore 있음" || no "전역 gitignore 없음"

echo "== 홈 규약 =="
# 저장소가 아니라 작업 기계의 규약이다. FAIL 로 올리지 않는다.
# ★ `ls | grep` 을 쓰지 않는다. 이름에 개행이나 특수문자가 들어가면 판정이
#   흔들린다 — 보여주기용이 아니라 ok/skip 을 가르는 값이다.
OUT=""
for e in "$HOME"/*; do
  [ -e "$e" ] || continue
  b="$(basename "$e")"
  [ "$b" = "projects" ] || OUT="$OUT$b "
done
[ -z "$OUT" ] && ok "홈 바로 아래에 규약 밖 이름 없음" || skip "규약 밖: $OUT"

echo "== 산출물 =="
# ★ 설정이 틀린 것과 마운트가 안 붙은 것은 다르다. 전자는 저장소 규약 위반이고
#   후자는 지금 이 순간의 상태다. 한 줄로 묶으면 노트북을 도킹하지 않았다는
#   이유로 커밋이 막힌다.
if [ -z "${THOTH_SSD_ROOT:-}" ]; then
  no "THOTH_SSD_ROOT 가 .env 에 없다"
elif [ -d "$THOTH_SSD_ROOT" ]; then
  ok "SSD 프로젝트 폴더 있음"
else
  warn "THOTH_SSD_ROOT 가 가리키는 곳이 없다 — 마운트를 본다 ($THOTH_SSD_ROOT)"
fi
# ★ **파생물이 정본과 같은지 본다.** 브라우저가 읽는 것은 `extension/` 이 아니라
#   `THOTH_EXT_DEST` 의 사본이다. 2026-09-16 에 CSS 네 판이 저장소에만 들어가
#   있었고 브라우저는 나흘 된 파일을 보고 있었다 — 도구는 있었는데 아무도
#   돌리지 않았고 돌렸는지 보는 것이 없었다(DECISIONS §92).
#
# ★ **없으면 WARN 이다. 못 잰 것이지 틀린 것이 아니다**(§59). 마운트가 안 붙은
#   기계와 동기화를 잊은 기계는 다르다.
#
# ★ `config.local.js` 는 비교에서 뺀다. 파생물 쪽에만 값이 들어가는 파일이라
#   같을 수가 없다.
if [ -z "${THOTH_EXT_DEST:-}" ]; then
  warn "THOTH_EXT_DEST 가 .env 에 없다 — 확장 사본을 재지 못했다"
elif [ ! -d "$THOTH_EXT_DEST" ]; then
  warn "확장 사본이 없다 — bash tools/sync_ext.sh ($THOTH_EXT_DEST)"
elif ! command -v rsync >/dev/null 2>&1; then
  warn "rsync 가 없어 확장 사본을 재지 못했다"
else
  EXT_DIFF="$(rsync -rlcn --delete --out-format='%n' \
    --exclude=tests/ --exclude=node_modules/ --exclude=package*.json \
    --exclude=preview.html \
    --exclude=src/config.local.js \
    "$ROOT/extension/" "$THOTH_EXT_DEST/" 2>/dev/null | grep -v '/$' || true)"
  if [ -z "$EXT_DIFF" ]; then
    ok "확장 사본이 저장소와 같다"
  else
    no "확장 사본이 낡았다 — bash tools/sync_ext.sh"
    printf '%s\n' "$EXT_DIFF" | head -8 | sed 's/^/       /'
  fi
fi

# 경로는 .env 에만 산다. 스크립트가 기본값을 들면 두 곳이 조용히 어긋난다.
HARD="$(grep -rn "/mnt/[cf]/" tools/ 2>/dev/null | grep -v "^tools/doctor.sh:.*grep -rn" | wc -l)"
[ "$HARD" = "0" ] && ok "tools/ 에 하드코딩된 경로 없음" \
                  || no "tools/ 에 하드코딩된 경로 ${HARD}건 (.env 로 옮긴다)"
# 디렉터리가 아직 없으면 check-ignore 가 매칭하지 않는다. 경로로 검사한다.
git check-ignore -q .cache/translations.json \
  && ok ".cache/ 무시됨" || no ".cache/ 가 추적될 수 있다"

echo "== 엔진 전제 =="
# ★ **여기서 다시 판단하지 않는다.** 정본은 `worker/app/preflight.py` 이고
#   doctor 는 결과를 옮겨 적기만 한다. 전에는 같은 기본값(OLLAMA_URL)이
#   `engine.py` · `run_worker.sh` · 여기 세 곳에 있었다.
#
# ★ `--cheap` 이다. doctor 는 커밋마다 도는 자리이고 bedrock 전검사는 실제
#   호출이다. 검사가 돈을 쓰거나 네트워크에 기대면 비행기에서 커밋이 막힌다.
#   **못 잰 것은 통과가 아니라 SKIP 으로 적는다**(DECISIONS §41 ㉢ · §47).
#
# ★ FAIL 로 올리지 않는다. 문서 세 줄을 고치는 커밋이 엔진 미기동으로 막힐
#   일이 아니다. 막는 것은 실제로 필요한 자리인 `run_worker.sh` 가 한다(§46).
if command -v uv >/dev/null 2>&1; then
  PF="$( cd worker && uv run python -m app.preflight --cheap --brief 2>/dev/null )"
  # 첫 필드(ok)는 코드가 대신한다. 받아만 두면 '쓰지 않는 변수' 가 된다.
  IFS='|' read -r _ PF_CODE PF_FACT <<< "$PF"
  case "${PF_CODE:-}" in
    ok)           ok "engine=${ENGINE:-echo} 전제 충족 — ${PF_FACT:-}" ;;
    not_measured) skip "engine=${ENGINE:-echo} 전제 — bash tools/preflight.sh 가 본다" ;;
    unregistered) skip "${PF_FACT:-전검사가 없다}" ;;
    "")           warn "전검사를 돌리지 못했다 (bash tools/preflight.sh)" ;;
    *)            warn "engine=${ENGINE:-echo} 전제가 깨졌다 (${PF_CODE}) — ${PF_FACT:-}" ;;
  esac
else
  skip "uv 가 없어 엔진 전제를 보지 못한다"
fi

echo "== 모델 위생 =="
# ★ **잔재 검사가 ollama 기동에 묶여 있었다.** 서버가 내려가 있으면 SSD 잔재를
#   보는 줄까지 통째로 돌지 않았고, 화면에는 "ollama 미기동" 한 줄만 남아
#   통과처럼 보였다 — 조용히 아무것도 하지 않는 검사다(DECISIONS §21 · §54).
#   잔재는 서버와 무관하므로 갈라 둔다.
[ -d "${THOTH_SSD_ROOT:-/nonexistent}/ollama-models" ] \
  && warn "SSD 에 모델 잔재가 있다 (DrvFs 는 로딩이 느려 쓰지 않는다)" \
  || ok "SSD 모델 잔재 없음"

# 벤치에서 진 모델은 즉시 지운다. 필요하면 다시 받는다(재현 가능).
# ★ `ollama list` 는 서버에 묻는다. 서버가 없으면 **못 잰 것이지 깨끗한 것이
#   아니다.** 미채택 모델은 디스크를 먹지 저장소를 틀리게 하지 않으므로 WARN 이다.
if command -v ollama >/dev/null 2>&1 && ollama list >/dev/null 2>&1; then
  # ★ **ollama 는 기계 하나에 하나다.** 이웃 저장소(seshat)의 모델도 같은 목록에 뜬다. 남의 것을 "미채택" 으로
  #   세면 지우라고 안내하게 된다 — 내 것이 아닌 것을 치우는 것은 위생이 아니다(DECISIONS §42 · §121).
  #   이웃의 모델은 `.env` 의 `OLLAMA_KEEP_ALSO`(공백으로 나눈다)에 적는다. 기계마다 다른 값이라 `.env` 다.
  KEEP="${OLLAMA_MODEL:-} ${OLLAMA_KEEP_ALSO:-}"
  EXTRA_M="$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | while read -r m; do
      case " $KEEP " in *" $m "*) ;; *) printf '%s ' "$m" ;; esac; done)"
  [ -z "$EXTRA_M" ] && ok "채택 모델만 남아 있음 (${KEEP% })" \
                    || warn "미채택 모델: $EXTRA_M (ollama rm 으로 정리 · 이웃의 것이면 .env 의 OLLAMA_KEEP_ALSO 에 적는다)"
else
  skip "ollama 에 묻지 못해 미채택 모델을 재지 못했다"
fi

fi   # SCOPE

echo "== 기준선 =="
# ★ stale 은 재측정 대기다. FAIL 로 올리지 않는다 — 코드를 고친 커밋과
#   재측정 커밋은 나뉠 수밖에 없고, 그 사이 커밋을 막을 이유가 없다.
#   다만 조용히 지나가면 플래그가 영영 남는다(DECISIONS §21).
# ★ **엔진 블록 안의 `stale` 을 못 보고 있었다.** 기준선이 엔진별로 갈린 뒤에도
#   최상위 키만 읽어서, 두 엔진이 모두 stale 인데 화면에는 `OK 기준선이 현재
#   코드와 맞는다` 가 떴다. **검사가 조용히 아무것도 하지 않았다**(DECISIONS §21
#   · §67). pytest 는 잡고 있었으므로 커밋은 막혔을 것이나, doctor 화면은
#   거짓이었다.
STALE="$(python3 - <<'EOF' 2>/dev/null
import json
d = json.load(open("docs/bench/baseline.json"))
names = [n for n, b in (d.get("engines") or {}).items() if b.get("stale")]
if d.get("stale"):
    names.append("전체")
print(" · ".join(names))
EOF
)"
if [ -n "$STALE" ]; then
  skip "기준선이 stale 이다 ($STALE) — 재측정 후 값을 채우고 플래그를 지운다"
else
  ok "기준선이 현재 코드와 맞는다"
fi

echo "== 위생 =="
# ★ FAIL 로 올리지 않는다. 잔재가 쌓인 것은 커밋을 막을 일이 아니고, 막으면
#   급할 때 --no-verify 로 넘기는 버릇이 든다. 조용히 지나가지도 않는다 —
#   그러면 아무도 치우지 않는다(DECISIONS §41).
SWEEP_N="$(python3 tools/sweep.py --brief 2>/dev/null || true)"
[ -n "$SWEEP_N" ] && skip "$SWEEP_N — python3 tools/sweep.py" \
                  || skip "위생을 재지 못했다"

echo "== 문서 =="
for f in docs/MASTER.md docs/PLAN.md docs/DECISIONS.md README.md; do
  [ -s "$f" ] && ok "$f" || no "$f 가 없거나 비어 있다"
done
# ★ 해결 표시(⬛ · ✅) 검사는 `check_docs.py::check_plan` 으로 옮겼다(DECISIONS §111).
#   같은 규칙을 두 곳에서 보면 한쪽만 고쳐진다.
# 문서는 실행 파일이 아니다. DrvFs 경유 복사에서 실행 비트가 붙는다.
EXEC="$(find docs README.md -name "*.md" -perm -u+x 2>/dev/null | wc -l)"
[ "$EXEC" = "0" ] && ok "문서에 실행 비트 없음" || no "실행 비트가 붙은 문서 ${EXEC}건"

# 세션이 바뀌면 문맥이 초기화된다. 문체 규약은 사람의 기억이 아니라
# 도구가 지킨다(DECISIONS §9).
# ★ 도구가 죽은 것과 위반이 있는 것을 구분한다. 전에는 traceback 이 나도
#   FAIL 한 줄로만 보였다. 더 위험한 쪽은 반대다 — 검사가 조용히 아무것도
#   하지 않고 0 으로 끝나면 통과로 보인다(DECISIONS §21).
DOC_OUT="$(python3 tools/check_docs.py 2>&1)"; DOC_RC=$?
case "$DOC_RC" in
  0) ok "문서 서술 규약" ;;
  1) no "문서 서술 규약 위반"; printf '%s\n' "$DOC_OUT" | sed 's/^/       /' ;;
  *) no "check_docs.py 가 죽었다 (exit $DOC_RC)"
     printf '%s\n' "$DOC_OUT" | tail -5 | sed 's/^/       /' ;;
esac

# ★ **문서 ↔ 실물.** check_docs 가 문서끼리를 본다면 이쪽은 문서가 적은 경로 · 테스트 ·
#   도구가 실재하는지를 본다(DECISIONS §111 · 하토르 D-0189).
FSCK_OUT="$(python3 tools/doc_fsck.py 2>&1)"; FSCK_RC=$?
case "$FSCK_RC" in
  0) ok "문서가 가리키는 실물" ;;
  1) no "문서가 없는 실물을 가리킨다"; printf '%s\n' "$FSCK_OUT" | sed 's/^/       /' ;;
  *) no "doc_fsck.py 가 죽었다 (exit $FSCK_RC)"
     printf '%s\n' "$FSCK_OUT" | tail -5 | sed 's/^/       /' ;;
esac

# ★ **기획서는 밖이 읽는다.** 시제 규칙 밖이라 강제자가 없기 쉽다(DECISIONS §112).
DOCX_OUT="$(python3 tools/docx_check.py 2>&1)"; DOCX_RC=$?
case "$DOCX_RC" in
  0) ok "기획서가 정본과 맞다" ;;
  1) no "기획서가 정본과 어긋난다"; printf '%s\n' "$DOCX_OUT" | sed 's/^/       /' ;;
  *) no "docx_check.py 가 죽었다 (exit $DOCX_RC)"
     printf '%s\n' "$DOCX_OUT" | tail -5 | sed 's/^/       /' ;;
esac

# ★ 이 검사는 커밋 전 작업 트리에서만 의미가 있다. CI 에서는 작업 트리가
#   언제나 HEAD 와 같으므로 항상 통과한다 — 조용히 아무것도 하지 않는
#   검사다(DECISIONS §21). 훅이 정본이고 CI 는 통과만 한다.
# DECISIONS 는 추가만 한다. 이미 적힌 절을 고치면 그때 무엇을 몰랐는지가
# 사라진다(DECISIONS §3). 기존 절의 수정을 커밋 전에 잡는다.
if git rev-parse --git-dir >/dev/null 2>&1; then
  CUT="$(git show HEAD:docs/DECISIONS.md 2>/dev/null | wc -l)"
  if [ -n "$CUT" ] && [ "$CUT" -gt 0 ]; then
    DIFF="$(git diff HEAD -- docs/DECISIONS.md | grep -c "^-[^-]" || true)"
    [ "${DIFF:-0}" = "0" ] && ok "DECISIONS 가 추가만 되었다" \
                           || no "DECISIONS 의 기존 줄 ${DIFF}건이 수정·삭제됐다"
  fi
fi

echo "== 셸 =="
# ★ **오늘까지 이 자리가 비어 있었다.** JS 는 `node --check` 가 보는데 셸 18개는
#   아무도 보지 않았고, 패치를 줄 때마다 사람이 `bash -n` 을 손으로 돌렸다.
#   사람의 성실성에 기댄 자리는 도구로 옮긴다(DECISIONS §9 · §63).
#
# ★ 대상은 `git ls-files` 로 고른다. 추적되는 것만 저장소의 불변식이다.
mapfile -t SH_FILES < <(git ls-files 'tools/*.sh' 'tools/lib/*.sh' '.githooks/*' 2>/dev/null)
if [ "${#SH_FILES[@]}" = 0 ]; then
  skip "셸 파일을 찾지 못했다"
else
  SHBAD=0
  for f in "${SH_FILES[@]}"; do
    bash -n "$f" 2>/dev/null || { no "셸 문법 오류: $f"; SHBAD=1; }
  done
  [ "$SHBAD" = 0 ] && ok "셸 문법 (${#SH_FILES[@]}개)"

  # ★ **등급을 warning 까지만 본다.** info · style 은 취향이고 커밋을 막을 일이
  #   아니다. warning 은 실제로 깨지는 것이다 — `cd` 실패 미처리 · 쓰지 않는
  #   변수 · `ls | grep` 파싱(DECISIONS §46).
  #
  # ★ 로컬에 없으면 SKIP 이다. CI 러너에는 있고 거기서는 넘어갈 수 없다 —
  #   정본이 하나인 것과 모든 자리에서 똑같이 구는 것은 다르다(DECISIONS §54).
  if command -v shellcheck >/dev/null 2>&1; then
    SC_OUT="$(shellcheck -S warning -f gcc "${SH_FILES[@]}" 2>&1)"; SC_RC=$?
    case "$SC_RC" in
      0) ok "shellcheck (-S warning)" ;;
      1) no "shellcheck 위반"; printf '%s\n' "$SC_OUT" | head -15 | sed 's/^/       /' ;;
      *) no "shellcheck 가 죽었다 (exit $SC_RC)"
         printf '%s\n' "$SC_OUT" | tail -5 | sed 's/^/       /' ;;
    esac
  else
    skip "shellcheck 가 없어 보지 못한다 (CI 에서는 돈다)"
  fi
fi

echo "== 인프라 =="
# ★ **형식은 늘 보고 의미는 초기화됐을 때만 본다.** `terraform validate` 는
#   `init` 을 요구하고 `init` 은 프로바이더를 받는다. 커밋마다 받게 하면 검사가
#   네트워크에 기대게 되므로, 이미 받아 둔 기계에서만 본다(DECISIONS §73).
#
# ★ 로컬에 terraform 이 없으면 SKIP 이다. 없는 도구를 통과로 세지 않는다(§59).
if [ ! -d infra ]; then
  skip "infra 가 없다"
elif ! command -v terraform >/dev/null 2>&1; then
  skip "terraform 이 없어 보지 못한다"
else
  TF_FMT="$(terraform fmt -check -recursive infra 2>&1)"; TF_RC=$?
  if [ "$TF_RC" = 0 ]; then
    ok "terraform fmt"
  else
    no "terraform fmt 위반 — terraform fmt -recursive infra"
    printf '%s\n' "$TF_FMT" | head -10 | sed 's/^/       /'
  fi
  if [ -d infra/.terraform ]; then
    TF_VAL="$(terraform -chdir=infra validate -no-color 2>&1)"; TF_RC=$?
    if [ "$TF_RC" = 0 ]; then
      ok "terraform validate"
    else
      no "terraform validate 실패"
      printf '%s\n' "$TF_VAL" | head -12 | sed 's/^/       /'
    fi
  else
    skip "infra/.terraform 이 없다 — bash tools/tf.sh init 후에 본다"
  fi
fi

# ★ **배포 게이트는 저장소 밖에 있다**(DECISIONS §98 · §110). GitHub 에 묻는 검사라
#   기계 설정과 같은 취급이다 — `--repo` 에서는 재지 않는다. 커밋이 네트워크와
#   gh 인증에 기대면 안 된다.
if [ "$SCOPE" = "--repo" ]; then
  skip "배포 게이트 (GitHub 설정이다)"
elif ! command -v gh >/dev/null 2>&1; then
  skip "gh 가 없어 배포 게이트를 보지 못한다"
else
  GATE_OUT="$(python3 tools/env_protection.py 2>&1)"; GATE_RC=$?
  case "$GATE_RC" in
    0) ok "production 에 승인자 · v* 태그 제한이 걸려 있다" ;;
    1) no "배포 게이트가 빠졌다"; printf '%s\n' "$GATE_OUT" | sed 's/^/       /' ;;
    *) skip "배포 게이트를 재지 못했다 — ${GATE_OUT}" ;;
  esac
fi

# ★ **봇의 가지가 쌓이지 않게 한다**(DECISIONS §122). 합친 PR 의 가지를 GitHub 이 지우는지 본다.
if [ "$SCOPE" = "--repo" ]; then
  skip "합친 가지 자동 삭제 (GitHub 설정이다)"
elif command -v gh >/dev/null 2>&1; then
  DEL="$(gh api "repos/{owner}/{repo}" --jq .delete_branch_on_merge 2>/dev/null || true)"
  case "$DEL" in
    true)  ok "합친 PR 의 가지를 GitHub 이 지운다" ;;
    false) no "합친 PR 의 가지가 남는다 — Settings → General → Automatically delete head branches" ;;
    *)     skip "합친 가지 설정을 재지 못했다" ;;
  esac
fi

echo "== 파이썬 =="
# ★ **`F` 만 켠다.** 스타일이 아니라 오류를 잡는 것이 목적이다. 2026-09-14 에
#   테스트 7개가 재정의로 죽어 있는 것을 이것이 찾았고, 그때까지 pytest 도
#   doctor 도 CI 도 초록불이었다(DECISIONS §63).
#
# ★ `uv.lock` 을 건드리지 않는다. 개발 의존성으로 넣으면 락이 따라 움직이고
#   CI 에서 트리가 더러워진다. `uvx` 는 받아서 캐시만 쓴다.
RUFF=()
if command -v ruff >/dev/null 2>&1; then
  RUFF=(ruff)
elif command -v uvx >/dev/null 2>&1 && uvx ruff --version >/dev/null 2>&1; then
  RUFF=(uvx ruff)
fi
if [ "${#RUFF[@]}" = 0 ]; then
  # ★ 받지 못한 것과 위반이 없는 것은 다르다(DECISIONS §59).
  skip "ruff 를 부르지 못해 파이썬을 보지 못한다"
else
  PYL_OUT="$("${RUFF[@]}" check --no-cache --output-format concise tools worker 2>&1)"; PYL_RC=$?
  case "$PYL_RC" in
    0) ok "ruff (F)" ;;
    1) no "파이썬 린트 위반"; printf '%s\n' "$PYL_OUT" | head -15 | sed 's/^/       /' ;;
    *) no "ruff 가 죽었다 (exit $PYL_RC)"
       printf '%s\n' "$PYL_OUT" | tail -5 | sed 's/^/       /' ;;
  esac
fi

echo "== 원격이 거절하는 것 =="
# ★ **문법은 맞는데 받는 쪽이 거절하는 것들.** `terraform validate` 는 AWS API 의
#   값 제약을 보지 않고 git 은 YAML 을 보지 않는다. 그래서 둘 다 원격에 나간
#   다음에야 안다 — 2026-09-15 에 하나씩 걸렸다(DECISIONS §87).
if ST_OUT="$(python3 tools/check_static.py 2>&1)"; then
  printf '%s\n' "$ST_OUT" | sed 's/^ *//' | while read -r l; do [ -n "$l" ] && ok "$l"; done
else
  no "원격이 거절할 것이 있다"
  printf '%s\n' "$ST_OUT" | head -10 | sed 's/^/       /'
fi

echo "== 확장 =="
# 콘텐츠 스크립트는 재주입 시 전부 다시 평가된다. 최상위 let · const · class
# 는 재선언이 SyntaxError 이고, 한 번 터지면 그 파일이 통째로 죽는다
# (DECISIONS §16). MASTER §9 의 규약을 도구가 지킨다.
# ★ background.js 는 대상이 아니다. 서비스 워커는 한 번만 평가되고
#   재주입되지 않으므로 최상위 const 가 문제되지 않는다. 주입되는 파일만
#   본다 — 대상을 뭉뚱그리면 검사가 맞는 코드를 위반으로 잡는다(§21).
CS="$(grep -oE '"src/[^"]+\.js"' extension/src/background.js | tr -d '"' | sed 's|^|extension/|')"
TOPLINES="$(grep -nE "^(let|const|class|function) " $CS 2>/dev/null || true)"
TOP="$(printf '%s' "$TOPLINES" | grep -c . || true)"
[ "${TOP:-0}" = "0" ] && ok "콘텐츠 스크립트에 최상위 선언 없음" \
                     || { no "최상위 선언 ${TOP}건 — 재주입 시 SyntaxError"
                          printf '%s\n' "$TOPLINES" | sed 's/^/       /'; }

# 문법 오류는 크롬에 넣어 보기 전에 잡는다.
if command -v node >/dev/null 2>&1; then
  JSBAD=0
  for f in extension/src/*.js extension/src/adapters/*.js; do
    node --check "$f" >/dev/null 2>&1 || { no "문법 오류: $f"; JSBAD=1; }
  done
  [ "$JSBAD" = "0" ] && ok "확장 JS 문법"
else
  skip "node 가 없어 JS 문법을 보지 못한다"
fi

# manifest 와 실제 파일이 어긋나면 주입이 조용히 실패한다.
python3 - <<'EOF' && ok "manifest 정합" || no "manifest 가 없는 파일을 가리킨다"
import json, pathlib, re, sys
root = pathlib.Path("extension")
m = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
miss = []

def need(rel):
    if rel and not (root / rel).exists():
        miss.append(rel)

sw = m.get("background", {}).get("service_worker")
need(sw)
if sw and (root / sw).exists():
    bg = (root / sw).read_text(encoding="utf-8")
    for f in re.findall(r'"(src/[^"]+\.js)"', bg):
        need(f)

# ★ 팝업도 본다. `default_popup` 이 가리키는 파일과 그 안에서 부르는 자산이
#   없으면 아이콘을 눌러도 빈 창이 뜬다 — 조용히 죽는 자리다.
popup = m.get("action", {}).get("default_popup")
need(popup)
if popup and (root / popup).exists():
    html = (root / popup).read_text(encoding="utf-8")
    for f in re.findall(r'(?:src|href)="([^"#:]+)"', html):
        need(f)
for icon in (m.get("icons") or {}).values():
    need(icon)

if miss:
    print("       " + " · ".join(sorted(set(miss))))
sys.exit(1 if miss else 0)
EOF

# 확장의 동적 테스트. 정적 검사(문법 · 최상위 선언 · manifest)는 저장 로직이
# 맞는지 보지 못한다. 판정을 순수 함수로 떼어 그 부분만이라도 기계가 본다.
if command -v node >/dev/null 2>&1; then
  EXT_OUT="$(node --test "extension/tests/*.test.js" 2>&1)"
  if [ $? -ne 0 ]; then
    no "확장 테스트 실패 (node --test \"extension/tests/*.test.js\")"
  else
    # ★ **건너뛴 테스트를 통과로 세지 않는다.** jsdom 이 없으면 어댑터 검사가
    #   전부 skip 되는데, 그 상태로 "통과" 라고 적으면 수집이 깨져도 모른다.
    #   못 잰 것과 깨끗한 것은 다르다(DECISIONS §41 ㉢ · §47).
    EXT_SKIP="$(printf '%s' "$EXT_OUT" | sed -n 's/^# skipped \([0-9]*\)$/\1/p')"
    # ★ 문서가 적은 건수를 대조하는 데 쓴다. **여기서 이미 재고 있으므로 다시
    #   돌리지 않는다** — 같은 것을 두 번 재면 두 값이 갈릴 자리가 생긴다.
    EXT_N="$(printf '%s' "$EXT_OUT" | sed -n 's/^# tests \([0-9]*\)$/\1/p')"
    if [ "${EXT_SKIP:-0}" -gt 0 ]; then
      warn "확장 테스트 ${EXT_SKIP}건 건너뜀 (cd extension && npm install)"
    else
      ok "확장 테스트 통과"
    fi
  fi
else
  skip "node 가 없어 확장 테스트를 돌리지 못한다"
fi

echo "== 워커 =="
if command -v uv >/dev/null 2>&1; then
  # ★ **출력을 버리지 않는다.** 전에는 "테스트 실패" 한 줄뿐이라 무엇이
  #   깨졌는지 알 수 없어 같은 명령을 손으로 다시 쳐야 했다. `check_docs`
  #   쪽은 이미 원문을 남긴다 — 같은 규칙을 여기에도 적용한다(§21).
  if PY_OUT="$( cd worker && uv run pytest -q 2>&1 )"; then
    ok "테스트 통과"
    PY_N="$(printf '%s' "$PY_OUT" | grep -oE '[0-9]+ passed' | head -1 | cut -d' ' -f1)"
  else
    no "테스트 실패"
    printf '%s\n' "$PY_OUT" | tail -15 | sed 's/^/       /'
  fi
else
  skip "uv 가 없어 테스트를 돌리지 못한다"
fi

echo "== 문서 건수 =="
# ★ **문서에 적은 수의 정본은 실행이다.** 같은 숫자가 두 곳에 살면 한쪽만
#   늙는다(DECISIONS §57). 위에서 이미 잰 값을 넘겨 대조한다 — 재는 곳과
#   판정하는 곳을 나누되 측정은 한 번만 한다(DECISIONS §62).
#
# ★ **표시된 것만 본다.** `<!--count:이름-->` 뒤의 정수만 주장이다. PLAN 의 ★
#   문단은 과거 서술이라 옛 숫자가 있는 것이 정상이다(DECISIONS §54).
#
# ★ 재지 못한 이름은 통과가 아니라 SKIP 이다. node 나 uv 가 없는 기계에서
#   조용히 초록불이 되면 안 된다(DECISIONS §59).
CNT_OUT="$(python3 tools/check_counts.py \
             "ext_tests=${EXT_N:-}" "worker_tests=${PY_N:-}" 2>&1)"; CNT_RC=$?
case "$CNT_RC" in
  0) ok "문서가 적은 건수가 실측과 같다" ;;
  1) no "문서 건수가 실측과 다르다"; printf '%s\n' "$CNT_OUT" | sed 's/^/    /' ;;
  3) printf '%s\n' "$CNT_OUT" | sed 's/^    //' | while IFS= read -r l; do skip "$l"; done ;;
  *) no "check_counts.py 가 죽었다 (exit $CNT_RC)"
     printf '%s\n' "$CNT_OUT" | tail -5 | sed 's/^/       /' ;;
esac

echo
[ "$FAIL" = "0" ] && echo "이상 없음" || echo "위 FAIL 항목을 확인한다"
exit "$FAIL"
