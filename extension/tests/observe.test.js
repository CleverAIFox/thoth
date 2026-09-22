// 사이트 어댑터의 관측 행(PLAN §2-4 #25).
//
// ★ **기대도 마크업도 픽스처에서 읽는다.** `fixtures/udemy.html` 의 `<template>` 이
//   브라우저 검사와 이 검사의 공통 입력이고, 화면마다 `data-expect` 에 기대가 적혀
//   있다. 여기에 기대를 다시 적으면 두 곳에 살고 한쪽만 고쳐진다(DECISIONS §14).
//   화면을 하나 더하면 이 파일을 고치지 않아도 그 화면이 검사된다.
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

/** 픽스처의 화면들. 속성이 정본이므로 여기서 읽기만 한다. */
const SCREENS = [...FIXTURE.matchAll(/<template id="t-([\w-]+)"([^>]*)>([\s\S]*?)<\/template>/g)]
  .map(([, id, attrs, html]) => {
    // ★ 작은따옴표 값 안에 `"` 가 있다(`data-expect`). 따옴표 종류를 갈라 읽지
    //   않으면 첫 `"` 에서 잘리고 JSON 이 깨진다.
    const at = (k) => {
      const m = new RegExp(`data-${k}=(?:"([^"]*)"|'([^']*)')`).exec(attrs);
      return m ? (m[1] ?? m[2]) : undefined;
    };
    return {
      id,
      html,
      url: at("url"),
      kind: at("kind"),
      expected: at("expected") === "true",
      probes: JSON.parse(at("expect") || "{}"),
      units: Number(at("units")),
      boxes: Number(at("boxes")),
    };
  });

/** 한 화면을 문서로. `host` 를 주면 진짜 호스트가 그것이 된다. */
function docFor(s, { host } = {}) {
  const meta = `<meta name="st-fixture-url" content="${s.url}">`;
  return harness.makeDoc(meta + s.html, host ? { url: host } : {});
}

async function udemy() {
  const ST = await harness.loadAdapters(["generic", "udemy"]);
  return { ST, ad: ST.adapters.find((a) => a.name === "udemy") };
}

test("픽스처에 화면이 여섯이고 전부 기대를 들고 있다", need, () => {
  // ★ 정규식이 조용히 0건을 내면 아래 검사가 전부 통과한 척한다(DECISIONS §21).
  assert.equal(SCREENS.length, 6);
  for (const s of SCREENS) {
    assert.ok(s.url && s.kind, `${s.id} 에 data-url · data-kind 가 없다`);
    assert.ok(Object.keys(s.probes).length === 5, `${s.id} 의 data-expect 가 다섯 축이 아니다`);
    assert.ok(Number.isInteger(s.units) && Number.isInteger(s.boxes), `${s.id} 의 수가 비었다`);
  }
});

test("화면마다 주소가 다르다", need, () => {
  // ★ 같으면 화면을 바꿔도 `watchHref` 가 움직이지 않아 `settle` 관측이 안 돈다.
  assert.equal(new Set(SCREENS.map((s) => s.url)).size, SCREENS.length);
});

for (const s of SCREENS) {
  test(`화면 ${s.id} — 관측이 data-expect 와 같다`, need, async () => {
    const { ad } = await udemy();
    const doc = docFor(s);
    const o = ad.observe(doc);
    assert.deepEqual(o.probes, s.probes);
    assert.equal(o.kind, s.kind);
    assert.equal(o.expected, s.expected);
  });

  test(`화면 ${s.id} — 수집이 data-units 와 같다`, need, async () => {
    // 관측이 센 것과 어댑터가 실제로 모으는 것이 갈리면 관측이 거짓말을 한다.
    const { ad } = await udemy();
    assert.equal(ad.collect(docFor(s)).length, s.units);
  });
}

test("스코프가 깨진 화면에는 글이 남아 있다", need, async () => {
  // ★ 전부 0 인데 blocks 가 0 이면 그냥 빈 페이지다. **둘의 차이가 깨짐의 신호다.**
  const { ST, ad } = await udemy();
  const s = SCREENS.find((x) => x.id === "renamed-scope");
  const doc = docFor(s);
  assert.equal(ad.collect(doc).length, 0);
  assert.ok(ST.textBlocks(doc) >= 5);
});

test("번역 박스는 글 덩어리로 세지 않는다", need, async () => {
  const { ST } = await udemy();
  const doc = harness.makeDoc(`
    <p>This paragraph is long enough to count as a block of text.</p>
    <div class="st-translation"><p>이 문단은 번역 박스 안에 있어 세지 않는다 twenty chars.</p></div>`);
  assert.equal(ST.textBlocks(doc), 1);
});

// ---------- 픽스처 판별 ----------

test("로컬에서는 fixture meta 가 먹는다", need, async () => {
  const { ST, ad } = await udemy();
  docFor(SCREENS[0]);
  assert.equal(ST.fixtureUrl(), SCREENS[0].url);
  assert.ok(ad.match());
});

test("남의 호스트에서는 fixture meta 를 무시한다", need, async () => {
  // ★ 이것이 없으면 아무 사이트나 meta 한 줄로 어댑터를 바꾸고 관측을 읽어 간다.
  const { ST, ad } = await udemy();
  docFor(SCREENS[0], { host: "https://evil.example/page" });
  assert.equal(ST.fixtureUrl(), "");
  assert.equal(ST.pageUrl(), "https://evil.example/page");
  assert.equal(ad.match(), false);
});

// ---------- 브로커 ----------

async function brokerOn(id, opts) {
  const { ST } = await udemy();
  ST.SETTLE_MS = 0;          // 자동 관측을 끄고 손으로 부른다
  const doc = docFor(SCREENS.find((s) => s.id === id), opts);
  globalThis.chrome = harness.fakeChrome().api;
  globalThis.fetch = harness.fakeFetch([{ ok: true, body: { translations: "echo" } }]);
  const b = await harness.loadBroker();
  return { ST, doc, b };
}

/** `st:obs` 로 나온 줄을 모은다. 픽스처 페이지가 하는 것과 같은 일이다. */
function sink(doc) {
  const seen = [];
  doc.addEventListener("st:obs", (e) => seen.push(e.detail));
  return seen;
}

test("같은 페이지 · 같은 수면 행을 다시 만들지 않는다", need, async () => {
  const { ST, b } = await brokerOn("before");
  try {
    const first = ST.observe("manual");
    assert.ok(first);
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
    doc.querySelector(".quiz-page-content").outerHTML =
      SCREENS.find((s) => s.id === "renamed-scope").html;
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

// ---------- 픽스처로 내보내기 (DECISIONS §104) ----------

test("픽스처에서는 관측이 페이지로 나간다", need, async () => {
  // ★ 콘텐츠 스크립트와 페이지는 다른 세계다. 이 이벤트가 없으면 픽스처가 스스로
  //   채점하지 못하고 사람이 DevTools 컨텍스트를 바꿔야 한다.
  const { ST, doc, b } = await brokerOn("before");
  try {
    const seen = sink(doc);
    const rec = ST.observe("manual");
    assert.equal(seen.length, 1);
    assert.equal(typeof seen[0], "string", "세계를 넘는 것은 문자열이다");
    const got = JSON.parse(seen[0]);
    assert.deepEqual(got.probes, rec.probes);
    assert.equal(got.kind, rec.kind);
    assert.equal(got.reason, "manual");
  } finally {
    b.stop();
  }
});

test("남의 사이트로는 한 줄도 나가지 않는다", need, async () => {
  const { ST, doc, b } = await brokerOn("before", { host: "https://evil.example/page" });
  try {
    const seen = sink(doc);
    assert.equal(ST.emitObservation({ k: "obs" }), false);
    assert.equal(seen.length, 0);
  } finally {
    b.stop();
  }
});

test("어느 워커로 나갔는지 함께 싣는다", need, async () => {
  // ★ 배포본을 때리면 픽스처 문장이 과금되고 쌍으로 쌓인다. **호스트만** 싣는다.
  const { ST, doc, b } = await brokerOn("before");
  try {
    await ST.translate(["Pipeline probe for the fixture worker line."]);
    const seen = sink(doc);
    ST.observe("manual");
    const got = JSON.parse(seen[0]);
    assert.equal(got.worker, "127.0.0.1:8000");
    assert.ok(!JSON.stringify(got).includes("translate"), "경로는 싣지 않는다");
  } finally {
    b.stop();
  }
});
