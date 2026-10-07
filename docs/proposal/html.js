// 기획서의 **두 번째 렌더러**(DECISIONS §166). `part*.js` 를 한 글자도 안 고치고 HTML 을 굽는다.
//
// ★ **이것이 「본문이 포맷 중립이다」 의 증명이다.** §155 가 `extract.js` 로 **기록만 하는
//   가짜**를 끼워 「본문이 docx 를 안 만진다」 까지 왔다. 거기서 멈추면 그 말은 **아직
//   주장**이다 — 블록 어휘로 **실제 산출물이 하나 더 나와야** 증명이 끝난다.
// ★ **같은 수법이다.** `require.cache` 에 `lib` 자리를 가로채고, 같은 이름 열다섯에
//   HTML 을 내는 몸을 끼운다. 다른 점은 **기록이 아니라 산출**이라는 것뿐이다.
// ★ **한 파일로 굽는다.** 그림은 `data:` 로 싣는다 — CDN 도 옆 파일도 없다. 받은 사람이
//   파일 하나를 열면 그걸로 끝이고, **그물이 끊겨도 보인다**(종전 화면은 `jsdelivr` 에서
//   `docx-preview` 를 받아 와 브라우저에서 docx 를 풀었다).
// ★ **쪽 번호·머리말·꼬리말은 없다.** HTML 에 쪽이 없다 — 「없는 것을 흉내내지 않는다」.
//   그 자리는 `docx` 가 맡고, 정본은 여전히 `docs/proposal.docx` 다.
const fs = require("fs");
const path = require("path");
const { ROOT, SEP, RNG, secs, 그림 } = require("./facts");

const libPath = require.resolve("./lib");
// ★ **그림을 못 구운 나무에서도 돌아야 한다**(DECISIONS §168). `--그림없이` 는 자리와
//   설명만 내고 PNG 를 비운다 — `check_proposal` 이 `.build/fig` 가 없을 때 그렇게 부른다.
const 그림없이 = process.argv.includes("--그림없이");
// ★ **따옴표까지 바꾼다**(DECISIONS §171). 2026-10-05 에 `&` · `<` · `>` 셋만 바꿨고,
//   그 값이 **속성 안에** 들어가는 자리가 둘 있었다 — `data-st-fig="…"` 와 `alt="…"`.
//   본문 글자에서는 셋이면 되지만 **속성 안에서는 `"` 하나로 속성이 끝난다.** 그 뒤에
//   오는 글자가 **새 속성으로 읽힌다**(`onerror=` 를 포함해서). CodeQL 이 이틀 동안
//   경보 둘로 들고 있었고 `doctor` 는 그동안 「CI 가 초록으로 봤다」 를 찍었다.
//
// ★ **함수를 둘로 안 나눈다.** 「본문용」 과 「속성용」 을 나누면 **언젠가 틀린 쪽을 쓴다** —
//   그리고 틀린 쪽을 쓴 것은 아무도 안 터지고 산출물만 깨진다. 다섯을 전부 바꾸는 한 함수면
//   **고를 일이 없다.** 본문에서 `&quot;` 가 되는 것은 브라우저가 `"` 로 그리므로 같고,
//   `check_proposal` 의 두 렌더러 대조는 `html.unescape` 를 거치므로 글자도 그대로다.
//
// ★ **빈말이 아니다.** `facts` 는 `.build/fig/*.facts.json` 에서 오고 그 글은
//   DECISIONS 에서 나온다 — 거기 큰따옴표가 **993 개** 있다. 하나만 그림 선언에 들어오면
//   `alt` 가 그 자리에서 끝나고, `docx_check` 의 `check_figures` 는 **깨진 글을 사실로 읽는다.**
const esc = (s) => String(s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#x27;");

// **굵게** · `코드` — `lib.js` 의 `runs` 와 **같은 가름**이다. 가름이 갈리면 두 산출물의
// 글자가 달라지고, 그 차이는 **아무 검사도 안 본다** — 그래서 `check_proposal` 이 두 쪽의
// 정규식을 글자로 맞댄다(DECISIONS §166).
function 굵게(s) {
  return String(s).split(/(\*\*[^*]+\*\*)/).map((seg) => {
    if (!seg) return "";
    const bold = seg.startsWith("**") && seg.endsWith("**");
    const body = bold ? seg.slice(2, -2) : seg;
    const 속 = body.split(/(`[^`]+`)/).map((part) => {
      if (!part) return "";
      const 코드 = part.startsWith("`") && part.endsWith("`") && part.length > 1;
      const 글 = esc(코드 ? part.slice(1, -1) : part);
      return 코드 ? `<code>${글}</code>` : 글;
    }).join("");
    return bold ? `<b>${속}</b>` : 속;
  }).join("");
}

let 표번 = 0, 그림번 = 0;
const 셀 = (s) => String(s).split("\n").map((l) => {
  const 머리 = /^\[.*\]$/.test(l) || l.startsWith("○ ");
  const 항목 = l.startsWith("- ");
  const 글 = 굵게(l || " ");
  const 갈래 = 머리 ? ' class="ch"' : 항목 ? ' class="ci"' : "";
  return `<div${갈래}>${머리 ? `<b>${글}</b>` : 글}</div>`;
}).join("");

function 표(head, rows, widths, o = {}) {
  const 합 = widths.reduce((a, b) => a + b, 0);
  const col = widths.map((w) => `<col style="width:${((w / 합) * 100).toFixed(2)}%">`).join("");
  const 머리 = head ? `<thead><tr>${head.map((h) => `<th>${셀(h)}</th>`).join("")}</tr></thead>` : "";
  const 몸 = rows.map((r) => `<tr>${r.map((c, i) =>
    `<td${o.rowHead && i === 0 ? ' class="rh"' : ""}>${셀(c)}</td>`).join("")}</tr>`).join("");
  const 캡 = o.caption ? `<p class="cap">[표 ${++표번}] ${굵게(o.caption)}</p>` : "";
  return [`${캡}<table><colgroup>${col}</colgroup>${머리}<tbody>${몸}</tbody></table>`];
}

const 가짜 = {
  ROOT, RNG, secs, W: 0, NAVY: "1F3864", RED: "C00000", GRAY: "555555", FONT: "맑은 고딕",
  // ★ **`D` 를 만지면 터진다.** `extract.js` 는 기록만 하지만 이쪽은 **굽는 중**이라
  //   조용히 넘기면 **반쪽짜리 산출물**이 나온다 — 없는 것은 없다고 터뜨린다.
  D: new Proxy({}, { get(_t, k) { throw new Error(`본문이 docx 를 직접 만졌다 — D.${String(k)}`); } }),
  t: (s) => [esc(s)],
  runs: (s) => [굵게(s)],
  P: (s, o = {}) => [`<p${o.indent ? ' class="ind"' : ""}>${굵게(s)}</p>`],
  GAP: () => ['<div class="gap"></div>'],
  BR: () => ['<hr class="pb">'],
  PART: (s) => [`<h1 class="part">${esc(s)}</h1>`],
  H1: (s) => [`<h2>${굵게(s)}</h2>`],
  H2: (s) => [`<h3>□ ${굵게(s)}</h3>`],
  H3: (s) => [`<h4>${굵게(s)}</h4>`],
  B: (s, lvl = 0) => [`<p class="b l${lvl}">${lvl ? "– " : "- "}${굵게(s)}</p>`],
  NOTE: (s) => [`<p class="note">${굵게(s)}</p>`],
  CODE: (lines) => [`<pre>${lines.map((l) => esc(l || " ")).join("\n")}</pre>`],
  TBL: 표,
  KV: (rows, lw = 1.6) => 표(null, rows, [lw, 10 - lw], { rowHead: true }),
  // ★ **그림 없이도 굽는다**(DECISIONS §168). `.build/fig` 는 gitignore 라 **깨끗한 사본에
  //   없다** — CI 가 바로 그 사본이다. 그림을 요구하면 **관문이 CI 에서 2 로 죽고**,
  //   그러면 「두 렌더러가 같은 글을 받았나」 를 **CI 에서 영영 안 묻는다.**
  // ★ **묻는 것은 PNG 바이트가 아니라 글이다.** 자리와 설명은 그대로 내고 그림만 비운다 —
  //   `FIGURE` 의 캡션이 두 렌더러 대조에 그대로 든다.
  // ★ **「비웠다」 를 글로 적는다.** 조용히 빈 `<figure>` 를 내면 배포본에서도 그럴 수 있다.
  FIGURE: (name, caption) => {
    const 캡 = `<figcaption>[그림 ${++그림번}] ${esc(caption)}</figcaption>`;
    if (그림없이) return [`<figure data-st-fig="${esc(name)}" data-st-빈그림="1">${캡}</figure>`];
    const { data, facts } = 그림(name);
    return [`<figure><img alt="${esc(facts.join(SEP))}" src="data:image/png;base64,${data.toString("base64")}">`
            + 캡 + `</figure>`];
  },
  COVER: (줄) => [`<section class="cover">${줄.map(([글]) => `<p>${esc(글)}</p>`).join("")}</section>`],
  TOC: (항목) => [`<nav class="toc"><h2>목차</h2>${항목.map(([x, l]) =>
    `<p class="l${l ? 1 : 0}">${esc(x)}</p>`).join("")}</nav>`],
};
require.cache[libPath] = { id: libPath, filename: libPath, loaded: true, exports: 가짜 };

const { cover, toc, s1, s2 } = require("./part1");
const { part2 } = require("./part2");
const { part3 } = require("./part3");
const 몸 = [...cover, ...toc, ...s1, ...s2, ...part2, ...part3].join("\n");

// ★ **색은 여섯 자리로 적는다**(DECISIONS §166). 세 자리 꼴(샵 다음 숫자 셋)은
//   `docx_check.bare_ref_fails` 가 **문서명 없는 PLAN 행 번호**로 읽는다 — 그 자의 머리말이
//   「16진 색은 네 자리라 안 걸린다」 고 적고 있었는데 **세 자리 꼴을 안 봤다.**
//   자를 느슨하게 하는 대신 **글자를 맞춘다** — 느슨해진 자는 다음에 진짜를 놓친다.
const 꾸밈 = `
:root { --navy:#1f3864; --red:#c00000; --gray:#555555; --head:#d9e2f3; --sub:#f2f2f2; --line:#8ea9db; }
* { box-sizing:border-box }
body { margin:0; background:#eef1f5; color:#111111;
  font:10.5pt/1.75 "맑은 고딕","Malgun Gothic",-apple-system,system-ui,sans-serif; }
main { max-width:900px; margin:0 auto; padding:48px 56px 80px; background:#ffffff;
  box-shadow:0 1px 3px rgba(0,0,0,.12); }
p { margin:0 0 6px } p.ind { margin-left:14px }
h1.part { font-size:17pt; color:var(--navy); text-align:center; border-bottom:1.5px solid var(--navy);
  padding-bottom:8px; margin:40px 0 18px }
h2 { font-size:14.5pt; margin:22px 0 10px } h3 { font-size:11.5pt; margin:16px 0 7px }
h4 { font-size:10.5pt; color:var(--navy); margin:11px 0 5px }
p.b { margin:0 0 4px; padding-left:14px; text-indent:-14px }
p.b.l1 { padding-left:30px; text-indent:-14px }
p.note { font-size:9pt; color:var(--gray); margin:0 0 6px }
code { font:9.5pt/1.5 Consolas,ui-monospace,monospace; color:#7a2e0e }
pre { font:8.5pt/1.5 Consolas,ui-monospace,monospace; background:#f3f4f6; padding:9px 11px;
  margin:0 0 10px; overflow-x:auto; white-space:pre }
table { width:100%; border-collapse:collapse; margin:0 0 12px; font-size:9pt; table-layout:fixed }
th,td { border:.5pt solid var(--line); padding:4px 7px; vertical-align:middle; word-break:break-word }
th { background:var(--head); text-align:center } td.rh { background:var(--sub); font-weight:700 }
td .ci { padding-left:12px; text-indent:-12px }
p.cap { font-size:9pt; font-weight:700; color:var(--navy); margin:8px 0 4px }
figure { margin:12px 0 16px; text-align:center } figure img { max-width:100%; height:auto }
figcaption { font-size:9pt; color:var(--gray); margin-top:5px }
.gap { height:7px } hr.pb { border:0; border-top:1px dashed #cfd6e0; margin:26px 0 }
.cover { text-align:center; padding:90px 0 40px } .cover p { margin:0 0 10px }
.toc { margin:0 0 28px } .toc h2 { color:var(--navy) } .toc p.l0 { font-weight:700; color:var(--navy); margin-top:12px }
.toc p.l1 { padding-left:20px }
.hd { background:#0e1116; color:#e6ebf2; padding:16px 24px }
.hd h1 { margin:0; font-size:12.5pt }
.hd p { margin:5px 0 0; color:#8b97a8; font-size:9pt; max-width:900px }
.hd a { color:#6fa8dc } .hd code { color:#9ec5fe }
@media print { .hd { display:none } }
@media (max-width:760px) { main { padding:28px 16px 60px } body { font-size:11pt } }
@media print { body { background:#ffffff } main { box-shadow:none; max-width:none; padding:0 } hr.pb { page-break-after:always; border:0 } }
`.trim();

const out = process.argv.find((x, i) => i >= 2 && !x.startsWith("--"))
  || path.join(ROOT, "site/proposal.html");
fs.writeFileSync(out, `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>thoth · seshat 기획서</title>
<style>${꾸밈}</style>
</head>
<body>
<header class="hd">
  <h1>thoth · seshat 기획서</h1>
  <p>이 화면은 <b>제출본과 같은 본문</b>에서 구운 것이다 — <code>part*.js</code> 하나에서 docx 와 HTML 이
     함께 나온다(DECISIONS §166). 정본은 <code>docs/proposal.docx</code> 다.
     <a href="./proposal.docx" download>원본 내려받기</a> ·
     <a href="https://github.com/CleverAIFox/thoth">저장소</a></p>
</header>
<main>
${몸}
</main>
</body>
</html>
`);
console.log("ok", out, fs.statSync(out).size);
