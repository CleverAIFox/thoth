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
cd "$ROOT"
[ -f .env ] && { set -a; . ./.env; set +a; }
SCOPE="${1:-all}"
FAIL=0
skip(){ printf '  \033[33mSKIP\033[0m %s\n' "$1"; }
ok(){ printf '  \033[32mOK\033[0m   %s\n' "$1"; }
no(){ printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAIL=1; }

echo "== 비밀값 =="
git check-ignore -q .env && ok ".env 가 무시된다" || no ".env 가 추적될 수 있다"
# ★ .env 존재는 기계 설정이지 저장소 불변식이 아니다. .env 는 커밋되지
#   않으므로 CI 에는 언제나 없고, 없다고 저장소가 틀린 것이 아니다.
#   검사가 무엇을 금지하는지만 정하고 어디에 적용되는지를 정하지 않으면
#   맞는 상태를 위반으로 잡는다(DECISIONS §22).
[ "$SCOPE" = "--repo" ] && skip ".env 존재 (기계 설정이다)" \
                        || { [ -f .env ] && ok ".env 가 있다" \
                                         || no ".env 가 없다 (.env.example 을 복사한다)"; }
git ls-files | grep -qE '(^|/)\.env$|credential|\.pem$' \
  && no "추적 중인 비밀 파일" || ok "추적 중인 비밀 파일 없음"

echo "== .env 키 정합 =="
if [ ! -f .env ]; then skip ".env 가 없어 비교하지 않는다"; else
# 키 목록의 정본은 .env.example 이다. 한쪽만 늘면 조용히 어긋난다.
keys(){ grep -oE '^[A-Z_][A-Z0-9_]*=' "$1" 2>/dev/null | tr -d '=' | sort -u; }
MISS="$(comm -23 <(keys .env.example) <(keys .env))"
EXTRA="$(comm -13 <(keys .env.example) <(keys .env))"
[ -z "$MISS" ]  && ok ".env 에 빠진 키 없음"         || no ".env 에 없는 키: $(echo $MISS)"
[ -z "$EXTRA" ] && ok ".env.example 에 빠진 키 없음" || no ".env.example 에 없는 키: $(echo $EXTRA)"
fi

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
OUT="$(ls ~ | grep -vE '^projects$' | tr '\n' ' ')"
[ -z "$OUT" ] && ok "홈 바로 아래에 규약 밖 이름 없음" || skip "규약 밖: $OUT"

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
  skip "ollama 서버 미기동"
fi

fi   # SCOPE

echo "== 기준선 =="
# ★ stale 은 재측정 대기다. FAIL 로 올리지 않는다 — 코드를 고친 커밋과
#   재측정 커밋은 나뉠 수밖에 없고, 그 사이 커밋을 막을 이유가 없다.
#   다만 조용히 지나가면 플래그가 영영 남는다(DECISIONS §21).
if python3 -c "import json,sys; sys.exit(0 if json.load(open('docs/bench/baseline.json')).get('stale') else 1)" 2>/dev/null; then
  skip "기준선이 stale 이다 — 재측정 후 값을 채우고 플래그를 지운다"
else
  ok "기준선이 현재 코드와 맞는다"
fi

echo "== 문서 =="
for f in docs/MASTER.md docs/PLAN.md docs/DECISIONS.md README.md; do
  [ -s "$f" ] && ok "$f" || no "$f 가 없거나 비어 있다"
done
# 해결된 항목은 PLAN 에서 행째로 지운다. 포인터조차 남기지 않는다 —
# DECISIONS 를 읽으면 알 수 있는 사실의 복제이기 때문이다(DECISIONS §18).
DONE="$(grep -cE "⬛" docs/PLAN.md 2>/dev/null)"
[ "$DONE" = "0" ] && ok "PLAN 에 해결 표시가 없다" \
                  || no "PLAN 에 ⬛ ${DONE}건. 해결된 항목은 행째로 지운다"
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
import json, pathlib, sys
m = json.loads(pathlib.Path("extension/manifest.json").read_text(encoding="utf-8"))
root = pathlib.Path("extension")
miss = [f for f in [m.get("background", {}).get("service_worker")] if f and not (root / f).exists()]
bg = (root / m["background"]["service_worker"]).read_text(encoding="utf-8")
import re
for f in re.findall(r'"(src/[^"]+\.js)"', bg):
    if not (root / f).exists():
        miss.append(f)
sys.exit(1 if miss else 0)
EOF

echo "== 워커 =="
if command -v uv >/dev/null 2>&1; then
  ( cd worker && uv run pytest -q >/dev/null 2>&1 ) && ok "테스트 통과" || no "테스트 실패"
else
  skip "uv 가 없어 테스트를 돌리지 못한다"
fi

echo
[ "$FAIL" = "0" ] && echo "이상 없음" || echo "위 FAIL 항목을 확인한다"
exit "$FAIL"
