// 기획서 생성기(DECISIONS §116). 읽는 법은 README.md.
const fs = require("fs");
const path = require("path");
const { D, t, FONT, NAVY } = require("./lib");
const { Document, Packer, Paragraph, Header, Footer, AlignmentType, TextRun, PageNumber } = D;
const { cover, toc, s1, s2 } = require("./part1");
const { part2 } = require("./part2");
const { part3 } = require("./part3");

const doc = new Document({
  creator: "오창준", title: "thoth · seshat 기획서", description: "영어 자격증 문제 화면 번역 확장과 자체 영한 번역 모델",
  styles: {
    default: { document: { run: { font: FONT, size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: FONT }, paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, font: FONT }, paragraph: { spacing: { before: 220, after: 100 }, outlineLevel: 1 } },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [t("thoth · seshat 기획서 2.0", { size: 16, color: "888888" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "888888" })] })] }) },
    children: [...cover, ...toc, ...s1, ...s2, ...part2, ...part3],
  }],
});
Packer.toBuffer(doc).then((b) => { const out = process.argv[2] || path.join(__dirname, "../proposal.docx");
  fs.writeFileSync(out, b); console.log("ok", out, b.length); });
