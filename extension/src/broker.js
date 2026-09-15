// 어댑터를 고르고, 플레이스홀더를 선점하고, group 단위로 번역을 채운다.
// 사이트 지식은 어댑터에만 있다. 이 파일은 어떤 사이트인지 모른다.
(() => {
  // generic.js 가 먼저 실행되지만 주입 순서가 어긋날 수 있다. 여기서 세운다.
  const ST = (globalThis.ST ??= {});
  if (ST.__running) return;
  ST.__running = true;

  const CLS = "st-translation";
  // 배치 크기는 엔진에 달렸다. 코드에 박지 않고 chrome.storage 의 stBatch 로
  // 둔다(DECISIONS §80).
  //
  // ★ **3 이 최적점이다.** 로컬 엔진 45유닛 실측에서 위반이 U자를 그린다 —
  //   배치 1·2·3·6·9 에서 9·6·3·5·6 건이다. 양쪽 끝이 다 나쁘고 가운데가
  //   가장 적다(DECISIONS §51).
  //
  // ★ **위로 무너지는 것과 아래로 무너지는 것은 원인이 다르다.** 크면 프롬프트가
  //   길어져 용어집이 묻히고(§20), 작으면 `BATCH_RULE` 이 빠져 규칙 4·5 를
  //   붙들던 것이 풀린다 — 배치 1 에서 물음표 소실 2 · 문체 2 · 길이 2.95배가
  //   돌아왔다. 한 숫자로 재면 U자지만 원인은 둘이다.
  //
  // ★ **묶는 이득이 속도가 아니라 문맥이다.** ollama 는 슬롯 하나로 직렬
  //   처리하므로 묶어도 GPU 에서 다시 줄을 선다(MASTER §7-1). 로컬은 왕복도
  //   공짜다. 얻는 것은 같은 문항의 보기들이 한 프롬프트에 들어가 용어가
  //   저절로 맞는 것뿐이고, 3 이면 문제+보기 둘 또는 보기 셋이 묶인다.
  //
  // ★ **이 값은 로컬 기준이다.** 호스팅은 왕복이 수백 ms 라 묶는 것이 곧
  //   비용이고 컨텍스트도 크다. `bedrock` 확정 후 다시 잰다.
  let MAX_BATCH = 3;
  const MAX_BATCH_CAP = 50;   // 워커 계약의 texts 상한
  const POLL_MS = 1500;
  const POLL_MAX = 12000;   // 새 유닛이 없으면 여기까지 늘린다
  const MAX_RETRY = 2;   // 일시 실패의 재시도 횟수. 무한이면 워커를 때린다

  // ★ 대상 언어와 같은 문자로 쓰인 텍스트는 번역 대상이 아니다. 한 페이지
  //   안에 언어가 섞이므로(구글 폼의 안내문 · Udemy 의 UI) 사이트나 페이지
  //   단위로 정할 수 없고, 유닛마다 본다.
  //
  //   언어 '감지' 를 하지 않는다. 감지는 짧은 문장에서 자주 틀리고 API 를
  //   쓰면 항목마다 왕복이 는다. 대신 '제외' 만 한다 — 한글 비율이 높으면
  //   번역해도 얻을 것이 없다는 확정적 사실이라 판정이 필요 없다.
  const HANGUL = /[가-힣ㄱ-ㅎㅏ-ㅣ]/g;
  const LETTER = /[\p{L}]/gu;
  const KO_RATIO = 0.3;        // 이 이상이 한글이면 번역하지 않는다

  const alreadyKorean = (text) => {
    const letters = (text.match(LETTER) || []).length;
    if (!letters) return true;              // 숫자·기호뿐이면 번역할 것이 없다
    return (text.match(HANGUL) || []).length / letters >= KO_RATIO;
  };

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
    // ★ 재시도 횟수를 유닛 객체에 두면 안 된다. 유닛은 순회마다 collect 가
    //   새로 만들므로 카운터가 매번 0 으로 리셋되고, 상한이 영영 안 걸린다.
    //   §12 에서 "실패를 잊는 재시도는 폭주" 라 적고 횟수를 잊는 코드를
    //   남겼다. 상태는 순회를 넘겨 사는 곳 — DOM 요소 — 에 둔다.
    const n = (Number(u.el.dataset.stRetry) || 0) + 1;
    u.el.dataset.stRetry = String(n);
    delete u.el.dataset.stDone;
    if (n >= MAX_RETRY) u.el.dataset.stFail = "1";
  };

  // 상한에 걸렸거나 엔드포인트가 틀린 상태에서 순회를 계속하는 것은 의미가 없다.
  let halted = "";
  let observer = null;
  let poll = 0;
  let streak = 0;          // 연속 실패. 워커가 꺼져 있으면 계속 때릴 이유가 없다
  const MAX_STREAK = 3;

  // ★ 판정을 `catch` 안에 두지 않는다. 한 블록에서 세 가지를 정하면서 —
  //   자리를 영구히 버릴지 · 순회를 멈출지 · 연속 실패를 셀지 — 상태를 셋
  //   건드리면, 읽어서는 어느 경우에 무엇이 되는지 알기 어렵다. 입력과 출력만
  //   있는 함수로 떼어 두면 브라우저 없이 검사된다(DECISIONS §48).
  //
  // ★ `ST` 에 붙이는 이유는 이 파일이 주입되는 클래식 스크립트라 `export` 를
  //   쓸 수 없기 때문이다. 최상위 선언도 아니므로 재주입에 안전하다(§16).
  globalThis.ST.failureAction = (err, n) => {
    const code = err?.code || "";
    const fatal = err?.fatal === true;
    // 상한 초과 · 카운터 불통은 페이지를 새로 열어도 안 풀린다. 센 횟수는
    // 의미가 없으므로 0 으로 둔다.
    if (code === "quota_exceeded" || code === "guard_unavailable") {
      return { fatal, halt: code, streak: 0 };
    }
    const next = n + 1;
    // 워커 미기동 · 엔드포인트 오류. 꺼진 워커를 1.5초마다 때릴 이유가 없다.
    return { fatal, halt: next >= MAX_STREAK ? "worker_unreachable" : "", streak: next };
  };
  let idle = 0;            // 연속으로 아무것도 못 찾은 순회 수
  let relaxed = false;     // 주기를 이미 늘렸는가
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

    // ★ 수집이 계속 비면 주기를 늘린다. 정적인 페이지에서 1.5초마다 DOM 을
    //   훑을 이유가 없다. MutationObserver 가 변화를 놓치지 않으므로 주기는
    //   style·class 로만 나타나는 영역에 대한 보험일 뿐이다.
    if (idle >= 4 && poll && !relaxed) {
      clearInterval(poll);
      poll = setInterval(run, POLL_MAX);
      relaxed = true;
      console.debug("[st] 순회 주기 완화 —", POLL_MAX, "ms");
    }

    let units;
    try {
      units = ad.collect(document) || [];
    } catch (e) {
      console.warn("[st] collect 실패", ad.name, e);
      return;
    }
    if (!units.length) { idle++; return; }
    idle = 0;

    // await 이전에 동기적으로 자리를 선점한다.
    const live = [];
    for (const u of units) {
      if (u.el.dataset.stDone || u.el.dataset.stFail) continue;
      const { body, urls } = splitUrls(u.text);
      u.el.dataset.stDone = "1";
      if (!body) continue;          // URL 만 있는 노드는 건너뛴다
      if (alreadyKorean(body)) continue;   // 이미 한국어다
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
          const { translations: out, partial } = await ST.translate(batch.map((u) => u.body));
          streak = 0;
          batch.forEach((u, i) => (out[i] ? finish(u, out[i]) : drop(u, true)));
          // ★ 부분 응답은 200 이지만 사유는 재시도로 풀리지 않는다. 여기서
          //   멈추지 않으면 캐시 히트만 계속 받으면서 1.5초마다 워커를 때린다
          //   (DECISIONS §12). 받은 번역은 이미 위에서 채웠다.
          if (partial) halt(partial);
        } catch (e) {
          console.warn("[st] 번역 실패", e?.message || e);
          const act = globalThis.ST.failureAction(e, streak);
          streak = act.streak;
          batch.forEach((u) => drop(u, act.fatal));
          if (act.halt) halt(act.halt);
        }
      }
    }
  }

  // 토글은 DOM 요소를 두지 않는다. 고정 위치 버튼은 사이트마다 남의 UI 를 가린다.
  const KEY = "stOff";
  chrome.storage.local.get([KEY, "stBatch"]).then(({ stOff, stBatch }) => {
    document.documentElement.classList.toggle("st-off", !!stOff);
    const n = Number(stBatch);
    if (Number.isInteger(n) && n >= 1) MAX_BATCH = Math.min(n, MAX_BATCH_CAP);
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
  observer = new MutationObserver(debounce(() => {
    if (poll && relaxed) {
      clearInterval(poll);
      poll = setInterval(run, POLL_MS);
      relaxed = false;
    }
    idle = 0;
    run();
  }, 250));
  observer.observe(document.body, { childList: true, subtree: true });
  poll = setInterval(run, POLL_MS);
  run();

  console.log("[st] 브로커 시작 —", pickAdapter()?.name, "· Alt+K 로 표시 전환");
})();
