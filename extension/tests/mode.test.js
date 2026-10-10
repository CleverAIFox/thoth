// **끊는 자리가 어디인가**(DECISIONS §177).
//
// ★ **끄기가 CSS 한 줄이었다.** `html.st-off .st-translation { display: none }`.
//   상자만 숨었고 수집 · 자리 선점 · **워커 호출 · 과금은 그대로 돌았다.** 콘솔은
//   「번역 표시 끔」 이라 **정직했고**, 사람은 「번역 끔」 으로 읽었다. 2026-10-09
//   까지 꺼 둔 줄 알고 보던 지메일에서 Bedrock 요청이 계속 나갔다.
//
// ★ **그래서 이 검사의 본체는 「요청이 몇 번 나갔나」 다.** 「클래스가 붙었나」 는
//   종전에도 초록이었다 — **재는 자가 돈이 나가는 자리를 안 보고 있었다**(§171 과
//   같은 모양 : 참말인 초록이 가장 오래 숨긴다).
import assert from "node:assert/strict";
import { test } from "node:test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

let harness = null;
try {
  harness = await import("./harness.js");
} catch {
  // jsdom 미설치. 도는 검사만 skip 하고 글자 검사는 그대로 돈다.
}
const need = { skip: harness ? false : "jsdom 이 없다 — npm install (extension/)" };

const 뿌리 = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const 읽 = (rel) => fs.readFileSync(path.join(뿌리, rel), "utf8");
// ★ **주석 걷기를 제 손으로 쓰지 않는다**(DECISIONS §178). 처음 판은 정규식이었고
//   `popup.js` 의 `"/*"` **문자열**을 주석 시작으로 읽어 코드 2,747 자를 지웠다.
//   §173 의 가드도 같은 정규식을 들고 있어서 **지키려던 구간을 안 보고 있었다.**
import { 글벗긴다, 코드벗긴다 } from "./strip.js";

const 글 = "A shard stores records for the stream in this one long sentence here.";

/** 저장소를 주고 브로커를 한 판 돌린다.
 *
 * ★ **단언 뒤에 `b.stop()` 을 두면 안 된다.** 단언이 터지는 순간 그 줄을 못 지나고
 *   `setInterval` 이 남아 **러너가 영영 안 끝난다** — 돌연변이를 먹였을 때 「살아남음」
 *   이 아니라 **300 초 타임아웃**으로 나왔고, 그 둘은 다른 말이다(§59). 그래서 아래
 *   검사는 모두 `try … finally { b.stop(); }` 꼴이다. */
async function 올린다(저장소) {
  const { loadAdapters, makeDoc, loadBroker, fakeChrome, fakeFetch } = harness;
  await loadAdapters(["generic"]);
  makeDoc(`<p>${글}</p>`);
  const c = fakeChrome(저장소);
  globalThis.chrome = c.api;
  const f = fakeFetch([{ ok: true, body: { translations: "echo" } }]);
  globalThis.fetch = f;
  const b = await loadBroker();
  await new Promise((r) => setTimeout(r, 2000));
  return { c, f, b, ST: globalThis.ST, doc: globalThis.document, win: globalThis.window };
}

// ---------- 돈이 나가는 자리 ----------

test("저장소가 비면 워커를 한 번도 안 부른다", need, async () => {
  // ★ **기본값이 수집이다.** `host_permissions` 가 모든 사이트를 먹으므로 기본이
  //   「번역」 이면 **은행·사내 시스템 본문까지** 첫 순회에 나간다.
  // ★ 저장소 읽기는 비동기인데 `run()` 은 **올라가는 줄에서** 돈다. 순서로 막지
  //   않고 **기본값으로** 막는다 — 경주가 있어도 안전한 쪽으로 진다.
  const { f, b, ST, doc } = await 올린다({});
  try {
    assert.equal(f.calls.length, 0, "수집만인데 요청이 나갔다 — 그대로 과금이 난다");
    assert.equal(doc.querySelectorAll(".st-translation").length, 0, "상자를 꽂았다");
    assert.ok(!doc.querySelector("[data-st-done]"), "표식을 남겼다 — DOM 을 건드렸다");

    // ★ **「안 번역했다」 와 「안 돈다」 는 다른 말이다.** 수집 경로가 죽어 있으면
    //   끈 것이 아니라 멈춘 것이고, 그러면 모을 것이 애초에 없다.
    assert.ok(ST.수집.length >= 1, "수집 경로가 죽었다");
    assert.equal(ST.수집[0].단위, 1);
    assert.equal(ST.수집[0].adapter, "generic");
    assert.ok(ST.수집[0].글자 >= 글.length - 2, `글자를 안 센다 : ${ST.수집[0].글자}`);
  } finally { b.stop(); }
});

test("번역을 켜면 워커로 간다", need, async () => {
  // ★ 끈 쪽만 재면 **영영 번역 안 되는 확장**도 초록이다(§152 의 양방향).
  const { f, b } = await 올린다({ stOff: false });
  try {
    assert.ok(f.calls.length >= 1, "켠 채로도 요청이 안 나간다");
  } finally { b.stop(); }
});

test("끄면 새 글이 들어와도 요청이 안 나간다", need, async () => {
  // ★ **`stDone` 으로 가려지는 자리다**(§175 와 같은 모양). 이미 번역한 단위는
  //   다시 안 나가므로 「끈 뒤 요청 수가 그대로」 는 **끄지 않아도 참**이다.
  //   그래서 끈 뒤에 **새 문단을 넣고** 센다.
  const { c, f, b, doc } = await 올린다({ stOff: false });
  try {
    const 전 = f.calls.length;
    assert.ok(전 >= 1, "켠 상태를 못 만들었다");
    assert.equal(doc.documentElement.classList.contains("st-off"), false);

    await c.api.storage.local.set({ stOff: true });
    // ★ **이미 선 상자는 숨긴다.** ①에서 끊으면 새 상자는 안 서지만 먼저 선 것은 남는다.
    assert.ok(doc.documentElement.classList.contains("st-off"), "선 상자가 그대로 보인다");

    const p = doc.createElement("p");
    p.textContent = "Another whole sentence that is long enough to be collected now.";
    doc.body.appendChild(p);
    await new Promise((r) => setTimeout(r, 2000));
    assert.equal(f.calls.length, 전, "끈 뒤에 들어온 글을 워커로 보냈다");
    assert.equal(doc.querySelectorAll(".st-translation").length, 전,
                 "끈 뒤에 상자를 더 꽂았다");
  } finally { b.stop(); }
});

test("Alt+K 가 저장소를 거쳐 적용된다", need, async () => {
  // ★ **길을 하나로 둔다**(DECISIONS §173). 쓰기는 저장소에만, 적용은 `onChanged`
  //   에서만 한다 — 그래야 팝업에서 눌러도 **같은 한 길**이다.
  const { c, b, doc, win } = await 올린다({ stOff: false });
  try {
    assert.equal(c.store.stOff, false);
    doc.dispatchEvent(new win.KeyboardEvent("keydown",
      { altKey: true, code: "KeyK", bubbles: true }));
    await new Promise((r) => setTimeout(r, 50));
    assert.equal(c.store.stOff, true, "저장소에 안 썼다");
    assert.ok(doc.documentElement.classList.contains("st-off"),
              "onChanged 를 안 듣는다 — 눌러도 안 꺼진다");
  } finally { b.stop(); }
});

// ---------- 배선 : 끊는 자리가 어디에 적혔나 ----------

test("끊는 자리가 수집 뒤이고 꽂기·워커 앞이다", () => {
  const src = 코드벗긴다(읽("src/broker.js"));
  const 자리 = {
    수집: src.indexOf("ad.collect(document)"),
    끊음: src.indexOf("if (번역끔) { 수집만한다"),
    표식: src.indexOf('u.el.dataset.stDone = "1"'),
    워커: src.indexOf("ST.translate("),
  };
  for (const [이름, i] of Object.entries(자리))
    assert.ok(i >= 0, `${이름} 자리를 못 찾았다`);
  assert.ok(자리.수집 < 자리.끊음, "수집 앞에서 끊으면 셀 것이 없다");
  assert.ok(자리.끊음 < 자리.표식, "표식을 남긴 뒤에 끊으면 이미 DOM 을 건드렸다");
  assert.ok(자리.끊음 < 자리.워커, "워커를 부른 뒤에 끊으면 과금이 난다");
});

test("기본값이 꺼진 쪽이고 팝업이 같은 뜻으로 적었다", () => {
  // ★ **같은 사실이 두 곳에 살면 한쪽만 고쳐진다**(§91 · §173). 팝업이 「켬」 을
  //   보여 주고 브로커가 수집만 도는 어긋남은 **아무것도 안 터지고 거짓말만 한다.**
  const broker = 코드벗긴다(읽("src/broker.js"));
  assert.match(broker, /let 번역끔 = true;/,
               "기본이 번역이면 첫 순회가 모든 사이트를 내보낸다");
  assert.match(broker, /stOff === undefined \? true : stOff/, "빈 칸을 번역 켬으로 읽는다");
  assert.match(코드벗긴다(읽("src/popup.js")), /stOff === undefined \? false : !s\.stOff/,
               "팝업이 빈 칸을 켬으로 그린다");
});

test("팝업이 번역을 제 손으로 끄지 않는다", () => {
  // ★ 종전에는 팝업이 `executeScript` 로 열린 탭의 클래스를 **직접 뒤집었다.**
  //   끄기가 「상자 숨김」 이던 동안은 그것으로 충분했고, ①에서 끊는 지금 그 길은
  //   **워커를 안 끈다.** 돌아오면 또 조용히 과금이 난다.
  const popup = 코드벗긴다(읽("src/popup.js"));
  assert.ok(!/st-off/.test(popup), "팝업이 클래스를 직접 뒤집는다");
  assert.ok(!/executeScript/.test(popup), "팝업이 탭에 코드를 꽂아 끈다");
  assert.match(popup, /storage\.local\.set\(\{\s*stOff/, "저장소에 안 쓴다");
  assert.match(코드벗긴다(읽("src/broker.js")), /storage\.onChanged\?\.addListener/,
               "브로커가 저장소 변화를 안 듣는다");
});

test("모든 사이트를 설치 때 한 번에 먹는다", () => {
  // ★ 선택 권한이면 **사이트마다 버튼**을 눌러야 주입되고, 그러면 수집이 안 돈다.
  //   수집은 상시여야 하고, 기본이 「번역 끔」 이라 상시여도 밖으로 나가는 것이 없다.
  const m = JSON.parse(읽("manifest.json"));
  assert.deepEqual(m.host_permissions, ["<all_urls>"]);
  assert.ok(!("optional_host_permissions" in m),
            "선택 권한이 남아 있다 — 사이트마다 허용을 눌러야 한다");
});

test("팝업 글자가 끄면 무엇이 멈추는지 적는다", () => {
  // ★ **「표시」 가 사람을 속였다.** 글자가 참이어도 읽는 쪽이 「번역」 으로 읽으면
  //   그 글자는 못 쓴 것이다. 무엇이 멈추는지를 적는다.
  const html = 읽("popup.html");
  const 본문 = 글벗긴다(html);
  assert.ok(!/번역 표시/.test(본문), "「번역 표시」 가 남아 있다");
  assert.match(본문, /수집까지만/, "끄면 무엇이 도는지 안 적혀 있다");
});

test("검사가 진짜로 무는가", () => {
  // ★ **0 건이 목표인 검사는 0 건을 성공으로만 읽으면 안 된다**(§152). 합성으로 묻는다.
  assert.ok(/st-off/.test('x.classList.toggle("st-off", v)'));
  assert.ok(!/st-off/.test("await chrome.storage.local.set({ stOff: true });"));
  assert.ok("optional_host_permissions" in { optional_host_permissions: [] },
            "manifest 검사가 안 문다");
  // ★ **주석 걷기가 도는가.** 죽으면 위의 `st-off` 검사가 제 주석에 걸린다.
  assert.equal(코드벗긴다("// st-off 를 뒤집었다\nconst a = 1;").trim(), "const a = 1;");
  assert.equal(글벗긴다("<!-- 번역 표시 -->\n<p>x</p>").trim(), "<p>x</p>");
  // ★ **그리고 코드를 안 먹는가**(DECISIONS §178). 이 한 줄이 §173 의 가드를 2,747 자
  //   동안 눈멀게 했다 — `"/*"` 는 문자열이고 주석이 아니다.
  const 함정 = 'const a = x + "/*";\nconst 주소 = "http://127.0.0.1:8000";\nconst b = 1;';
  assert.equal(코드벗긴다(함정), 함정, "문자열 안의 /* 를 주석으로 읽는다");
  assert.ok(/127\.0\.0\.1/.test(코드벗긴다(함정)),
            "주소가 든 줄이 먹혔다 — 가드가 그 자리를 못 본다");
});
