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

let 표번 = 0, 그림번 = 0, 자리번 = 0;
const 제목들 = [];
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
  // ★ **곁목차를 손 목록에서 만들지 않는다.** `TOC` 는 **사람이 적은 목록**이라 본문과
  //   어긋날 수 있고, 어긋나도 아무도 안 운다. 곁목차는 **실제로 찍힌 제목**에서 만든다 —
  //   없는 자리로는 못 가고, 제목이 늘면 저절로 따라온다(seshat DECISIONS §302 와 같은 꼴).
  PART: (s) => { const id = `p${++자리번}`; 제목들.push({ id, 글: s.trim(), 부: true });
                 return [`<h1 class="part" id="${esc(id)}">${esc(s)}</h1>`]; },
  H1: (s) => { const id = `p${++자리번}`; 제목들.push({ id, 글: String(s).replace(/[*`]/g, "").trim(), 부: false });
               return [`<h2 id="${esc(id)}">${굵게(s)}</h2>`]; },
  // ★ **`□` 는 워드의 글머리다.** docx 는 글자로 찍을 수밖에 없지만 화면에는 **모양으로
  //   그릴 수단이 있다** — 없는 것을 흉내내지 않는 것과 같은 자리다. 글자를 안 넣으므로
  //   두 렌더러 대조도 그대로다(대조는 블록이 받은 **글**을 본다).
  H2: (s) => [`<h3>${굵게(s)}</h3>`],
  H3: (s) => [`<h4>${굵게(s)}</h4>`],
  // ★ **글머리도 모양으로 그린다**(`□` 와 같은 자리). docx 는 글자로 찍을 수밖에 없고
  //   화면에는 수단이 있다 — 글자를 안 넣으므로 두 렌더러 대조는 그대로다.
  B: (s, lvl = 0) => [`<p class="b l${lvl}">${굵게(s)}</p>`],
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
  // ★ **두 번째 렌더러도 앞장을 세 덩어리로 낸다**(DECISIONS §166). docx 는 쪽으로,
  //   HTML 은 구획으로 가른다 — 「없는 것을 흉내내지 않는다」 라 쪽 나눔은 `<hr class="pb">`
  //   하나로 족하고, 보이는 위계는 docx 와 같은 차례여야 한다.
  COVER: (표) => [
    `<section class="cover">`
    + `<p class="label">${esc(표.라벨)}</p>`
    + `<h1 class="mark">${esc(표.이름)}</h1>`
    + `<p class="sub">${esc(표.부제)}</p>`
    + `<p class="lede">${(표.한줄 || []).map(esc).join("<br>")}</p>`
    + `<dl class="meta">${(표.메타 || []).map(([n, v]) => `<dt>${esc(n)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>`
    + (표.판 ? `<p class="stamp">${esc(표.판)}</p>` : "")
    + `</section>`,
    `<hr class="pb">`,
    `<section class="pre"><h2>${esc(표.전제제목 || "전제")}</h2>`
    + (표.전제 || []).map((s) => `<p class="note">${굵게(s)}</p>`).join("")
    + `</section>`,
  ],
  TOC: (항목) => [`<nav class="toc"><h2>목차</h2>${항목.map(([x, l]) =>
    `<p class="l${l ? 1 : 0}">${esc(x)}</p>`).join("")}</nav>`],
};
// ★ **자료는 가짜가 아니라 정본을 그대로 넘긴다**(DECISIONS §180). 여기서 다시 적으면
//   같은 수가 두 렌더러에 따로 살고 **두 산출물이 갈린 채 둘 다 만들어진다**(§91 · §166).
Object.assign(가짜, require("./수"));
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
/* ★ **웹판은 docx 를 흉내내지 않는다**(DECISIONS §166 의 그 원칙을 모양에도 적용한다).
   머리말은 일찍이 「쪽 번호·머리말·꼬리말은 없다 — 없는 것을 흉내내지 않는다」 고 적어
   뒀는데, **색과 글꼴과 선은 docx 값을 그대로 베끼고 있었다** — 표 머리 D9E2F3, 칸마다
   실선, 맑은 고딕, 단위가 pt, 그리고 회색 바탕 위에 **종이 한 장을 그리는 그림자**까지.
   화면에서 쪽은 없는 것이므로 종이도 없는 것이다. 정본은 그대로 \`docs/proposal.docx\` 다.
   ★ **그물은 안 탄다.** 글꼴은 **깔려 있으면 쓰고 없으면 물러나는** 목록으로만 적는다 —
   한 파일로 열리는 것이 이 산출물의 계약이다. */
:root{
  --ink:#171c24; --dim:#5d6876; --faint:#8b94a3; --bg:#ffffff; --panel:#f6f8fa;
  --line:#e2e7ee; --rule:#cbd3de; --navy:#1b4f8a; --red:#b3242b; --mark:#7a2e0e;
  --measure:46rem;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ink:#e4e9f0; --dim:#9aa5b4; --faint:#6f7988; --bg:#0f1318; --panel:#161b22;
    --line:#242b35; --rule:#333c48; --navy:#7fb0e6; --red:#e8707a; --mark:#d9a07a;
  }
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.78 "Pretendard Variable",Pretendard,-apple-system,"Apple SD Gothic Neo",
       "Noto Sans KR","맑은 고딕","Malgun Gothic",system-ui,sans-serif;
  -webkit-text-size-adjust:100%}
.hd{border-bottom:1px solid var(--line);padding:18px 24px;background:var(--panel)}
.hd h1{margin:0;font-size:1rem;font-weight:700;letter-spacing:-.01em}
.hd p{margin:6px 0 0;color:var(--dim);font-size:.8125rem;line-height:1.6;max-width:62rem}
.hd a{color:var(--navy)}
.wrap{display:grid;grid-template-columns:16rem minmax(0,1fr);gap:0;align-items:start}
/* 곁목차 — 실제 제목에서 만든다 */
.side{position:sticky;top:0;max-height:100vh;overflow-y:auto;padding:26px 14px 40px;
  border-right:1px solid var(--line);font-size:.8125rem}
.side b{display:block;margin:0 0 10px;padding-left:10px;color:var(--faint);
  font-size:.6875rem;font-weight:700;letter-spacing:.14em}
.side a{display:block;padding:4px 10px;border-radius:5px;color:var(--dim);text-decoration:none;
  line-height:1.45}
.side a:hover{background:var(--panel);color:var(--ink)}
.side a.pt{margin-top:12px;color:var(--navy);font-weight:700}
main{max-width:66rem;margin:0 auto;padding:36px 40px 120px;min-width:0}
main>p,main>.b,main>.note,main>.ind{max-width:var(--measure)}
p{margin:0 0 .7em}
p.ind{margin-left:1em}
h1.part{margin:72px 0 26px;padding-bottom:12px;border-bottom:2px solid var(--navy);
  font-size:1.5rem;font-weight:800;color:var(--navy);letter-spacing:-.015em}
h2{margin:48px 0 14px;font-size:1.25rem;font-weight:700;letter-spacing:-.01em;scroll-margin-top:16px}
h3{position:relative;margin:34px 0 10px;padding-left:.85em;font-size:1.0625rem;font-weight:700;color:var(--ink)}
h3::before{content:"";position:absolute;left:0;top:.42em;width:.3em;height:.9em;background:var(--navy);border-radius:1px}
h4{margin:20px 0 6px;font-size:.9375rem;font-weight:700;color:var(--navy)}
p.b{position:relative;margin:0 0 .4em;padding-left:1.15em;max-width:var(--measure)}
p.b::before{content:"";position:absolute;left:.3em;top:.78em;width:.34em;height:1.5px;
  background:var(--faint)}
p.b.l1{padding-left:2.3em}
p.b.l1::before{left:1.45em;width:.26em}
p.note{margin:0 0 .6em;color:var(--dim);font-size:.875rem;line-height:1.7;max-width:var(--measure)}
code{font:.875em/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--mark);
  background:var(--panel);padding:.08em .34em;border-radius:4px}
pre{margin:0 0 1em;padding:14px 16px;background:var(--panel);border:1px solid var(--line);
  border-radius:8px;overflow-x:auto;white-space:pre;
  font:.8125rem/1.6 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
/* ★ **표는 가로선만 쓴다.** 칸마다 선을 두르면 종이의 꼴이고, 화면에서는 **글보다 격자가
   먼저 읽힌다.** 머리는 바탕색 대신 **글자 꼴**로 가른다. */
table{width:100%;border-collapse:collapse;margin:0 0 1.2em;font-size:.875rem;
  table-layout:fixed;line-height:1.6}
th,td{padding:10px 12px;vertical-align:top;text-align:left;word-break:break-word;
  border-bottom:1px solid var(--line)}
th{border-bottom:1.5px solid var(--rule);color:var(--dim);font-size:.75rem;font-weight:700;
  letter-spacing:.06em;white-space:nowrap}
tbody tr:last-child td{border-bottom:1.5px solid var(--rule)}
td.rh{font-weight:700;color:var(--ink);background:transparent}
td .ch{font-weight:700;margin-top:.3em}
td .ci{padding-left:.9em;text-indent:-.9em}
p.cap{margin:1.4em 0 .4em;color:var(--dim);font-size:.8125rem;font-weight:700}
figure{margin:1.4em 0 1.8em;text-align:center}
figure img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:8px}
figcaption{margin-top:.6em;color:var(--dim);font-size:.8125rem}
.gap{height:.5em}
hr.pb{border:0;border-top:1px solid var(--line);margin:56px 0}
/* 표지 */
.cover{text-align:center;padding:72px 0 24px}
.cover .label{margin:0 0 20px;font-size:.75rem;font-weight:700;letter-spacing:.42em;color:var(--navy)}
.cover .mark{margin:0;font-size:clamp(2.4rem,6vw,3.4rem);font-weight:800;color:var(--red);
  letter-spacing:-.02em;border:0}
.cover .mark::after{content:"";display:block;width:220px;height:2px;margin:16px auto 22px;
  background:var(--navy)}
.cover .sub{margin:0 0 12px;font-size:1.125rem;font-weight:700;max-width:none}
.cover .lede{margin:0 auto;max-width:40rem;color:var(--dim);font-size:.9375rem;line-height:1.8}
.cover .meta{display:grid;grid-template-columns:auto auto;justify-content:center;
  column-gap:18px;row-gap:9px;margin:60px 0 0;text-align:left;font-size:.875rem}
.cover .meta dt{color:var(--navy);font-weight:700;text-align:right;letter-spacing:.06em}
.cover .meta dd{margin:0}
.cover .stamp{margin:28px auto 0;padding-top:16px;max-width:28rem;border-top:1px solid var(--line);
  color:var(--faint);font-size:.75rem}
.pre h2{margin:0 0 12px;padding-bottom:10px;border-bottom:1px solid var(--rule);
  font-size:1.125rem;color:var(--navy)}
.pre .note{margin:0 0 1em}
/* 본문 안 목차(사람이 적은 것) — 곁목차와 다른 물건이라 모양도 다르게 둔다 */
.toc{margin:0 0 2em;padding:20px 22px;background:var(--panel);border:1px solid var(--line);
  border-radius:10px;max-width:var(--measure)}
.toc h2{margin:0 0 10px;font-size:1rem;color:var(--navy)}
.toc p{margin:0;font-size:.875rem}
.toc p.l0{margin-top:12px;font-weight:700;color:var(--navy)}
.toc p.l1{padding-left:1.1em;color:var(--dim)}
@media (max-width:980px){
  .wrap{grid-template-columns:1fr}
  .side{position:static;max-height:none;border-right:0;border-bottom:1px solid var(--line);
    padding:16px 18px;display:flex;flex-wrap:wrap;gap:2px}
  .side b{width:100%;padding-left:0}
  .side a{padding:4px 8px}
  .side a.pt{margin-top:0}
  main{padding:24px 18px 80px}
}
@media print{
  :root{--ink:#111111;--dim:#555555;--bg:#ffffff;--panel:#f4f6f8;--line:#c9d1dc;--rule:#9aa6b5;
        --navy:#1f3864;--red:#c00000}
  .hd,.side{display:none}
  .wrap{display:block}
  main{max-width:none;padding:0}
  hr.pb{page-break-after:always;border:0;margin:0}
  h1.part{page-break-before:always}
  table{font-size:9pt} th,td{padding:4px 7px}
}
`.trim();

// ★ **곁목차는 본문이 실제로 낸 제목에서 만든다.** 사람이 적은 `TOC` 와 어긋날 수 있고,
//   어긋나면 **클릭해도 없는 자리로 간다.** 여기서 만들면 그 일이 구조적으로 안 생긴다.
// ★ **어긋난 것은 말한다.** 막지는 않는다 — 목차 글은 줄여 적는 자리가 있어서 **다른 것이
//   곧 틀린 것은 아니다.** 다만 **말없이 넘어가지는 않는다**(DECISIONS §46 과 같은 꼴).
const 곁목차 = 제목들.map((h) =>
  `<a class="${esc(h.부 ? "pt" : "")}" href="#${esc(h.id)}">${esc(h.글)}</a>`).join("");
{
  const 손 = (toc.join("").match(/<p class="l[01]">([^<]*)<\/p>/g) || [])
    .map((x) => x.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim());
  const 실 = 제목들.map((h) => h.글.replace(/\s+/g, " ").trim());
  const 빠진 = 실.filter((x) => !손.includes(x));
  if (빠진.length) console.error(`  ※ 목차에 없는 제목 ${빠진.length} : ${빠진.slice(0, 4).join(" · ")}`);
}

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
<div class="wrap">
<aside class="side"><b>차례</b>${곁목차}</aside>
<main>
${몸}
</main>
</div>
</body>
</html>
`);
console.log("ok", out, fs.statSync(out).size);
