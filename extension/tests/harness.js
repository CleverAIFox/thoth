// 어댑터를 브라우저 없이 돌린다.
//
// ★ `collect` 는 DOM 조작이 본체라 떼어낼 순수 부분이 없다(DECISIONS §39).
//   `state.js` 처럼 chrome API 를 피해 가는 방법이 통하지 않으므로 DOM 을
//   가져온다.
//
// ★ **직접 만든 스텁을 쓰지 않는다.** `querySelectorAll` 에 셀렉터 파서를 다시
//   만들어야 하는데, 그 파서가 브라우저와 다르게 답하면 **테스트가 통과하면서
//   틀린다.** jsdom 은 같은 명세를 구현한 것이라 그 위험이 훨씬 작다(§21).
//
// ★ **`innerText` 는 jsdom 에 없다.** 렌더링이 필요해서다. 어댑터는
//   `innerText || ""` 로 방어하므로 그대로 두면 텍스트가 전부 빈 문자열이 되어
//   **유닛을 하나도 모으지 못한 채 0건으로 통과한다.** 여기서 `textContent` 로
//   채운다.
//
// ★ 그 대체는 정확하지 않다 — `textContent` 는 숨김 요소를 포함하고 `<br>` 을
//   개행으로 만들지 않는다. 그래서 **이 하네스로는 수집 구조만 본다.** 무엇이
//   몇 개 모였는지 · 어떻게 묶였는지 · 어디에 위임했는지가 검사 대상이고,
//   텍스트가 정확히 무엇인지는 브라우저에서 본다(픽스처, MASTER §11-5).
import { JSDOM } from "jsdom";

// ★ 어댑터는 `new Function(src)()` 로 평가되며 그 시점의 전역을 본다.
//   `CSS.escape` 를 `makeDoc` 에서 세우면 이미 늦다 — 어댑터가 먼저 평가되면
//   `CSS` 가 `undefined` 라 `labelOf` 가 조용히 null 을 돌려준다. 모듈이 로드될
//   때 한 번 세워 순서에 기대지 않는다.
{
  const { JSDOM: J } = await import("jsdom");
  globalThis.CSS = new J("").window.CSS;
}

/** 어댑터 파일을 읽어 `globalThis.ST` 에 등록시킨다. */
export async function loadAdapters(names) {
  const { readFileSync } = await import("node:fs");
  const { fileURLToPath } = await import("node:url");
  const { dirname, join } = await import("node:path");
  const here = dirname(fileURLToPath(import.meta.url));

  globalThis.ST = { adapters: [] };
  for (const n of names) {
    const src = readFileSync(join(here, "..", "src", "adapters", `${n}.js`), "utf8");
    // 어댑터는 콘텐츠 스크립트라 모듈이 아니다. 그대로 평가한다 —
    // 최상위 선언이 없으므로(DECISIONS §16) 재평가해도 안전하다.
    new Function(src)();
  }
  return globalThis.ST;
}

/**
 * HTML 로 문서를 만들고 `innerText` 를 채운다.
 *
 * `opts.url` 을 주면 `location` 이 그 주소가 된다. 사이트 어댑터의 `match` 를
 * 실제 호스트로 잴 때 쓴다.
 */
export function makeDoc(html, opts = {}) {
  const dom = new JSDOM(`<!doctype html><body>${html}</body>`, opts.url ? { url: opts.url } : {});
  const win = dom.window;

  // ★ 프로토타입에 정의한다. 개별 요소에 붙이면 나중에 만들어지는 요소가
  //   빠져 검사가 일부만 돈다.
  Object.defineProperty(win.Element.prototype, "innerText", {
    get() { return this.textContent; },
    configurable: true,
  });

  // ★ 브로커는 전역에서 찾는다. jsdom 의 **창 안에만** 있는 것은 못 본다 —
  //   `CSS` 에서 겪은 것과 같은 함정이고, 빠뜨리면 `is not defined` 로 죽거나
  //   더 나쁘게는 조용히 빈손이 된다(DECISIONS §47).
  for (const k of ["MutationObserver", "Node", "Element", "HTMLElement",
                   "getComputedStyle", "requestAnimationFrame", "location"]) {
    if (win[k] !== undefined) globalThis[k] = win[k];
  }
  globalThis.window = win;
  globalThis.document = win.document;
  return win.document;
}

/** 수집 결과를 읽기 쉬운 모양으로. 텍스트는 앞 30자만 본다. */
export function summarize(units) {
  return units.map((u) => ({
    id: u.id,
    group: u.group ?? null,
    text: u.text.slice(0, 30),
    tag: u.el.tagName.toLowerCase(),
  }));
}

/** 그룹별 유닛 수. 그룹이 없는 것은 `null` 키로 모인다. */
export function groupSizes(units) {
  const m = new Map();
  for (const u of units) {
    const k = u.group ?? null;
    m.set(k, (m.get(k) ?? 0) + 1);
  }
  return m;
}

// ---------- 브로커 ----------
//
// ★ 흉내내는 것은 `chrome.storage` 와 `fetch` 둘뿐이다. `document` 는 jsdom 이,
//   타이머는 `node:test` 의 `mock.timers` 가, `MutationObserver` 와
//   `AbortController` 는 각각 jsdom 과 Node 가 이미 한다. **흉내가 적을수록
//   실제와 어긋날 자리가 적다**(DECISIONS §47).
//
// ★ 그래도 흉내인 것은 맞다. 이 하네스로 보는 것은 **판정과 배선**이고,
//   실제 네트워크·렌더링 동작은 픽스처와 실사이트에서 본다.

/** `chrome.storage.local` 최소 구현. 계약이 단순해 어긋날 여지가 작다. */
export function fakeChrome(initial = {}) {
  const store = { ...initial };
  return {
    store,
    api: {
      storage: {
        local: {
          async get(keys) {
            const ks = typeof keys === "string" ? [keys] : keys;
            const out = {};
            for (const k of ks) if (k in store) out[k] = store[k];
            return out;
          },
          async set(obj) { Object.assign(store, obj); },
        },
      },
      runtime: { lastError: null },
    },
  };
}

/**
 * `fetch` 스텁. 응답을 차례로 돌려준다.
 *
 * 각 항목은 `{ ok, status, body }` 이거나 `Error` 다. `Error` 면 던진다 —
 * 네트워크 실패를 그렇게 흉내낸다.
 */
export function fakeFetch(responses) {
  const calls = [];
  const queue = [...responses];
  const fn = async (url, init) => {
    calls.push({ url, body: init?.body ? JSON.parse(init.body) : null,
                 headers: init?.headers ?? {} });
    const r = queue.length > 1 ? queue.shift() : queue[0];
    if (r instanceof Error) throw r;
    // ★ `translations: "echo"` 면 보낸 수만큼 돌려준다. 고정 배열로 두면 배치
    //   크기를 바꾸는 검사에서 길이가 어긋나 `contract_violation` 이 나고,
    //   브로커가 재시도하며 1개씩 쪼개 **엉뚱한 것을 재게 된다.**
    const body = r.body ?? {};
    const n = init?.body ? JSON.parse(init.body).texts.length : 0;
    return {
      ok: r.ok ?? true,
      status: r.status ?? 200,
      async json() {
        if (body.translations === "echo") {
          return { ...body, translations: Array.from({ length: n }, (_, i) => `번역${i}`) };
        }
        return body;
      },
    };
  };
  fn.calls = calls;
  return fn;
}

/**
 * 브로커와 클라이언트를 문서 위에 올린다. 어댑터는 먼저 등록돼 있어야 한다.
 *
 * ★ **브로커는 올라가는 순간 순회를 시작한다.** 실제 타이머로 두면 테스트가
 *   끝나도 `setInterval` 이 남아 프로세스가 죽지 않는다. 잡아서 핸들을
 *   돌려주고, 호출한 쪽이 `stop()` 으로 끊는다.
 *
 * ★ 타이머를 통째로 가짜로 바꾸지 않는다. 그것도 흉내이고, 지금 보려는 것은
 *   주기가 아니라 판정이다. **필요 없는 흉내는 하지 않는다**(DECISIONS §47).
 */
export async function loadBroker() {
  const { readFileSync } = await import("node:fs");
  const { fileURLToPath } = await import("node:url");
  const { dirname, join } = await import("node:path");
  const here = dirname(fileURLToPath(import.meta.url));
  const timers = [];
  const realSI = globalThis.setInterval;
  const realST = globalThis.setTimeout;
  globalThis.setInterval = (fn, ms) => { const t = realSI(fn, ms); timers.push(t); return t; };
  globalThis.setTimeout = (fn, ms) => { const t = realST(fn, ms); timers.push(t); return t; };

  for (const n of ["client", "broker"]) {
    new Function(readFileSync(join(here, "..", "src", `${n}.js`), "utf8"))();
  }

  globalThis.setInterval = realSI;
  globalThis.setTimeout = realST;
  return {
    stop() {
      for (const t of timers) { clearInterval(t); clearTimeout(t); }
      timers.length = 0;
    },
  };
}
