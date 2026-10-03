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

globalThis.ST.CSS_EXPECT = {
  display: "block",
  whiteSpace: "pre-wrap",
  overflowWrap: "break-word",
  boxSizing: "border-box",
};

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
