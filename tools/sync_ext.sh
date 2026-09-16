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
# ★ `preview.html` 도 뺀다. 개발용 화면이고 크롬은 폴더 안의 모든 파일을
#   확장의 일부로 본다.
#
# ★ 테스트와 그 의존성은 배포물이 아니다. 크롬에 실릴 필요가 없고, 실리면
#   웹스토어 심사에 설명할 것만 는다. 확장 자체는 의존성이 없다 —
#   `package.json` 은 테스트 전용이다.
rsync -rlt --delete --no-perms --no-owner --no-group \
  --exclude=tests/ --exclude=node_modules/ --exclude=package*.json \
  --exclude=preview.html \
  "$SRC/" "$DEST/"

# ★ **기계 기본값은 파생물에만 쓴다.** 저장소의 `src/config.local.js` 는 언제나
#   비어 있고, 값은 `.env` 에서 읽어 여기서만 채운다. 그래야 공개 저장소에
#   엔드포인트도 토큰도 나가지 않는다(DECISIONS §84).
#
# ★ **`WORKER_TOKEN` 을 쓰지 않는다.** 그 키는 로컬 워커가 **요구할** 토큰이고
#   채우면 골든셋과 스모크가 401 을 받는다. 확장 쪽은 `EXT_TOKEN` 으로 따로
#   둔다 — 같은 이름의 다른 것을 한 키에 담지 않는다(§14).
{
  echo "// tools/sync_ext.sh 가 만든다. 손으로 고치지 않는다."
  echo "globalThis.ST ??= {};"
  echo "globalThis.ST.CONFIG = {"
  echo "  endpoint: \"${EXT_ENDPOINT:-}\","
  echo "  token: \"${EXT_TOKEN:-}\","
  echo "};"
} > "$DEST/src/config.local.js"

echo "동기화 완료 -> $(echo "$DEST" | sed 's|/mnt/f|F:|; s|/|\\|g')"
if [ -n "${EXT_ENDPOINT:-}" ]; then
  echo "  기본 엔드포인트 : $EXT_ENDPOINT"
else
  echo "  기본 엔드포인트 없음 — .env 의 EXT_ENDPOINT 를 채우면 팝업 입력이 필요 없다"
fi
[ -n "${EXT_TOKEN:-}" ] && echo "  토큰 : 있다" || echo "  토큰 : 없다"
