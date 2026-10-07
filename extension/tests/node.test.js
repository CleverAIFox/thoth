// 그려진 노드를 본다 — 박스가 어디에 꽂히고 어떤 상태를 거치는가.
//
// ★ **MASTER §10-1 이 적은 것들이 눈으로만 확인돼 있었다**(DECISIONS §137). 확장 검사는
//   실패 판정과 클라이언트 계약만 봤고, **박스가 실제로 어디에 생기고 어떤 클래스를
//   거쳐 무엇이 되는지**는 아무도 안 봤다. 사람이 브라우저를 열어 본 것이 전부였고,
//   그 확인은 **한 번 돌고 만다**(DECISIONS §135 · §137).
//
// ★ **jsdom 으로 된다.** 클래스가 붙고 떨어지는 것도, 어디에 꽂히는지도 **레이아웃이
//   필요 없다.** 막는 칸에 「jsdom 으로 되는지 모른다」 가 넉 달 적혀 있었는데
//   `fixture-page.test.js` 는 그동안 jsdom 을 쓰고 있었다 — **묻지 않았을 뿐이다.**
//
// ★ **여기서 못 보는 것은 명시도 다툼 하나다.** 그것은 레이아웃이 있어야 하고
//   `tools/cascade_check.py` 가 진짜 엔진으로 잰다. **못 재는 자리를 좁히고 그 자리를
//   적는다**(§73).
import assert from "node:assert/strict";
import { test } from "node:test";

let harness = null;
try {
  harness = await import("./harness.js");
} catch {
  // jsdom 미설치. 아래에서 전부 skip 한다.
}
const need = { skip: harness ? false : "jsdom 이 없다 — npm install (extension/)" };

const 긴글 = (s) => `${s} and this sentence is long enough to be collected here.`;

/** 한 바퀴 돌리고 문서를 돌려준다. 응답은 `fakeFetch` 의 꼴 그대로다. */
async function 한바퀴(html, 응답 = [{ ok: true, body: { translations: "echo" } }], 어댑터 = ["generic"], 손질 = null) {
  const { loadAdapters, makeDoc, loadBroker, fakeChrome, fakeFetch } = harness;
  await loadAdapters(어댑터);
  const doc = makeDoc(html);
  globalThis.chrome = fakeChrome().api;
  const f = fakeFetch(응답);
  globalThis.fetch = f;
  // ★ **손질은 `loadBroker` 가 `broker.js` 를 올리기 **직전**에 부른다.** 브로커는
  //   올라가는 줄에서 첫 순회를 돌리므로 **올라간 뒤에 얹으면 늦다.**
  const b = await loadBroker(손질);
  await new Promise((r) => setTimeout(r, 2000));
  b.stop();
  return { doc, f };
}

const 박스들 = (doc) => [...doc.querySelectorAll(".st-translation")];

// ★ **글자는 섀도 안에 있다**(DECISIONS §169). 박스는 호스트고 번역문은 그 안의
//   `.st-몸` 에 들어간다. **호스트에 쓰면 그려지지도 않는다** — 섀도 루트가 달린
//   요소의 자식은 슬롯이 없으면 렌더 트리에 안 올라간다. 아무도 안 터지고 번역만
//   사라지는 종류라, 아래 「호스트는 비어 있다」 가 그 자리를 따로 문다.
const 속 = (n) => n.shadowRoot?.querySelector(".st-몸") || null;

// ---------- 어디에 꽂히는가 ----------

test("박스는 앵커 바로 뒤 형제로 선다", need, async () => {
  const { doc } = await 한바퀴(`<p id="a">${긴글("The first paragraph")}</p>`);
  const 박스 = 박스들(doc);
  assert.equal(박스.length, 1, "박스가 하나 서야 한다");
  assert.equal(박스[0].previousElementSibling?.id, "a",
               "원문 바로 뒤가 아니면 번역이 엉뚱한 자리에 붙는다");
});

test("표 칸에서는 셀 안에 들어간다", need, async () => {
  // ★ `td`·`th` 뒤에 div 를 꽂으면 브라우저가 표 밖으로 튕겨낸다. 브로커가
  //   앵커를 보고 `appendChild` 로 가른다 — 어댑터가 아니라 브로커의 일이다.
  const { doc } = await 한바퀴(
    `<table><tr><td id="c">${긴글("A table cell")}</td></tr></table>`);
  const 박스 = 박스들(doc);
  assert.equal(박스.length, 1);
  assert.equal(박스[0].parentElement?.id, "c", "셀 밖으로 나가면 표가 깨진다");
});

test("같은 유닛에 박스를 두 번 꽂지 않는다", need, async () => {
  // ★ 순회가 1.5초마다 돈다. `data-st-done` 이 없으면 **같은 문단에 박스가 쌓인다.**
  const { doc } = await 한바퀴(`<p>${긴글("Only once")}</p>`);
  assert.equal(박스들(doc).length, 1);
  assert.equal(doc.querySelector("p").dataset.stDone, "1");
});

// ---------- 어떤 상태를 거치는가 ----------

test("번역이 도착하면 기다림 표시가 떨어진다", need, async () => {
  // ★ **이름표는 `--loading` 에만 붙는다**(DECISIONS §106). 클래스가 안 떨어지면
  //   다 된 번역에 「번역 중」 이 그대로 남고, 뼈대 배경도 깔린 채다.
  const { doc } = await 한바퀴(`<p>${긴글("Done")}</p>`);
  const n = 박스들(doc)[0];
  assert.ok(n.classList.contains("st-translation"));
  assert.ok(!n.classList.contains("st-translation--loading"), "기다림 표시가 안 떨어졌다");
  assert.equal(속(n).textContent, "번역0", "뼈대 글자가 번역으로 안 바뀌었다");
});

test("기다리는 동안에는 기다림 표시가 서 있다", need, async () => {
  // ★ 음성 대조 — 위 시험이 **언제나 참**이면 아무것도 안 재는 것이다.
  //   응답을 안 주면 박스는 `--loading` 인 채로 남아야 한다.
  const { loadAdapters, makeDoc, loadBroker, fakeChrome } = harness;
  await loadAdapters(["generic"]);
  const doc = makeDoc(`<p>${긴글("Waiting")}</p>`);
  globalThis.chrome = fakeChrome().api;
  // ★ **안 풀리는 promise 를 두지 않는다.** `client.js` 가 `TIMEOUT_MS`(200초)
  //   짜리 중단 타이머를 걸어 두므로, 끝까지 안 풀면 **검사 러너가 그만큼 기다린다.**
  //   늦게 오는 응답을 손으로 풀어 준다.
  let 풀기;
  globalThis.fetch = () => new Promise((r) => {
    풀기 = () => r({ ok: true, status: 200, async json() { return { translations: ["늦게"] }; } });
  });
  const b = await loadBroker();
  await new Promise((r) => setTimeout(r, 2000));
  const n = 박스들(doc)[0];
  assert.ok(n, "기다리는 동안에도 자리는 잡혀 있어야 한다");
  assert.ok(n.classList.contains("st-translation--loading"), "기다리는데 표시가 없다");
  풀기?.();
  await new Promise((r) => setTimeout(r, 50));
  b.stop();
  assert.ok(!n.classList.contains("st-translation--loading"),
            "응답이 온 뒤에도 표시가 남아 있다 — 위 단언이 「언제나 참」 이 아님을 함께 본다");
});

test("치명 실패는 자리를 비우지 않고 치운다", need, async () => {
  // ★ **박스만 지우고 `stDone` 을 되돌리면 다음 순회가 같은 유닛을 또 요청한다** —
  //   429 · 413 처럼 재시도로 안 풀리는 실패에서 1.5초마다 워커를 때린다(§12).
  const { doc } = await 한바퀴(`<p>${긴글("Dies")}</p>`,
    [{ ok: false, status: 413, body: { code: "too_long" } }]);
  assert.equal(박스들(doc).length, 0, "실패한 박스가 남아 있다");
  assert.equal(doc.querySelector("p").dataset.stFail, "1", "이 세션에서 다시 건드리지 않아야 한다");
});

// ---------- 무엇이 들어가고 무엇이 안 들어가는가 ----------

test("URL 은 번역에 안 들어가고 링크로 되붙는다", need, async () => {
  // ★ 번역기에 넣으면 경로가 깨지고 **깨진 채로 캐시에 박제된다.**
  const { doc, f } = await 한바퀴(
    `<p>${긴글("See https://example.com/a/b")}</p>`);
  assert.ok(!f.calls[0].body.texts[0].includes("https://"), "URL 이 번역기로 갔다");
  const a = 속(박스들(doc)[0]).querySelector("a");
  assert.ok(a, "링크가 되붙지 않았다");
  assert.equal(a.getAttribute("href"), "https://example.com/a/b");
  assert.equal(a.getAttribute("rel"), "noopener noreferrer");
});

test("원문에 스크립트가 섞여도 박스에 태그로 들어가지 않는다", need, async () => {
  // ★ `innerHTML` 을 쓰지 않는 까닭이다. 번역문은 **워커가 돌려준 남의 글**이고,
  //   그것을 태그로 해석하면 그 자리가 주입 지점이 된다.
  const { doc } = await 한바퀴(`<p>${긴글("Safe")}</p>`,
    [{ ok: true, body: { translations: ["<img src=x onerror=alert(1)>붙는다"] } }]);
  const n = 속(박스들(doc)[0]);
  assert.equal(n.querySelectorAll("img").length, 0, "번역문이 태그로 해석됐다");
  assert.ok(n.textContent.includes("<img"), "글자로는 그대로 보여야 한다");
});

test("이미 한국어면 박스를 아예 만들지 않는다", need, async () => {
  // ★ 감지가 아니라 **제외**다. 번역해도 얻을 것이 없는 확정적 사실이라 판정이 필요 없다.
  const { doc, f } = await 한바퀴(
    "<p>이 문장은 이미 한국어라서 번역할 이유가 전혀 없는 문장입니다.</p>");
  assert.equal(박스들(doc).length, 0);
  assert.equal(f.calls.length, 0, "번역 요청이 나갔다 — 돈이 나간다");
});

// ★ **메일 주소가 분모에 들어 한국어 줄이 번역으로 나갔다**(DECISIONS §160). 2026-10-05
//   지메일에서 `농업정책보험금융원 noreply@apfs.recruiter.co.kr` 가 **0.273** 이라 임계
//   0.3 아래로 떨어졌다. URL 은 부르는 쪽이 이미 떼는데 **주소는 안 뗐다.**
//   실물 문자열을 그대로 쓴다. **한글을 더 섞으면 고침 없이도 건너뛰어** 시험이 안 문다 —
//   처음에 그렇게 써서 돌연변이가 살아 돌아왔다.
const 주소줄 = [
  ["보낸사람 줄 0.273", "농업정책보험금융원 noreply@apfs.recruiter.co.kr"],
  ["지메일 머리 0.103", "longsupport@mail.example.co.kr 나에게"],
  ["본문 안 주소 0.250", "문의 support@example.co.kr 로 보낸다"],
];

for (const [이름, 글] of 주소줄) {
  test(`메일 주소는 한글 비율의 분모에 안 든다 — ${이름}`, need, async () => {
    const { doc, f } = await 한바퀴(`<p>${글}</p>`);
    assert.equal(박스들(doc).length, 0, `${이름} 에 박스가 섰다`);
    assert.equal(f.calls.length, 0, "한국어인데 번역 요청이 나갔다");
  });
}

test("글자가 없으면 박스를 안 만든다", need, async () => {
  // ★ 숫자·기호뿐인 토막은 **번역할 것이 없다.** 분모가 0 이라 비율을 낼 수도 없다 —
  //   그 자리를 「안 건너뜀」 으로 두면 전화번호 · 금액 줄마다 상자가 선다.
  const { doc, f } = await 한바퀴("<p>1234567890 (02) 3456-7890 / 1,234,567 ++ --</p>");
  assert.equal(박스들(doc).length, 0, "숫자뿐인데 박스가 섰다");
  assert.equal(f.calls.length, 0, "숫자뿐인데 번역 요청이 나갔다");
});

test("주소를 빼도 영문 본문은 그대로 번역한다", need, async () => {
  // ★ **제외를 넓히면 번역이 줄어든다.** 음성도 같이 본다 — 안 그러면 전부 건너뛰는
  //   자도 통과한다(DECISIONS §21).
  const { doc } = await 한바퀴(
    "<p>Please contact support@example.com before December 31 to update your mechanism.</p>");
  assert.equal(박스들(doc).length, 1, "영문이 건너뛰어졌다");
});

// ---------- 배선 ----------

test("검사가 확장과 같은 파일을 싣는다", need, async () => {
  // ★ **`harness.js` 가 실을 파일을 따로 적으면 `background.js` 와 갈린다**(§132).
  //   새 파일을 `ST_FILES` 에 더하고 harness 를 안 고치면, 검사는 **그 파일 없이**
  //   도는 확장을 재게 된다 — 통과하면서 틀린다.
  const { readFileSync } = await import("node:fs");
  const { fileURLToPath } = await import("node:url");
  const { dirname, join } = await import("node:path");
  const here = dirname(fileURLToPath(import.meta.url));
  const bg = readFileSync(join(here, "..", "src", "background.js"), "utf8");
  const 선언 = [...bg.matchAll(/"src\/([^"]+)\.js"/g)].map((m) => m[1]);
  assert.ok(선언.length >= 5, `ST_FILES 를 ${선언.length} 개밖에 못 읽었다 — 정규식이 늙었다`);
  // 어댑터는 `loadAdapters` 가 따로 싣는다. 나머지는 `loadBroker` 가 전부 실어야 한다.
  const 나머지 = 선언.filter((n) => !n.startsWith("adapters/") && n !== "config.local");
  assert.deepEqual(harness.BROKER_FILES, 나머지,
                   "harness 가 싣는 파일이 background.js 의 ST_FILES 와 다르다");
});

// ---------- 섀도 경계 (DECISIONS §169) ----------

test("호스트는 비어 있고 글자는 섀도 안에 있다", need, async () => {
  // ★ **아무도 안 터지고 번역만 사라지는 종류다.** 섀도 루트가 달린 요소의 자식
  //   노드는 슬롯이 없으면 **렌더 트리에 안 올라간다** — 호스트에 글자를 쓰면
  //   DOM 에는 있고 화면에는 없다. 그러면 「박스가 하나 섰다」 는 전부 초록인데
  //   **사용자는 아무것도 못 본다.** 그래서 두 쪽을 함께 묻는다.
  const { doc } = await 한바퀴(`<p>${긴글("Boundary")}</p>`);
  const n = 박스들(doc)[0];
  assert.ok(n.shadowRoot, "섀도가 안 달렸다");
  assert.equal(속(n).textContent, "번역0", "글자가 섀도 안에 없다");
  // 호스트의 **직접 자식**에는 글자가 없어야 한다.
  assert.equal(n.childNodes.length, 0,
               "호스트에 자식이 생겼다 — 슬롯이 없으므로 그려지지 않는다");
});

test("섀도 안 CSS 가 사이트 규칙에 안 밀린다 — 글자로 확인한다", need, async () => {
  // ★ **jsdom 에는 캐스케이드가 온전하지 않다.** 여기서 재는 것은 「이겼나」 가
  //   아니라 **「안쪽 꾸밈이 경계 안에 들어갔나」** 다 — 이긴다는 것은
  //   `tools/cascade_check.py` 가 진짜 엔진으로 `KILL` 사다리에서 잰다(§169).
  const { doc } = await 한바퀴(`<p>${긴글("Styled")}</p>`);
  const 스타일 = 박스들(doc)[0].shadowRoot.querySelector("style");
  assert.ok(스타일, "섀도 안에 스타일이 없다 — 박스가 맨몸으로 선다");
  assert.match(스타일.textContent, /\.st-몸/, "안쪽 규칙이 안 들어갔다");
});

test("테마를 호스트에도 붙인다", need, async () => {
  // ★ **섀도 선택자는 밖의 조상을 볼 수 없다**(§169). `html[data-st-theme]` 하나로는
  //   안쪽 어두운 면이 영영 안 선다 — 선언은 있고 적용은 0 인 꼴이다.
  const { doc } = await 한바퀴(`<p>${긴글("Theme")}</p>`);
  const n = 박스들(doc)[0];
  assert.ok(n.dataset.stTheme, "호스트에 테마가 없다");
  assert.equal(n.dataset.stTheme, doc.documentElement.dataset.stTheme,
               "호스트와 html 의 테마가 갈렸다 — 두 번 재고 있다");
});

test("뼈대 줄 수가 붙고, 긴 글과 짧은 글이 다르다", need, async () => {
  // ★ **`min-height: 104px` 를 박고 있었다**(DECISIONS §170). 스물두 자 토막도
  //   백네 픽셀을 잡아 목록이 회색 슬래브 바둑판이 됐다. 줄 수가 **안 갈리면**
  //   클래스만 생기고 병은 그대로다 — 그래서 **다르다**를 묻는다.
  const 줄 = (n) => [...n.classList].find((c) => c.startsWith("st-translation--줄"));
  const { doc: 짧 } = await 한바퀴(`<p>${긴글("Short")}</p>`);
  assert.ok(줄(박스들(짧)[0]), "줄 수 클래스가 안 붙었다");
  // jsdom 에는 레이아웃이 없어 폭이 0 이다 — **못 재면 셋**이 맞다(§59).
  assert.equal(줄(박스들(짧)[0]), "st-translation--줄3", "못 재는 데서 셋이 아니다");
});

test("행 다음에 서는 자리는 카드가 아니라 띠다", need, async () => {
  // ★ **모양을 사이트 이름이 아니라 잰 자리에서 고른다**(DECISIONS §170). 목록 행 뒤에
  //   둥근 면과 그림자짜리 카드를 세우면 **원문 행보다 번역이 더 크고 무겁다** —
  //   스무 줄이면 회색 슬래브 스무 장이다.
  //
  // ★ **jsdom 에 레이아웃이 없어 `잴수있나` 가 거짓이다.** 그 한 수만 손보면 **고르는
  //   자는 진짜가 돈다** — `행인가` 는 `matches("tr,[role=row]")` 라 레이아웃이 필요 없다.
  //   흉내를 그 한 줄로 줄인다(§47).
  const { doc } = await 한바퀴(
    `<table><tr><td><span>${긴글("Row anchored")}</span></td></tr></table>`,
    undefined, ["generic"], () => { globalThis.ST.잴수있나 = () => true; });
  const n = 박스들(doc)[0];
  assert.ok(n, "박스가 안 섰다");
  assert.ok(n.classList.contains("st-translation--띠"),
            "행 다음인데 카드로 섰다 — 꼴을 안 가르고 있다");
  assert.equal(n.closest("tr")?.className, "st-translation-row",
               "행 다음 줄에 안 섰다");
});

test("본문 안에 서는 자리는 띠가 아니라 카드다", need, async () => {
  // ★ 음성 대조 — 위 시험이 **언제나 참**이면 아무것도 안 재는 것이다.
  const { doc } = await 한바퀴(`<p>${긴글("Body anchored")}</p>`);
  assert.ok(!박스들(doc)[0].classList.contains("st-translation--띠"),
            "본문인데 띠로 섰다");
});
