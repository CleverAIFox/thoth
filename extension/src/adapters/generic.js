// Layer 0 — 사이트 지식 0. 항상 매치하는 폴백.
(globalThis.ST ??= {}).adapters ??= [];

// ★ **픽스처인가.** 빈 문자열이 아니면 픽스처이고 그 값이 흉내내는 주소다.
//   `<meta name="st-fixture-url">` 은 **로컬 호스트에서만** 먹는다 — 남의 사이트가
//   이 태그로 어댑터를 바꾸거나 관측을 읽어 가지 못하게 한다(DECISIONS §102 · §104).
//
// ★ **판별을 한 자리에 둔다.** 전에는 `pageUrl` 안에만 있었고, 관측을 페이지로
//   내보낼 때 같은 조건을 또 적을 뻔했다. 같은 판단이 두 곳에 살면 갈린다(§14).
globalThis.ST.fixtureUrl = function () {
  const host = location.hostname;
  if (host !== "127.0.0.1" && host !== "localhost" && host !== "") return "";
  return document.querySelector("meta[name=st-fixture-url]")?.content || "";
};

// ★ **어댑터는 `location` 을 직접 보지 않고 이것을 본다**(DECISIONS §102). 픽스처가
//   `127.0.0.1` 에서 Udemy 인 척할 수 있어야 사이트 어댑터를 사이트 없이 잰다.
globalThis.ST.pageUrl = function () {
  return globalThis.ST.fixtureUrl() || location.href;
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
  // ★ **말단을 가르는 목록에 표가 있어야 한다**(DECISIONS §160). 2026-10-05 지메일에서
  //   같은 문구가 **두 번** 떴다 — HTML 메일은 **표 안의 표**로 짜는 것이 표준인데
  //   `td` 와 `table` 이 이 목록에 없어 **바깥 `td` 도 말단으로 세어졌다.** 그래서 같은
  //   글이 두 번 모이고, 앵커가 둘 다 `td` 라 **셀 안에 상자가 겹쳐 꽂혔다.**
  const BLOCK = "p,li,div,section,article,table,td,th";
  const out = [];

  // ★ 이미 처리한 요소를 셀렉터 단계에서 뺀다. 매 순회마다 페이지 전체를
  //   다시 훑으면 innerText 호출이 누적돼 강제 리플로가 난다(실측 125ms).
  //   :not() 은 CSS 엔진이 처리하므로 JS 순회에 들어오지도 않는다.
  //
  // ★ **`div` 가 여기 없어서 본문이 통째로 사각이었다**(DECISIONS §160). 지메일은 메일
  //   본문을 `div` 로 그리고, HTML 메일은 `td > div > 글` 로 싼다. 재 보니 아홉 꼴 중
  //   **다섯이 0건**이었다 — `div > 글` · `div > div > 글` · `td > div > 글` ·
  //   `td > div > span` 이 전부 안 잡혔다. 바깥 `td` 는 `BLOCK` 에 걸려 빠지고 안쪽
  //   `div` 는 **후보가 아니어서**, 그 사이에 든 글이 아무에게도 안 보였다.
  // ★ **딸려 오는 것이 없다.** 지메일 껍데기의 `div`(받은편지함 · 답장 …)는 20자 미만이라
  //   길이 문턱이 거른다 — 실물 꼴로 재서 확인했다.
  const TAGS = ["p", "li", "td", "dd", "div", "h1", "h2", "h3", "h4", "blockquote"];
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

  // ★ **`anchorFor` 도 `decorate` 도 없다**(DECISIONS §135).
  //
  //   `anchorFor` 는 `el.matches("td,th") ? el : el` 이었다 — **두 갈래가 같은 값을
  //   돌려주는 삼항**이라 아무 일도 안 하면서 「표를 특별히 다룬다」 고 말하고 있었다.
  //   표 안에 꽂는 일은 `broker.js` 가 앵커를 보고 직접 한다.
  //
  //   `decorate` 는 표 칸에 `st-translation--cell` 을 붙였는데, 재어 보니 그 비상구가
  //   구해 내는 자리가 **0** 이었다. 표 칸에서 박스가 눕던 것은 `content.css` 의 바탕
  //   규칙이 `display` 를 **선언하지 않아서**였고, 거기 한 줄을 적는 순간 사라졌다.
  //   **증상이 난 자리에 반창고를 붙이면 원인은 그대로 남는다.**
});
