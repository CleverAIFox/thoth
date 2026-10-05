#!/usr/bin/env bash
# 기획서를 다시 만든다 — 그림 셋 · docx · 자물쇠 · 대조까지 한 줄로(DECISIONS §126).
#
#   bash tools/build_proposal.sh
#
# ★ **이 파일이 있는 까닭.** 전에는 README 가 네 명령을 늘어놓았고 `--with` 묶음이
#   명령마다 달랐다. 2026-10-03 에 그중 하나(`shots.py`)의 묶음에서 `matplotlib` 이
#   빠져 있는 것이 드러났다 — `shots.py` 는 그림을 안 그리지만 `figlib` 을 끌어오고
#   그것이 matplotlib 을 import 한다. **같은 의존성 목록이 네 곳에 살면 한 곳만 늙는다**
#   (DECISIONS §14 의 되풀이). 이제 목록은 이 파일 하나에 산다.
#
# ★ **멈추는 자리를 안 숨긴다.** `charts.py` 는 DECISIONS 에 이름표 없는 날짜를 만나면
#   죽는다 — 맞는 설계다. 그런데 2026-09-28 부터 그렇게 죽어 있었고 **아무도 그 죽음을
#   안 봤다.** 생성기가 안 돌면 docx 를 다시 만들 수가 없으니 배포본이 뒤진 것이다.
#   그래서 여기서는 `set -e` 로 **첫 실패에서 멈추고 무엇이 막혔는지 이름을 댄다.**
#
# ★ **`shots.py` 만 건너뛸 수 있다.** 크로미움이 없는 기계가 있다 — 그 그림은 옛것이
#   남고, 그 사실을 찍는다. 나머지 둘은 건너뛰지 않는다. 숫자를 그리는 그림이다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/docs/proposal" || exit 1

# ★ 묶음을 한 곳에 적는다. 셋 다 `figlib` 을 거치므로 matplotlib 이 공통이다.
PY_COMMON=(--with matplotlib --with pillow)

# ★ 함수 이름도 ASCII 다. 배시는 받지만 shellcheck 가 못 읽는다(DECISIONS §123 과 같은 자리).
say(){ printf '\n== %s ==\n' "$1"; }

# ★ **`npm ci` 다 — `npm install` 이 아니다**(DECISIONS §128). `install` 은 잠금을
#   **고쳐 쓸 수 있고**, 그러면 같은 생성기가 다른 `docx` 판으로 다른 산출물을 낸다.
#   자물쇠는 **생성기 파일**의 지문만 보므로 그 차이를 못 잡는다 — 잠금은 잠금이 지킨다.
# ★ `package-lock.json` 이 없으면 `ci` 가 거절한다. 그것이 맞다 — 잠금 없이 구운 docx 는
#   「무엇으로 구웠는지」 를 아무도 모른다.
say "npm"
npm ci --silent

say "차트 — 수를 산출물에서 읽는다"
uv run "${PY_COMMON[@]}" --with numpy python figures/charts.py

say "도식 — 그린 수를 손으로 선언한다"
uv run "${PY_COMMON[@]}" python figures/diagrams.py

# ★ **건너뛰기는 옛 그림이 있을 때만 성립한다**(DECISIONS §126). `shots.py` 머리말이
#   「없으면 이 그림만 건너뛰고 옛 그림이 남는다」 고 적는데, 그 전제는 `.build/` 가
#   남아 있을 때만 참이다 — **`.build/` 는 gitignore 다.** 깨끗한 나무에서 건너뛰면
#   `build.js` 가 `f_popup: 사실 선언이 없다` 로 죽는다. 2026-10-03 에 그렇게 막혔다.
#   그래서 **건너뛴 뒤에 사실 파일이 실제로 있는지 본다.** 없으면 멈춘다.
SHOT_FACTS=(.build/fig/f_popup.facts.json .build/fig/f_preview_a.facts.json)

say "화면 — 실제 popup.html · preview.html 을 찍는다"
if uv run "${PY_COMMON[@]}" --with playwright python figures/shots.py; then
  :
else
  MISSING=""
  for f in "${SHOT_FACTS[@]}"; do [ -f "$f" ] || MISSING="$MISSING $f"; done
  if [ -n "$MISSING" ]; then
    echo "  멈춘다 — 크로미움이 없고 **옛 그림도 없다.**$MISSING"
    echo "  .build/ 는 gitignore 라 깨끗한 나무에는 옛것이 없다 — 건너뛸 수가 없다"
    echo "  깔고 다시 돌린다 : uv run --with playwright python -m playwright install chromium"
    exit 1
  fi
  echo "  건너뛴다 — 크로미움이 없다. **이 그림만 옛것이 남는다**(사실 파일 둘 확인했다)"
fi

say "docx + 자물쇠"
node build.js

# ★ **두 번째 렌더러**(DECISIONS §166). 같은 `part*.js` 로 HTML 을 굽는다 — 이것이 돌아야
#   「본문이 포맷 중립이다」 가 주장에서 사실이 된다. 터지면 여기서 멈춘다.
# ★ **한 파일이다.** 그림은 `data:` 로 실려 CDN 도 옆 파일도 없다 — 종전 화면은
#   `jsdelivr` 에서 `docx-preview` 를 받아 와 브라우저에서 docx 를 풀었다.
say "html — 같은 블록으로 두 번째 산출물"
node html.js

say "대조"
cd "$ROOT"
python3 tools/docx_check.py --deploy
echo
echo "다음 : git add docs/proposal.docx docs/proposal/build.lock.json site/proposal.html && git commit"
