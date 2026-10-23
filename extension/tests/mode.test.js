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

// ★ **고정 잠을 판정에 쓰지 않는다**(DECISIONS §196). 조건이 참이 될 때까지 기다리고
//   상한에 걸리면 **무엇을 기다렸는지** 말하며 죽는다. 잠은 기계 속도를 판정에
//   들이고, 그러면 **같은 코드가 기계마다 다른 색**을 낸다.
const 까지기다린다 = async (조건, 말, 상한 = 15000) => {
  const 끝 = Date.now() + 상한;
  while (Date.now() < 끝) {
    if (조건()) return;
    await new Promise((r) => setTimeout(r, 25));
  }
  assert.fail(typeof 말 === "function" ? 말() : 말);
};

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
  const { f, b } = await 올린다({ ...harness.번역켬() });
  try {
    assert.ok(f.calls.length >= 1, "켠 채로도 요청이 안 나간다");
  } finally { b.stop(); }
});

test("끄면 새 글이 들어와도 요청이 안 나간다", need, async () => {
  // ★ **`stDone` 으로 가려지는 자리다**(§175 와 같은 모양). 이미 번역한 단위는
  //   다시 안 나가므로 「끈 뒤 요청 수가 그대로」 는 **끄지 않아도 참**이다.
  //   그래서 끈 뒤에 **새 문단을 넣고** 센다.
  const { c, f, b, doc } = await 올린다({ ...harness.번역켬() });
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

test("순회 한가운데서 꺼도 남은 묶음이 안 나간다", need, async () => {
  // ★ **§177 이 문을 입구에만 달았다.** 끊는 자리 ①은 순회 **들머리**에 있어서,
  //   들어온 뒤에 끄면 남은 묶음이 **끝까지** 워커로 나갔다 — 2026-10-12 에 재니
  //   그룹 셋짜리 한 페이지에서 **6건 중 5건이 끈 뒤**였다(DECISIONS §184).
  // ★ **재는 것은 「클래스가 붙었나」 가 아니라 「요청이 몇 번 나갔나」 다** — 이
  //   파일의 머리말이 §177 에서 그렇게 적어 놨고, 그 자리가 하나 더 있었다.
  const { loadAdapters, makeDoc, loadBroker, fakeChrome } = harness;
  await loadAdapters(["generic", "standard"]);
  // 그룹 셋 × 보기 넷 ⇒ 한 순회가 요청을 여러 번 낸다. 하나면 잴 수가 없다.
  let html = "";
  for (let g = 0; g < 3; g++) {
    html += '<div role="radiogroup">';
    for (let i = 0; i < 4; i++)
      html += `<div role="radio">Group ${g} option ${i} ${글}</div>`;
    html += "</div>";
  }
  makeDoc(html);
  const c = fakeChrome({ ...harness.번역켬() });
  globalThis.chrome = c.api;

  const 부름 = [];
  let 껐나 = false;
  globalThis.fetch = async (url, init) => {
    const body = JSON.parse(init.body);
    부름.push({ 끈뒤: 껐나 });
    // ★ **첫 요청이 나간 직후에 끈다** — 팝업·Alt+K 와 **같은 길**(저장소)로 끈다.
    if (부름.length === 1) { 껐나 = true; await c.api.storage.local.set({ stOff: true }); }
    await new Promise((r) => setTimeout(r, 120));        // 워커가 느린 척
    return { ok: true, status: 200,
             json: async () => ({ translations: body.texts.map(() => "echo") }) };
  };
  const b = await loadBroker();
  try {
    await new Promise((r) => setTimeout(r, 3000));
    const 샌것 = 부름.filter((x) => x.끈뒤).length;
    assert.equal(샌것, 0, `끈 뒤에 ${샌것}건이 워커로 나갔다 (전체 ${부름.length}건)`);
    assert.ok(부름.length >= 1, "켠 상태를 못 만들었다 — 재는 것이 없다");
  } finally { b.stop(); }
});

test("끄느라 거둔 자리는 다시 켜면 번역된다", need, async () => {
  // ★ **끔은 실패가 아니다.** 거두는 자리에 `drop(u, false)` 를 쓰면 `stRetry` 가
  //   올라 **몇 번 끄면 그 자리가 영영 `stFail`** 이 되고, `drop(u, true)` 는 한 번에
  //   버린다. 둘 다 조용하다 — **다시 켰을 때 거기만 안 되는** 꼴로만 드러난다.
  // ★ 그래서 **글자로 묻지 않고 돌려서 묻는다.** 처음 판은 `거둔다` 의 몸만 봤고,
  //   **호출부를 `drop` 으로 바꾼 돌연변이가 둘 다 살아남았다**(§184).
  const { loadAdapters, makeDoc, loadBroker, fakeChrome } = harness;
  await loadAdapters(["generic", "standard"]);
  let html = "";
  for (let g = 0; g < 3; g++) {
    html += '<div role="radiogroup">';
    for (let i = 0; i < 4; i++)
      html += `<div role="radio">Group ${g} option ${i} ${글}</div>`;
    html += "</div>";
  }
  const doc = makeDoc(html);
  const c = fakeChrome({ ...harness.번역켬() });
  globalThis.chrome = c.api;

  let 껐나 = false;
  const 보낸글 = [];
  let 첫묶음 = null;
  globalThis.fetch = async (url, init) => {
    const body = JSON.parse(init.body);
    body.texts.forEach((t) => 보낸글.push(t));
    if (!껐나) {
      껐나 = true;
      첫묶음 = body.texts.length;
      await c.api.storage.local.set({ stOff: true });
    }
    await new Promise((r) => setTimeout(r, 60));
    return { ok: true, status: 200,
             json: async () => ({ translations: body.texts.map(() => "echo") }) };
  };
  const b = await loadBroker();
  try {
    await 까지기다린다(() => 껐나, "첫 요청이 안 나갔다 — 켠 상태를 못 만들었다");
    // ★ **0 을 통과로 세지 않는다**(§59). 첫 묶음이 12 를 다 담았으면 **순회 한가운데서
    //   거둘 자리가 없고**, 그러면 이 시험은 아무것도 안 묻는다 — 그런데 **통과한다.**
    //   2026-10-19 에 그의 기계가 그 갈래로 떨어져 `끊는자리2` 돌연변이가 살아남았고
    //   내 사본 3/3 은 물었다. **같은 코드가 기계마다 다른 색을 냈다.** 이제 그 갈래는
    //   초록이 아니라 **이 줄에서 빨강**이다 — 무엇이 어긋났는지 말하면서 죽는다.
    assert.ok(첫묶음 !== null && 첫묶음 < 12,
              `첫 묶음이 ${첫묶음}/12 다 — 거둘 자리가 없어 이 시험이 아무것도 안 묻는다`);
    await new Promise((r) => setTimeout(r, 800));      // 끈 채로 돈다 — 거두는 자리를 지난다
    await c.api.storage.local.set({ stOff: false });   // **다시 켠다**
    await 까지기다린다(() => 보낸글.length >= 12,
                       () => `다시 켠 뒤에도 안 나간 자리가 있다 — 보낸 글 ${보낸글.length}/12`);

    const 버린것 = doc.querySelectorAll("[data-st-fail]").length;
    assert.equal(버린것, 0, `끄기만 했는데 자리 ${버린것}개가 버려졌다`);
    const 센것 = [...doc.querySelectorAll("[data-st-retry]")]
      .map((el) => el.dataset.stRetry);
    assert.deepEqual(센것, [], `끄기를 실패로 세어 재시도가 ${센것} 쌓였다`);
    assert.equal(보낸글.length, 12,
                 `다시 켠 뒤에도 안 나간 자리가 있다 — 보낸 글 ${보낸글.length}/12`);
  } finally { b.stop(); }
});

test("Alt+K 가 저장소를 거쳐 적용된다", need, async () => {
  // ★ **길을 하나로 둔다**(DECISIONS §173). 쓰기는 저장소에만, 적용은 `onChanged`
  //   에서만 한다 — 그래야 팝업에서 눌러도 **같은 한 길**이다.
  // ★ **이 사이트만 뒤집는다**(DECISIONS §209). 종전에는 전역 `stOff` 를 뒤집어서
  //   **다른 탭의 번역까지** 같이 꺼지고 켜졌다 — 그 조합을 쓰는 사이트에서 한 번
  //   눌리면 아무 데서나 전역이 뒤집혔고, 그것이 「자동으로 꺼진다」 의 정체였다.
  const { c, b, doc, win } = await 올린다({
    ...harness.번역켬(), st번역사이트: { localhost: true, "남.example": true },
  });
  try {
    doc.dispatchEvent(new win.KeyboardEvent("keydown",
      { altKey: true, code: "KeyK", bubbles: true }));
    await new Promise((r) => setTimeout(r, 50));
    assert.equal(c.store.st번역사이트.localhost, undefined, "이 사이트를 저장소에서 안 껐다");
    assert.equal(c.store.st번역사이트["남.example"], true, "남의 사이트까지 같이 껐다");
    assert.equal(c.store.stOff, undefined, "마스터 차단을 건드렸다");
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

test("코드벗긴다 가 문자열 안의 주석표를 안 걷는다", () => {
  // ★ **음성 단언은 너무 많이 벗기는 것을 못 잡는다**(DECISIONS §209). 종전 시험은
  //   벗긴 코드에 **있어야 할 글자**를 찾았고(양성), 그래서 `strip.js` 가 문자열 안의
  //   `/*` 를 주석으로 읽기 시작하면 바로 울었다. 이 판이 그 단언을 「없어야 할 글자」
  //   로 바꾸자 **`주석걷기` 돌연변이 넷이 살아남았다** — 가드가 조용히 죽었다.
  //   그래서 그 자리를 **직접** 문다.
  const 벗김 = 코드벗긴다('const re = "a /* b */ c";\n// 진짜 주석\nconst x = 1;\n');
  assert.match(벗김, /a \/\* b \*\/ c/, "문자열 안의 /* 를 주석으로 읽었다");
  assert.match(벗김, /const x = 1;/, "주석 뒤를 통째로 먹었다");
  assert.ok(!/진짜 주석/.test(벗김), "줄 주석을 안 걷었다");
});

test("기본값이 꺼진 쪽이고 판정이 한 곳에만 산다", () => {
  // ★ **같은 사실이 두 곳에 살면 한쪽만 고쳐진다**(§91 · §173). 팝업이 「켬」 을
  //   보여 주고 브로커가 수집만 도는 어긋남은 **아무것도 안 터지고 거짓말만 한다.**
  // ★ **그래서 판정을 글자로 안 묻고 함수로 묻는다**(DECISIONS §209). 종전에는
  //   `stOff === undefined ? true : stOff` 라는 **글자**를 양쪽에서 찾았다 —
  //   글자가 같아도 뜻이 갈릴 수 있고, 뜻이 같아도 글자가 달라지면 운다.
  const broker = 코드벗긴다(읽("src/broker.js"));
  assert.match(broker, /let 번역끔 = true;/,
               "기본이 번역이면 첫 순회가 모든 사이트를 내보낸다");
  assert.match(broker, /ST\.사이트/, "브로커가 판정을 제 손으로 다시 적는다");
  assert.ok(!/stOff === undefined/.test(broker), "브로커에 옛 전역 판정이 남았다");

  const popup = 코드벗긴다(읽("src/popup.js"));
  assert.match(popup, /globalThis\.ST\.사이트/, "팝업이 열쇠 글자를 제 손으로 적는다");
  assert.ok(!/stOff === undefined/.test(popup), "팝업에 옛 전역 판정이 남았다");

  // 정본 함수 자체의 기본값
  const ST = {};
  new Function("globalThis", 읽("src/지문.js"))({ ST });
  assert.equal(ST.사이트.번역할까("mail.google.com", {}), false, "빈 칸이 번역 켬이다");
  assert.equal(ST.사이트.번역할까("", { st번역사이트: { "": true } }), false,
               "호스트를 못 읽은 탭이 번역된다");
});

test("한 사이트를 켜도 남의 사이트는 안 켜진다", () => {
  // ★ **2026-10-23 에 난 일이다**(DECISIONS §209). `stOff` 가 **전역 하나**라
  //   어디서든 한 번 켜면 **지메일도 사내 시스템도 같이 켜졌다** — 그날 AWS 초대
  //   메일 본문이 그렇게 워커로 나갔다. 권한은 수집을 위한 것이지 번역 허락이 아니다.
  const ST = {};
  new Function("globalThis", 읽("src/지문.js"))({ ST });
  const { 번역할까, 뒤집는다 } = ST.사이트;

  const 켠뒤 = 뒤집는다("udemy.com", {});
  assert.equal(번역할까("udemy.com", { st번역사이트: 켠뒤 }), true);
  assert.equal(번역할까("mail.google.com", { st번역사이트: 켠뒤 }), false,
               "한 사이트를 켜니 남의 사이트도 켜졌다");

  // 마스터 차단은 지도보다 세다
  assert.equal(번역할까("udemy.com", { stOff: true, st번역사이트: 켠뒤 }), false);

  // 끌 때는 칸을 **지운다** — 빈 칸이 기본이라 `false` 를 남기면 뜻이 둘이 된다
  assert.deepEqual(뒤집는다("udemy.com", 켠뒤), {});
});

test("팝업이 번역을 제 손으로 끄지 않는다", () => {
  // ★ 종전에는 팝업이 `executeScript` 로 열린 탭의 클래스를 **직접 뒤집었다.**
  //   끄기가 「상자 숨김」 이던 동안은 그것으로 충분했고, ①에서 끊는 지금 그 길은
  //   **워커를 안 끈다.** 돌아오면 또 조용히 과금이 난다.
  const popup = 코드벗긴다(읽("src/popup.js"));
  assert.ok(!/st-off/.test(popup), "팝업이 클래스를 직접 뒤집는다");
  assert.ok(!/executeScript/.test(popup), "팝업이 탭에 코드를 꽂아 끈다");
  // ★ 사이트 토글은 지도에, 마스터 차단은 `stOff` 에 쓴다(DECISIONS §209).
  assert.match(popup, /storage\.local\.set\(\{\s*\[사이트키\]/, "사이트 지도를 저장소에 안 쓴다");
  assert.match(popup, /storage\.local\.set\(\{\s*\[차단키\]/, "마스터 차단을 저장소에 안 쓴다");
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

test("HTML 주석 걷기가 치환이 아니라 훑기다", () => {
  // ★ **CodeQL 이 물었다** — `js/incomplete-multi-character-sanitization`
  //   (2026-10-10, `strip.js:45`). 여러 글자 구분자를 **한 번만 훑어 지우는 치환**은
  //   지운 자리에서 새 구분자가 생기면 샌다. 이 집 HTML 에서는 안 나는 일이지만
  //   **「여기서는 안 난다」 가 §178 이 방금 지운 바로 그 논증**이라 기전을 바꿨다.
  assert.equal(글벗긴다("<p>a</p><!-- 가\n나 --><p>b</p>"), "<p>a</p><p>b</p>",
               "여러 줄 주석을 못 걷는다");
  // ★ **겹친 여는 표는 명세대로 첫 `-->` 에서 닫힌다.** 남는 `-->` 를 삼키면
  //   **더 지우는 쪽**이고, 더 지우면 금지된 글자가 그 안에 숨는다.
  assert.equal(글벗긴다("<!--<!-- 겹 -->-->"), "-->", "겹친 표에서 더 지운다");
  // ★ **안 닫힌 주석은 그 줄만 버린다.** 끝까지 버리면 **뒤가 통째로 사각**이 된다.
  assert.equal(글벗긴다("<p>a</p><!-- 안 닫힘\n<p>b</p>"), "<p>a</p>\n<p>b</p>",
               "안 닫힌 주석이 뒤를 통째로 먹는다");
  assert.equal(글벗긴다("주석 없음"), "주석 없음");

  // ★ **치환으로 돌아가지 않았는가.** 돌아가면 CodeQL 이 다시 울고, 우는 것은
  //   미는 **뒤**다 — 여기서 먼저 문다.
  // ★ **이 줄이 제 주석에 걸렸다 — 일곱 번째다.** `strip.js` 의 머리글이 옛 꼴을
  //   **글자 그대로 인용**하므로, 안 걷고 읽으면 「치환으로 지운다」 가 참이 된다.
  //   §178 이 세운 규칙을 그 다음 줄에서 어겼다 : **글을 코드로 읽는 검사는 글부터
  //   지운다.** 그리고 지우는 자가 `코드벗긴다` 자신이다.
  const src = 코드벗긴다(읽("tests/strip.js"));
  assert.ok(!/replace\(\s*\/<!--/.test(src),
            "HTML 주석을 치환으로 지운다 — CodeQL 이 무는 꼴이다");
  // ★ 합성으로 묻는다 — 안 걷으면 못 잡는다는 것까지(§152).
  assert.ok(/replace\(\s*\/<!--/.test('return html.replace(/<!--[\\s\\S]*?-->/g, "");'));
});
