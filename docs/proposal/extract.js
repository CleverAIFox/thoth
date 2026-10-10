// 블록 나무를 낸다 — **`lib` 자리에 기록만 하는 가짜를 끼워** `part*.js` 를 그대로 읽는다.
//
// ★ **이것이 「본문이 포맷 중립인가」 의 증명이다**(DECISIONS §155). 본문이 `docx` 를 직접
//   만지면 여기서 **터진다** — 주장이 아니라 실행으로 갈린다.
// ★ 출력은 JSON 한 덩이다. 판정은 `tools/check_proposal.py` 가 한다 — **재는 곳과 판정하는
//   곳을 나눈다**(DECISIONS §62).
const libPath = require.resolve("./lib");
const 블록 = [];
let 번 = 0;
const 담기 = (종류) => (...a) => {
  번++;
  블록.push({ n: 번, 종류, 글: a.filter((x) => typeof x === "string") });
  return [{ 종류, n: 번 }];   // ★ 펼침(...)으로 쓰는 자리가 있어 배열을 낸다
};
const 가짜 = {};
const 블록이름 = ["P", "GAP", "BR", "PART", "H1", "H2", "H3", "B", "NOTE", "CODE",
                 "TBL", "KV", "FIGURE", "COVER", "TOC"];
for (const k of [...블록이름, "t", "runs"]) 가짜[k] = 담기(k);
Object.assign(가짜, { ROOT: "", RNG: {}, secs: () => "§0–§0", W: 0,
  NAVY: "", RED: "", GRAY: "", FONT: "",
  // ★ `D` 를 **프록시로 둔다** — 본문이 만지면 기록되고, 그 기록이 관문의 증거다
  D: new Proxy({}, { get: () => { 블록.push({ n: ++번, 종류: "DOCX직접", 글: [] }); return function () { return {}; }; } }) });
// ★ **자료는 가짜로 안 만든다 — 정본을 그대로 넘긴다**(DECISIONS §180). 본문이 산문에
//   박지 않고 **읽어 가는 수**라, 여기서 빈 값을 주면 **블록이 안 돌고** 「본문이 끝까지
//   안 돈다」 로만 보인다. 세 번째 렌더러도 같은 자리를 읽어야 한다(§166).
Object.assign(가짜, require("./수"));
require.cache[libPath] = { id: libPath, filename: libPath, loaded: true, exports: 가짜 };

const 난것 = [];
for (const f of ["./part1", "./part2", "./part3"]) {
  let m;
  try { m = require(f); } catch (e) { 난것.push(`${f} 못 읽는다 — ${e.message}`); continue; }
  // ★ **본문은 데이터다**(DECISIONS §155). 내보내는 것이 전부 배열이라 `require` 만으로
  //   블록이 다 모인다. 함수를 내보내면 **부르는 쪽마다 다른 글이 나올 수 있고**, 그러면
  //   이 자가 본 것과 렌더러가 굽는 것이 갈린다.
  //   첫 판은 「함수면 불러 본다」 로 적었는데 **부를 함수가 하나도 없어 죽은 줄**이었다 —
  //   돌연변이가 그것을 살려 보내서 알았다(§145 와 같은 자리).
  for (const [k, v] of Object.entries(m)) {
    if (!Array.isArray(v)) 난것.push(`${f}:${k} 가 배열이 아니다(${typeof v}) — 본문은 데이터다`);
  }
}
process.stdout.write(JSON.stringify({ 블록, 난것, 블록이름 }));
