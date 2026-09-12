#!/usr/bin/env bash
# ENGINE=local 용 추론 서버. systemd 서비스는 .env 를 읽지 못하고
# ollama 시스템 사용자로 돌아 프로젝트 설정이 반영되지 않으므로 끄고 이걸 쓴다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$ROOT/.env" ] && { set -a; . "$ROOT/.env"; set +a; }
exec ollama serve
