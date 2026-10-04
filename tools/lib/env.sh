#!/usr/bin/env bash
# .env 로더. 모든 도구가 이것 하나를 쓴다.
#
# ★ 같은 한 줄이 여섯 스크립트에 복제되어 있었다. 같은 판단을 여러 곳에서
#   하면 언젠가 갈린다(DECISIONS §14 · §28 · §30 · §32). 한 곳으로 모은다.
#
# ★ **이미 환경에 있는 키는 덮지 않는다.** 전에는 `set -a; . .env` 가 무조건
#   덮어써서 `ENGINE=echo bash tools/run_worker.sh` 같은 일회성 지정이 조용히
#   무시됐다. 한 번만 다른 엔진으로 띄우려면 `.env` 를 고쳤다 되돌려야 했고,
#   되돌리는 것을 잊으면 다음 측정이 오염된다(DECISIONS §40).
#
# ★ D-0066 이 막으려던 것은 `~/.bashrc` 에 박아 두는 **영구** 오염이고 그것은
#   `doctor.sh` 가 따로 검사한다. 한 줄 앞에 붙이는 일회성 지정은 다른 일이다.
#   둘을 같이 막고 있었다.
#
# ★ 파일을 직접 파싱하지 않는다. `.env` 는 셸 문법으로 읽히므로 따옴표와 확장을
#   흉내 내면 소싱과 결과가 갈린다. 소싱은 그대로 두고 **미리 있던 키만**
#   되돌린다.

# ★ **부른 쉘이 무엇을 들고 왔는지는 `load_env` 보다 먼저 재야 한다**(DECISIONS §154).
#   `load_env` 뒤에는 `.env` 에서 온 것과 쉘에서 온 것이 구별되지 않는다. 재는 자리가
#   `doctor.sh` 안에만 있었더니, `ship.sh` 처럼 **`load_env` 를 먼저 하고 `doctor` 를
#   부르는 쪽**에서 `.env` 값 스물셋이 전부 「쉘 오염」 으로 찍혔다 — **늘 울리는 경보는
#   아무도 안 읽는다.**
# ★ **값이 빈 것은 안 센다** — `WORKER_TOKEN=` 는 「인증 없음」 이라 해롭지 않다.
# ★ **키 목록을 뽑는 자리는 하나다**(DECISIONS §154 · §132). `doctor.sh` 가 같은 일을
#   `keys()` 와 `ENV_KEYS` 로 두 번 더 하고 있었고, 꼴이 조금씩 달랐다(`grep -oE` 와 `sed`).
#   같은 판단이 세 곳에 살면 언젠가 갈린다 — 갈려도 **아무도 모른다**.
env_keys() {
  sed -n 's/^\([A-Z_][A-Z0-9_]*\)=.*/\1/p' "${1:-.env.example}" 2>/dev/null | sort -u
}

ambient_keys() {
  local f="${1:-.env.example}"
  local k
  env_keys "$f" \
  | while read -r k; do [ -n "${!k:-}" ] && printf '%s ' "$k"; done
  # ★ **재는 함수가 실패를 돌려주지 않는다.** 마지막 `[ -n ]` 의 결과가 그대로 함수의
  #   상태가 되어 「아무것도 안 떠 있다」 가 **1** 로 나왔다 — `set -e` 아래서는 거기서
  #   스크립트가 죽는다. 측정은 판정이 아니다.
  return 0
}

load_env() {
  local f="$1"
  [ -f "$f" ] || return 0

  local -a names=() values=()
  local k
  while IFS= read -r k; do
    # `${!k+x}` 는 '설정되었는가' 를 묻는다. 빈 문자열로 설정된 것도 설정이다.
    if [ -n "${!k+x}" ]; then
      names+=("$k")
      values+=("${!k}")
    fi
  done < <(grep -oE '^[A-Z_][A-Z0-9_]*=' "$f" 2>/dev/null | tr -d '=' | sort -u)

  set -a
  # shellcheck disable=SC1090
  . "$f"
  set +a

  local i
  for i in "${!names[@]}"; do
    export "${names[$i]}=${values[$i]}"
  done
}
