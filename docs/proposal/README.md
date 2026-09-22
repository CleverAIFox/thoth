# 기획서 생성기

`docs/proposal.docx` 를 만든다(DECISIONS §116). **docx 를 손으로 고치지 않는다** — 여기를 고치고 다시
만든다. 규칙은 MASTER §0-7 이다.

| 파일 | 담는 것 |
|---|---|
| `part1.js` · `part2.js` · `part3.js` | 본문 — 제안서 · 요구사항 분석서 · 상세 설계서 |
| `lib.js` | 표 · 그림 · 문단 도구. 그림의 사실 선언을 대체 텍스트에 싣는다 |
| `figures/charts.py` | 차트. 수를 산출물에서 읽는다 |
| `figures/diagrams.py` | 도식. 그린 수를 손으로 선언한다 |
| `figures/shots.py` | 확장 화면. 실제 `popup.html` · `preview.html` 을 찍는다 |
| `.build/` | 중간 산출물. 커밋하지 않는다 |

```bash
npm install
uv run --with matplotlib --with numpy --with pillow python figures/charts.py
uv run --with matplotlib --with pillow python figures/diagrams.py
uv run --with playwright --with pillow python figures/shots.py
node build.js
python3 ../../tools/docx_check.py
```

★ **그림마다 사실을 선언한다.** 선언이 없으면 생성기가 멈추고, 선언이 산출물과 어긋나면
`docx_check` 가 멈춘다. 문법은 `figures/figlib.py` 머리에 있다.

★ 한글 글꼴이 있어야 그림이 그려진다 — Noto Sans CJK 또는 윈도우의 맑은 고딕.
