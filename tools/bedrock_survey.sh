#!/usr/bin/env bash
# Bedrock 쪽 실정을 잰다. 아무것도 바꾸지 않는다.
#
#   bash tools/bedrock_survey.sh
#
# ★ **전검사와 역할이 다르다.** `preflight.sh` 는 \"지금 돌릴 수 있는가\" 에
#   예/아니오로 답한다. 여기는 아니오일 때 **무엇이 있는지** 를 본다 — 어느
#   신원으로 붙었는지, 이 리전에 그 모델이 있기는 한지, 추론 프로파일 이름이
#   맞는지. 둘을 한 스크립트에 넣으면 기동 경로가 느려지고 실패 판정이 흐려진다.
#
# ★ **모델 접근 승인에는 CLI 가 없다.** Bedrock 콘솔의 Model access 에서만
#   한다. 여기서 재는 것은 승인 여부가 아니라 그 앞뒤의 사실이다.
#
# ★ `set -e` 를 쓰지 않는다. 한 항목이 권한으로 막히는 것 자체가 정보이므로
#   거기서 멈추면 나머지를 못 본다.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/tools/lib/env.sh"; load_env "$ROOT/.env"

REGION="${BEDROCK_REGION:-${AWS_REGION:-ap-northeast-2}}"
MODEL="${BEDROCK_MODEL:-}"

command -v aws >/dev/null 2>&1 || { echo "aws CLI 가 없다" >&2; exit 1; }

echo "profile=${AWS_PROFILE:-(기본 자격증명 체인)} region=$REGION model=${MODEL:-(없음)}"
echo "aws $(aws --version 2>&1 | awk '{print $1}')"

echo
echo "== 신원 =="
# ★ **여기서 막히면 아래는 전부 같은 이유로 막힌다.** 계속 돌리면 같은 오류를
#   네 번 찍고, 마지막 절이 "목록에 없다" 로 끝나 자격증명 문제가 모델 문제로
#   보인다. 먼저 보고 실패하면 멈춘다(DECISIONS §59).
if ID="$(aws sts get-caller-identity --output text --query 'Arn' 2>&1)"; then
  echo "  $ID"
else
  printf '%s\n' "$ID" | sed 's/^/  /'
  echo
  echo "자격증명이 막혀 나머지를 재지 못했다 — 재인증 후 다시 돌린다"
  echo "  bash tools/preflight.sh   프로파일에 맞는 명령을 알려 준다"
  exit 1
fi

echo
echo "== 추론 프로파일 =="
# ★ `apac.*` · `us.*` 는 모델 ID 가 아니라 크로스리전 추론 프로파일이다.
#   목록에 없으면 모델 접근과 무관하게 호출이 ValidationException 으로 죽는다.
aws bedrock list-inference-profiles --region "$REGION" \
  --output text --query 'inferenceProfileSummaries[].[inferenceProfileId,status]' 2>&1 \
  | sed 's/^/  /' | head -40 || true

echo
echo "== 기반 모델 (설정된 모델과 이름이 겹치는 것) =="
# ★ 전체 목록은 길다. 설정된 모델의 어간으로 좁힌다 — 이름을 잘못 적었을 때
#   비슷한 것이 무엇인지 보이는 편이 \"없다\" 한 줄보다 낫다.
STEM="$(printf '%s' "$MODEL" | sed 's/^[a-z][a-z]*\.//; s/-v[0-9].*$//')"
if [ -n "$STEM" ]; then
  aws bedrock list-foundation-models --region "$REGION" \
    --output text --query "modelSummaries[?contains(modelId, '$STEM')].[modelId]" 2>&1 \
    | sed 's/^/  /' | head -20 || true
else
  echo "  BEDROCK_MODEL 이 비어 좁히지 못했다"
fi

echo
echo "== 설정된 모델이 목록에 있는가 =="
# ★ 목록에 있다는 것과 호출할 수 있다는 것은 다르다. 호출 가능 여부는
#   `bash tools/preflight.sh` 가 실제로 때려서 본다.
# ★ **못 잰 것과 없는 것을 가른다.** 목록 호출이 권한이나 자격증명으로 막히면
#   `grep` 은 어느 쪽이든 빈손으로 돌아온다. 그것을 "없다" 로 적으면 원인이
#   바뀐다(DECISIONS §59).
if [ -z "$MODEL" ]; then
  echo "  BEDROCK_MODEL 이 비었다"
else
  PROFILES="$(aws bedrock list-inference-profiles --region "$REGION" \
    --output text --query 'inferenceProfileSummaries[].inferenceProfileId' 2>/dev/null)"
  PROFILES_RC=$?
  MODELS="$(aws bedrock list-foundation-models --region "$REGION" \
    --output text --query 'modelSummaries[].modelId' 2>/dev/null)"
  MODELS_RC=$?
  if printf '%s' "$PROFILES" | tr '\t' '\n' | grep -qx "$MODEL"; then
    echo "  추론 프로파일로 존재한다"
  elif printf '%s' "$MODELS" | tr '\t' '\n' | grep -qx "$MODEL"; then
    echo "  기반 모델로 존재한다"
  elif [ "$PROFILES_RC" != 0 ] || [ "$MODELS_RC" != 0 ]; then
    echo "  목록을 받지 못해 재지 못했다 (위 절의 오류를 본다)"
  else
    echo "  이 리전의 목록에 없다 — BEDROCK_MODEL 이나 BEDROCK_REGION 을 본다"
  fi
fi

echo
echo "다음 : bash tools/preflight.sh   실제로 호출해 본다"
