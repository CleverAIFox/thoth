// 어댑터를 고르고, 플레이스홀더를 선점하고, group 단위로 번역을 채운다.
// 사이트 지식은 어댑터에만 있다. 이 파일은 어떤 사이트인지 모른다.
(() => {
  // generic.js 가 먼저 실행되지만 주입 순서가 어긋날 수 있다. 여기서 세운다.
  const ST = (globalThis.ST ??= {});
  if (ST.__running) return;
  ST.__running = true;

  const CLS = "st-translation";
  const MAX_BATCH = 2;   // 로컬 추론은 항목당 수 초다. 통짜로 묶으면 전부 끝날
                         // 때까지 화면이 비어 있다. 쪼개서 점진적으로 채운다.
                         // 호스팅 엔진으로 옮기면 되돌린다(PLAN §2-2 #13).
  const POLL_MS = 1500;
  const MAX_RETRY = 2;   // 일시 실패의 재시도 횟수. 무한이면 워커를 때린다

  // URL 은 번역 대상에서 뺀다. 번역기에 넣으면 경로가 깨지고, 깨진 채로
  // 캐시에 박제된다. 번역 후 클릭 가능한 링크로 따로 되붙인다.
  const URL_RE = /(https?:\/\/[^\s]+)|(www\.[^\s]+)/g;

  const splitUrls = (text) => {
    const urls = text.match(URL_RE) || [];
    return { body: text.replace(URL_RE, " ").replace(/[ \t]{2,}/g, " ").trim(), urls };
  };

  const appendLinks = (node, urls) => {
    for (const u of urls) {
      const a = document.createElement("a");
      a.href = u.startsWith("http") ? u : `https://${u}`;
      a.textContent = u;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      // innerHTML 을 쓰지 않는다. 원문에 스크립트가 섞여도 실행되지 않는다.
      node.appendChild(document.createTextNode(" "));
      node.appendChild(a);
    }
  };

  const pickAdapter = () =>
    [...(ST.adapters || [])].sort((a, b) => b.priority - a.priority).find((a) => a.match());

  const chunk = (arr, n) =>
    arr.reduce((acc, x, i) => (i % n ? acc[acc.length - 1].push(x) : acc.push([x]), acc), []);

  const finish = (u, text) => {
    if (!u.node.isConnected) return;   // 그 사이 SPA 가 갈아엎었다
    u.node.textContent = text;
    appendLinks(u.node, u.urls);
  };

  // ★ 실패한 자리를 그냥 비우면 안 된다. stDone 을 지우면 다음 순회가 같은
  //   유닛을 다시 수집해 재요청하고, 429 · 413 처럼 재시도로 풀리지 않는
  //   실패에서는 1.5초마다 영원히 워커를 때린다(DECISIONS §12).
  const drop = (u, fatal) => {
    u.node.remove();
    if (fatal) {
      u.el.dataset.stFail = "1";       // 이 세션에서 다시 건드리지 않는다
      delete u.el.dataset.stDone;
      return;
    }
    u.retry = (u.retry || 0) + 1;
    if (u.retry >= MAX_RETRY) {
      u.el.dataset.stFail = "1";
      delete u.el.dataset.stDone;
    } else {
      delete u.el.dataset.stDone;      // 다음 순회에서 한 번 더 본다
    }
  };

  // 상한에 걸렸거나 엔드포인트가 틀린 상태에서 순회를 계속하는 것은 의미가 없다.
  let halted = "";
  let observer = null;
  let poll = 0;
  const halt = (why) => {
    halted = why;
    clearInterval(poll);
    observer?.disconnect();
    console.warn("[st] 중단 —", why, "· 새로고침하면 다시 시도한다");
  };

  let running = false;

  async function run() {
    if (running || halted) return;     // 순회가 겹치면 같은 배치를 두 번 보낸다
    running = true;
    try {
      await pass();
    } finally {
      running = false;
    }
  }

  async function pass() {
    const ad = pickAdapter();
    if (!ad) return;

    let units;
    try {
      units = ad.collect(document) || [];
    } catch (e) {
      console.warn("[st] collect 실패", ad.name, e);
      return;
    }
    if (!units.length) return;

    // await 이전에 동기적으로 자리를 선점한다.
    const live = [];
    for (const u of units) {
      if (u.el.dataset.stDone || u.el.dataset.stFail) continue;
      const { body, urls } = splitUrls(u.text);
      u.el.dataset.stDone = "1";
      if (!body) continue;          // URL 만 있는 노드는 건너뛴다
      u.body = body;
      u.urls = urls;
      u.node = document.createElement("div");
      u.node.className = CLS;
      u.node.textContent = "…";
      ad.decorate?.(u.node, u);
      const anchor = ad.anchorFor ? ad.anchorFor(u.el) : u.anchor;
      // 앵커가 이미 떨어져 나갔으면 꽂을 자리가 없다.
      if (!anchor?.isConnected) { delete u.el.dataset.stDone; continue; }
      if (anchor.matches("td,th")) anchor.appendChild(u.node);
      else anchor.insertAdjacentElement("afterend", u.node);
      live.push(u);
    }
    if (!live.length) return;

    const groups = new Map();
    for (const u of live) {
      const k = u.group ?? `solo:${u.id}`;
      groups.set(k, [...(groups.get(k) || []), u]);
    }

    for (const list of groups.values()) {
      for (const batch of chunk(list, MAX_BATCH)) {
        if (halted) { batch.forEach((u) => drop(u, true)); continue; }
        try {
          const out = await ST.translate(batch.map((u) => u.body));
          batch.forEach((u, i) => (out[i] ? finish(u, out[i]) : drop(u, true)));
        } catch (e) {
          const fatal = e?.fatal === true;
          console.warn("[st] 번역 실패", e?.message || e);
          batch.forEach((u) => drop(u, fatal));
          // 상한 초과는 페이지를 새로 열어도 안 풀린다. 순회를 멈춘다.
          if (e?.code === "quota_exceeded" || e?.code === "guard_unavailable") {
            halt(e.code);
          }
        }
      }
    }
  }

  // 토글은 DOM 요소를 두지 않는다. 고정 위치 버튼은 사이트마다 남의 UI 를 가린다.
  const KEY = "stOff";
  chrome.storage.local.get(KEY).then(({ stOff }) => {
    document.documentElement.classList.toggle("st-off", !!stOff);
  });

  document.addEventListener("keydown", (e) => {
    // e.key 는 레이아웃과 데드키에 흔들린다. 물리 키로 본다.
    if (!e.altKey || e.ctrlKey || e.metaKey || e.code !== "KeyK") return;
    const off = document.documentElement.classList.toggle("st-off");
    chrome.storage.local.set({ [KEY]: off });
    console.log("[st] 번역 표시", off ? "끔" : "켬");
  });

  const debounce = (fn, ms) => {
    let t;
    return () => { clearTimeout(t); t = setTimeout(fn, ms); };
  };

  // style·class 변경만으로 나타나는 영역 대비. run 은 stDone 으로 멱등하다.
  // halt() 가 이 둘을 참조하므로 첫 run() 보다 먼저 세운다.
  observer = new MutationObserver(debounce(run, 250));
  observer.observe(document.body, { childList: true, subtree: true });
  poll = setInterval(run, POLL_MS);
  run();

  console.log("[st] 브로커 시작 —", pickAdapter()?.name, "· Alt+K 로 표시 전환");
})();
