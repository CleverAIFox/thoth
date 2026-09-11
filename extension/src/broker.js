// 어댑터를 고르고, 플레이스홀더를 선점하고, group 단위로 번역을 채운다.
// 사이트 지식은 어댑터에만 있다. 이 파일은 어떤 사이트인지 모른다.
(() => {
  if (globalThis.ST?.__running) return;   // 중복 주입 방지
  globalThis.ST.__running = true;

  const CLS = "st-translation";
  const MAX_BATCH = 20;

  const pickAdapter = () =>
    [...globalThis.ST.adapters].sort((a, b) => b.priority - a.priority).find((a) => a.match());

  const chunk = (arr, n) =>
    arr.reduce((acc, x, i) => (i % n ? acc[acc.length - 1].push(x) : acc.push([x]), acc), []);

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

    // await 이전에 동기적으로 자리를 선점한다. 다음 호출이 같은 노드를 다시 잡지 않는다.
    for (const u of units) {
      u.el.dataset.stDone = "1";
      u.node = document.createElement("div");
      u.node.className = CLS;
      u.node.textContent = "…";
      ad.decorate?.(u.node, u);
      u.anchor.insertAdjacentElement("afterend", u.node);
    }

    // group 별로 묶고, 한 배치가 너무 커지지 않게 자른다.
    const groups = new Map();
    for (const u of units) {
      const k = u.group ?? `solo:${u.id}`;
      groups.set(k, [...(groups.get(k) || []), u]);
    }

    for (const list of groups.values()) {
      for (const batch of chunk(list, MAX_BATCH)) {
        try {
          const out = await globalThis.ST.translate(batch.map((u) => u.text));
          batch.forEach((u, i) => {
            if (out[i]) u.node.textContent = out[i];
            else { u.node.remove(); delete u.el.dataset.stDone; }
          });
        } catch (e) {
          console.warn("[st] 번역 실패", e);
          batch.forEach((u) => { u.node.remove(); delete u.el.dataset.stDone; });
        }
      }
    }
  }

  const debounce = (fn, ms) => {
    let t;
    return () => { clearTimeout(t); t = setTimeout(fn, ms); };
  };
  const debounced = debounce(run, 250);

  run();
  new MutationObserver(debounced).observe(document.body, { childList: true, subtree: true });
  // style·class 변경만으로 나타나는 영역 대비. run 은 stDone 으로 멱등하다.
  setInterval(run, 1500);

  console.log("[st] 브로커 시작 —", pickAdapter()?.name);
})();
