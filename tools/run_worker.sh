#!/usr/bin/env bash
# 저장소 루트의 .env 를 읽어 워커를 띄운다.
# 우선순위는 셸 > 파일이 아니라 파일이 기본값이므로, 이미 export 된 값이 있으면
# .env 가 조용히 덮어쓴다. 프로젝트 설정을 셸에 export 하지 않는 이유가 그것이다(D-0066).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$ROOT/.env" ] && { set -a; . "$ROOT/.env"; set +a; }
cd "$ROOT/worker"
exec uv run uvicorn app.main:app --port "${PORT:-8000}" --reload
