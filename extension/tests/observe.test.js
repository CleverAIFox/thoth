// 사이트 어댑터의 관측 행(PLAN §2-4 #25).
//
// ★ **마크업은 픽스처에서 읽는다.** `fixtures/udemy.html` 의 `<template>` 이 브라우저
//   검사와 이 검사의 공통 입력이다. 여기에 HTML 을 따로 적으면 두 곳에 살고
//   한쪽만 고쳐진다(DECISIONS §14).
//
// ★ **판정을 검사하지 않는다.** 관측은 수만 세고 깨짐은 읽을 때 가른다
//   (DECISIONS §102). 여기서 보는 것은 **화면마다 수가 기대대로 나오는가**다.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

let harness = null;
try {
  harness = await import("./harness.js");
} catch {
  // jsdom 미설치
}
const need = { skip: harness ? false : "jsdom 이 없다 — npm install (extension/)" };

const FIXTURE = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), "fixtures", "udemy.html"), "utf8");
const QUIZ_URL = /name="st-fixture-url" content="([^"]+)"/.exec(FIXTURE)[1];

/** 픽스처의 한 화면을 문서로. `data-url` 이 있으면 그 주소인 척한다. */
function screen(mode, { host } = {}) {
  const m = new RegExp(`<template id="t-${mode}"([^>]*)>([\\s\\S]*?)</template>`).exec(FIXTURE);
  assert.ok(m, `픽스처에 ${mode} 화면이 없다`);
  const url = /data-url="([^"]+)"/.exec(m[1])?.[1] || QUIZ_URL;
  const meta = `<meta name="st-fixture-url" content="${url}">`;
  return harness.makeDoc(meta + m[2], host ? { url: host } : {});
}

async function udemy() {
  const ST = await harness.loadAdapters(["generic", "udemy"]);
  return { ST, ad: ST.adapters.find((a) => a.name === "udemy") };
}

test("픽스처가 로컬에서 Udemy 인 척한다", need, async () => {
  const { ad } = await udemy();
  screen("before");
  assert.ok(ad.match(), "meta 가 먹어야 어댑터를 사이트 없이 잰다");
});

test("남의 호스트에서는 fixture meta 를 무시한다", need, async () => {
  // ★ 이것이 없으면 아무 사이트나 meta 한 줄로 어댑터를 바꾼다.
  const { ST, ad } = await udemy();
  screen("before", { host: "https://evil.example/page" });
  assert.equal(ST.pageUrl(), "https://evil.example/page");
  assert.equal(ad.match(), false);
});

test("채점 전 — 문제 하나 · 보기 넷", need, async () => {
  const { ad } = await udemy();
  const doc = screen("before");
  const o = ad.observe(doc);
  assert.equal(o.kind, "quiz");
  assert.equal(o.expected, true);
  assert.deepEqual(o.probes, { scope: 1, prompt: 1, answer_before: 4, answer_after: 0, explanation: 0 });
  assert.equal(ad.collect(doc).length, 5, "관측이 센 것과 수집이 모은 것이 같아야 한다");
});

test("채점 후 — 보기 넷 · 해설 넷", need, async () => {
  const { ad } = await udemy();
  const o = ad.observe(screen("after"));
  assert.deepEqual(o.probes, { scope: 1, prompt: 1, answer_before: 0, answer_after: 4, explanation: 4 });
});

test("시작 화면 — 문제가 없는 것이 정상이다", need, async () => {
  // ★ 쓸 때 \"prompt 0 이면 깨짐\" 으로 박았다면 여기서 오탐이 난다(DECISIONS §102).
  const { ad } = await udemy();
  const o = ad.observe(screen("start"));
  assert.equal(o.expected, true);
  assert.equal(o.probes.scope, 1);
  assert.equal(o.probes.prompt, 0);
});

test("스코프 이름이 바뀌면 전부 0 이고 글은 남는다", need, async () => {
  const { ST, ad } = await udemy();
  const doc = screen("renamed-scope");
  const o = ad.observe(doc);
  assert.deepEqual(o.probes, { scope: 0, prompt: 0, answer_before: 0, answer_after: 0, explanation: 0 });
  assert.equal(ad.collect(doc).length, 0, "어댑터는 아무것도 못 모은다");
  assert.ok(ST.textBlocks(doc) >= 5, "그런데 페이지에는 글이 있다 — 이 차이가 깨짐의 신호다");
});

test("문제 셀렉터만 바뀌면 보기는 잡히고 문제만 빠진다", need, async () => {
  const { ad } = await udemy();
  const doc = screen("renamed-prompt");
  const o = ad.observe(doc);
  assert.equal(o.probes.prompt, 0);
  assert.equal(o.probes.answer_before, 4);
  assert.equal(ad.collect(doc).length, 4);
});

test("퀴즈 경로가 아니면 기대하지 않는다", need, async () => {
  const { ad } = await udemy();
  const o = ad.observe(screen("landing"));
  assert.equal(o.kind, "other");
  assert.equal(o.expected, false);
});

test("번역 박스는 글 덩어리로 세지 않는다", need, async () => {
  const { ST } = await udemy();
  const doc = harness.makeDoc(`
    <p>This paragraph is long enough to count as a block of text.</p>
    <div class="st-translation"><p>이 문단은 번역 박스 안에 있어 세지 않는다 twenty chars.</p></div>`);
  assert.equal(ST.textBlocks(doc), 1);
});

// ---------- 브로커 ----------

async function brokerOn(mode) {
  const { ST } = await udemy();
  ST.SETTLE_MS = 0;          // 자동 관측을 끄고 손으로 부른다
  const doc = screen(mode);
  globalThis.chrome = harness.fakeChrome().api;
  globalThis.fetch = harness.fakeFetch([{ ok: true, body: { translations: "echo" } }]);
  const b = await harness.loadBroker();
  return { ST, doc, b };
}

test("같은 페이지 · 같은 수면 행을 다시 만들지 않는다", need, async () => {
  const { ST, b } = await brokerOn("before");
  try {
    const first = ST.observe("manual");
    assert.ok(first, "첫 관측은 행이 된다");
    assert.equal(first.k, "obs");
    assert.equal(first.adapter, "udemy");
    assert.equal(ST.observe("manual"), null, "바뀐 것이 없으면 행이 없다");
    assert.equal(ST.observations.length, 1);
  } finally {
    b.stop();
  }
});

test("세션 중에 셀렉터가 빠지면 새 행이 생긴다", need, async () => {
  const { ST, doc, b } = await brokerOn("before");
  try {
    ST.observe("manual");
    const m = /<template id="t-renamed-scope"[^>]*>([\s\S]*?)<\/template>/.exec(FIXTURE);
    doc.querySelector(".quiz-page-content").outerHTML = m[1];
    const rec = ST.observe("manual");
    assert.ok(rec, "수가 바뀌었으니 행이 생긴다");
    assert.equal(rec.probes.scope, 0);
    assert.ok(rec.blocks > 0);
  } finally {
    b.stop();
  }
});

test("행에 경로를 싣지 않는다", need, async () => {
  // 강의 slug 와 id 가 경로에 있다.
  const { ST, b } = await brokerOn("before");
  try {
    const rec = ST.observe("manual");
    assert.ok(!JSON.stringify(rec).includes("/learn/quiz/"));
    assert.ok(!JSON.stringify(rec).includes("fixture"));
  } finally {
    b.stop();
  }
});

test("관측이 없는 어댑터는 행을 만들지 않는다", need, async () => {
  const ST = await harness.loadAdapters(["generic"]);
  ST.SETTLE_MS = 0;
  harness.makeDoc("<p>Only the generic layer runs on this plain page of text.</p>");
  globalThis.chrome = harness.fakeChrome().api;
  globalThis.fetch = harness.fakeFetch([{ ok: true, body: { translations: "echo" } }]);
  const b = await harness.loadBroker();
  try {
    assert.equal(ST.observe("manual"), null);
  } finally {
    b.stop();
  }
});
