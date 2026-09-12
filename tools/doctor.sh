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
[ -d /mnt/f/projects/thoth ] && ok "SSD 프로젝트 폴더 있음" || no "/mnt/f/projects/thoth 없음"
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
  [ -d /mnt/f/projects/thoth/ollama-models ] \
    && no "SSD 에 모델 잔재가 있다 (DrvFs 는 로딩이 느려 쓰지 않는다)" \
    || ok "SSD 모델 잔재 없음"
else
  echo "  SKIP ollama 서버 미기동"
fi

echo "== 워커 =="
( cd worker && uv run pytest -q >/dev/null 2>&1 ) && ok "테스트 통과" || no "테스트 실패"

echo
[ "$FAIL" = "0" ] && echo "이상 없음" || echo "위 FAIL 항목을 확인한다"
exit "$FAIL"
