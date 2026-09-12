// Layer 0 — 사이트 지식 0. 항상 매치하는 폴백.
(globalThis.ST ??= {}).adapters ??= [];

// 상위 계층이 재사용한다. 어댑터가 배타 선택이므로, 상위 계층이 자기 몫만
// 모으면 본문이 통째로 빠진다(DECISIONS §11).
globalThis.ST.genericCollect = function (root, opts) {
  const skipRoots = (opts && opts.skip) || [];
  const SKIP = "script,style,noscript,nav,header,footer,pre,code,textarea,input,select,button";
  const BLOCK = "p,li,div,section,article";
  const out = [];

  for (const el of root.querySelectorAll("p,li,td,dd,h1,h2,h3,h4,blockquote")) {
    if (el.dataset.stDone || el.dataset.stFail) continue;
    if (el.querySelector(BLOCK)) continue;          // 말단 노드만
    if (el.closest(SKIP) || el.closest(".st-translation")) continue;
    if (skipRoots.some((r) => r.contains(el))) continue;

    // textContent 로 먼저 거른다. innerText 는 강제 리플로를 일으키므로
    // 후보가 아닌 요소에까지 물으면 페이지 전체를 매 순회마다 다시 재게 된다.
    if (el.textContent.trim().length < 20) continue;
    const text = (el.innerText || "").trim();
    if (text.length < 20) continue;

    out.push({ id: "g" + out.length, text, el, anchor: el, group: null });
  }
  return out;
};

if (!globalThis.ST.adapters.some((a) => a.name === "generic"))
globalThis.ST.adapters.push({
  name: "generic",
  priority: 0,
  match: () => true,
  collect: (root) => globalThis.ST.genericCollect(root),

  anchorFor(el) {
    // td · th 뒤에 div 를 꽂으면 브라우저가 테이블 밖으로 튕겨낸다.
    // 표 안에서는 셀 내부에 붙인다.
    return el.matches("td,th") ? el : el;
  },

  decorate(node, unit) {
    if (unit.el.matches("td,th")) node.style.setProperty("display", "block");
  },
});
