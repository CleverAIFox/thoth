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

// ★ **저장소가 세면 되는 수는 저장소가 센다**(DECISIONS §167 · §197). 아래 셋은 종전에
//   산문에 글자로 박혀 있었는데, **표 칸 안이라 장부가 못 봤다** — `check_proposal` 의
//   산문 갈래에 `TBL` · `KV` 가 없다(「표는 데이터다」). 1장을 절로 가르자 그 셋이 산문이
//   되면서 **처음으로 세어졌다.** 가려져 있었을 뿐 박혀 있던 것은 그 전에도 같다.
// ★ **읽는 자리는 실물이다.** 용어집이 늘면 기획서가 따라 늘고, 안 따라오면 그것이 흠이다.
const fs = require("fs");
const path = require("path");
const 뿌리 = path.join(__dirname, "../..");

/** 어미 코퍼스의 **줄**. 첫 줄은 `meta` 머리라 뺀다 — 세는 자가 머리를 세면 늘 하나 많다. */
const 어미코퍼스줄 = () => {
  const 줄 = fs.readFileSync(path.join(뿌리, "worker/tests/endings/corpus.jsonl"), "utf8")
    .split("\n").filter((x) => x.trim());
  return 줄.length - (줄[0] && JSON.parse(줄[0]).meta ? 1 : 0);
};

// ★ **파이썬 상수를 글자로 읽는다.** 기본값이 `guard.py` 에 살고 그것이 정본이다 —
//   여기 다시 적으면 **같은 수가 두 곳에 살고 한쪽만 고쳐진다**(§91). 못 찾으면 터진다:
//   조용히 0 을 내면 **기획서가 「월 상한 0 자」 라고 말한다.**
const 월상한자 = () => {
  const 글 = fs.readFileSync(path.join(뿌리, "worker/app/guard.py"), "utf8");
  const m = /MAX_CHARS_PER_MONTH",\s*"(\d+)"/.exec(글);
  if (!m) throw new Error("guard.py 에서 MAX_CHARS_PER_MONTH 를 못 읽었다 — 꼴이 바뀌었다");
  return Number(m[1]);
};

const 센것 = {
  용어집항목: Object.keys(require(path.join(뿌리, "worker/app/glossary/aws.json"))).length,
  어미코퍼스줄: 어미코퍼스줄(),
  월상한자: 월상한자(),
};

/** 천 단위 쉼표. 산문이 `2,472` 로 적으므로 읽어 온 수도 같은 꼴이어야 한다. */
const 쉼표 = (n) => n.toLocaleString("en-US");

/** 로컬 엔진 대비 몇 배 빠른가. **환산이지 실측이 아니다** — 두 실측에서 나온다. */
const 로컬대비배수 = Math.round(기준선.engines.local.speed.sec_per_question
                          / 기준선.engines.bedrock.speed.sec_per_question);

module.exports = { 기준선, 문턱, 체감, 센것, 쉼표, 로컬대비배수 };
