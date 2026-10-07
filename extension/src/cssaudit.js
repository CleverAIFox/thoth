// 번역 박스가 사이트 CSS 에 지고 있는가 — 재는 자리 하나.
//
// ★ **이 파일이 있는 까닭은 세 곳이 같은 것을 재기 때문이다.** 런타임의
//   `broker.js`, 픽스처를 여는 `tools/cascade_check.py`, 그리고 그 둘을 묶는
//   시험. 각자 적으면 **같은 사실이 세 곳에 살고 언젠가 하나만 고쳐진다** —
//   오늘 하루에만 네 번 본 모양이다(DECISIONS §132 · §134 · §135).
//
// ★ **최상위 선언을 두지 않는다**(DECISIONS §16). 콘텐츠 스크립트는 재주입되고,
//   `const` 는 두 번째 주입에서 SyntaxError 가 된다. 전역에 얹기만 한다.
//
// ★ **기대값을 여기 적는다. `content.css` 가 선언하는 것과 같아야 하고, 같은지는
//   `extension/tests/styles.test.js` 가 두 파일을 함께 읽어 본다.** 값이 두 곳에
//   사는 것을 피할 수 없으면 **검사가 둘을 묶는다**(§131 의 태그와 같은 처방).
globalThis.ST ??= {};

// ★ **이 목록이 손으로 들려 있어서 열일곱을 못 봤다**(DECISIONS §169). `content.css`
//   의 바탕 규칙이 선언하던 속성은 **스물둘**이었고 여기 적힌 것은 **다섯**이었다 —
//   `padding` · `border` · `border-radius` · `background` · `box-shadow` · `font-size`
//   · `line-height` · `margin` · `color` 는 **아무도 안 보고 있었다.** 그래서 지메일에서
//   박스가 싼티나게 깨져 있는데 콘솔은 조용했다. **「못 쟀다」 를 「없다」 로 읽었다**(§59).
//
// ★ **고친 길은 목록을 늘리는 것이 아니라 싸울 거리를 줄이는 것이다.** 열일곱은
//   섀도 경계 뒤로 갔고 — 거기서는 **질 수가 없다** — 페이지에 남은 것은 호스트의
//   **넷**뿐이다. 아래 목록은 이제 `content.css` 의 페이지 구역이 선언하는 것과
//   **전수로 같다.** 같은지는 `extension/tests/styles.test.js` 가 두 파일을 함께
//   읽어 보고, **분류가 빠짐없는지**까지 문다(족 가드 — 목록이 다시 짧아질 수 없다).
globalThis.ST.CSS_EXPECT = {
  display: "block",
  boxSizing: "border-box",
  overflow: "visible",
};

/** 섀도 안쪽 본문 요소의 클래스. 브로커가 붙이고 `content.css` 가 꾸민다. */
globalThis.ST.몸클래스 = "st-몸";

// 폭은 키워드가 아니라 수다. 1px 은 소수 반올림 몫이다.
globalThis.ST.CSS_WIDTH_TOL = 1;

/**
 * 판정만 한다. DOM 을 안 읽으므로 브라우저 없이 시험할 수 있다(§21).
 * @param {object} computed  `getComputedStyle` 또는 같은 꼴의 객체
 * @param {number} 폭        박스의 `offsetWidth`
 * @param {number} 그릇폭    부모의 안쪽 폭. 못 재면 0 이하를 넘긴다
 * @returns {string[]} 어긋난 속성 이름들. 빈 배열이면 이겼다
 */
globalThis.ST.cssFaults = function (computed, 폭, 그릇폭) {
  const 기대 = globalThis.ST.CSS_EXPECT;
  const out = Object.keys(기대).filter((k) => computed[k] !== 기대[k]);
  // ★ **모르는 것을 틀렸다고 적지 않는다.** 부모가 inline 이면 `clientWidth` 가 0 이다.
  //   재지 못한 것을 어긋남으로 세면 그 줄은 곧 안 읽힌다(§59).
  if (그릇폭 > 0 && Math.abs(폭 - 그릇폭) > globalThis.ST.CSS_WIDTH_TOL) out.push("width");
  return out;
};

/** 실제 노드를 재서 `cssFaults` 에 넘긴다. 레이아웃이 끝난 뒤에 불러야 한다. */
globalThis.ST.cssMeasure = function (node) {
  const p = node.parentElement;
  if (!p) return [];
  const ps = getComputedStyle(p);
  const 그릇폭 = p.clientWidth
    - parseFloat(ps.paddingLeft || 0) - parseFloat(ps.paddingRight || 0);
  return globalThis.ST.cssFaults(getComputedStyle(node), node.offsetWidth, 그릇폭);
};


// ── 어디에 꽂을 것인가(DECISIONS §165) ──────────────────────────────────────
//
// ★ **재는 자가 고자질만 하고 있었다.** 위 `cssFaults` 는 **꽂고 나서** 「졌다」 를 적는다.
//   같은 수로 **꽂기 전에 고르면** 그것이 곧 사이트 중립이다 — 지메일을 몰라도
//   「폭 147px 짜리 칸」 은 어느 사이트에서나 못 쓴다.
// ★ **2026-10-05 실측**(지메일 받은편지함, 상자 22개) :
//     TD[gridcell] w=200 · 318      ← 여기 꽂으면 147px 폭에 222px 높이로 선다
//     TR[row]      w=694            ← 여기 다음에 꽂으면 694px 폭에 61px 다
//     DIV[link]    w=308 overflow:hidden  ← 넣으면 잘린다
// ★ **순수 함수다.** `[{폭, 잘림, 행인가}]` 만 받는다 — jsdom 에 레이아웃이 없으므로
//   **수를 합성으로 먹여** 전부 시험한다(`cssFaults` 와 같은 꼴, §132).
// ★ **밖 — `li` 는 행 경계가 아니다.** 지메일이 `tr` 이고, `li` 까지 넣으면 Udemy 쪽
//   자리가 같이 바뀐다. **오늘 잰 병만 고친다**(§133). `li` 꼴의 목록은 **안 본다.**

/**
 * **레이아웃을 잴 수 있는 자리인가**(DECISIONS §168).
 *
 * ★ **앵커의 폭으로 묻지 않는다.** §165 가 처음 그렇게 적었고 **지메일에서 셋 중 둘이
 *   칸 안에 섰다** — 인라인 요소(`span`)는 **레이아웃이 멀쩡해도 `clientWidth` 가 0** 이다.
 *   지메일의 제목 · 미리보기 앵커가 전부 `span` 이라 고르는 자가 통째로 건너뛰어졌다.
 * ★ **묻는 것은 「이 노드가 넓나」 가 아니라 「이 문서에 레이아웃이 있나」 다.** 둘을
 *   한 수로 물으면 **좁은 것과 레이아웃 없는 것이 같아 보인다** — jsdom 과 `span` 이
 *   똑같이 0 을 준다. 뿌리의 폭으로 묻는다.
 */
globalThis.ST.잴수있나 = function () {
  if (typeof getComputedStyle !== "function") return false;
  const 뿌리 = globalThis.document && globalThis.document.documentElement;
  return !!뿌리 && 뿌리.clientWidth > 0;
};

/** 행 경계로 세는 것. 여기 꽂으면 **덮지 않고 민다.** */
globalThis.ST.행경계 = "tr,[role=row]";

/** 글이 읽히는 최소 폭(px). 이보다 좁으면 **안 꽂는다** — 억지로 꽂은 것이 그 기둥이다. */
globalThis.ST.최소폭 = 280;

/**
 * 어디에 꽂을지 **수로만** 고른다.
 * @param {{폭:number, 잘림:boolean, 행인가:boolean}[]} 길 가까운 조상부터
 * @returns {{자리:number, 꼴:"행다음"|"형제"}|null} 못 고르면 null — **못 꽂는 것도 답이다**
 */
globalThis.ST.고른다 = function (길) {
  // ★ **행이 있으면 행이 이긴다.** 칸 안은 높이가 고정이라 **넓어도 겹친다** —
  //   폭만 보면 318 짜리 칸을 고르고, 그 칸은 행 높이가 40px 이다.
  const 행 = 길.findIndex((x) => x.행인가);
  if (행 >= 0) return { 자리: 행, 꼴: "행다음" };
  // ★ **가장 가까운 쓸 만한 자리.** 가장 넓은 자리를 고르면 `body` 까지 올라간다.
  for (let i = 0; i < 길.length; i++) {
    if (길[i].잘림) continue;
    if (길[i].폭 >= globalThis.ST.최소폭) return { 자리: i, 꼴: "형제" };
  }
  return null;
};

// ── 뼈대를 몇 줄로 세울 것인가(DECISIONS §170) ──────────────────────────────
//
// ★ **`min-height: 104px` 를 박고 있었다.** 스물두 자짜리 UI 토막도 백네 픽셀을
//   잡았고, 메일 목록 스무 줄이면 **회색 슬래브 스무 장**이 됐다. 그것이 「싼티」 의
//   절반이다. 자리를 잡는 것은 맞지만 **얼마나 잡을지를 안 재고 있었다.**
//
// ★ **두 수를 실측했다** — 추측으로 안 짓는다(§294 의 처방).
//     번역/원문 글자수 비 : 골든셋 45유닛의 `ratio_min` 0.3 · `ratio_max` 0.75,
//                           가운데 **0.525**(`worker/tests/golden/cases.json`)
//     한 줄에 드는 글자수 : 크로미움 실측(2026-10-06, 한글 지문 612자)
//                           카드 15.5px/1.74 — 폭 320·480·600·694 에서 20·34·41·51 자
//                           띠   14px/1.62  — 같은 폭에서 26·41·51·56 자
//                           → 거의 선형이다. **폭 ÷ 14**(카드) · **폭 ÷ 12.4**(띠)
globalThis.ST.번역비 = 0.525;
globalThis.ST.글자폭 = { 카드: 14, 띠: 12.4 };
globalThis.ST.줄상한 = 4;

/**
 * 원문 길이와 폭으로 **뼈대 줄 수**를 센다. 순수 함수다 — 브라우저 없이 시험한다.
 *
 * ★ **못 재면 셋이다.** 폭이 0 이면 §170 전의 값(세 줄)으로 둔다 —
 *   **「못 쟀다」 를 「한 줄」 로 읽으면 자리가 모자라 글자가 튄다**(§59).
 * ★ **넷에서 끊는다.** 뼈대는 「기다린다」 를 말하는 장치고, 넷을 넘으면 어차피
 *   스크롤 밖이다. 상한이 없으면 긴 지문 하나가 화면을 통째로 덮는다.
 *
 * @param {number} 원문글자  번역 전 원문의 글자수
 * @param {number} 폭        박스가 설 자리의 안쪽 폭(px). 0 이하면 못 쟀다는 뜻
 * @param {"카드"|"띠"} 꼴
 * @returns {number} 1 .. ST.줄상한
 */
globalThis.ST.줄수 = function (원문글자, 폭, 꼴) {
  if (!(폭 > 0)) return 3;
  const 자폭 = globalThis.ST.글자폭[꼴 === "띠" ? "띠" : "카드"];
  const 한줄 = Math.max(1, Math.floor(폭 / 자폭));
  const 줄 = Math.ceil((원문글자 * globalThis.ST.번역비) / 한줄);
  return Math.min(globalThis.ST.줄상한, Math.max(1, 줄));
};

/** 실제 노드를 재서 `고른다` 에 넘긴다. 레이아웃이 있는 곳에서만 부른다. */
globalThis.ST.꽂을자리 = function (anchor) {
  const 요소 = [];
  const 길 = [];
  let n = anchor;
  // ★ **아홉 칸에서 끊는다.** 깊은 사이트에서 `body` 까지 올라가는 것을 막는다.
  while (n && 요소.length < 9) {
    const s = getComputedStyle(n);
    요소.push(n);
    길.push({
      폭: n.clientWidth,
      잘림: s.overflow === "hidden" || s.overflowX === "hidden",
      행인가: typeof n.matches === "function" && n.matches(globalThis.ST.행경계),
    });
    if (길[길.length - 1].행인가) break;      // 행에서 멈춘다 — 더 올라갈 까닭이 없다
    n = n.parentElement;
  }
  const 뽑 = globalThis.ST.고른다(길);
  // ★ **고른 자리의 폭을 함께 돌려준다**(DECISIONS §170). 뼈대 줄 수가 그 수에서
  //   나온다 — **이미 잰 값을 버리고 나중에 다시 재면** 꽂기 전과 꽂은 뒤가 갈린다.
  return 뽑 ? { 자리: 요소[뽑.자리], 꼴: 뽑.꼴, 폭: 길[뽑.자리].폭 } : null;
};
