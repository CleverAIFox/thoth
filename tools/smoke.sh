#!/usr/bin/env bash
# 워커 계약을 실제 HTTP 로 때려 본다. pytest 는 TestClient 라 미들웨어·포트·
# .env 로딩을 건너뛴다. 여기서만 잡히는 결함이 있다.
#   bash tools/smoke.sh
set -uo pipefail
URL="${WORKER_URL:-http://127.0.0.1:8000}"
FAIL=0
ok(){ printf '  \033[32mOK\033[0m   %s\n' "$1"; }
no(){ printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAIL=1; }

req(){ curl -s -o /tmp/smoke.body -w '%{http_code}' -X POST "$URL/translate" \
       -H 'Content-Type: application/json' -H 'Origin: https://www.udemy.com' -d "$1"; }

curl -sf "$URL/health" >/dev/null || { echo "워커가 안 떠 있다: $URL"; exit 1; }

echo "== /health =="
H="$(curl -s "$URL/health")"
echo "  $H"
echo "$H" | grep -q '"status":"ok"' && ok "degraded 아님" || no "status 가 ok 가 아니다"
echo "$H" | grep -q 'chars_used' && ok "카운터 조회됨" || no "카운터를 못 읽는다"

echo "== 계약 =="
[ "$(req '{"texts":["hello world"],"target":"ko"}')" = 200 ] \
  && ok "정상 200" || no "정상 요청 실패: $(cat /tmp/smoke.body)"
grep -q '"cached":\[false\]' /tmp/smoke.body && ok "첫 호출은 미스" || no "cached 가 이상하다"

req '{"texts":["hello world"],"target":"ko"}' >/dev/null
grep -q '"cached":\[true\]' /tmp/smoke.body && ok "두번째는 히트" || no "캐시가 안 산다"

[ "$(req '{"texts":["hello"],"target":"ja"}')" = 400 ] \
  && ok "미지원 target 400" || no "target 검증이 없다"
[ "$(req '{"texts":[],"target":"ko"}')" = 422 ] \
  && ok "빈 배열 422" || no "빈 배열이 통과한다"
[ "$(req "{\"texts\":[\"$(head -c 6000 /dev/zero | tr '\0' 'x')\"],\"target\":\"ko\"}")" = 413 ] \
  && ok "길이 초과 413" || no "MAX_TEXT_LEN 이 안 걸린다"

echo "== CORS =="
# 예외가 미들웨어를 건너뛰면 브라우저는 원인을 CORS 로 오인한다(DECISIONS §2·§10).
for t in '{"texts":["hello"],"target":"ja"}' '{"texts":["cors check ok"],"target":"ko"}'; do
  curl -s -D /tmp/smoke.h -o /dev/null -X POST "$URL/translate" \
    -H 'Content-Type: application/json' -H 'Origin: https://www.udemy.com' -d "$t"
  grep -qi 'access-control-allow-origin' /tmp/smoke.h \
    && ok "CORS 헤더 있음 ($(echo "$t" | grep -o 'ja\|ko'))" || no "CORS 헤더 없음: $t"
done

echo "== 캐시 · 카운터 영속 =="
for f in "${CACHE_FILE:-.cache/translations.json}" "${QUOTA_FILE:-.cache/quota.json}"; do
  P="worker/$f"
  [ -s "$P" ] && ok "$P ($(wc -c <"$P") 바이트)" || no "$P 가 없거나 비었다"
done

echo
[ "$FAIL" = 0 ] && echo "이상 없음" || echo "위 FAIL 을 확인한다"
exit "$FAIL"
