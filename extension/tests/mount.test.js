// 어디에 꽂을 것인가 — **수로만 고른다**(DECISIONS §165).
//
// ★ **레이아웃이 없는 곳에서 레이아웃을 시험한다.** jsdom 에는 폭이 없다. 그래서
//   고르는 자를 **순수 함수**로 떼어 두고 **수를 합성으로 먹인다** — `cssFaults` 가
//   2026-09-16 에 세운 꼴 그대로다(§132). 실제 노드를 재는 쪽(`꽂을자리`)은 얇다.
//
// ★ **수는 실측이다.** 2026-10-05 지메일 받은편지함, 상자 스물둘 :
//     TD[gridcell] 200 · 318 · TR[row] 694 · DIV[link] 308 overflow:hidden
//   그 자리에 꽂으면 147px 폭에 222px 높이로 서고(세로 기둥), 행 다음에 꽂으면
//   694px 폭에 61px 다. **3.6배다.**
import assert from "node:assert/strict";
import { test } from "node:test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const 뿌리 = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
globalThis.ST = {};
new Function(fs.readFileSync(path.join(뿌리, "src/cssaudit.js"), "utf8"))();
const ST = globalThis.ST;

const 칸 = (폭, opt = {}) => ({ 폭, 잘림: !!opt.잘림, 행인가: !!opt.행 });

test("지메일 실측 — 칸을 지나 행을 고른다", () => {
  // TD 200 → TR 694. 칸이 280 보다 좁지만 **폭 때문이 아니라 행이 있어서** 행을 고른다.
  const 뽑 = ST.고른다([칸(200), 칸(694, { 행: true })]);
  assert.deepEqual(뽑, { 자리: 1, 꼴: "행다음" });
});

test("행은 칸보다 넓어도 이긴다", () => {
  // ★ **폭만 보면 318 짜리 칸을 고른다.** 그 칸은 행 높이가 40px 이라 **넓어도 겹친다** —
  //   이것이 「덮지 말고 밀어라」 의 코드 꼴이다.
  const 뽑 = ST.고른다([칸(318), 칸(694, { 행: true })]);
  assert.equal(뽑.꼴, "행다음");
  assert.equal(뽑.자리, 1);
});

test("행이 없으면 가장 가까운 쓸 만한 자리다", () => {
  // ★ **가장 넓은 자리를 고르면 `body` 까지 올라간다.** 글은 제 문단 옆에 서야 한다.
  const 뽑 = ST.고른다([칸(120), 칸(600), 칸(1200)]);
  assert.deepEqual(뽑, { 자리: 1, 꼴: "형제" });
});

test("잘리는 자리는 건너뛴다", () => {
  // DIV[link] 308 overflow:hidden — 넣으면 잘린다
  const 뽑 = ST.고른다([칸(308, { 잘림: true }), 칸(600)]);
  assert.deepEqual(뽑, { 자리: 1, 꼴: "형제" });
});

test("쓸 만한 자리가 없으면 안 꽂는다", () => {
  // ★ **못 꽂는 것도 답이다**(DECISIONS §59). 억지로 꽂은 것이 그 세로 기둥이다 —
  //   147px 에 222자를 밀어 넣으면 한 글자씩 세로로 쌓인다.
  assert.equal(ST.고른다([칸(147), 칸(200), 칸(260)]), null);
  assert.equal(ST.고른다([칸(1200, { 잘림: true })]), null);
  assert.equal(ST.고른다([]), null);
});

test("최소폭이 글자 수가 아니라 폭이다", () => {
  assert.equal(ST.고른다([칸(ST.최소폭)]).꼴, "형제");
  assert.equal(ST.고른다([칸(ST.최소폭 - 1)]), null);
});

test("행 경계에 li 가 없다", () => {
  // ★ **오늘 잰 병만 고친다**(§133). 지메일은 `tr` 이고, `li` 까지 넣으면 Udemy 쪽
  //   자리가 같이 바뀐다. **안 보는 꼴이라고 적어 둔다** — 안 적으면 본다고 믿는다(§73).
  assert.ok(!ST.행경계.includes("li"));
  assert.ok(ST.행경계.includes("tr") && ST.행경계.includes("[role=row]"));
});

// ── 노드를 재는 쪽(DECISIONS §165) ───────────────────────────────────────────
//
// ★ **얇게 두되 안 돌면 없는 것이다**(§255). 고르는 규칙은 위에서 순수하게 물었고,
//   여기서는 **그 규칙에 무엇을 먹이는가**를 본다 — 폭을 어디서 읽는지 · 행에서
//   멈추는지 · 아홉 칸에서 끊는지.
let JSDOM = null;
try { ({ JSDOM } = await import("jsdom")); } catch { /* 아래에서 skip */ }
const 돔필요 = { skip: JSDOM ? false : "jsdom 이 없다 — npm install (extension/)" };

function 창(html, 폭표) {
  const dom = new JSDOM(`<!doctype html><body>${html}</body>`);
  const win = dom.window;
  Object.defineProperty(win.Element.prototype, "clientWidth", {
    get() { return 폭표[this.dataset.w] ?? 0; }, configurable: true,
  });
  globalThis.getComputedStyle = (el) => ({
    overflow: el.dataset.ov || "visible", overflowX: el.dataset.ov || "visible",
  });
  return win.document;
}

test("실물 꼴 — 칸에서 시작해 행을 고른다", 돔필요, () => {
  const doc = 창(`<table><tbody><tr data-w="행"><td data-w="칸"><span data-w="글">x</span></td></tr></tbody></table>`,
                 { 글: 0, 칸: 200, 행: 694 });
  const 뽑 = ST.꽂을자리(doc.querySelector("span"));
  assert.equal(뽑.꼴, "행다음");
  assert.equal(뽑.자리.tagName, "TR");
});

test("행에서 멈춘다 — 더 올라가지 않는다", 돔필요, () => {
  // ★ 행 위의 `table` 과 `body` 는 **읽지도 않는다.** 읽으면 깊은 사이트에서
  //   `body` 까지 올라가고, 거기 꽂은 박스는 제 글과 아무 상관이 없다.
  const doc = 창(`<table data-w="표"><tbody><tr data-w="행"><td data-w="칸"><span data-w="글">x</span></td></tr></tbody></table>`,
                 { 글: 0, 칸: 200, 행: 694, 표: 9999 });
  assert.equal(ST.꽂을자리(doc.querySelector("span")).자리.tagName, "TR");
});

test("잘리는 조상을 건너뛰고 행을 고른다", 돔필요, () => {
  const doc = 창(`<table><tbody><tr data-w="행"><td data-w="칸"><div data-w="링크" data-ov="hidden"><span data-w="글">x</span></div></td></tr></tbody></table>`,
                 { 글: 0, 링크: 308, 칸: 318, 행: 694 });
  assert.equal(ST.꽂을자리(doc.querySelector("span")).꼴, "행다음");
});

test("행이 없고 좁기만 하면 null 이다", 돔필요, () => {
  const doc = 창(`<div data-w="겉"><span data-w="글">x</span></div>`, { 글: 0, 겉: 147 });
  assert.equal(ST.꽂을자리(doc.querySelector("span")), null);
});
