#!/usr/bin/env bash
# 인프라 코드의 지문과 「마지막으로 올린 것」 도장.
#
#   . tools/lib/infra.sh
#   infra_hash  "$ROOT"      # 지금 infra/ 가 선언하는 것의 sha256
#   infra_stamp "$ROOT"      # 도장 파일 경로 (.cache/infra-applied)
#
# ★ **적용은 사람이 손으로 돌린다 — 그래서 안 돌아도 아무도 모른다.** 2026-10-03
#   에 `#126` 의 인프라(pairs 버전 관리 · lifecycle · OIDC `sub` 좁히기 · 배포
#   정책)가 며칠을 올라가지 않은 채 **모든 검사가 초록이었다.** `plan` 이 비어
#   있는지 보는 자가 하나도 없었다(DECISIONS §133).
#
# ★ **두 곳이 같은 수를 따로 세지 않는다.** 적는 쪽(`tf.sh`)과 보는 쪽
#   (`doctor.sh`)이 각자 해시를 만들면 그 둘이 갈리는 날이 온다 — 그것이 §132
#   에서 지운 모양이다. 셈은 여기 하나뿐이고 양쪽이 이것을 부른다.
#
# ★ **`git` 에 묻지 않는다.** 추적 파일만 보면 `terraform.tfvars` 가 빠지는데
#   거기 변수 값이 산다. 값이 바뀌어도 도장이 맞으면 **초록으로 위장한다.**
#   그래서 디렉터리를 그대로 읽는다 — 도장은 `.cache/` 에 있어 기계 밖으로
#   나가지 않으므로 기계마다 달라도 된다.
#
# ★ **빼는 것은 terraform 이 스스로 쓰는 것뿐이다.** 상태 · plan 산출물 ·
#   받아 둔 프로바이더. 넣을지 말지 애매하면 **넣는다** — 과하게 넣으면
#   쓸데없이 한 번 더 경고하고(WARN 이라 막지 않는다), 덜 넣으면 뒤처진 인프라를
#   맞다고 말한다. 두 틀림의 값이 다르다.

infra_hash(){
  local root="${1:?infra_hash <저장소 뿌리>}"
  [ -d "$root/infra" ] || return 1
  # 이름까지 함께 해싱된다 — 파일을 지우거나 이름만 바꿔도 지문이 바뀐다.
  ( cd "$root/infra" && find . -type f \
      ! -path './.terraform/*' \
      ! -name '*.tfstate' ! -name '*.tfstate.*' \
      ! -name 'tfplan' ! -name '*.tfplan' \
      -print0 \
    | LC_ALL=C sort -z \
    | xargs -0 -r sha256sum \
  ) | sha256sum | cut -d' ' -f1
}

infra_stamp(){
  local root="${1:?infra_stamp <저장소 뿌리>}"
  printf '%s\n' "$root/.cache/infra-applied"
}
