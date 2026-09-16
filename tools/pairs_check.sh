#!/usr/bin/env bash
# 쌍이 실제로 쌓였는지 본다. **로그가 아니라 버킷과 테이블을 본다**(DECISIONS §96).
#
#   bash tools/pairs_check.sh            오늘(UTC)
#   bash tools/pairs_check.sh 2026-09-16 특정 날짜
#
# ★ **세 층을 따로 본다.** S3 에 객체가 있는 것과 Glue 테이블로 읽히는 것은 다른
#   사실이다. 열 이름 · 타입 · 파티션 투영 중 하나가 틀리면 객체는 있고 쿼리는
#   빈 결과다. 그래서 Athena 로 한 번 읽는다.
#
# ★ **빈 레코드 오류는 셈에서 뺀다.** 구독 필터를 만들 때 CloudWatch Logs 가 제어
#   메시지를 한 번 보내고, 메시지 추출 뒤에는 빈 레코드가 되어
#   `DataFormatConversion.MalformedData` 로 `errors/` 에 떨어진다. 2026-09-16 에
#   필터 생성 직후 한 건이 그렇게 났다(DECISIONS §98). 쌍이 든 오류만 실패로 센다.
#
# ★ **`.env` 를 여기서 읽는다.** `tf.sh output` 이 내던 명령은 프로파일 없이 돌아
#   `AWS_PROFILE` 을 export 하지 않은 셸에서 죽었다.
#
#   0  오늘 쌍이 있고 진짜 오류가 없다
#   1  쌍이 든 변환 오류 · 못 읽은 오류 · Athena 실패
#   3  오늘 쌍이 없다 — 못 잼이지 통과가 아니다
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/tools/lib/env.sh"; load_env "$ROOT/.env"
[ -n "${AWS_PROFILE:-}" ] && export AWS_PROFILE

DAY="${1:-$(date -u +%F)}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text 2>/dev/null)" \
  || { echo "자격증명이 없다 — aws login --profile ${AWS_PROFILE:-?}" >&2; exit 1; }
B="thoth-pairs-$ACCOUNT"
RC=0

echo "== S3 · $B · dt=$DAY =="
PAIRS="$(aws s3 ls "s3://$B/pairs/dt=$DAY/" 2>/dev/null)"
if [ -z "$PAIRS" ]; then
  echo "  쌍 객체 0 — 새 문장을 번역했는지, 버퍼 간격이 지났는지 본다"
  RC=3
else
  echo "  쌍 객체 $(printf '%s\n' "$PAIRS" | wc -l)"
  printf '%s\n' "$PAIRS" | tail -3 | sed 's/^/    /'
fi

echo "== errors/ · dt=$DAY =="
# ★ **셈을 파이썬이 한다**(`pairs_errors.py`). 첫 판은 jq 로 셌고 jq 가 없는 기계에서
#   오류 객체가 있는데도 `0 · 0` 을 냈다(DECISIONS §99).
CTRL=0; REAL=0; UNREAD=0; OBJS=0
while read -r key; do
  [ -n "$key" ] || continue
  OBJS=$((OBJS + 1))
  line="$(aws s3 cp "s3://$B/$key" - 2>/dev/null | python3 "$ROOT/tools/pairs_errors.py")"
  # ★ 도구가 줄을 못 냈으면 객체 하나를 통째로 못 읽은 것이다. 0 으로 두지 않는다.
  if ! [[ "$line" =~ ctrl=([0-9]+)\ real=([0-9]+)\ unparsed=([0-9]+) ]]; then
    UNREAD=$((UNREAD + 1)); continue
  fi
  CTRL=$((CTRL + BASH_REMATCH[1]))
  REAL=$((REAL + BASH_REMATCH[2]))
  UNREAD=$((UNREAD + BASH_REMATCH[3]))
done < <(aws s3 ls "s3://$B/errors/" --recursive 2>/dev/null | awk '{print $4}' | grep "dt=$DAY/")
echo "  객체 $OBJS · 제어 메시지(무해) $CTRL · 쌍이 든 오류 $REAL · 못 읽음 $UNREAD"
if [ "$REAL" -gt 0 ]; then
  echo "  aws logs tail /aws/kinesisfirehose/thoth-pairs --since 1h 로 이유를 본다"
  RC=1
elif [ "$UNREAD" -gt 0 ]; then
  echo "  못 읽은 오류가 있다 — 통과로 세지 않는다"
  RC=1
fi

[ "$RC" = 3 ] && exit 3

echo "== Athena · thoth.pairs =="
Q="$(aws athena start-query-execution \
  --query-string "SELECT count(*), count(DISTINCT site), max(from_unixtime(ts / 1000)) FROM thoth.pairs WHERE dt = '$DAY'" \
  --result-configuration "OutputLocation=s3://$B/athena/" \
  --query QueryExecutionId --output text 2>/dev/null)" || { echo "  쿼리를 시작하지 못했다"; exit 1; }
STATE=QUEUED
for _ in $(seq 30); do
  STATE="$(aws athena get-query-execution --query-execution-id "$Q" \
    --query 'QueryExecution.Status.State' --output text 2>/dev/null)"
  case "$STATE" in SUCCEEDED|FAILED|CANCELLED) break ;; esac
  sleep 1
done
if [ "$STATE" != SUCCEEDED ]; then
  # ★ 판정만 적지 않고 이유를 싣는다(§70).
  echo "  $STATE — $(aws athena get-query-execution --query-execution-id "$Q" \
    --query 'QueryExecution.Status.StateChangeReason' --output text 2>/dev/null)"
  exit 1
fi
aws athena get-query-results --query-execution-id "$Q" \
  --query 'ResultSet.Rows[1].Data[].VarCharValue' --output text \
  | awk -F'\t' '{printf "  행 %s · 사이트 %s · 마지막 %s\n", $1, $2, $3}'
exit "$RC"
