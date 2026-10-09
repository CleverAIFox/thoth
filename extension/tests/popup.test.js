// 팝업이 번역기와 **같은 사슬**을 쓰는가(DECISIONS §173).
//
// ★ **팝업이 제 사슬을 따로 들고 있었고 그 사슬이 한 칸 짧았다.** 번역기는
//   `storage → config.local.js → 127.0.0.1` 인데 팝업은 `storage → 127.0.0.1` 이었다.
//   ext-build 에서는 기계 기본값이 그 파일에 있으므로, **번역은 람다로 멀쩡히 가는데
//   팝업만 로컬을 두드리고 「워커에 닿지 못했다」 를 띄웠다.** 2026-10-07 실물에서 났다.
//
// ★ **값을 맞추는 규칙 대신 함수를 같이 쓴다**(§91 · §132). 「양쪽이 같아야 한다」 가
//   문서에 필요하다는 것 자체가 **이미 갈렸다는 신호**다.
//
// ★ **jsdom 이 필요 없다.** 사슬은 순수 함수이고, 배선은 **어디에 적혔는가**가 본체다.
import assert from "node:assert/strict";
import { test } from "node:test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const 뿌리 = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const 읽 = (rel) => fs.readFileSync(path.join(뿌리, rel), "utf8");
/** 주석을 지운다. **글을 코드로 읽으면 제 주석이 증거가 된다.** */
const 벗긴다 = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

/** `config.local.js` 와 `client.js` 를 팝업과 **같은 순서로** 올린다. */
function 올린다(config = { endpoint: "", token: "" }) {
  delete globalThis.ST;
  new Function(읽("src/config.local.js"))();
  globalThis.ST.CONFIG = config;
  new Function(읽("src/client.js"))();
  return globalThis.ST;
}

// ---------- 사슬 ----------

test("팝업 값이 파일을 이기고, 파일이 기본값을 이긴다", () => {
  const ST = 올린다({ endpoint: "https://람다/translate", token: "t-파일" });
  assert.equal(ST.쓸주소("https://팝업/translate", false), "https://팝업/translate");
  assert.equal(ST.쓸주소("", false), "https://람다/translate", "파일을 안 본다");
  assert.equal(ST.쓸토큰("t-팝업", false), "t-팝업");
  assert.equal(ST.쓸토큰("", false), "t-파일", "토큰도 파일을 안 본다");
});

test("파일이 비면 로컬 기본값이 선다", () => {
  const ST = 올린다();
  assert.equal(ST.쓸주소("", false), "http://127.0.0.1:8000/translate");
  assert.equal(ST.쓸토큰("", false), "");
});

test("픽스처는 팝업 값도 파일 토큰도 이긴다", () => {
  // ★ 손을 기억에 맡기면 지어낸 문장이 배포본에 과금된다(DECISIONS §106).
  const ST = 올린다({ endpoint: "https://람다/translate", token: "t-파일" });
  assert.equal(ST.쓸주소("https://팝업/translate", true), ST.FIXTURE_ENDPOINT);
  assert.equal(ST.쓸토큰("t-팝업", true), "", "픽스처에 토큰을 싣는다");
});

// ---------- 배선 : 사슬이 하나인가 ----------

test("팝업이 기본 주소를 제 글자로 안 들고 있다", () => {
  // ★ **같은 값이 두 곳에 살면 한쪽만 고쳐진다**(§91). 팝업에 그 글자가 돌아오면
  //   사슬이 다시 갈린다 — 그리고 갈린 것은 **아무도 안 터지고 거짓말만 한다.**
  // ★ **주석을 먼저 걷는다.** 첫 판이 **제 주석에 걸렸다** — 「`127.0.0.1` 이 박혀
  //   있었다」 고 적은 줄이 「박혀 있다」 로 세어졌다. §168 의 `#555`, §171 의 `&#39;`
  //   와 같은 모양이다. **글을 코드로 읽는 검사는 글부터 지운다.**
  const popup = 벗긴다(읽("src/popup.js"));
  assert.ok(!/127\.0\.0\.1|localhost|https?:\/\//.test(popup),
            "popup.js 에 주소가 글자로 박혀 있다 — ST.쓸주소 를 쓴다");
});

test("팝업이 번역기와 같은 함수를 부른다", () => {
  const popup = 읽("src/popup.js");
  for (const 이름 of ["쓸주소", "쓸토큰"])
    assert.ok(popup.includes(`ST.${이름}(`), `팝업이 ST.${이름} 를 안 쓴다`);
  // ★ **번역기도 그 함수를 써야 한다.** 한쪽만 쓰면 사슬이 둘인 채로 이름만 같다.
  const client = 읽("src/client.js");
  assert.match(client, /const url = globalThis\.ST\.쓸주소\(/);
  assert.match(client, /const token = globalThis\.ST\.쓸토큰\(/);
});

test("팝업이 사슬을 올리고 나서 제 모듈을 올린다", () => {
  // ★ **순서가 틀리면 `ST.쓸주소` 가 없는 채로 팝업이 돈다** — 터지고 팝업이 통째로
  //   하얗게 뜬다. 클래식 스크립트는 순서대로, 모듈은 그 뒤다.
  const html = 읽("popup.html");
  const 자리 = ["src/config.local.js", "src/client.js", "src/popup.js"]
    .map((f) => html.indexOf(f));
  assert.ok(자리.every((i) => i >= 0), `popup.html 이 셋을 다 안 싣는다 : ${자리}`);
  assert.deepEqual([...자리].sort((a, b) => a - b), 자리, "싣는 순서가 어긋났다");
  assert.ok(!/type="module"[^>]*config\.local|type="module"[^>]*client\.js/.test(html),
            "사슬을 모듈로 실으면 늦게 돈다");
});

test("client.js 는 최상위에 부수효과가 없다", () => {
  // ★ **팝업에서 실어도 아무 일이 안 일어나야 한다.** 최상위에서 `chrome.*` 을 부르거나
  //   타이머를 걸면 팝업을 열 때마다 그것이 돈다 — 그 자리를 글자로 막는다.
  const client = 읽("src/client.js");
  const 본문 = 벗긴다(client).split("\n")
    .filter((l) => /^\S/.test(l));                  // 들여쓰기 없는 줄 = 최상위
  // `globalThis.ST.X = …` · `globalThis.ST.X ??= …` 만 허용한다.
  const 난것 = 본문.filter((l) => !/^globalThis\.ST\.\S+\s*\?{0,2}=/.test(l)
                                  && l.trim() !== "};" && l.trim() !== "}"
                                  && l.trim() !== "");
  assert.deepEqual(난것, [], "client.js 최상위에 정의가 아닌 줄이 있다");
});

test("검사가 진짜로 무는가", () => {
  // ★ **0 건이 목표인 검사는 0 건을 성공으로만 읽으면 안 된다**(§152). 합성으로 물어본다.
  assert.ok(/127\.0\.0\.1|localhost|https?:\/\//.test('const u = "http://127.0.0.1:8000/x";'));
  assert.ok(!/127\.0\.0\.1|localhost|https?:\/\//.test('const u = ST.쓸주소(s.stEndpoint, false);'));
  const 나쁜순서 = '<script type="module" src="src/popup.js"></script>\n<script src="src/client.js"></script>';
  const 자리 = ["src/client.js", "src/popup.js"].map((f) => 나쁜순서.indexOf(f));
  assert.notDeepEqual([...자리].sort((a, b) => a - b), 자리, "순서 검사가 안 문다");
});
