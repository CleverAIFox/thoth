// 픽스처 페이지가 스스로 채점하는 부분(DECISIONS §104).
//
// ★ **이 스크립트는 페이지 세계에서 돈다.** 확장 검사가 보는 자리가 아니라, 전에는
//   브라우저로 열어 보는 것이 유일한 검사였다. 채점 로직에 결함이 있으면 **픽스처가
//   틀린 초록불을 낸다** — 검사의 검사가 없는 자리라 여기서 본다(DECISIONS §21).
//
// ★ 여기서 보는 것은 **표와 판정**이다. 확장은 없다 — 관측은 `st:obs` 를 직접
//   띄워 흉내낸다. 확장과 이 이벤트가 실제로 이어지는지는 `observe.test.js` 가 본다.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

let JSDOM = null;
try {
  ({ JSDOM } = await import("jsdom"));
} catch {
  // jsdom 미설치
}
const need = { skip: JSDOM ? false : "jsdom 이 없다 — npm install (extension/)" };

const FILE = join(dirname(fileURLToPath(import.meta.url)), "fixtures", "udemy.html");

/** 픽스처를 띄운다. 스크립트를 실제로 돌리므로 창을 반드시 닫는다. */
function open() {
  const dom = new JSDOM(readFileSync(FILE, "utf8"), {
    url: "http://127.0.0.1:8099/udemy.html",
    runScripts: "dangerously",
  });
  const { document } = dom.window;
  const rows = () => [...document.querySelector("#grid").tBodies[0].rows]
    .map((tr) => [...tr.cells].map((td) => td.textContent));
  const press = (id) => [...document.querySelector("#modes").children]
    .find((b) => b.dataset.mode === id).click();
  /** 확장이 보낸 것처럼 관측 한 줄을 띄운다. */
  const emit = (rec) => document.dispatchEvent(
    new dom.window.CustomEvent("st:obs", { detail: JSON.stringify(rec) }));
  return { dom, document, rows, press, emit };
}

/** 픽스처가 스스로 적어 둔 기대. 검사도 페이지도 이것을 읽는다. */
function expectOf(document, id) {
  const t = document.getElementById("t-" + id);
  return {
    probes: JSON.parse(t.dataset.expect),
    kind: t.dataset.kind,
    expected: t.dataset.expected === "true",
    boxes: Number(t.dataset.boxes),
  };
}

const rec = (e, extra = {}) => ({
  k: "obs", v: 1, site: "127.0.0.1", adapter: "udemy",
  kind: e.kind, expected: e.expected, units: 0, blocks: 3,
  probes: e.probes, reason: "settle", worker: "127.0.0.1:8000", ...extra,
});

test("열면 화면 여섯이 전부 미방문이다", need, () => {
  const { dom, rows } = open();
  try {
    const r = rows();
    assert.equal(r.length, 6);
    // 첫 화면은 보여 주지만 관측이 오기 전이므로 판정은 아직 없다.
    assert.ok(r.every((c) => c[1] === "미방문"), r.map((c) => c[1]).join(","));
  } finally {
    dom.window.close();
  }
});

test("기대와 같은 관측이 오면 통과다", need, () => {
  // 박스 0 을 기대하는 화면으로 본다 — 확장이 없어 박스는 0 이다.
  const { dom, document, rows, press, emit } = open();
  try {
    press("renamed-scope");
    emit(rec(expectOf(document, "renamed-scope")));
    const row = rows().find((c) => c[0].startsWith("renamed-scope"));
    assert.equal(row[1], "통과");
    assert.equal(row[4], "0 / 0", "박스도 대조한다");
  } finally {
    dom.window.close();
  }
});

test("probes 가 하나라도 다르면 실패다", need, () => {
  const { dom, document, rows, press, emit } = open();
  try {
    const e = expectOf(document, "renamed-scope");
    press("renamed-scope");
    emit(rec({ ...e, probes: { ...e.probes, prompt: 1 } }));
    const row = rows().find((c) => c[0].startsWith("renamed-scope"));
    assert.match(row[1], /^실패/);
    assert.match(row[1], /probes/);
  } finally {
    dom.window.close();
  }
});

test("박스가 모자라면 관측이 맞아도 실패다", need, () => {
  // ★ 이것이 워커가 죽은 경우다. 관측만 보면 통과라서 **못 본다**.
  const { dom, document, rows, press, emit } = open();
  try {
    press("before");                       // 박스 5 를 기대한다
    emit(rec(expectOf(document, "before")));
    const row = rows().find((c) => c[0].startsWith("before"));
    assert.match(row[1], /박스/);
    assert.equal(row[4], "0 / 5");
  } finally {
    dom.window.close();
  }
});

test("probes 의 키 순서가 달라도 통과다", need, () => {
  // 어댑터가 축을 하나 더하면 순서가 바뀐다. 순서로 판정하면 그때 거짓 실패가 난다.
  const { dom, document, rows, press, emit } = open();
  try {
    const e = expectOf(document, "start");
    const flipped = Object.fromEntries(Object.entries(e.probes).reverse());
    press("start");
    emit(rec({ ...e, probes: flipped }));
    assert.equal(rows().find((c) => c[0].startsWith("start"))[1], "통과");
  } finally {
    dom.window.close();
  }
});

test("누른 순서는 상관없다", need, () => {
  // ★ 이것이 이 페이지를 고친 이유다(DECISIONS §104).
  const { dom, document, rows, press, emit } = open();
  try {
    for (const id of ["landing", "start", "renamed-scope"]) {
      press(id);
      emit(rec(expectOf(document, id)));
    }
    const pass = rows().filter((c) => c[1] === "통과").map((c) => c[0].replace(" ←", ""));
    assert.deepEqual(pass.sort(), ["landing", "renamed-scope", "start"]);
    assert.match(document.getElementById("status").textContent, /방문 3 \/ 6 · 통과 3/);
  } finally {
    dom.window.close();
  }
});

test("화면을 다시 누르면 그 줄을 다시 잰다", need, () => {
  // 관측은 남아 있는데 화면이 바뀌었으면 옛 판정은 거짓말이다.
  const { dom, document, rows, press, emit } = open();
  try {
    press("start");
    emit(rec(expectOf(document, "start")));
    assert.equal(rows().find((c) => c[0].startsWith("start"))[1], "통과");
    press("start");
    assert.equal(rows().find((c) => c[0].startsWith("start"))[1], "미방문");
  } finally {
    dom.window.close();
  }
});

test("워커가 로컬이 아니면 경고로 띄운다", need, () => {
  // ★ 배포본을 때리면 지어낸 문장이 과금되고 쌍으로 쌓인다.
  const { dom, document, press, emit } = open();
  try {
    press("start");
    emit(rec(expectOf(document, "start"), { worker: "abc.lambda-url.ap-northeast-2.on.aws" }));
    assert.equal(document.getElementById("worker").className, "warn");
    emit(rec(expectOf(document, "start"), { worker: "127.0.0.1:8000" }));
    assert.equal(document.getElementById("worker").className, "note");
  } finally {
    dom.window.close();
  }
});

test("화면을 바꾸면 흉내낸 주소도 바뀐다", need, () => {
  // ★ 주소가 같으면 확장이 화면이 바뀐 것을 모른다 — `settle` 관측이 다시 안 돈다.
  const { dom, document, press } = open();
  try {
    const meta = document.querySelector("meta[name=st-fixture-url]");
    press("landing");
    const landing = meta.content;
    press("before");
    assert.notEqual(meta.content, landing);
    assert.equal(meta.content, document.getElementById("t-before").dataset.url);
  } finally {
    dom.window.close();
  }
});

test("보고서에 화면과 동작이 다 들어간다", need, () => {
  const { dom, document, press, emit } = open();
  try {
    press("start");
    emit(rec(expectOf(document, "start")));
    document.getElementById("copy").click();     // jsdom 에는 클립보드가 없다 → 편다
    const text = document.getElementById("report").value;
    assert.ok(text.includes("[통과] start"), text.slice(0, 200));
    assert.ok(text.includes("# 동작 기록"));
    assert.ok(text.includes("화면  start"));
  } finally {
    dom.window.close();
  }
});
