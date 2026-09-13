#!/usr/bin/env bash
# 위생을 설계하기 전에 **실정을 잰다.** 아무것도 지우지 않는다.
#
#   bash tools/scan.sh > /tmp/scan.txt 2>&1
#
# ★ 무엇이 쌓이는지 모르고 목록을 적으면 상상이 된다. 실측 없이 정한 목록은
#   검사가 아니다(DECISIONS §19 의 결). 이 스크립트의 출력이 `tidy` 와
#   `sweep` 의 대상 목록을 정하는 근거다.
#
# ★ **경로를 박지 않는다.** `.env` 의 값을 쓴다. 기계마다 다른 값을 스크립트가
#   들면 두 곳이 조용히 어긋난다(sync_ext.sh 와 같은 이유).
#
# ★ 저장소 안만 보지 않는다. WSL 홈, 마운트, `/tmp` 까지 훑는다 — 도구가
#   저장소 밖에 흘리는 것이 있는지는 저장소 안을 봐서는 알 수 없다.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
. "$ROOT/tools/lib/env.sh"; load_env "$ROOT/.env"

hr(){ printf '\n=== %s ===\n' "$1"; }
sz(){ du -sh "$1" 2>/dev/null | cut -f1; }

hr "환경"
echo "ROOT           $ROOT"
for k in THOTH_SSD_ROOT THOTH_EXT_DEST WIN_DOWNLOADS OLLAMA_URL CACHE_FILE QUOTA_FILE; do
  v="${!k-}"
  if [ -z "$v" ]; then echo "$k  (없음)"
  elif [ -e "$v" ]; then echo "$k  $v  [$(sz "$v")]"
  else echo "$k  $v  (경로 없음)"
  fi
done

hr "저장소 — 추적되지 않는 것 전부"
# ★ .gitignore 된 것까지 본다. 그게 쌓이는 것들이다.
git status --porcelain --ignored 2>/dev/null | grep '^!!' | sed 's/^!! //' \
  | while read -r p; do printf '  %-48s %s\n' "$p" "$(sz "$p")"; done

hr "저장소 — 커밋되지 않은 것"
git status --porcelain 2>/dev/null | head -20

hr "저장소 — 큰 것 20개 (.git 제외)"
find . -type f -not -path "./.git/*" -printf '%s\t%p\n' 2>/dev/null \
  | sort -rn | head -20 | awk '{printf "  %8.1fMB  %s\n", $1/1048576, $2}'

hr "홈 — ~/ 바로 아래"
ls -A "$HOME" 2>/dev/null | while read -r n; do
  printf '  %-32s %s\n' "$n" "$(sz "$HOME/$n")"
done

hr "홈 — 도구가 흘린 것으로 보이는 자리"
for p in "$HOME/.cache" "$HOME/.local/share" "$HOME/.ollama" "$HOME/.npm" \
         "$HOME/.cargo" "$HOME/.rustup" "$HOME/go" "$HOME/.venv"; do
  [ -e "$p" ] && printf '  %-32s %s\n' "${p#"$HOME"/}" "$(sz "$p")"
done

hr "프로젝트 — ~/projects 아래"
if [ -d "$HOME/projects" ]; then
  for d in "$HOME/projects"/*; do
    [ -d "$d" ] && printf '  %-32s %s\n' "$(basename "$d")" "$(sz "$d")"
  done
else
  echo "  ~/projects 가 없다"
fi

hr "마운트 — 산출물"
if [ -n "${THOTH_EXT_DEST-}" ] && [ -d "$THOTH_EXT_DEST" ]; then
  echo "  $THOTH_EXT_DEST"
  find "$THOTH_EXT_DEST" -maxdepth 2 2>/dev/null | sed "s|$THOTH_EXT_DEST|    .|" | head -30
else
  echo "  못 잼 — THOTH_EXT_DEST 에 닿지 못한다"
fi

hr "마운트 — 수신함의 thoth 파일"
if [ -n "${WIN_DOWNLOADS-}" ] && [ -d "$WIN_DOWNLOADS" ]; then
  ls -la "$WIN_DOWNLOADS" 2>/dev/null | grep -i thoth | head -30
  echo "  --- 전체 파일 수: $(ls -1 "$WIN_DOWNLOADS" 2>/dev/null | wc -l) ---"
else
  echo "  못 잼 — WIN_DOWNLOADS 에 닿지 못한다"
fi

hr "마운트 — SSD 루트"
if [ -n "${THOTH_SSD_ROOT-}" ] && [ -d "$THOTH_SSD_ROOT" ]; then
  find "$THOTH_SSD_ROOT" -maxdepth 2 2>/dev/null | head -30
else
  echo "  못 잼 — THOTH_SSD_ROOT 에 닿지 못한다"
fi

hr "/tmp — thoth 가 흘린 것"
find /tmp -maxdepth 1 \( -name "*thoth*" -o -name "w.log" -o -name "fx.log" \
  -o -name "ollama.log" -o -name "worker.log" -o -name "*.json" -o -name "smoke.*" \) \
  -printf '  %-40p %s바이트\n' 2>/dev/null | head -20

hr "떠 있는 것"
pgrep -a -f "uvicorn|ollama|http.server" 2>/dev/null | head -10 || echo "  없음"

hr "디스크"
df -h / /mnt/c /mnt/f 2>/dev/null | grep -v "^Filesystem" | awk '{printf "  %-12s %5s / %-5s (%s)\n", $6, $3, $2, $5}'

hr "끝"
echo "이 출력이 tidy · sweep 의 대상 목록을 정하는 근거다."
