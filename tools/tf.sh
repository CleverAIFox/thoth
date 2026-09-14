#!/usr/bin/env bash
# terraform 을 이 저장소의 설정으로 부른다.
#
#   bash tools/tf.sh plan
#   bash tools/tf.sh apply
#   bash tools/tf.sh output worker_url
#
# ★ **terraform 은 `.env` 를 읽지 않는다.** `AWS_PROFILE` 이 거기 있는데 저장소
#   도구만 로더를 탄다. 직접 부르면 프로파일이 비어 "No valid credential sources"
#   가 난다 — 호출 경로마다 환경이 갈리는 그 모양이다(DECISIONS §58 · §74).
#
# ★ **자격증명을 CLI 가 풀어 넘긴다.** `fox` 는 `aws login` 이 만드는
#   `login_session` 프로파일인데 terraform 은 Go SDK 를 쓰고 그쪽이 이 형식을
#   아는지는 버전에 달렸다. `aws configure export-credentials` 는 프로파일이
#   SSO 든 login 이든 정적 키든 **CLI 가 해석한 결과**를 환경변수로 내놓는다.
#   무엇으로 로그인했는지를 terraform 이 몰라도 된다.
#
# ★ 환경변수는 이 프로세스 안에서만 산다. 파일로 떨구지 않는다 — 떨구면
#   `doctor` 가 막는 자리에 비밀이 생긴다(DECISIONS §43).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/tools/lib/env.sh"; load_env "$ROOT/.env"

command -v terraform >/dev/null 2>&1 || {
  echo "terraform 이 없다" >&2; exit 1; }

if [ -n "${AWS_PROFILE:-}" ] && command -v aws >/dev/null 2>&1; then
  # ★ 실패해도 멈추지 않는다. 프로파일 없이도 되는 자격증명(환경변수 · 인스턴스
  #   역할)이 있을 수 있고, 정말 없으면 terraform 이 스스로 그렇게 말한다.
  #   여기서 단정하면 틀린 원인이 나간다(DECISIONS §37).
  if CREDS="$(aws configure export-credentials --profile "$AWS_PROFILE" \
                --format env-no-export 2>/dev/null)"; then
    # ★ **stdout 에 쓰지 않는다.** `$(bash tools/tf.sh output -raw worker_url)`
    #   이 이 줄까지 삼켜 URL 이 오염됐다. 사람에게 하는 말과 도구가 읽는 값을
    #   같은 통로로 내보내면, 그 도구를 스크립트가 부르는 순간 깨진다
    #   (DECISIONS §75).
    echo "자격증명 : 프로파일 $AWS_PROFILE 을 풀어 넘긴다" >&2
    while IFS='=' read -r k v; do
      [ -n "$k" ] && export "$k=$v"
    done <<< "$CREDS"
    unset AWS_PROFILE   # 둘 다 있으면 무엇이 이겼는지 알 수 없다
  else
    echo "경고 : 프로파일 $AWS_PROFILE 의 자격증명을 풀지 못했다" >&2
    echo "       aws login --profile $AWS_PROFILE 이 필요할 수 있다" >&2
  fi
fi

exec terraform -chdir="$ROOT/infra" "$@"
