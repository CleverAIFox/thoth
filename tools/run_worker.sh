#!/usr/bin/env bash
# 저장소 루트의 .env 를 읽어 워커를 띄운다.
# 우선순위는 셸 > 파일이 아니라 파일이 기본값이므로, 이미 export 된 값이 있으면
# .env 가 조용히 덮어쓴다. 프로젝트 설정을 셸에 export 하지 않는 이유가 그것이다(D-0066).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$ROOT/.env" ] && { set -a; . "$ROOT/.env"; set +a; }
PORT="${PORT:-8000}"

# ★ --reload 는 reloader(부모)와 server(자식) 두 프로세스를 띄운다. 부모만
#   죽이면 자식이 잠깐 포트를 붙들고 있어 다음 기동이 Address already in use
#   로 실패한다. 띄우기 전에 포트가 비었는지 확인하고 비운다.
if command -v fuser >/dev/null 2>&1 && fuser "$PORT/tcp" >/dev/null 2>&1; then
  echo "포트 $PORT 사용 중 — 정리한다"
  fuser -k "$PORT/tcp" >/dev/null 2>&1
  for _ in $(seq 10); do fuser "$PORT/tcp" >/dev/null 2>&1 || break; sleep 0.3; done
fi

cd "$ROOT/worker"
exec uv run uvicorn app.main:app --port "$PORT" --reload
