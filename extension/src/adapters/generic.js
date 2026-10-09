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
// ── 무엇이 한 단위인가 (DECISIONS §174) ──────────────────────────────────────
//
// ★ **정본은 모질라의 페이지 번역이다**(`mozilla/firefox-translations` 의
//   `extension/view/js/InPageTranslation.js`). 파이어폭스에 실려 나간 코드이고, 이 물음을
//   이미 풀어 두었다. **추측으로 짓지 않는다**(§294) — 받아서 읽고 옮겼다.
//
// ★ **묻는 것이 「무슨 태그인가」 도 「몇 글자인가」 도 아니다.** 직계 자식을 세어
//   **「이게 문단인가, 문단을 담는 상자인가」** 를 묻는다. 그래서 태그 목록이 필요 없다 —
//   §160 에서 `div` 가 후보에 없어 **본문이 통째로 사각**이었던 것은 고정 목록의 필연이다.
//   목록을 늘리는 것은 그 다음 사이트까지만 맞다.

/** 인라인으로 세는 태그. 글의 **안쪽 꾸밈**이지 새 덩이가 아니다. */
globalThis.ST.인라인태그 = new Set([
  "abbr", "b", "bdi", "bdo", "br", "cite", "code", "data", "del", "dfn", "em", "i",
  "ins", "kbd", "mark", "q", "rp", "rt", "ruby", "s", "samp", "small", "strong",
  "sub", "sup", "time", "u", "var", "wbr",
]);

/** **제 안을 보고 정하는** 태그. `<a>` 는 버튼일 때도 있고 글 속 링크일 때도 있다. */
globalThis.ST.일반태그 = new Set(["a", "span"]);

/** 통째로 안 보는 태그. 번역해도 뜻이 없거나 깨진다. */
globalThis.ST.제외태그 = new Set([
  "script", "style", "noscript", "template", "svg", "math", "canvas", "iframe",
  "code", "kbd", "samp", "var", "pre", "textarea", "input", "select", "option",
  "button", "nav", "header", "footer", "address", "form",
]);

/** 판정 셋. `TreeWalker` 의 `NodeFilter` 와 같은 뜻이고 **수로 두어 jsdom 없이 시험한다.** */
globalThis.ST.받다 = 1;    // 이 서브트리 통째로 한 단위. 아래로 안 내려간다
globalThis.ST.파다 = 2;    // 이건 단위가 아니다. 더 파고든다
globalThis.ST.버리다 = 3;  // 이것도 아래도 전부 버린다

/**
 * **이 노드가 글의 그릇인가, 그릇들의 그릇인가.**
 *
 * ★ **직계 자식만 센다.** 손자까지 세면 문서 전체가 한 단위가 된다.
 * ★ **같으면 글 쪽으로 본다**(`>=`). 모질라와 같다 — 글 하나에 블록 하나가 섞인
 *   꼴(`<div>글<hr></div>`)은 문단으로 다루는 편이 덜 쪼갠다.
 * @param {Node} node
 * @returns {boolean}
 */
globalThis.ST.안이글인가 = function (node) {
  if (node.nodeType === 3) return true;            // 글 노드
  let 인라인 = 0, 블록 = 0;
  for (const c of node.childNodes || []) {
    if (c.nodeType === 3) { if (c.textContent.trim()) 인라인 += 1; continue; }
    if (c.nodeType !== 1) continue;
    const t = c.nodeName.toLowerCase();
    if (globalThis.ST.인라인태그.has(t)) 인라인 += 1;
    else if (globalThis.ST.일반태그.has(t) && globalThis.ST.안이글인가(c)) 인라인 += 1;
    else 블록 += 1;
  }
  return 인라인 >= 블록;
};

/**
 * **웹 표준이 「번역하지 말라」 고 말하는 자리.**
 *
 * ★ **이 셋이 공짜로 따라온다** — 구글 번역도 지키는 신호다.
 *     `[translate=no]` · `.notranslate` · `[lang]` 이 대상 언어와 다를 때
 * ★ **`lang` 이 중요하다.** 이미 한국어인 토막을 다시 번역하는 일이 여기서 끊긴다 —
 *   종전에는 글자 비율(`alreadyKorean`)로만 걸렀고 그것은 **섞인 글에서 샌다.**
 */
globalThis.ST.제외인가 = function (node) {
  if (node.nodeType !== 1) return false;
  if (globalThis.ST.제외태그.has(node.nodeName.toLowerCase())) return true;
  if (node.getAttribute && node.getAttribute("translate") === "no") return true;
  if (node.classList && node.classList.contains("notranslate")) return true;
  if (node.hasAttribute && node.hasAttribute("contenteditable")) return true;
  return false;
};

/**
 * **이미 대상 언어로 적힌 토막인가 — 단위에서만 묻는다**(DECISIONS §176).
 *
 * ★ **가지째 자르면 안 된다.** 2026-10-09 지메일에서 수집이 **0건**이었다. `<html lang="ko">`
 *   (사용자 UI 가 한국어다) 하나에서 끊기고 **문서 전체가 제외**됐다. 영어 메일 본문은
 *   제 `lang` 이 없어 앱 껍데기의 `ko` 를 뒤집어쓴다.
 * ★ **모질라에서 베끼며 뜻을 뒤집었다.** 그쪽은 「**출발어와 다른** `lang` 을 제외」 이고
 *   전체 페이지 번역이라 `html lang` 이 곧 출발어다. 이쪽은 「**대상어와 같은** `lang` 」
 *   으로 적었는데, **앱 껍데기의 UI 언어가 대상어인 판**에서는 그것이 문서를 통째로 죽인다.
 * ★ **`lang` 은 그 글의 언어를 말하지, 그 안에 든 남의 글의 언어를 말하지 않는다.**
 *   그래서 **받으려는 그 노드에서만** 묻는다 — 내려가는 길에서는 묻지 않는다.
 */
globalThis.ST.대상어인가 = function (node, 대상 = "ko") {
  if (!node.getAttribute) return false;
  const lang = node.getAttribute("lang");
  return !!lang && lang.toLowerCase().split("-")[0] === 대상;
};

/** 글이 번역할 만큼 있나. **단위 판정이 아니라 표시 정책이다** — 아래 주석을 본다. */
globalThis.ST.최소글자 = 20;

/**
 * 한 노드의 판정. **DOM 을 읽지만 레이아웃은 안 읽는다** — jsdom 으로 전부 시험한다.
 *
 * ★ **`최소글자` 는 여기서만 쓴다.** 이것은 **「문단인가」 와 아무 상관이 없다** —
 *   짧은 문단도 문단이다. 다만 이 확장은 **덧붙이는** 쪽이라 「확인」 같은 두 글자에
 *   상자를 세우면 화면이 상자로 덮인다. **갈아끼우는 제품에는 이 줄이 없다**(모질라).
 *   그래서 단위 고르기(`안이글인가`)와 **분리해서** 맨 끝에 둔다.
 * ★ **못 받은 것을 버리지 않는다.** 짧아도 **그 아래는 더 판다** — 짧은 포장 안에
 *   긴 글이 있는 꼴이 메일에 흔하다.
 */
globalThis.ST.판정 = function (node) {
  const ST = globalThis.ST;
  if (node.nodeType !== 1) return ST.버리다;
  if (ST.제외인가(node)) return ST.버리다;
  if (node.textContent.trim().length === 0) return ST.버리다;
  if (!ST.안이글인가(node)) return ST.파다;
  // ★ **`lang` 은 여기서만 묻는다**(§176) — 위에서 물으면 `<html lang="ko">` 가 문서를 죽인다.
  if (ST.대상어인가(node)) return ST.버리다;
  // ★ **짧으면 아래도 반드시 짧다.** `textContent` 는 자손을 합한 값이라 **여기서 짧은
  //   가지에 긴 글이 숨어 있을 수 없다** — 처음에 `파다` 로 적었는데 돌연변이가
  //   **그 줄이 아무 일도 안 한다**고 말해 줬다. 「더 판다」 는 **할 수 없는 약속**이었다.
  if (node.textContent.trim().length < ST.최소글자) return ST.버리다;
  return ST.받다;
};

// 상위 계층이 재사용한다. 어댑터가 배타 선택이므로, 상위 계층이 자기 몫만
// 모으면 본문이 통째로 빠진다(DECISIONS §11).
globalThis.ST.genericCollect = function (root, opts) {
  const ST = globalThis.ST;
  const skipRoots = (opts && opts.skip) || [];
  const out = [];

  // ★ **`TreeWalker` 가 아니라 직접 판다.** `TreeWalker` 의 `FILTER_ACCEPT` 는 **자손으로
  //   계속 내려간다** — 모질라가 `isParentQueued` 로 다시 막는 까닭이다. 직접 파면
  //   **받은 자리에서 멈추는 것이 한 줄**이고, 멈췄다는 사실이 코드에 보인다.
  const 판다 = (el) => {
    for (const c of el.children) {
      if (skipRoots.some((r) => r === c || r.contains(c))) continue;
      if (c.dataset && (c.dataset.stDone || c.dataset.stFail)) {
        // ★ **처리된 노드는 **그 자신만** 건너뛴다.** 종전에는 셀렉터에서 통째로
        //   빼서 **그 아래가 영영 안 보였고**, 그래서 순회를 넘어선 판단이 불가능했다.
        판다(c);
        continue;
      }
      if (c.classList && c.classList.contains("st-translation")) continue;
      const 몫 = ST.판정(c);
      if (몫 === ST.버리다) continue;
      if (몫 === ST.파다) { 판다(c); continue; }
      const text = (c.innerText !== undefined ? c.innerText : c.textContent).trim();
      if (!text) continue;
      // ★ **받은 자리에서 멈춘다 — 여기서 `판다(c)` 를 안 부르는 것이 전부다.**
      //   모질라는 `TreeWalker` 를 쓰는데 그쪽의 `FILTER_ACCEPT` 는 **자손으로 계속
      //   내려가서** `isParentQueued` 로 다시 막아야 한다. 직접 파면 그 가드가 필요 없다 —
      //   처음에 그 가드를 따라 적었다가 **돌연변이가 죽은 줄이라고 알려 줬다.**
      out.push({ id: "g" + out.length, text, el: c, anchor: c, group: null });
    }
  };
  판다(root);
  return ST.한행에하나(ST.행안의포함을_뺀다(out));
};

// ★ **한 행 안에서 남의 글을 통째로 품은 것은 모으지 않는다**(DECISIONS §165).
//   2026-10-05 지메일 받은편지함에서 **한 행에 상자가 둘** 떴다 — 하나는 제목만,
//   하나는 `보낸사람 + 제목 + 시각 + 본문 앞머리` 를 통째로. 뒤엣것이 앞엣것을 품는다.
//   §160 이 `표 안의 표`(조상-자손)는 `BLOCK` 으로 막았는데, 이쪽은 **둘 다 말단**이고
//   **형제**다 — 그 가름으로는 안 보인다.
// ★ **품은 쪽을 버린다.** 그쪽에는 보낸사람·시각이 섞여 있어 번역이 더 나쁘다.
// ★ **밖 — 행이 없으면 아무것도 안 버린다.** 문서 본문에서 같은 문장이 두 번 나오는 것은
//   정상이고, 그것까지 지우면 **글이 사라진다.** 행이라는 울타리 안에서만 묻는다.
globalThis.ST.행안의포함을_뺀다 = function (units) {
  const 행경계 = globalThis.ST.행경계 || "tr,[role=row]";
  const 납작 = (s) => s.replace(/\s+/g, " ").trim();
  const 행 = units.map((u) => (typeof u.el.closest === "function" ? u.el.closest(행경계) : null));
  const 버린다 = new Set();
  for (let i = 0; i < units.length; i++) {
    if (!행[i]) continue;
    const a = 납작(units[i].text);
    for (let j = 0; j < units.length; j++) {
      if (i === j || 행[j] !== 행[i]) continue;
      const b = 납작(units[j].text);
      if (a.length > b.length && a.includes(b)) { 버린다.add(i); break; }
    }
  }
  return units.filter((_, i) => !버린다.has(i));
};

/**
 * **한 목록 행에는 번역이 하나다**(DECISIONS §174).
 *
 * ★ **이것은 「중복인가」 를 묻는 규칙이 **아니다**.** 글자를 비교하지 않는다 —
 *   **표시 정책**이다. 목록 행은 **훑는 자리**지 읽는 자리라서, 한 행이 번역을 둘 받으면
 *   그 순간 격자가 깨진다. 어느 쪽이 더 나은가는 `행안의포함을_뺀다` 가 **한 순회 안에서**
 *   정하고, 이 함수는 **순회를 넘어** 둘째가 서는 것을 막는다.
 * ★ **수미상관을 안 건드린다.** 행이 없으면 아무 일도 안 한다. 같은 글이 두 번 나오는
 *   것은 **버릴 일이 아니다** — 그 가름을 글자로 하려 했던 것이 틀린 길이었다.
 * ★ **DOM 에 묻는다.** `data-st-done` 은 노드마다의 표식이라 **순회를 넘으면 짝이 안
 *   보인다.** 행에 상자가 이미 섰는지는 **DOM 이 순회를 넘어 들고 있는 사실**이다.
 */
globalThis.ST.한행에하나 = function (units) {
  const 행경계 = globalThis.ST.행경계 || "tr,[role=row]";
  const 찬행 = new Set();
  const out = [];
  for (const u of units) {
    const 행 = typeof u.el.closest === "function" ? u.el.closest(행경계) : null;
    if (!행) { out.push(u); continue; }          // 행 밖 — 아무것도 안 한다
    // 이미 이 행에 번역이 서 있나. 상자는 행 안에 있거나 **행 바로 다음 줄**에 있다(§165).
    const 섰나 = 행.querySelector(".st-translation")
      || (행.nextElementSibling && 행.nextElementSibling.classList
          && 행.nextElementSibling.classList.contains("st-translation-row"));
    if (섰나 || 찬행.has(행)) continue;
    찬행.add(행);
    out.push(u);
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
