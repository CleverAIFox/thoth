// 렌더러가 **둘 다** 쓰는 사실들 — 포맷을 안 타는 것만 여기 산다(DECISIONS §166).
//
// ★ **정본이 하나여야 한다**(DECISIONS §91). 두 번째 렌더러를 세우면서 `decisionsRanges`
//   를 베끼면 **한쪽만 늙는다** — 날짜 → 절 범위는 `docx` 와도 `html` 과도 상관이 없다.
// ★ **여기에 포맷이 들어오면 안 된다.** `docx` 도 태그도 import 하지 않는다. 그 규칙을
//   `tools/check_proposal.py` 가 글자로 본다 — 규칙으로 지키는 일관성은 언젠가 깨진다.
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");
const FIG = path.join(__dirname, ".build/fig") + "/";
const SEP = " ¦ "; // 사실 구분자. tools/docx_check.py 와 같다

// DECISIONS 의 날짜 줄 → { 날짜: [첫 절, 끝 절] }. figures/figlib.py 의 decisions_ranges 와 같은 규칙
function decisionsRanges() {
  const out = {};
  let cur = null;
  for (const line of fs.readFileSync(path.join(ROOT, "docs/DECISIONS.md"), "utf8").split("\n")) {
    let m = line.match(/^## §(\d+)\./);
    if (m) { cur = +m[1]; continue; }
    m = line.match(/^\*\*(\d{4}-\d{2}-\d{2})\*\*$/);
    if (m && cur !== null) {
      const [a, b] = out[m[1]] || [cur, cur];
      out[m[1]] = [Math.min(a, cur), Math.max(b, cur)];
      cur = null;
    }
  }
  return out;
}

const RNG = decisionsRanges();
const secs = (...days) => {
  const a = Math.min(...days.map((d) => RNG[d][0])), b = Math.max(...days.map((d) => RNG[d][1]));
  return a === b ? `§${a}` : `§${a}–§${b}`;
};

/** 그림 하나의 (png 바이트, 가로, 세로, 사실 선언). 선언이 없으면 **터진다** — 조용히 안 싣는다. */
function 그림(name) {
  const f = FIG + name + ".png";
  const factsFile = FIG + name + ".facts.json";
  if (!fs.existsSync(factsFile)) throw new Error(`${name}: 사실 선언이 없다 — figures/ 를 먼저 돌린다`);
  const data = fs.readFileSync(f);
  return { data, w: data.readUInt32BE(16), h: data.readUInt32BE(20),
           facts: JSON.parse(fs.readFileSync(factsFile, "utf8")) };
}

module.exports = { ROOT, FIG, SEP, decisionsRanges, RNG, secs, 그림 };
