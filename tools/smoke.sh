#!/usr/bin/env bash
# 워커 계약을 실제 HTTP 로 때려 본다. pytest 는 TestClient 라 미들웨어·포트·
# .env 로딩을 건너뛴다. 여기서만 잡히는 결함이 있다.
#   bash tools/smoke.sh
set -uo pipefail
URL="${WORKER_URL:-http://127.0.0.1:8000}"
FAIL=0
ok(){ printf '  \033[32mOK\033[0m   %s\n' "$1"; }
no(){ printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAIL=1; }
skip(){ printf '  \033[33mSKIP\033[0m %s\n' "$1"; }

# 토큰이 비면 헤더를 붙이지 않는다. 워커의 기본값과 같은 경로를 탄다.
AUTH=()
[ -n "${WORKER_TOKEN:-}" ] && AUTH=(-H "X-Thoth-Token: ${WORKER_TOKEN}")

req(){ curl -s -o /tmp/smoke.body -w '%{http_code}' -X POST "$URL/translate" \
       -H 'Content-Type: application/json' -H 'Origin: https://www.udemy.com' \
       "${AUTH[@]}" -d "$1"; }

# ★ **받은 값을 메시지에 싣는다.** 전에는 `[ "$(req ...)" = 422 ]` 가 실패하면
#   "빈 배열이 통과한다" 가 나갔다. 실제로는 400 으로 막혔고 통과한 적이 없다 —
#   기대값이 늙었을 뿐인데 메시지는 계약이 깨졌다고 말한다. 틀린 원인을 단정하는
#   메시지는 침묵보다 나쁘다(DECISIONS §37 · §70).
want(){ local expect="$1" label="$2" body="$3" got
        got="$(req "$body")"
        [ "$got" = "$expect" ] && ok "$label $expect" \
          || no "$label — $expect 를 기대했는데 $got 이다: $(head -c 120 /tmp/smoke.body)"; }

# ★ `curl -sf` 는 연결 거부와 HTTP 오류를 함께 잡는다. 워커가 500 을 돌려줘도
#   "안 떠 있다" 가 나가고, 시킨 대로 다시 띄우면 같은 500 이 난다
#   (DECISIONS §37 · §52).
CODE="$(curl -s -o /dev/null -w '%{http_code}' "$URL/health" 2>/dev/null)"
case "$CODE" in
  200) ;;
  000) echo "워커에 닿지 못했다: $URL"; echo "  bash tools/run_worker.sh & 로 띄운다"; exit 1 ;;
  *)   echo "워커가 $CODE 를 돌려줬다 — 살아 있다. 로그를 본다"; exit 1 ;;
esac

# ★ **JSON 을 문자열로 보지 않는다.** `grep '"status":"ok"'` 는 직렬화 형태에
#   기댄다. 배포본은 공백을 넣고 로컬은 넣지 않아, 같은 값인데 검사가 갈렸다.
#   **검사가 표현에 기대면 그 표현을 바꾸는 순간 거짓말을 한다**(DECISIONS §76).
field(){ python3 -c '
import json, sys
try:
    d = json.loads(sys.stdin.read())
except ValueError:
    sys.exit(2)
v = d
for k in sys.argv[1].split("."):
    if not isinstance(v, dict) or k not in v:
        sys.exit(1)
    v = v[k]
print(json.dumps(v, ensure_ascii=False))
' "$1"; }

echo "== /health =="
H="$(curl -s "${AUTH[@]}" "$URL/health")"
echo "  $H"
[ "$(printf '%s' "$H" | field status)" = '"ok"' ] \
  && ok "degraded 아님" || no "status 가 ok 가 아니다 (받은 값: $(printf '%s' "$H" | field status))"
printf '%s' "$H" | field chars_used >/dev/null \
  && ok "카운터 조회됨" || no "카운터를 못 읽는다"

echo "== 계약 =="

# ★ **매 실행 다른 문장을 쓴다.** 고정 문장이면 두 번째 실행부터 캐시 히트라
#   `첫 호출은 미스` 가 영영 실패한다. 로컬에서는 워커를 새로 띄울 때마다 캐시가
#   비어 보이지 않았고, **배포본에서 캐시가 영속이 되자 바로 드러났다.**
#   `warmup()` 이 같은 이유로 이미 그렇게 한다(DECISIONS §21 · §77).
#
# ★ **과금 엔진에서는 실행마다 실제 번역이 한 번 일어난다.** 수십 자라 무시할
#   크기이나 공짜는 아니고, 그 문장은 캐시에 남는다. 미스→히트 전이는 캐시
#   계약의 핵심이라 그 값을 치를 만하다.
UNIQ="thoth smoke probe $(date +%s%N)"
PROBE="$(python3 -c 'import json,sys; print(json.dumps({"texts":[sys.argv[1]],"target":"ko"}))' "$UNIQ")"

[ "$(req "$PROBE")" = 200 ] \
  && ok "정상 200" || no "정상 요청 실패: $(cat /tmp/smoke.body)"
[ "$(field cached < /tmp/smoke.body)" = "[false]" ] \
  && ok "첫 호출은 미스" || no "cached 가 [false] 가 아니다 (받은 값: $(field cached < /tmp/smoke.body))"

req "$PROBE" >/dev/null
[ "$(field cached < /tmp/smoke.body)" = "[true]" ] \
  && ok "두번째는 히트" || no "캐시가 [true] 가 아니다 (받은 값: $(field cached < /tmp/smoke.body))"

want 400 "미지원 target" '{"texts":["hello"],"target":"ja"}'
# ★ **422 가 아니라 400 이다.** 검증을 pydantic 에서 계약으로 옮기면서 바뀌었다.
#   맡겨 두면 같은 입력이 로컬에서는 422, Lambda 에서는 다른 코드가 된다
#   (DECISIONS §68).
want 400 "빈 배열" '{"texts":[],"target":"ko"}'
want 400 "본문에 texts 가 없음" '{"nope":1}'
want 400 "texts 가 문자열 아님" '{"texts":[1,2],"target":"ko"}'
want 413 "길이 초과" "{\"texts\":[\"$(head -c 6000 /dev/zero | tr '\0' 'x')\"],\"target\":\"ko\"}"

echo "== CORS =="
# 예외가 미들웨어를 건너뛰면 브라우저는 원인을 CORS 로 오인한다(DECISIONS §2·§10).
for t in '{"texts":["hello"],"target":"ja"}' '{"texts":["cors check ok"],"target":"ko"}'; do
  curl -s -D /tmp/smoke.h -o /dev/null -X POST "$URL/translate" \
    -H 'Content-Type: application/json' -H 'Origin: https://www.udemy.com' -d "$t"
  grep -qi 'access-control-allow-origin' /tmp/smoke.h \
    && ok "CORS 헤더 있음 ($(echo "$t" | grep -o 'ja\|ko'))" || no "CORS 헤더 없음: $t"
done

echo "== 인증 =="
# ★ 토큰을 끈 워커에서 '401 이 안 온다' 는 결함이 아니다. 설정에 따라 무엇을
#   기대할지가 달라지므로 갈라서 본다. 뭉뚱그리면 맞는 상태를 FAIL 로 잡는다
#   (DECISIONS §22).
if [ -n "${WORKER_TOKEN:-}" ]; then
  CODE="$(curl -s -o /dev/null -w '%{http_code}' -X POST "$URL/translate" \
          -H 'Content-Type: application/json' -d '{"texts":["no token"],"target":"ko"}')"
  [ "$CODE" = 401 ] && ok "토큰 없는 요청 401" || no "토큰이 설정됐는데 $CODE 로 통과한다"
  [ "$(req '{"texts":["auth ok here"],"target":"ko"}')" = 200 ] \
    && ok "토큰 있는 요청 200" || no "맞는 토큰이 거부된다"
else
  ok "토큰 미설정 — 로컬 전용 설정이다"
fi

echo "== 캐시 · 카운터 영속 =="
# ★ **원격을 때릴 때 로컬 파일을 보지 않는다.** 배포본은 DynamoDB 를 쓰는데
#   이 검사가 로컬 `.cache/` 를 보고 `OK` 를 냈다. 거기 있던 것은 예전 로컬
#   실행의 잔재였다 — **못 잰 것을 통과로 센 것**이다(DECISIONS §59 · §76).
#
# ★ 원격의 영속은 위의 `두번째는 히트` 가 이미 본다. 같은 문장을 두 번 보내
#   `cached` 가 참이면 저장소가 사는 것이다.
case "$URL" in
  http://127.0.0.1*|http://localhost*)
    for f in "${CACHE_FILE:-.cache/translations.json}" "${QUOTA_FILE:-.cache/quota.json}"; do
      P="worker/$f"
      [ -s "$P" ] && ok "$P ($(wc -c <"$P") 바이트)" || no "$P 가 없거나 비었다"
    done
    ;;
  *)
    skip "원격 워커다 — 로컬 캐시 파일을 보지 않는다 (위 '두번째는 히트' 가 본다)"
    ;;
esac

echo
[ "$FAIL" = 0 ] && echo "이상 없음" || echo "위 FAIL 을 확인한다"
exit "$FAIL"
