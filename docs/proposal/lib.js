// 기획서 생성기의 공통 도구(DECISIONS §116). 파이어레인 기획서의 모양을 따른다 — 맑은 고딕
// 10pt · 표 머리 D9E2F3 · 제목 1F3864 · 이름 C00000.
const D = require("docx");
const { Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType,
  BorderStyle, PageBreak, ImageRun, VerticalAlign, HeadingLevel } = D;

const FONT = "맑은 고딕";
const MONO = "Consolas";
const W = 9638; // A4 · 좌우 여백 1134(2cm)
const NAVY = "1F3864", RED = "C00000", HEAD = "D9E2F3", SUB = "F2F2F2", GRAY = "555555";
// ★ **포맷을 안 타는 사실은 `facts.js` 하나에 산다**(DECISIONS §166). 두 번째 렌더러
//   (`html.js`)가 같은 것을 쓰고, 베끼면 한쪽만 늙는다.
const { ROOT, SEP, RNG, secs, 그림 } = require("./facts");

const t = (text, o = {}) => new TextRun({ text, font: o.mono ? MONO : FONT, size: o.size || 20, bold: o.bold,
  color: o.color, italics: o.it });

// **굵게** · `코드` 를 런으로 가른다
function runs(s, o = {}) {
  const out = [];
  String(s).split(/(\*\*[^*]+\*\*)/).forEach((seg) => {
    if (!seg) return;
    const bold = seg.startsWith("**") && seg.endsWith("**");
    const body = bold ? seg.slice(2, -2) : seg;
    body.split(/(`[^`]+`)/).forEach((part) => {
      if (!part) return;
      if (part.startsWith("`") && part.endsWith("`") && part.length > 1)
        out.push(t(part.slice(1, -1), { ...o, bold: bold || o.bold, mono: true, size: (o.size || 20) - 2, color: "7A2E0E" }));
      else out.push(t(part, { ...o, bold: bold || o.bold }));
    });
  });
  return out;
}

const P = (s, o = {}) => new Paragraph({ children: runs(s, o), alignment: o.align,
  spacing: { before: o.before || 0, after: o.after ?? 100, line: 300 }, indent: o.indent ? { left: o.indent } : undefined });
const GAP = (n = 100) => new Paragraph({ children: [], spacing: { after: n } });
const BR = () => new Paragraph({ children: [new PageBreak()] });

const PART = (s) => [new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200, after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: NAVY, space: 6 } },
    children: [t(s, { size: 32, bold: true, color: NAVY })] }), GAP(160)];
// ★ **제목도 `runs` 를 쓴다**(DECISIONS §166). 종전에는 `t()` 였고, 그래서 제목에 든
//   `` `bes` `` 가 **백틱째 찍히고 있었다** — 두 번째 렌더러를 세워 글자를 맞대 보고서야
//   났다. 한 자리뿐이라 눈에 안 띄었고, **눈에 안 띄는 것이 안 틀린 것은 아니다.**
const H1 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 160 },
  children: runs(s, { size: 28, bold: true, color: "000000" }) });
const H2 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 220, after: 100 },
  children: runs("□ " + s, { size: 22, bold: true }) });
const H3 = (s) => new Paragraph({ spacing: { before: 140, after: 80 }, children: runs(s, { size: 20, bold: true, color: NAVY }) });
const B = (s, lvl = 0) => new Paragraph({ children: [t(lvl ? "– " : "- ", {}), ...runs(s)],
  indent: { left: 200 + lvl * 300, hanging: 160 }, spacing: { after: 60, line: 290 } });
const NOTE = (s) => new Paragraph({ children: runs(s, { size: 18, color: GRAY }), spacing: { after: 80, line: 270 } });
const CODE = (lines) => lines.map((l, i) => new Paragraph({
  children: [t(l || " ", { mono: true, size: 17 })],
  shading: { type: ShadingType.CLEAR, fill: "F3F4F6", color: "auto" },
  spacing: { after: i === lines.length - 1 ? 140 : 0, line: 250 },
}));

const border = { style: BorderStyle.SINGLE, size: 4, color: "8EA9DB" };
const borders = { top: border, bottom: border, left: border, right: border };

// 셀 안 줄: "○ " 는 소제목풍, "[..]" 는 굵게, "- " 는 들여쓴 항목
function cellParas(s, o = {}) {
  return String(s).split("\n").map((line) => {
    let opt = { size: o.size || 18, bold: o.bold };
    let indent;
    if (/^\[.*\]$/.test(line) || line.startsWith("○ ")) opt.bold = true;
    if (line.startsWith("- ")) indent = { left: 160, hanging: 160 };
    return new Paragraph({ children: runs(line || " ", opt), indent, alignment: o.align,
      spacing: { after: 30, line: 264 } });
  });
}

let TABLE_N = 0;
function TBL(head, rows, widths, o = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const ws = widths.map((w) => Math.round((w / total) * W));
  ws[ws.length - 1] += W - ws.reduce((a, b) => a + b, 0);
  const cell = (s, i, hd, rowHead) => new TableCell({
    width: { size: ws[i], type: WidthType.DXA }, borders, verticalAlign: VerticalAlign.CENTER,
    shading: hd ? { type: ShadingType.CLEAR, fill: HEAD, color: "auto" }
      : rowHead ? { type: ShadingType.CLEAR, fill: SUB, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: cellParas(s, { bold: hd || rowHead, align: hd ? AlignmentType.CENTER : undefined, size: o.size }),
  });
  const out = [];
  if (o.caption) out.push(new Paragraph({ children: [t(`[표 ${++TABLE_N}] ${o.caption}`, { size: 18, bold: true, color: NAVY })], spacing: { before: 80, after: 60 } }));
  out.push(new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: ws,
    rows: [
      ...(head ? [new TableRow({ tableHeader: true, children: head.map((h, i) => cell(h, i, true)) })] : []),
      ...rows.map((r) => new TableRow({ cantSplit: !!o.cantSplit, children: r.map((c, i) => cell(c, i, false, o.rowHead && i === 0)) })),
    ],
  }));
  out.push(GAP(120));
  return out;
}

// 2단 개요표 — 왼쪽 머리칸이 음영
function KV(rows, lw = 1.6) { return TBL(null, rows, [lw, 10 - lw], { rowHead: true }); }

let FIG_N = 0;
// ★ 그림의 사실 선언(figures/figlib.py)을 대체 텍스트에 싣는다. docx_check 가 그것을 다시 대조한다.
function FIGURE(name, caption, widthIn = 6.5) {
  const { data, w, h, facts } = 그림(name);
  const pw = Math.round(widthIn * 96);
  const ph = Math.round((pw * h) / w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 100, after: 40 },
      children: [new ImageRun({ type: "png", data, transformation: { width: pw, height: ph },
        altText: { name, title: caption, description: "src: " + facts.join(SEP) } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
      children: [t(`[그림 ${++FIG_N}] ${caption}`, { size: 18, color: GRAY })] }),
  ];
}

// ★ **표지와 목차도 블록이다**(DECISIONS §155). 종전에는 `part1.js` 가 `docx` 를 직접 만졌다 —
//   열 곳. 그러면 **본문이 렌더러를 침범하고**, 「렌더러가 아는 블록만 굽는다」 가 성립하지 않는다.
//   여기로 올리면 `part*.js` 는 **데이터만** 넘기고, 그 사실을 관문이 걸 수 있다.
const 가운데 = (글, o) => new Paragraph({ alignment: AlignmentType.CENTER,
  spacing: { after: o.after ?? 60 }, children: [t(글, o)] });

/** 표지. `줄` 은 `[글, 모양]` 들이고 모양은 `t()` 가 아는 것 + `after`. */
const COVER = (줄) => [new Paragraph({ children: [], spacing: { before: 1500 } }),
                       ...줄.map(([글, o]) => 가운데(글, o || {}))];

/** 목차. `항목` 은 `[글, 깊이]` — 깊이 0 은 부, 1 은 장.
 *  ★ **필드 목차를 쓰지 않는다.** 웹 뷰어는 필드를 갱신하지 못해 빈 쪽이 된다. */
const TOC = (항목) => [BR(),
  new Paragraph({ children: [t("목차", { size: 28, bold: true, color: NAVY })], spacing: { after: 200 } }),
  ...항목.map(([x, l]) => new Paragraph({
    children: [t(x, { size: l ? 21 : 23, bold: !l, color: l ? "000000" : NAVY })],
    spacing: { before: l ? 0 : 160, after: 80 }, indent: { left: l ? 500 : 100 } }))];

// ★ **본문이 자료를 직접 안 부른다**(DECISIONS §167 · §180). `check_proposal` 이
//   「본문은 `./lib` 만 부른다」 를 지키므로 산출물에서 읽는 수도 여기를 거친다. 다만
//   **값은 `./수` 가 들고 있다** — `html.js` 가 이 파일을 가짜로 갈아 끼우기 때문이다(§166).
const 수 = require("./수");

module.exports = {
  ...수, ROOT, RNG, secs, D, t, runs, P, GAP, BR, PART, H1, H2, H3, B, NOTE, CODE, TBL, KV, FIGURE, COVER, TOC, W, NAVY, RED, GRAY, FONT };
