#!/usr/bin/env bash
# 저장소 루트의 .env 를 읽어 워커를 띄운다.
#
#   bash tools/run_worker.sh
#   ENGINE=echo bash tools/run_worker.sh    이번 한 번만 다른 엔진으로
#
# ★ 셸에 앞세운 지정이 .env 를 이긴다(DECISIONS §40). `~/.bashrc` 에 박아 두는
#   영구 오염은 여전히 금지이고 `doctor` 가 검사한다(D-0066).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/tools/lib/env.sh"; load_env "$ROOT/.env"
PORT="${PORT:-8000}"

# ★ --reload 는 reloader(부모)와 server(자식) 두 프로세스를 띄운다. 부모만
#   죽이면 자식이 잠깐 포트를 붙들고 있어 다음 기동이 Address already in use
#   로 실패한다. 띄우기 전에 포트가 비었는지 확인하고 비운다.
if command -v fuser >/dev/null 2>&1 && fuser "$PORT/tcp" >/dev/null 2>&1; then
  echo "포트 $PORT 사용 중 — 정리한다"
  fuser -k "$PORT/tcp" >/dev/null 2>&1
  for _ in $(seq 10); do fuser "$PORT/tcp" >/dev/null 2>&1 || break; sleep 0.3; done
fi

# ★ **여기가 ollama 가 실제로 필요한 자리다.** `doctor` 는 이것을 `warn` 으로만
#   알린다 — 문서를 고치는 커밋까지 막을 일이 아니기 때문이다. 막는 것은 정말
#   못 돌아가는 지점이어야 하고, 그곳이 여기다(DECISIONS §46).
#
# ★ 띄운 뒤에 502 로 알게 되면 원인을 찾는 데 시간이 든다. 기동 전에 죽는 편이
#   낫다 — 실패는 그것이 일어난 자리에서 알린다(§37).
if [ "${ENGINE:-echo}" = "local" ]; then
  if ! curl -sf "${OLLAMA_URL:-http://127.0.0.1:11434}/api/version" >/dev/null 2>&1; then
    echo "ENGINE=local 인데 ollama 가 응답하지 않는다" >&2
    echo "  bash tools/run_ollama.sh > /tmp/ollama.log 2>&1 &" >&2
    echo "  이번 한 번만 엔진 없이 띄우려면 : ENGINE=echo bash tools/run_worker.sh" >&2
    exit 1
  fi
fi

cd "$ROOT/worker"
exec uv run uvicorn app.main:app --port "$PORT" --reload
