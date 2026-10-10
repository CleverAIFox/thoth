// **산문이 글자로 박지 않고 읽어 가는 수**(DECISIONS §167 · §180).
//
// ★ **제 모듈이어야 한다.** `html.js` 는 두 번째 렌더러라 `require.cache` 에서 `./lib` 을
//   **가짜로 갈아 끼운다**(§166). 자료를 `lib.js` 안에 두면 docx 에서는 보이고 html 에서는
//   `undefined` 가 된다 — 그리고 **두 산출물이 갈린 채 둘 다 만들어진다.**
//   떼어 두면 두 렌더러가 **같은 자리**를 읽는다.
//
// ★ **잰 수와 정한 수를 섞지 않는다.** `기준선` 은 실측이고 `문턱` 은 설계가 정한 것이다.
//   섞으면 「목표를 이미 넘었다」 를 아무도 못 본다 — 지금 문항 지연이 그 자리다.
const 기준선 = require("../bench/baseline.json");
const 문턱 = require("./targets.json");

/** 첫 페이지 체감 = 콜드 로딩 + 문항 하나. 로컬만 로딩이 붙는다. */
const 체감 = (e) => Math.round((e.cold_load_seconds || 0) + e.sec_per_question);

module.exports = { 기준선, 문턱, 체감 };
