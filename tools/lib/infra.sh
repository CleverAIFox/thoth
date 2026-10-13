#!/usr/bin/env bash
# 인프라 코드의 지문과 「마지막으로 올린 것」 도장.
#
#   . tools/lib/infra.sh
# ★ **변수 이름은 ASCII 다**(§123). 배시는 함수 이름에 한글을 받지만 **변수에는
#   안 받는다** — `공개=...` 는 대입이 아니라 **명령**으로 읽히고, `bash -n` 은
#   그것을 문법 오류로 보지 않는다. shellcheck 가 잡았다.
#   infra_hash         "$ROOT"   # infra/ 디렉터리 전부의 sha256 (tfvars 포함 · 로컬 전용)
#   infra_hash_tracked "$ROOT"   # **git 이 추적하는 것만**의 sha256 (CI 가 잴 수 있다)
#   infra_stamp        "$ROOT"   # 로컬 도장 (.cache/infra-applied)
#   infra_public_stamp     "$ROOT"   # 커밋되는 기록 (tools/infra_applied.json)
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
# ★ **그런데 그 때문에 CI 는 이 눈을 못 가졌다**(DECISIONS §186).
#   `.cache/` 는 clone 에 없고, 전체 지문은 **CI 에서 재현할 수가 없다** —
#   `terraform.tfvars` 가 거기 없기 때문이다. 실측 :
#
#       tfvars 없음   a058eb6f…      ← clone 이 보는 것
#       tfvars 있음   48ff5f8f…      ← 적용하는 기계
#
#   그래서 **지문을 둘로 가른다.** 전체 지문은 그대로 두고(로컬이 보는 눈),
#   **추적분 지문**을 따로 내어 `tools/infra_applied.json` 으로 커밋한다.
#   CI 는 clone 만으로 그것을 다시 재어 맞춰 본다.
#
# ★ **둘은 보는 것이 다르고, 그 차이를 적어 둔다**(§59).
#
#       전체 지문   .tf · tfvars · backend.hcl · lock 전부   로컬에서만 잴 수 있다
#       추적 지문   .tf · lock · example 들                  CI 도 잴 수 있다
#
#   추적 지문은 **tfvars 가 바뀐 것을 못 본다.** 그것은 「없다」 가 아니라
#   **「이 눈으로는 못 쟀다」** 이고, CI 는 그렇게 말해야 한다.
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

# ★ **git 의 해시를 쓴다 — 제 손으로 세지 않는다.** `sha256sum` 으로 파일을
#   읽으면 줄끝 정규화 · 실행 비트에서 기계마다 갈릴 수 있다. `git hash-object`
#   는 **git 이 저장하는 바로 그 바이트**를 해싱하므로 clone 과 작업 트리가
#   같은 값을 낸다 — CI 와 맞추려면 그 쪽이어야 한다.
# ★ **이름을 같이 넣는다.** 파일을 지우거나 이름만 바꿔도 지문이 바뀐다.
infra_hash_tracked(){
  local root="${1:?infra_hash_tracked <저장소 뿌리>}"
  [ -d "$root/infra" ] || return 1
  ( cd "$root" && git ls-files -z -- infra 2>/dev/null \
      | LC_ALL=C sort -z \
      | while IFS= read -r -d '' f; do
          printf '%s  %s\n' "$(git hash-object -- "$f")" "$f"
        done
  ) | sha256sum | cut -d' ' -f1
}

infra_stamp(){
  local root="${1:?infra_stamp <저장소 뿌리>}"
  printf '%s\n' "$root/.cache/infra-applied"
}

# ★ **이것만 커밋된다.** 비밀이 아니다 — 추적 파일들의 해시 하나와 올린 때뿐이다.
#   전체 지문은 **안 적는다**: tfvars 가 바뀌었다는 사실까지 밖으로 낼 까닭이 없고,
#   CI 는 어차피 그것을 못 잰다.
infra_public_stamp(){
  local root="${1:?infra_public_stamp <저장소 뿌리>}"
  printf '%s\n' "$root/tools/infra_applied.json"
}
