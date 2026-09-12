#!/usr/bin/env bash
# 저장소·환경 불변식 점검. 막지 않고 보여준다.
#   bash tools/doctor.sh
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
[ -f .env ] && { set -a; . ./.env; set +a; }
FAIL=0
ok(){ printf '  \033[32mOK\033[0m   %s\n' "$1"; }
no(){ printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAIL=1; }

echo "== 비밀값 =="
git check-ignore -q .env && ok ".env 가 무시된다" || no ".env 가 추적될 수 있다"
[ -f .env ] || no ".env 가 없다 (.env.example 을 복사한다)"
git ls-files | grep -qE '(^|/)\.env$|credential|\.pem$' \
  && no "추적 중인 비밀 파일" || ok "추적 중인 비밀 파일 없음"

echo "== .env 키 정합 =="
# 키 목록의 정본은 .env.example 이다. 한쪽만 늘면 조용히 어긋난다.
keys(){ grep -oE '^[A-Z_][A-Z0-9_]*=' "$1" 2>/dev/null | tr -d '=' | sort -u; }
MISS="$(comm -23 <(keys .env.example) <(keys .env))"
EXTRA="$(comm -13 <(keys .env.example) <(keys .env))"
[ -z "$MISS" ]  && ok ".env 에 빠진 키 없음"         || no ".env 에 없는 키: $(echo $MISS)"
[ -z "$EXTRA" ] && ok ".env.example 에 빠진 키 없음" || no ".env.example 에 없는 키: $(echo $EXTRA)"

echo "== 셸 오염 (D-0066) =="
# 프로젝트 설정을 셸에 export 하면 .env 가 조용히 무시된다.
POL="$(grep -cE '^\s*export\s+(AWS_PROFILE|ENGINE|CACHE|OLLAMA_|MAX_CHARS|TERMINOLOGY)' ~/.bashrc 2>/dev/null || true)"
[ "$POL" = "0" ] && ok "~/.bashrc 에 프로젝트 변수 없음" || no "~/.bashrc 에 프로젝트 변수 ${POL}건"

echo "== 훅 =="
[ -z "$(git config --local --get core.hooksPath)" ] \
  && ok "로컬 hooksPath 없음 (전역 훅이 돈다)" \
  || no "로컬 hooksPath 가 전역 자격증명 검사를 가린다"
[ -x "$HOME/.githooks/pre-commit" ] && ok "전역 pre-commit 있음" || no "전역 pre-commit 없음"
[ -f "$(git config --global --get core.excludesFile 2>/dev/null)" ] \
  && ok "전역 gitignore 있음" || no "전역 gitignore 없음"

echo "== 홈 규약 =="
OUT="$(ls ~ | grep -vE '^projects$' | tr '\n' ' ')"
[ -z "$OUT" ] && ok "홈 바로 아래에 규약 밖 이름 없음" || no "규약 밖: $OUT"

echo "== 산출물 =="
[ -d "${THOTH_SSD_ROOT:-}" ] && ok "SSD 프로젝트 폴더 있음" \
                             || no "THOTH_SSD_ROOT 가 없거나 가리키는 경로가 없다"
# 경로는 .env 에만 산다. 스크립트가 기본값을 들면 두 곳이 조용히 어긋난다.
HARD="$(grep -rn "/mnt/[cf]/" tools/ 2>/dev/null | grep -v "^tools/doctor.sh:.*grep -rn" | wc -l)"
[ "$HARD" = "0" ] && ok "tools/ 에 하드코딩된 경로 없음" \
                  || no "tools/ 에 하드코딩된 경로 ${HARD}건 (.env 로 옮긴다)"
# 디렉터리가 아직 없으면 check-ignore 가 매칭하지 않는다. 경로로 검사한다.
git check-ignore -q .cache/translations.json \
  && ok ".cache/ 무시됨" || no ".cache/ 가 추적될 수 있다"

echo "== 모델 =="
# 벤치에서 진 모델은 즉시 지운다. 필요하면 다시 받는다(재현 가능).
if command -v ollama >/dev/null 2>&1 && curl -sf "${OLLAMA_URL:-http://127.0.0.1:11434}/api/version" >/dev/null; then
  KEEP="${OLLAMA_MODEL:-}"
  EXTRA_M="$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | grep -v "^${KEEP}$" | tr '\n' ' ')"
  [ -z "$EXTRA_M" ] && ok "채택 모델만 남아 있음 ($KEEP)" \
                    || no "미채택 모델: $EXTRA_M (ollama rm 으로 정리)"
  [ -d "${THOTH_SSD_ROOT:-/nonexistent}/ollama-models" ] \
    && no "SSD 에 모델 잔재가 있다 (DrvFs 는 로딩이 느려 쓰지 않는다)" \
    || ok "SSD 모델 잔재 없음"
else
  echo "  SKIP ollama 서버 미기동"
fi

echo "== 문서 =="
for f in docs/MASTER.md docs/PLAN.md docs/DECISIONS.md README.md; do
  [ -s "$f" ] && ok "$f" || no "$f 가 없거나 비어 있다"
done
# 해결된 PLAN 항목은 포인터만 남는다. 내용이 남으면 MASTER·DECISIONS 와
# 같은 사실이 두 곳에 살게 되고, 한쪽만 고쳐질 때 정본을 알 수 없다.
# 번호로 시작하는 행만 항목이다. 상태 표기 범례는 세지 않는다.
DUP="$(grep -E "^\| *[0-9]+ *\| ⬛ \|" docs/PLAN.md 2>/dev/null | grep -cv "→")"
[ "$DUP" = "0" ] && ok "완료 항목이 포인터만 남았다" \
                 || no "PLAN 의 ⬛ 행 ${DUP}건이 내용을 들고 있다"
# 문서는 실행 파일이 아니다. DrvFs 경유 복사에서 실행 비트가 붙는다.
EXEC="$(find docs -name "*.md" -perm -u+x 2>/dev/null | wc -l)"
[ "$EXEC" = "0" ] && ok "문서에 실행 비트 없음" || no "실행 비트가 붙은 문서 ${EXEC}건"

# 세션이 바뀌면 문맥이 초기화된다. 문체 규약은 사람의 기억이 아니라
# 도구가 지킨다(DECISIONS §9).
python3 tools/check_docs.py && ok "문서 서술 규약" || no "문서 서술 규약 위반"

echo "== 워커 =="
( cd worker && uv run pytest -q >/dev/null 2>&1 ) && ok "테스트 통과" || no "테스트 실패"

echo
[ "$FAIL" = "0" ] && echo "이상 없음" || echo "위 FAIL 항목을 확인한다"
exit "$FAIL"
