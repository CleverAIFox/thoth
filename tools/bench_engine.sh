#!/usr/bin/env bash
# 번역 엔진 후보를 재는 도구 (PLAN §5 #37).
# 서버 기동 · GPU 점유 샘플링 · 2회 측정을 한 셸에서 처리한다.
# 1회차는 모델 로딩을 포함하므로 2회차가 실사용 체감이다.
#
#   bash tools/bench_engine.sh exaone3.5:7.8b
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/tools/lib/env.sh"; load_env "$ROOT/.env"

MODEL="${1:-${OLLAMA_MODEL:-qwen2.5:3b}}"
URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
SRC="Kinesis Data Streams almost immediately makes records older than 72 hours inaccessible."
SYS="Translate English to Korean. Keep AWS service names, API names, and parameter names in English, but attach Korean particles to them naturally (예: Kinesis Data Streams는, S3에). Use 합니다 style. Write grammatical Korean. Output ONLY the translation."

curl -sf "$URL/api/version" >/dev/null || {
  echo "== ollama 기동 =="
  bash "$ROOT/tools/run_ollama.sh" > /tmp/ollama.log 2>&1 &
  for _ in $(seq 20); do curl -sf "$URL/api/version" >/dev/null && break; sleep 1; done
}

ollama list | grep -q "^${MODEL}" || { echo "== $MODEL 내려받기 =="; ollama pull "$MODEL"; }

req() {
  python3 -c '
import json,sys
print(json.dumps({"model":sys.argv[1],"system":sys.argv[2],"prompt":sys.argv[3],
                  "stream":False,"think":False,"options":{"temperature":0,"seed":42}}))
' "$MODEL" "$SYS" "$SRC"
}

for round in 1 2; do
  echo; echo "===== $MODEL · ${round}회차 ====="
  ( while :; do
      nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits
      sleep 1
    done ) > /tmp/gpu_samples.txt 2>/dev/null &
  SAMPLER=$!

  START=$(date +%s.%N)
  OUT=$(req | curl -s "$URL/api/generate" -d @- \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["response"].strip())')
  END=$(date +%s.%N)

  kill "$SAMPLER" 2>/dev/null; wait "$SAMPLER" 2>/dev/null

  printf '소요   : %.1fs\n' "$(echo "$END - $START" | bc)"
  printf 'GPU최대: %s MiB\n' "$(sort -n /tmp/gpu_samples.txt 2>/dev/null | tail -1)"
  echo "출력   : $OUT"
done
