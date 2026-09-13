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
