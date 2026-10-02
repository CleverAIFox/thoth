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
// ★ **산출물과 함께 입력의 지문을 적는다**(DECISIONS §126). docx 는 zip 이라 같은 입력에서
//   같은 바이트가 안 나오므로 바이트로는 「다시 만들었나」 를 못 본다. 그래서 **입력**을 적는다 —
//   `tools/docx_check.py` 가 이것과 지금 생성기를 견주고, 어긋나면 배포가 멈춘다.
//   2026-10-03 까지 이 줄이 없어서 **배포본이 생성기보다 몇 주 뒤진 채로 초록이었다.**
const 자물쇠 = () => {
  const crypto = require("crypto");
  const 것 = ["build.js", "lib.js", "part1.js", "part2.js", "part3.js",
            "figures/figlib.py", "figures/charts.py", "figures/diagrams.py", "figures/shots.py"];
  const 생성기 = {};
  for (const rel of 것) {
    const q = path.join(__dirname, rel);
    생성기[rel] = fs.existsSync(q)
      ? crypto.createHash("sha256").update(fs.readFileSync(q)).digest("hex").slice(0, 16)
      : "없다";
  }
  fs.writeFileSync(path.join(__dirname, "build.lock.json"),
    JSON.stringify({ 적는이: "docs/proposal/build.js", 만든때: new Date().toISOString(), 생성기 }, null, 2) + "\n");
};

Packer.toBuffer(doc).then((b) => { const out = process.argv[2] || path.join(__dirname, "../proposal.docx");
  fs.writeFileSync(out, b); 자물쇠(); console.log("ok", out, b.length); });
