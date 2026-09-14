#!/usr/bin/env bash
# 현재 엔진의 기동 전제를 확인한다. 워커를 띄우지 않는다.
#
#   bash tools/preflight.sh
#   ENGINE=bedrock bash tools/preflight.sh   이번 한 번만 다른 엔진으로
#
# ★ **.env 를 여기서 읽는다.** 전에는 검사 스크립트를 `uv run` 으로 직접 부를 수
#   있었고, 그러면 `load_env` 를 타지 않아 AWS_PROFILE 이 비었다. 호출 경로마다
#   환경이 갈리면 같은 명령이 다른 답을 낸다 — 재현되지 않는 검사는 검사가
#   아니다. 입구를 하나로 둔다.
#
# ★ 엔진 이름을 모른다. 무엇을 확인할지는 `app/preflight.py` 의 레지스트리가
#   정한다. 엔진이 늘어도 이 파일은 그대로다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/tools/lib/env.sh"; load_env "$ROOT/.env"
cd "$ROOT/worker"
exec uv run python -m app.preflight "$@"
