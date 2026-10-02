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
bash ../../tools/build_proposal.sh     # 그림 셋 · docx · 자물쇠 · 대조까지
```

★ **묶음을 네 곳에 적지 않는다**(DECISIONS §126). 전에는 여기에 명령 넷이 늘어서 있었고
`--with` 묶음이 명령마다 달랐다 — `shots.py` 쪽에서 `matplotlib` 이 빠져 있었다.
그림을 안 그리는 스크립트인데 `figlib` 을 끌어오고 그것이 matplotlib 을 import 한다.
목록은 이제 `tools/build_proposal.sh` 하나에 산다.

손으로 하나씩 돌릴 때는 그 파일의 명령을 그대로 쓴다.


★ **`build.lock.json` 은 커밋한다.** `build.js` 가 생성기 아홉 파일의 지문을 거기 적고,
`docx_check` 가 그것을 지금 생성기와 견준다 — 어긋나면 **`기획서 배포` 가 멈춘다**(DECISIONS §126).
`doctor` 에서는 WARN 이다. 다시 쓰는 중에 커밋을 막을 일은 아니지만 **낡은 기획서를 밖으로
내보내는 것**은 막아야 한다.

★ **docx 를 바이트로 견주지 않는다.** zip 이라 같은 입력에서 같은 바이트가 안 나온다 —
그래서 **입력의 지문**을 적는다. 봉인과 같은 꼴이다.

★ **그림마다 사실을 선언한다.** 선언이 없으면 생성기가 멈추고, 선언이 산출물과 어긋나면
`docx_check` 가 멈춘다. 문법은 `figures/figlib.py` 머리에 있다.

★ 한글 글꼴이 있어야 그림이 그려진다 — Noto Sans CJK 또는 윈도우의 맑은 고딕.
