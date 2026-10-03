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
. "$ROOT/tools/lib/infra.sh"

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
    # ★ **이 기계는 `--remote` 가 아니면 로그인이 안 된다.** WSL2 의 기본 브라우저는
    #   윈도우 쪽에서 열리는데, `aws login` 의 기본 흐름은 `client_id` 가
    #   `devtools/same-device` 이고 `redirect_uri` 가 `http://127.0.0.1:<포트>` 다.
    #   브라우저가 다른 기계에 있으므로 "same device" 가 거짓이고 **AWS 가 400
    #   Bad Request 로 거절한다.** `--no-browser` 는 이 CLI 에 없는 옵션이다.
    #   2026-10-03 에 이 안내를 그대로 따라 30분을 썼다(DECISIONS §133).
    echo "경고 : 프로파일 $AWS_PROFILE 의 자격증명을 풀지 못했다" >&2
    echo "       aws login --profile $AWS_PROFILE --remote" >&2
    echo "       (WSL2 는 --remote 다 — 브라우저가 윈도우에 있어 기본 흐름이 400 이다)" >&2
    echo "       뜬 URL 을 지금 열고, 그 창의 「Copy verification code」 로 받은 값을 붙인다" >&2
    echo "       — 묵은 탭의 코드를 붙이면 State parameter ... does not match 가 난다" >&2
  fi
fi

# ★ **`init` 에만 백엔드 설정을 붙인다.** 버킷 이름은 저장소에 없고
#   `infra/backend.hcl` 이 들고 있다(부분 설정). 나머지 명령은 `.terraform/` 에
#   적힌 것을 읽으므로 다시 넘길 필요가 없고, 넘기면 terraform 이 경고한다.
#
# ★ **없으면 그냥 부른다.** 아직 부트스트랩 전이거나 로컬 상태로 도는 기계다.
#   여기서 막으면 `bootstrap_backend.sh` 를 돌리기 전에는 아무것도 못 한다.
if [ "${1:-}" = "init" ] && [ -f "$ROOT/infra/backend.hcl" ]; then
  shift
  exec terraform -chdir="$ROOT/infra" init -backend-config=backend.hcl "$@"
fi

# ★ **`apply` 만 `exec` 하지 않는다.** 끝나고 **무엇을 올렸는지 적어야** 하는데
#   `exec` 는 이 셸을 덮어쓴다. 나머지 명령은 그대로 넘긴다 — 특히 `output` 은
#   값을 그대로 돌려줘야 하고 종료 코드도 그대로여야 한다(`plan -detailed-exitcode`).
if [ "${1:-}" != "apply" ]; then
  exec terraform -chdir="$ROOT/infra" "$@"
fi

RC=0
terraform -chdir="$ROOT/infra" "$@" || RC=$?

# ★ **올리다 만 것은 적지 않는다.** 일부만 적용되고 끝난 `apply` 는 0 이 아니고,
#   그때 도장을 찍으면 **올라가지 않은 것을 올라갔다고 적는다.** 도장이 없는 쪽이
#   틀린 도장보다 낫다 — 없으면 `doctor` 가 "모른다" 고 말한다.
if [ "$RC" = 0 ]; then
  STAMP="$(infra_stamp "$ROOT")"
  mkdir -p "$(dirname "$STAMP")"
  printf '%s\t%s\n' "$(infra_hash "$ROOT")" "$(date -Iseconds)" > "$STAMP"
  echo "적용 도장 : $(cut -c1-12 < "$STAMP") — doctor 가 이것을 지금 코드와 맞춰 본다" >&2
fi
exit "$RC"
