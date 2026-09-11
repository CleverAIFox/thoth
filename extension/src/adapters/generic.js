// Layer 0 — 사이트 지식 0. 항상 매치하는 폴백.
(globalThis.ST ??= {}).adapters ??= [];

globalThis.ST.adapters.push({
  name: "generic",
  priority: 0,
  match: () => true,

  collect(root) {
    const SKIP = "script,style,noscript,nav,header,footer,pre,code,textarea,input,select,button";
    return [...root.querySelectorAll("p,li,td,dd,h1,h2,h3,h4,blockquote")]
      .filter((el) =>
        !el.dataset.stDone &&
        !el.querySelector("p,li,div,section,article") &&   // 말단 노드만
        !el.closest(SKIP) &&
        !el.closest(".st-translation") &&
        (el.innerText || "").trim().length >= 20
      )
      .map((el, i) => ({ id: "g" + i, text: el.innerText.trim(), el, anchor: el, group: null }));
  },
});
