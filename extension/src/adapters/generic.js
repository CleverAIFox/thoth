// Layer 0 — 사이트 지식 0. 항상 매치하는 폴백.
(globalThis.ST ??= {}).adapters ??= [];

// ★ **어댑터는 `location` 을 직접 보지 않고 이것을 본다**(DECISIONS §102). 픽스처가
//   `127.0.0.1` 에서 Udemy 인 척할 수 있어야 사이트 어댑터를 사이트 없이 잰다.
//   `<meta name="st-fixture-url">` 은 **로컬 호스트에서만** 먹는다 — 남의 사이트가
//   이 태그로 어댑터를 바꾸지 못하게 한다.
globalThis.ST.pageUrl = function () {
  const host = location.hostname;
  if (host === "127.0.0.1" || host === "localhost" || host === "") {
    const m = document.querySelector("meta[name=st-fixture-url]");
    if (m?.content) return m.content;
  }
  return location.href;
};

// 페이지에 읽을 만한 글 덩어리가 몇 개인가. 관측 행의 `blocks` 다.
//
// ★ **innerText 를 부르지 않는다.** 한 번이지만 페이지 전체라 강제 리플로가
//   난다(실측 125ms). 판정에 쓰는 수가 아니라 규모를 보는 수라 textContent 로
//   충분하다. 번역 박스는 뺀다 — 넣으면 번역할수록 늘어난다.
globalThis.ST.textBlocks = function (root) {
  let n = 0;
  for (const el of root.querySelectorAll("p,li,td,dd,h1,h2,h3,h4,blockquote")) {
    if (el.closest(".st-translation")) continue;
    if (el.textContent.trim().length >= 20) n++;
  }
  return n;
};

// 상위 계층이 재사용한다. 어댑터가 배타 선택이므로, 상위 계층이 자기 몫만
// 모으면 본문이 통째로 빠진다(DECISIONS §11).
globalThis.ST.genericCollect = function (root, opts) {
  const skipRoots = (opts && opts.skip) || [];
  const SKIP = "script,style,noscript,nav,header,footer,pre,code,textarea,input,select,button";
  const BLOCK = "p,li,div,section,article";
  const out = [];

  // ★ 이미 처리한 요소를 셀렉터 단계에서 뺀다. 매 순회마다 페이지 전체를
  //   다시 훑으면 innerText 호출이 누적돼 강제 리플로가 난다(실측 125ms).
  //   :not() 은 CSS 엔진이 처리하므로 JS 순회에 들어오지도 않는다.
  const TAGS = ["p", "li", "td", "dd", "h1", "h2", "h3", "h4", "blockquote"];
  const SEL = TAGS.map((t) => `${t}:not([data-st-done]):not([data-st-fail])`).join(",");

  for (const el of root.querySelectorAll(SEL)) {
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
