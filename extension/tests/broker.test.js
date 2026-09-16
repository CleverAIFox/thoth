// 브로커의 실패 분기와 배선을 본다.
//
// ★ 흉내내는 것은 `chrome.storage` 와 `fetch` 둘뿐이다. 나머지는 jsdom 과
//   Node 가 이미 한다(harness.js). **흉내가 적을수록 실제와 어긋날 자리가
//   적다**(DECISIONS §47).
//
// ★ 그래도 흉내인 것은 맞다. 여기서 보는 것은 **판정과 배선**이고, 실제
//   네트워크·렌더링 동작은 픽스처와 실사이트에서 본다(MASTER §11-5).
import assert from "node:assert/strict";
import { test } from "node:test";

let harness = null;
try {
  harness = await import("./harness.js");
} catch {
  // jsdom 미설치. 아래에서 전부 skip 한다.
}
const need = { skip: harness ? false : "jsdom 이 없다 — npm install (extension/)" };

// ---------- 실패 판정 ----------
//
// ★ 이 부분은 `catch` 블록 안에 섞여 있었다. 떼어내니 브라우저 없이 검사된다
//   (DECISIONS §48).

async function actions() {
  const { loadAdapters, makeDoc, loadBroker, fakeChrome, fakeFetch } = harness;
  await loadAdapters(["generic"]);
  makeDoc("<p>x</p>");
  globalThis.chrome = fakeChrome().api;
  globalThis.fetch = fakeFetch([{ ok: true, body: { translations: [] } }]);
  const b = await loadBroker();
  b.stop();
  return globalThis.ST.failureAction;
}

test("상한 초과는 즉시 멈춘다", need, async () => {
  // 페이지를 새로 열어도 안 풀린다. 연속 실패를 셀 이유가 없다.
  const act = (await actions())({ code: "quota_exceeded", fatal: true }, 0);
  assert.equal(act.halt, "quota_exceeded");
  assert.equal(act.streak, 0);
  assert.equal(act.fatal, true);
});

test("카운터 불통도 즉시 멈춘다", need, async () => {
  const act = (await actions())({ code: "guard_unavailable" }, 2);
  assert.equal(act.halt, "guard_unavailable");
});

test("워커 미기동은 세 번째에 멈춘다", need, async () => {
  // 다음에 될 수도 있는 실패다. 한 번에 포기하면 잠깐 끊긴 것에도 죽는다.
  const f = await actions();
  assert.equal(f({ code: "" }, 0).halt, "");
  assert.equal(f({ code: "" }, 1).halt, "");
  assert.equal(f({ code: "" }, 2).halt, "worker_unreachable");
});

test("성공하면 연속 실패가 끊긴다", need, async () => {
  // 브로커가 성공 시 streak 을 0 으로 되돌리므로, 두 번 실패 후 성공하면
  // 다음 실패는 다시 1 부터다.
  const f = await actions();
  assert.equal(f({ code: "" }, 0).streak, 1);
  assert.equal(f({ code: "" }, 0).halt, "", "0 에서 시작하면 멈추지 않는다");
});

test("fatal 여부가 그대로 전달된다", need, async () => {
  // 영구 실패면 자리를 버리고, 아니면 남겨 다음 순회에 다시 시도한다.
  const f = await actions();
  assert.equal(f({ code: "too_long", fatal: true }, 0).fatal, true);
  assert.equal(f({ code: "", fatal: false }, 0).fatal, false);
  assert.equal(f({}, 0).fatal, false, "fatal 이 없으면 영구 실패가 아니다");
});

// ---------- 클라이언트 계약 ----------

async function client(responses, storage = {}) {
  const { loadAdapters, makeDoc, loadBroker, fakeChrome, fakeFetch } = harness;
  await loadAdapters(["generic"]);
  makeDoc("<p>x</p>");
  globalThis.chrome = fakeChrome(storage).api;
  const f = fakeFetch(responses);
  globalThis.fetch = f;
  const b = await loadBroker();
  b.stop();
  return { translate: globalThis.ST.translate, fetch: f };
}

test("정상 응답을 그대로 돌려준다", need, async () => {
  const { translate } = await client([
    { ok: true, body: { translations: ["가", "나"], cached: [false, false] } },
  ]);
  const r = await translate(["a", "b"]);
  assert.deepEqual(r.translations, ["가", "나"]);
  assert.equal(r.partial, "");
});

test("부분 응답의 사유를 실어 온다", need, async () => {
  // 200 이지만 사유는 재시도로 풀리지 않는다(DECISIONS §24).
  const { translate } = await client([
    { ok: true, body: { translations: ["가", null], partial: "quota_exceeded" } },
  ]);
  const r = await translate(["a", "b"]);
  assert.equal(r.translations[1], null, "못 채운 자리는 null 이다");
  assert.equal(r.partial, "quota_exceeded");
});

test("429 는 코드를 달고 던진다", need, async () => {
  const { translate } = await client([
    { ok: false, status: 429, body: { error: "quota_exceeded" } },
  ]);
  await assert.rejects(() => translate(["a"]), (e) => {
    assert.equal(e.code, "quota_exceeded");
    assert.equal(e.status, 429);
    return true;
  });
});

test("본문이 JSON 이 아니어도 던진다", need, async () => {
  // 프록시가 HTML 오류 페이지를 돌려주는 경우가 있다. 코드는 비지만 죽지 않는다.
  const { translate } = await client([{ ok: false, status: 502, body: null }]);
  await assert.rejects(() => translate(["a"]), (e) => e.status === 502);
});

test("길이가 어긋나면 계약 위반이다", need, async () => {
  // ★ 엔진을 믿지 않는다. 워커가 이것을 막지만(§24) 확장도 확인한다 —
  //   짧은 배열을 그대로 쓰면 엉뚱한 자리에 번역이 붙는다(§1).
  const { translate } = await client([
    { ok: true, body: { translations: ["가"] } },
  ]);
  await assert.rejects(() => translate(["a", "b"]),
                       (e) => e.code === "contract_violation");
});

test("토큰이 있으면 헤더에 싣는다", need, async () => {
  const { translate, fetch } = await client(
    [{ ok: true, body: { translations: ["가"] } }], { stToken: "t0k" });
  await translate(["a"]);
  assert.equal(fetch.calls[0].headers["X-Thoth-Token"], "t0k");
});

test("토큰이 없으면 헤더를 붙이지 않는다", need, async () => {
  // 빈 값으로 보내면 preflight 가 도는데 얻는 것 없이 왕복만 는다.
  const { translate, fetch } = await client(
    [{ ok: true, body: { translations: ["가"] } }]);
  await translate(["a"]);
  assert.ok(!("X-Thoth-Token" in fetch.calls[0].headers));
});

test("엔드포인트 설정이 기본값을 이긴다", need, async () => {
  const { translate, fetch } = await client(
    [{ ok: true, body: { translations: ["가"] } }],
    { stEndpoint: "https://w.test/translate" });
  await translate(["a"]);
  assert.equal(fetch.calls[0].url, "https://w.test/translate");
});

test("source 를 본문에 싣는다", need, async () => {
  // 쌍 로그가 사이트 · 어댑터별로 갈리는 열이다(PLAN #23).
  const { translate, fetch } = await client(
    [{ ok: true, body: { translations: ["가"] } }]);
  await translate(["a"], { site: "www.udemy.com", adapter: "udemy" });
  assert.deepEqual(fetch.calls[0].body.source, { site: "www.udemy.com", adapter: "udemy" });
});

test("source 가 비면 키를 싣지 않는다", need, async () => {
  // 옛 워커도 받는다. `""` 과 null 이 한 열에 섞이지 않게 한다.
  const { translate, fetch } = await client(
    [{ ok: true, body: { translations: ["가"] } }]);
  await translate(["a"], { site: "", adapter: undefined });
  assert.ok(!("source" in fetch.calls[0].body));
  await translate(["a"]);
  assert.ok(!("source" in fetch.calls[1].body));
});

test("브로커가 호스트와 어댑터 이름을 넘긴다", need, async () => {
  const { loadAdapters, makeDoc, loadBroker, fakeChrome, fakeFetch } = harness;
  await loadAdapters(["generic"]);
  makeDoc("<p>A shard stores records for the stream in this sentence.</p>");
  globalThis.chrome = fakeChrome().api;
  const f = fakeFetch([{ ok: true, body: { translations: "echo" } }]);
  globalThis.fetch = f;
  const b = await loadBroker();
  await new Promise((r) => setTimeout(r, 2000));
  b.stop();
  assert.ok(f.calls.length >= 1, "요청이 나가지 않았다");
  assert.equal(f.calls[0].body.source.adapter, "generic");
  assert.ok(!("url" in f.calls[0].body.source), "경로는 싣지 않는다");
});

// ---------- 배치 기본값 ----------

test("배치 기본값이 실측 최적점이다", need, async () => {
  // ★ 로컬 엔진 45유닛 실측에서 위반이 U자를 그린다 — 배치 1·2·3·6·9 에서
  //   9·6·3·5·6 건이다(DECISIONS §51). 이 값이 바뀌면 근거가 사라진다.
  const { loadAdapters, makeDoc, loadBroker, fakeChrome, fakeFetch } = harness;
  await loadAdapters(["generic", "standard"]);
  makeDoc(`<div role="radiogroup">
    <div role="radio">The first option is long enough to be collected here now.</div>
    <div role="radio">The second option is long enough to be collected here now.</div>
    <div role="radio">The third option is long enough to be collected here now.</div>
    <div role="radio">The fourth option is long enough to be collected here now.</div>
  </div>`);
  globalThis.chrome = fakeChrome().api;
  const f = fakeFetch([{ ok: true, body: { translations: "echo" } }]);
  globalThis.fetch = f;
  const b = await loadBroker();
  await new Promise((r) => setTimeout(r, 2000));
  b.stop();

  assert.ok(f.calls.length > 0, "요청이 나가야 한다");
  assert.deepEqual(f.calls.map((c) => c.body.texts.length), [3, 1],
                   "보기 넷이 3+1 로 쪼개져야 한다");
});

test("그룹이 없는 본문은 낱개로 나간다", need, async () => {
  /**★ `MAX_BATCH` 는 **그룹 안에서만** 먹는다. 그룹이 없는 유닛은
   * `solo:${id}` 로 각각 다른 키를 받으므로 한 묶음에 하나뿐이다.
   *
   * ★ 그래서 **일반 웹페이지 본문에는 배치가 적용되지 않는다.** 배치 3 이
   * 최적이라는 실측은 골든셋(문항 단위로 묶인다)의 것이고, `generic` 이 걷는
   * 본문에는 해당하지 않는다. 그 차이를 모르면 실측을 잘못 옮긴다
   * (DECISIONS §51).
   */
  const { loadAdapters, makeDoc, loadBroker, fakeChrome, fakeFetch } = harness;
  await loadAdapters(["generic"]);
  makeDoc(Array.from({ length: 5 },
    (_, i) => `<p>Sentence number ${i} is long enough to be collected here now.</p>`).join(""));
  globalThis.chrome = fakeChrome().api;
  const f = fakeFetch([{ ok: true, body: { translations: "echo" } }]);
  globalThis.fetch = f;
  const b = await loadBroker();
  await new Promise((r) => setTimeout(r, 2000));
  b.stop();

  assert.equal(f.calls.length, 5, "다섯 문단이 다섯 번 나간다");
  assert.ok(f.calls.every((c) => c.body.texts.length === 1));
});
