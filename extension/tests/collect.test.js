// **수집 — 거름망 · 상한 · 새지 않음**(DECISIONS §183).
//
// ★ **거름망의 수는 HTTP Archive 2026-09 에서 쟀다**(모바일 · 1% · n≈91,000).
//   `tr` 있는 페이지 ~12% · `li` ~76% · 셋 합 ~87%. 종전 기본값 `tr,[role=row]` 는
//   **열에 아홉에서 아무것도 안 잡았다.**
//
// ★ **「얼마나 다른가」 는 안 쟀다.** 같은 데이터에 지문 정의만 바꾸니 61.4% 와
//   15.3% 가 나왔다 — 그 수는 웹이 아니라 **내가 고른 지문**을 재고 있었다. 그래서
//   이 판은 **모으기만 하고 값을 주장하지 않는다.** 1주 뒤 사람이 읽고 정한다(§133).
//
// ★ **이 판에는 보낼 데가 없다.** 워커도 DB 도 안 쓴다 — 주 35건짜리에 파이프라인을
//   짓는 것이 「없는 병에 관문을 세우는 것」이다. 그 약속을 아래가 붙든다.
import assert from "node:assert/strict";
import { test } from "node:test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { 코드벗긴다 } from "./strip.js";

let harness = null;
try {
  harness = await import("./harness.js");
} catch {
  // jsdom 미설치. 도는 검사만 skip 하고 순수 함수 · 글자 검사는 그대로 돈다.
}
const need = { skip: harness ? false : "jsdom 이 없다 — npm install (extension/)" };

const 뿌리 = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const 읽 = (rel) => fs.readFileSync(path.join(뿌리, rel), "utf8");

/** `지문.js` 를 올려 `ST.꼴` 을 꺼낸다. **DOM 도 chrome 도 필요 없다.** */
function 꼴올린다() {
  const 전 = globalThis.ST;
  globalThis.ST = undefined;
  new Function(읽("src/지문.js"))();
  const 꼴 = globalThis.ST.꼴;
  globalThis.ST = 전;
  return 꼴;
}

const 꼴 = 꼴올린다();

// ── 지문 — 순수 함수 ────────────────────────────────────────────────────

test("지문은 구조 태그만 든다 — SVG 내부를 안 센다", () => {
  // ★ **이 한 줄이 61.4% 와 15.3% 를 갈랐다**(§183). `path` · `circle` ·
  //   `fecolormatrix` 를 세면 **아이콘 세트가 다르다는 이유로 구조가 다르다**고 센다.
  const a = 꼴.지문({ div: 300, section: 9, path: 40, circle: 12, fecolormatrix: 8 });
  const b = 꼴.지문({ div: 300, section: 9, path: 2, circle: 99, use: 30 });
  assert.equal(a, b, "아이콘이 다른 같은 구조를 다른 꼴로 센다");
  assert.equal(a, "div,section");
});

test("문턱 아래 태그는 꼴이 아니다", () => {
  // 어느 페이지에나 div 하나쯤은 있다. 한두 개짜리를 세면 지문이 소음이 된다.
  assert.equal(꼴.지문({ div: 300, aside: 1, form: 4 }), "div");
  assert.equal(꼴.지문({ div: 300, aside: 5, form: 5 }), "div,aside,form");
});

test("같은 꼴이면 같은 글자다 — 입력 순서를 안 탄다", () => {
  assert.equal(꼴.지문({ section: 9, div: 300 }), 꼴.지문({ div: 300, section: 9 }));
});

test("빈 입력에도 안 터진다", () => {
  // ★ **못 센 것과 0 은 다르다**(§59). 둘 다 빈 지문이지만 **던지지는 않아야** 한다.
  assert.equal(꼴.지문({}), "");
  assert.equal(꼴.지문(null), "");
  assert.equal(꼴.지문(undefined), "");
});

// ── 거름망 ──────────────────────────────────────────────────────────────

test("행 경계가 잡힌 페이지는 안 모은다", () => {
  const r = 꼴.모을까({ div: 999 }, true);
  assert.equal(r.모은다, false);
  assert.equal(r.왜, "덮였다");
});

test("div 가 얇으면 안 모은다 — 번역할 것이 없는 페이지다", () => {
  // ★ 실측 : 안 덮인 페이지의 div 중위값이 AMP 10 · 맨 HTML 14 였다(§183).
  const r = 꼴.모을까({ div: 14 }, false);
  assert.equal(r.모은다, false);
  assert.match(r.왜, /얇다/);
});

test("안 덮였고 div 가 두꺼우면 모은다", () => {
  // ★ 실측 : Webflow 243 · Skolengo 241 · Framer 235 — 이쪽이 진짜 div soup 이다.
  const r = 꼴.모을까({ div: 243 }, false);
  assert.equal(r.모은다, true);
});

test("문턱 바로 양쪽을 가른다", () => {
  assert.equal(꼴.모을까({ div: 꼴.최소div - 1 }, false).모은다, false);
  assert.equal(꼴.모을까({ div: 꼴.최소div }, false).모은다, true);
});

test("안 모으는 까닭이 서로 다른 말이다", () => {
  // ★ **「안 모은다」 가 두 뜻이다.** 하나로 뭉치면 장부를 읽을 수 없다(§59).
  const 덮 = 꼴.모을까({ div: 999 }, true).왜;
  const 얇 = 꼴.모을까({ div: 3 }, false).왜;
  assert.notEqual(덮, 얇);
});

// ── 두 경계가 갈라져 있다 ───────────────────────────────────────────────

test("덮임 경계가 li 를 맨 앞에 든다", () => {
  // ★ **쟀다** : tr ~12% · li ~76% · 셋 합 ~87%(HTTP Archive 2026-09, §183).
  //   「표가 행이다」 는 Udemy 를 보고 세운 가정이었고, 웹 전체에서는 **열에 아홉이
  //   표가 없다.** 그래서 「이 페이지 구조를 아는가」 는 넷으로 묻는다.
  assert.match(꼴.덮임경계, /^li\b/);
  for (const s of ["li", "tr", "[role=row]", "article"]) {
    assert.ok(꼴.덮임경계.includes(s), `${s} 가 덮임 경계에 없다`);
  }
});

test("꽂는 경계는 안 넓혔다", () => {
  // ★ **안 잰 것으로 고치지 않는다**(§133). 내가 쟀던 것은 「구조를 아는가」 이고
  //   `행경계` 는 **상자를 어디에 꽂을까**를 정한다 — 다른 질문이다. `mount.test.js`
  //   가 「`li` 까지 넣으면 Udemy 쪽 자리가 같이 바뀐다」 고 적어 뒀고, 그 병은
  //   **아직 안 쟀다.** 측정 하나로 두 질문을 같이 답한 척하지 못하게 못 박는다.
  assert.ok(!꼴.행경계.includes("li"), "꽂는 경계에 li 가 들어왔다 — 그 병을 먼저 재라");
  assert.notEqual(꼴.행경계, 꼴.덮임경계);
});

test("경계 글자가 코드에 정본 한 곳뿐이다", () => {
  // ★ **종전에는 `"tr,[role=row]"` 가 네 자리에 박혀 있었다**(§91). 한 자리만 고치면
  //   나머지가 조용히 옛 값을 쓴다 — 그 꼴을 되돌리지 못하게 센다.
  // ★ **주석은 센 데서 뺀다.** 이 집안이 제 설명에 걸린 적이 여럿이다(§168 · §182).
  const 셈 = [];
  for (const rel of ["src/지문.js", "src/broker.js", "src/cssaudit.js",
                     "src/adapters/generic.js", "src/adapters/standard.js",
                     "src/adapters/udemy.js"]) {
    const 코드 = 코드벗긴다(읽(rel));
    for (const m of 코드.matchAll(/\[role=row\]/g)) 셈.push(`${rel}:${m.index}`);
  }
  // 정본 파일에 둘(행경계 · 덮임경계), 나머지 파일에 **영**이다.
  assert.equal(셈.length, 2, `경계 글자가 ${셈.length} 곳에 있다 : ${셈}`);
  assert.ok(셈.every((x) => x.startsWith("src/지문.js")), `정본 밖에 있다 : ${셈}`);
});

test("지문.js 가 그것을 읽는 자들보다 먼저 실린다", () => {
  // ★ **글자 울타리를 치웠으니 순서가 계약이 됐다.** 종전에는 `cssaudit.js` 와
  //   `generic.js` 가 `|| "tr,[role=row]"` 를 들고 있어서 순서가 틀려도 **옛 값으로
  //   조용히 돌았다**(§91). 이제 `cssaudit.js` 의 `||=` 는 **평가 시점에** 돌므로
  //   `지문.js` 가 그보다 뒤면 `행경계` 가 `undefined` 로 굳는다.
  // ★ **한 번도 안 돌아 본 가지를 만들지 않는다**(§182 · §305). 순서는 눈으로 맞출
  //   것이 아니라 묻는 것이다.
  const 목록 = [...읽("src/background.js").matchAll(/"src\/([^"]+\.js)"/g)].map((m) => m[1]);
  const 지문 = 목록.indexOf("지문.js");
  assert.notEqual(지문, -1, "ST_FILES 에 지문.js 가 없다");
  for (const n of 목록.filter((x) => x === "cssaudit.js" || x.startsWith("adapters/"))) {
    assert.ok(지문 < 목록.indexOf(n), `지문.js 가 ${n} 보다 뒤에 있다`);
  }
});

test("어댑터만 실어도 경계가 선다", () => {
  // ★ **jsdom 없이도 돈다**(DECISIONS §209). 종전에는 `harness` 를 거쳤는데 그 모듈
  //   임포트가 jsdom 에 달려 있어, jsdom 이 없으면 `harness` 가 `null` 이 되고 이
  //   줄이 **TypeError 로 터졌다** — 이 시험만 `need` 표시를 안 달았기 때문이다.
  //   `need` 를 다는 쪽은 **건너뛴 시험이 CI 에서 한 번도 안 도는 길**이고(§192),
  //   이 판정에는 DOM 이 필요 없다. 그래서 파일 둘을 **직접** 평가한다.
  // ★ **브로커는 안 싣는다.** 그게 요점이다 — 어댑터만으로 경계가 서야 한다.
  globalThis.ST = { adapters: [] };
  new Function(읽("src/지문.js"))();
  new Function(읽("src/adapters/generic.js"))();
  // ★ **오늘 터진 자리다.** `generic.js` 가 행 경계를 `ST.꼴` 에서 읽게 되자,
  //   `loadAdapters` 만 부르는 검사 여섯이 `closest(undefined)` 로 **던졌다.**
  //   배선이 끊기면 터지는 쪽이라 조용하지는 않았지만, **같은 끊김을 다시 겪지
  //   않도록 여기서 묻는다** — 검사 틀이 실제 배경과 같은 것을 싣는가(§173).
  assert.equal(typeof globalThis.ST?.행경계, "string");
  assert.ok(globalThis.ST.꼴?.덮임경계);
});

// ── 장부 — 담기는 칸 · 상한 · 안 나감 ───────────────────────────────────

test("장부에 담기는 칸이 선언된 것뿐이다", need, async () => {
  const { 장부, ST } = await 한판({ div: 300 });
  assert.equal(장부.length, 1);
  // ★ **양쪽을 다 본다.** 「담긴 것 ⊆ 선언」 만 보면 **선언이 넓어지는 것을 못 잡는다**
  //   — 2026-10-12 에 선언에 `"길"` 을 끼워 넣어도 검사가 초록이었다. 넓어진 선언은
  //   다음 사람이 「담아도 되는 칸」 으로 읽는다. 그러면 유출이 **합법이 된다**.
  const 더있는것 = Object.keys(장부[0]).filter((k) => !ST.담을칸.includes(k));
  assert.deepEqual(더있는것, [], `선언 안 된 칸이 담겼다 : ${더있는것}`);
  const 안담기는것 = ST.담을칸.filter((k) => !(k in 장부[0]));
  assert.deepEqual(안담기는것, [], `선언만 있고 안 담기는 칸이 있다 : ${안담기는것}`);
});

test("경로도 글자도 안 담긴다", need, async () => {
  // ★ **수집이 본문을 들고 나가면 그것은 수집이 아니라 유출이다**(§183 · §131 과 같은 결).
  //   `pageUrl` 은 중복 비교에만 쓰고 어디에도 안 담는다.
  const { 장부 } = await 한판({ div: 300 });
  const 글 = JSON.stringify(장부);
  assert.ok(!글.includes("/비밀경로"), "경로가 담겼다");
  assert.ok(!글.includes(본문글), "본문 글자가 담겼다");
  assert.ok(!/https?:\/\//.test(글), "주소가 담겼다");
});

test("네트워크로 한 바이트도 안 나간다", need, async () => {
  const { 부름 } = await 한판({ div: 300 });
  assert.equal(부름.length, 0, `수집이 워커를 불렀다 : ${JSON.stringify(부름)}`);
});

test("하루 상한을 넘겨 안 담는다", need, async () => {
  // 오늘 날짜로 상한만큼 채워 두고 한 판 더 돌린다.
  const 오늘 = new Date().toISOString().slice(0, 10);
  const 미리 = [];
  for (let i = 0; i < 하루상한(); i++) 미리.push({ 지문: `전${i}`, 날: 오늘 });
  const { 장부 } = await 한판({ div: 300 }, { st수집: 미리 });
  assert.equal(장부.length, 하루상한(), "상한을 넘겨 담았다");
});

test("어제 것은 오늘 상한을 안 먹는다", need, async () => {
  // ★ **상한은 하루치다.** 전부를 세면 장부가 차는 날 수집이 영영 멈춘다.
  const 미리 = [];
  for (let i = 0; i < 하루상한(); i++) 미리.push({ 지문: `전${i}`, 날: "2020-01-01" });
  const { 장부 } = await 한판({ div: 300 }, { st수집: 미리 });
  assert.equal(장부.length, 하루상한() + 1, "어제 것이 오늘 상한을 먹었다");
});

test("같은 꼴은 한 번만 담는다", need, async () => {
  const 첫판 = await 한판({ div: 300 });
  const { 장부 } = await 한판({ div: 300 }, { st수집: 첫판.장부 });
  assert.equal(장부.length, 1, "같은 지문을 두 번 담았다");
});

test("덮인 페이지는 장부에 안 간다", need, async () => {
  // li 가 있으면 행 경계가 잡힌다 → 거름망이 막는다
  const { 장부 } = await 한판({ div: 300, li: 1 });
  assert.equal(장부.length, 0);
});

test("얇은 페이지는 장부에 안 간다", need, async () => {
  const { 장부 } = await 한판({ div: 3 });
  assert.equal(장부.length, 0);
});

// ── 글자로 묻는 자리 ────────────────────────────────────────────────────

test("지문.js 에 DOM 도 네트워크도 저장소도 없다", () => {
  // ★ **순수하다는 말을 글로만 적지 않는다.** 순수해야 돌연변이가 물 수 있고
  //   브라우저 없이 시험할 수 있다 — 그 약속이 깨지면 여기서 운다.
  const 코드 = 코드벗긴다(읽("src/지문.js"));
  for (const 금지 of ["document", "fetch", "chrome", "location", "window", "XMLHttp"]) {
    assert.ok(!코드.includes(금지), `지문.js 가 ${금지} 를 든다 — 순수하지 않다`);
  }
});

test("브로커의 수집 경로에 보내는 자가 없다", () => {
  // ★ 이 판에는 **보낼 데가 없다**(§183). `/collect` 가 생기는 날 이 검사가 먼저 운다.
  const 코드 = 코드벗긴다(읽("src/broker.js"));
  const 머리 = 코드.indexOf("const 쌓는다");
  const 꼬리 = 코드.indexOf("const 수집만한다");
  assert.ok(머리 > 0 && 꼬리 > 머리, "쌓는다 를 못 찾았다 — 검사가 늙었다");
  const 몸 = 코드.slice(머리, 꼬리);
  for (const 금지 of ["fetch", "sendMessage", "XMLHttp", "navigator.send"]) {
    assert.ok(!몸.includes(금지), `쌓는다 가 ${금지} 를 쓴다`);
  }
  assert.ok(몸.includes("chrome.storage.local"), "쌓는다 가 저장소를 안 쓴다");
});

// ── 받침 ────────────────────────────────────────────────────────────────

const 본문글 = "A shard stores records for the stream in this one long sentence here.";

function 하루상한() {
  const m = 코드벗긴다(읽("src/broker.js")).match(/const 하루상한 = (\d+)/);
  assert.ok(m, "하루상한 선언을 못 찾았다 — 검사가 늙었다");
  return Number(m[1]);
}

/** 태그 개수를 지정해 문서를 짓고 브로커를 한 판 돌린다.
 *
 * ★ **단언 뒤에 `b.stop()` 을 두면 안 된다**(§177). 단언이 터지면 그 줄을 못 지나고
 *   `setInterval` 이 남아 러너가 영영 안 끝난다 — 「살아남음」 과 「300초 타임아웃」 은
 *   다른 말이다(§59). 그래서 여기서 `try … finally` 로 감싼다. */
async function 한판(개수, 저장소 = {}, 옵 = {}) {
  const { loadAdapters, makeDoc, loadBroker, fakeChrome } = harness;
  // ★ `지문.js` 는 `loadBroker` 가 싣는다 — `BROKER_FILES` 가 `background.js` 의
  //   `ST_FILES` 에서 뽑히므로 **여기서 따로 실으면 실제와 다른 배선을 재게 된다**.
  await loadAdapters(["generic"]);
  let html = `<p>${본문글}</p>`;
  for (let i = 0; i < (개수.div || 0); i++) html += "<div></div>";
  for (let i = 0; i < (개수.li || 0); i++) html += `<ul><li>${본문글}</li></ul>`;
  makeDoc(html, { url: "https://example.com/비밀경로?q=1" });
  const c = fakeChrome({ stOff: true, ...저장소 });
  globalThis.chrome = c.api;
  // ★ **흉내가 아니라 덫이다.** 이 판의 수집은 네트워크를 안 쓴다 — 부르면 잡힌다.
  const 부름 = [];
  globalThis.fetch = async (url, init) => {
    부름.push({ url: String(url), body: init?.body ?? null });
    return { ok: true, status: 200, json: async () => ({}) };
  };
  const b = await loadBroker();
  try {
    await new Promise((r) => setTimeout(r, 30));
    // ★ **두 순회를 재려면 DOM 을 휘저어야 한다.** 아무 변화가 없으면 브로커가
    //   주기를 `POLL_MAX` 까지 늘린다 — 그냥 기다리면 **한 판만 돌고 통과한다**(§177).
    if (옵.휘젓기) {
      document.body.appendChild(document.createElement("div"));
      await new Promise((r) => setTimeout(r, 2600));   // POLL_MS 1500 을 한 번 넘긴다
    }
    return { 장부: c.store.st수집 || [], 부름, ST: globalThis.ST, store: c.store };
  } finally {
    b.stop();
  }
}

test("장부가 끝없이 자라지 않는다", need, async () => {
  // ★ **상한이 둘이다.** `하루상한` 은 하루치고 `장부최대` 는 **총량**이다 — 어제
  //   것까지 쌓이면 1년이면 천 건이 되고, 저장소가 아니라 **읽는 사람이** 터진다.
  const 어제 = new Date(Date.now() - 86400e3).toISOString().slice(0, 10);
  const 미리 = Array.from({ length: 200 }, (_, i) => ({
    k: "col", v: 2, 지문: `낡은꼴${i}`, 날: 어제, div: 300,
  }));
  const { 장부 } = await 한판({ div: 300 }, { st수집: 미리 });
  assert.equal(장부.length, 200, "총량 상한을 안 지켰다");
  // **앞에서 버린다** — 새것이 남고 가장 낡은 것이 나간다.
  assert.ok(!장부.some((x) => x.지문 === "낡은꼴0"), "가장 낡은 것이 안 나갔다");
  assert.ok(장부.some((x) => x.지문 && !String(x.지문).startsWith("낡은꼴")),
            "새 기록이 안 들어왔다");
});

test("같은 페이지를 순회마다 다시 세지 않는다", need, async () => {
  // ★ **순회는 한 페이지에서 수십 번 돈다**(§102). 매번 세면 `ST.수집` 이 같은
  //   기록으로 가득 차서 **상한에 걸려 진짜 변화가 밀려 나간다** — 조용한 쪽이다.
  const { ST } = await 한판({ div: 300 }, {}, { 휘젓기: true });
  const 센것 = (ST.수집 || []).filter((x) => x.k === "col");
  assert.equal(센것.length, 1, `같은 꼴을 ${센것.length} 번 셌다`);
});
