#!/usr/bin/env bash
# 확장 산출물을 SSD 의 프로젝트 데이터 디렉터리로 내보낸다.
#
# 크롬은 \\wsl$ 같은 네트워크 경로에서 압축해제 확장을 로드하지 못한다.
# 정본은 WSL 의 extension/ 이고 대상은 --delete 로 덮어쓰는 파생물이다.
# 대상에서 편집하면 다음 실행에 사라진다.
#
# ★ 대상이 DrvFs 라 유닉스 퍼미션을 받지 못한다. rsync -a 는 -p 를 포함해
#   권한 설정에서 죽는다(hathor D-0120 과 같은 원인). 권한 보존을 끈다.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
. "$ROOT/tools/lib/env.sh"; load_env "$ROOT/.env"
# 경로의 정본은 .env 다. 스크립트가 기본값을 들고 있으면 두 곳이 어긋난다.
: "${THOTH_EXT_DEST:?.env 에 THOTH_EXT_DEST 가 없다}"
DEST="$THOTH_EXT_DEST"
SRC="$(cd "$(dirname "$0")/.." && pwd)/extension"

[ -d "$SRC" ] || { echo "소스 없음 : $SRC" >&2; exit 1; }
mkdir -p "$DEST"
# ★ 테스트와 그 의존성은 배포물이 아니다. 크롬에 실릴 필요가 없고, 실리면
#   웹스토어 심사에 설명할 것만 는다. 확장 자체는 의존성이 없다 —
#   `package.json` 은 테스트 전용이다.
rsync -rlt --delete --no-perms --no-owner --no-group \
  --exclude=tests/ --exclude=node_modules/ --exclude=package*.json \
  "$SRC/" "$DEST/"

echo "동기화 완료 -> $(echo "$DEST" | sed 's|/mnt/f|F:|; s|/|\\|g')"
