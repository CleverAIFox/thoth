#!/usr/bin/env bash
# 배치 크기별로 골든셋을 잰다. 한 판씩 조건을 확인하고 돌린다.
#
#   bash tools/bench_batch.sh 9 6 3
#   bash tools/bench_batch.sh --min-free 3000 9 6      여유 기준을 낮춘다
#
# ★ **오늘 세 판을 재고 두 판을 버렸다.** 메모리 조건이 다른 상태에서 잰
#   값끼리는 비교되지 않는다. 조건을 사람이 기억해서 확인하면 잊는다 —
#   `free -h` 를 찍어 놓고 224MB 인 것을 보고도 그냥 진행했다. 코드가 본다
#   (DECISIONS §50).
#
# ★ **속도만 조건을 탄다.** 위반은 `temperature 0` 이라 배치가 같으면
#   결정적이고 두 번 재서 확인했다. 그래서 이 스크립트가 막는 것은 속도를
#   못 쓰게 만드는 조건이다.
#
# ★ 판마다 워커를 다시 띄운다. **캐시 파일을 지우는 것만으로는 안 비워진다** —
#   워커가 한 번 읽어 메모리에 들고 있다. 그것으로 한 판을 날렸다.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
. "$ROOT/tools/lib/env.sh"; load_env "$ROOT/.env"

MIN_FREE=4000          # MB. 이보다 적으면 재지 않는다
MAX_SWAP=1000          # MB. 판 중에 이를 넘으면 그 판을 버린다
[ "${1:-}" = "--min-free" ] && { MIN_FREE="$2"; shift 2; }

SIZES=("$@")
[ ${#SIZES[@]} -gt 0 ] || { echo "배치 크기를 준다 — bash tools/bench_batch.sh 9 6 3" >&2; exit 1; }

OUT="${TMPDIR:-/tmp}/bench-batch-$(date +%H%M%S)"
mkdir -p "$OUT"

mb(){ awk "/^$1:/ {printf \"%d\", \$2/1024}" /proc/meminfo; }

wait_free() {
  local want="$1" n=0
  while [ "$(mb MemAvailable)" -lt "$want" ]; do
    n=$((n + 1))
    [ "$n" -gt 60 ] && return 1
    printf '\r  여유 %sMB · %sMB 를 기다린다 (%d/60)' "$(mb MemAvailable)" "$want" "$n"
    sleep 10
  done
  printf '\r%*s\r' 60 ""
  return 0
}

echo "기준 : 여유 ${MIN_FREE}MB 이상 · 판 중 스왑 ${MAX_SWAP}MB 이하"
echo "결과 : $OUT"

for SZ in "${SIZES[@]}"; do
  printf '\n\033[1m=== 배치 %s ===\033[0m\n' "$SZ"

  # ── 1. 자리 비우기 ─────────────────────────────────────
  fuser -k 8000/tcp >/dev/null 2>&1
  pkill -f "ollama serve" >/dev/null 2>&1
  sleep 3

  if ! wait_free "$MIN_FREE"; then
    echo "  건너뛴다 — 10분을 기다려도 여유가 ${MIN_FREE}MB 에 못 미친다"
    echo "  다른 작업이 도는 동안 잰 값은 그 작업을 재는 것이다"
    continue
  fi
  echo "  여유 $(mb MemAvailable)MB · 스왑 $(mb SwapTotal)MB 중 $(( $(mb SwapTotal) - $(mb SwapFree) ))MB 사용"

  # ── 2. 엔진 ────────────────────────────────────────────
  bash tools/run_ollama.sh > "${TMPDIR:-/tmp}/ollama.log" 2>&1 &
  for _ in $(seq 20); do
    curl -sf "${OLLAMA_URL:-http://127.0.0.1:11434}/api/version" >/dev/null 2>&1 && break
    sleep 1
  done
  curl -sf "${OLLAMA_URL:-http://127.0.0.1:11434}/api/version" >/dev/null 2>&1 \
    || { echo "  ollama 가 뜨지 않는다 — 멈춘다"; exit 1; }

  # ── 3. 캐시와 워커 ─────────────────────────────────────
  #
  # ★ 순서가 중요하다. 워커를 먼저 띄우면 지우기 전의 캐시를 메모리에 들고
  #   있어, 파일을 지워도 히트가 난다.
  rm -f "$ROOT/worker/${CACHE_FILE:-.cache/translations.json}"
  bash tools/run_worker.sh > "${TMPDIR:-/tmp}/w.log" 2>&1 &
  for _ in $(seq 20); do
    curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && break
    sleep 1
  done
  HEALTH="$(curl -s http://127.0.0.1:8000/health 2>/dev/null)"
  case "$HEALTH" in
    *'"engine":"local"'*) ;;
    "") echo "  워커가 뜨지 않는다 — ${TMPDIR:-/tmp}/w.log 를 본다"; exit 1 ;;
    *)  echo "  엔진이 local 이 아니다: $HEALTH"; exit 1 ;;
  esac

  # ── 4. 측정 ────────────────────────────────────────────
  SWAP_BEFORE=$(( $(mb SwapTotal) - $(mb SwapFree) ))
  python3 tools/bench_golden.py --batch "$SZ" --json "$OUT/b$SZ.json"
  SWAP_AFTER=$(( $(mb SwapTotal) - $(mb SwapFree) ))

  # ★ 판이 끝난 뒤에 스왑을 본다. 시작할 때 깨끗해도 도중에 밀리면 그 판의
  #   속도는 메모리를 잰 것이다(DECISIONS §36).
  if [ "$SWAP_AFTER" -gt "$MAX_SWAP" ]; then
    echo "  ⚠ 판 중에 스왑이 ${SWAP_BEFORE} → ${SWAP_AFTER}MB 로 늘었다"
    echo "    이 판의 속도는 쓰지 않는다. 위반은 결정적이므로 유효하다"
    mv "$OUT/b$SZ.json" "$OUT/b$SZ.tainted.json" 2>/dev/null
  fi
done

# ── 요약 ─────────────────────────────────────────────────
printf '\n\033[1m=== 요약 ===\033[0m\n'
python3 - "$OUT" <<'EOF'
import json, pathlib, sys
d = pathlib.Path(sys.argv[1])
rows = []
for f in sorted(d.glob("b*.json"), key=lambda p: int(p.name.split(".")[0][1:])):
    j = json.loads(f.read_text(encoding="utf-8"))
    kinds = {}
    for r in j.get("rows", []):
        for b in r.get("bad", []):
            kinds[b.split(":")[0]] = kinds.get(b.split(":")[0], 0) + 1
    rows.append((f.name.split(".")[0][1:], j["fail"], sum(kinds.values()),
                 j["seconds"], "tainted" in f.name))
if not rows:
    print("  잰 것이 없다")
else:
    print(f"  {'배치':>4} {'위반유닛':>6} {'종류':>4} {'초':>7} {'자/초':>6}  속도")
    for sz, fail, kinds, sec, tainted in rows:
        cps = 13954 / sec if sec else 0
        print(f"  {sz:>4} {fail:>6} {kinds:>4} {sec:>7.1f} {cps:>6.1f}  "
              f"{'버림 (스왑)' if tainted else '유효'}")
    print("\n  위반은 temperature 0 이라 배치가 같으면 결정적이다.")
    print("  속도는 '유효' 인 판끼리만 비교한다.")
EOF
echo
echo "원시 기록 : $OUT"
