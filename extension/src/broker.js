// 어댑터를 고르고, 플레이스홀더를 선점하고, group 단위로 번역을 채운다.
// 사이트 지식은 어댑터에만 있다. 이 파일은 어떤 사이트인지 모른다.
(() => {
  if (globalThis.ST?.__running) return;
  globalThis.ST.__running = true;

  const CLS = "st-translation";
  const MAX_BATCH = 2;   // 로컬 추론은 항목당 수 초다. 통짜로 묶으면 전부 끝날
                         // 때까지 화면이 비어 있다. 쪼개서 점진적으로 채운다.

  // URL 은 번역 대상에서 뺀다. 번역기에 넣으면 경로가 깨지고, 깨진 채로
  // 캐시에 박제된다. 번역 후 클릭 가능한 링크로 따로 되붙인다.
  const URL_RE = /(https?:\/\/[^\s]+)|(www\.[^\s]+)/g;

  const splitUrls = (text) => {
    const urls = text.match(URL_RE) || [];
    return { body: text.replace(URL_RE, "").trim(), urls };
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
    [...globalThis.ST.adapters].sort((a, b) => b.priority - a.priority).find((a) => a.match());

  const chunk = (arr, n) =>
    arr.reduce((acc, x, i) => (i % n ? acc[acc.length - 1].push(x) : acc.push([x]), acc), []);

  const finish = (u, text) => {
    u.node.textContent = text;
    appendLinks(u.node, u.urls);
  };

  const drop = (u) => {
    u.node.remove();
    delete u.el.dataset.stDone;
  };

  async function run() {
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
      const { body, urls } = splitUrls(u.text);
      u.el.dataset.stDone = "1";
      if (!body) continue;          // URL 만 있는 노드는 건너뛴다
      u.body = body;
      u.urls = urls;
      u.node = document.createElement("div");
      u.node.className = CLS;
      u.node.textContent = "…";
      ad.decorate?.(u.node, u);
      u.anchor.insertAdjacentElement("afterend", u.node);
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
        try {
          const out = await globalThis.ST.translate(batch.map((u) => u.body));
          batch.forEach((u, i) => (out[i] ? finish(u, out[i]) : drop(u)));
        } catch (e) {
          console.warn("[st] 번역 실패", e);
          batch.forEach(drop);
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
    if (!e.altKey || e.ctrlKey || e.metaKey || e.key.toLowerCase() !== "k") return;
    const off = document.documentElement.classList.toggle("st-off");
    chrome.storage.local.set({ [KEY]: off });
    console.log("[st] 번역 표시", off ? "끔" : "켬");
  });

  const debounce = (fn, ms) => {
    let t;
    return () => { clearTimeout(t); t = setTimeout(fn, ms); };
  };

  run();
  new MutationObserver(debounce(run, 250)).observe(document.body, {
    childList: true, subtree: true,
  });
  // style·class 변경만으로 나타나는 영역 대비. run 은 stDone 으로 멱등하다.
  setInterval(run, 1500);

  console.log("[st] 브로커 시작 —", pickAdapter()?.name, "· Alt+K 로 표시 전환");
})();
