// 기획서 생성기의 공통 도구(DECISIONS §116). 파이어레인 기획서의 모양을 따른다 — 맑은 고딕
// 10pt · 표 머리 D9E2F3 · 제목 1F3864 · 이름 C00000.
const fs = require("fs");
const path = require("path");
const D = require("docx");
const { Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType,
  BorderStyle, PageBreak, ImageRun, VerticalAlign, HeadingLevel } = D;

const FONT = "맑은 고딕";
const MONO = "Consolas";
const W = 9638; // A4 · 좌우 여백 1134(2cm)
const NAVY = "1F3864", RED = "C00000", HEAD = "D9E2F3", SUB = "F2F2F2", GRAY = "555555";
const ROOT = path.resolve(__dirname, "../..");
const FIG = path.join(__dirname, ".build/fig") + "/";
const SEP = " ¦ "; // 사실 구분자. tools/docx_check.py 와 같다

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
const H1 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 160 },
  children: [t(s, { size: 28, bold: true, color: "000000" })] });
const H2 = (s) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 220, after: 100 },
  children: [t("□ " + s, { size: 22, bold: true })] });
const H3 = (s) => new Paragraph({ spacing: { before: 140, after: 80 }, children: [t(s, { size: 20, bold: true, color: NAVY })] });
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

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), data: b };
}
let FIG_N = 0;
// ★ 그림의 사실 선언(figures/figlib.py)을 대체 텍스트에 싣는다. docx_check 가 그것을 다시 대조한다.
function FIGURE(name, caption, widthIn = 6.5) {
  const f = FIG + name + ".png";
  const factsFile = FIG + name + ".facts.json";
  if (!fs.existsSync(factsFile)) throw new Error(`${name}: 사실 선언이 없다 — figures/ 를 먼저 돌린다`);
  const facts = JSON.parse(fs.readFileSync(factsFile, "utf8"));
  const { w, h, data } = pngSize(f);
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

module.exports = { ROOT, RNG, secs, D, t, runs, P, GAP, BR, PART, H1, H2, H3, B, NOTE, CODE, TBL, KV, FIGURE, W, NAVY, RED, GRAY, FONT };
