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

/** HTML 로 문서를 만들고 `innerText` 를 채운다. */
export function makeDoc(html) {
  const dom = new JSDOM(`<!doctype html><body>${html}</body>`);
  const win = dom.window;

  // ★ 프로토타입에 정의한다. 개별 요소에 붙이면 나중에 만들어지는 요소가
  //   빠져 검사가 일부만 돈다.
  Object.defineProperty(win.Element.prototype, "innerText", {
    get() { return this.textContent; },
    configurable: true,
  });

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
