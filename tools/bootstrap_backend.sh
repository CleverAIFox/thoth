#!/usr/bin/env bash
# 상태 버킷을 세우고 로컬 상태를 옮긴다. 한 번만 하는 일이다.
#
#   bash tools/bootstrap_backend.sh
#
# ★ **이 버킷만 terraform 이 소유하지 않는다.** 상태를 담는 것을 상태로
#   관리하면 그것을 지울 때 자기 발을 딛는다. 대신 여기서 켜는 것을 적어 둔다 —
#   버전 관리 · 퍼블릭 차단 · 기본 암호화. 손으로 만들면 이 셋을 잊는다.
#
# ★ **여러 번 돌려도 같다.** 이미 있으면 만들지 않고 설정만 다시 건다.
#
# ★ **상태 이전은 terraform 이 한다.** 파일을 손으로 올리지 않는다.
#   `init -migrate-state` 가 옛 상태를 읽어 새 백엔드에 쓴다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/tools/lib/env.sh"; load_env "$ROOT/.env"

command -v aws >/dev/null 2>&1 || { echo "aws 가 없다" >&2; exit 1; }
P=(); [ -n "${AWS_PROFILE:-}" ] && P=(--profile "$AWS_PROFILE")
REGION="${AWS_REGION:-ap-northeast-2}"

ACCT="$(aws sts get-caller-identity "${P[@]}" --query Account --output text)" || {
  echo "자격증명이 없다 — aws login --profile ${AWS_PROFILE:-} " >&2; exit 1; }
BUCKET="thoth-tfstate-$ACCT"
echo "버킷 : $BUCKET ($REGION)" >&2

if aws s3api head-bucket --bucket "$BUCKET" "${P[@]}" >/dev/null 2>&1; then
  echo "  이미 있다" >&2
else
  aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
    --create-bucket-configuration "LocationConstraint=$REGION" "${P[@]}" >/dev/null
  echo "  만들었다" >&2
fi

# ★ 셋을 매번 다시 건다. 만든 적 있는 버킷이 이 설정을 갖고 있다는 보장이 없다.
aws s3api put-public-access-block --bucket "$BUCKET" "${P[@]}" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
aws s3api put-bucket-versioning --bucket "$BUCKET" "${P[@]}" \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$BUCKET" "${P[@]}" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
echo "  버전 관리 · 퍼블릭 차단 · 기본 암호화 켰다" >&2

HCL="$ROOT/infra/backend.hcl"
if [ -f "$HCL" ]; then
  echo "infra/backend.hcl : 이미 있다 — 건드리지 않는다" >&2
else
  { echo "bucket = \"$BUCKET\""
    echo "key    = \"thoth/terraform.tfstate\""
    echo "region = \"$REGION\""; } > "$HCL"
  echo "infra/backend.hcl : 만들었다" >&2
fi

echo >&2
echo "다음 : bash tools/tf.sh init -migrate-state" >&2
echo "       그 뒤 : bash tools/tf.sh plan   ← 'No changes' 여야 이전이 성공이다" >&2
