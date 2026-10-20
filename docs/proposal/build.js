// 기획서 생성기(DECISIONS §116). 읽는 법은 README.md.
const fs = require("fs");
const path = require("path");
const { D, t, FONT, NAVY } = require("./lib");
const { Document, Packer, Paragraph, Header, Footer, AlignmentType, TextRun, PageNumber } = D;
const { cover, toc, s1, s2 } = require("./part1");
const { part2 } = require("./part2");
const { part3 } = require("./part3");

// ★ **판 이름과 판 날짜를 한 곳에만 적는다**(DECISIONS §189). 머리글 글자와 docx 속성이
//   따로 살면 한쪽만 늙는다(§57). 그리고 이 날짜가 **벽시계가 아니라는 것**이 요점이다 —
//   아래를 보라.
const 판 = { 이름: "3.0", 날짜: new Date("2026-10-14T00:00:00Z") };

// ★ **라이브러리가 벽시계를 박는다 — 옵션이 없다**(docx 9.6.1, DECISIONS §189).
//   `dist/index.cjs` 의 `TimestampElement` 이 `new Date()` 를 그대로 쓴다. `Document` 에
//   `created` 를 줘도 안 읽는다 — 줘 보고 **재서** 확인했다. 그래서 인자 없는 `new Date()`
//   만 판 날짜로 돌린다. `Date.now()` · 인자 있는 `new Date(x)` 는 그대로다.
// ★ **`new Document()` 보다 먼저 건다.** 속성 XML 은 **문서를 만들 때** 짜인다 —
//   `Packer` 직전에 걸었더니 안 걸렸고, 그것도 재서 알았다. 되돌리기는 맨 끝 `finally`.
const 참Date = globalThis.Date;
globalThis.Date = new Proxy(참Date, {
  construct: (T, a) => (a.length ? new T(...a) : new T(판.날짜)),
});

// ★ **벽시계를 산출물에 넣지 않는다**(DECISIONS §189). `dcterms:created` 에
//   `new Date()` 를 넣으면 **소스를 한 글자도 안 고치고 다시 구워도 docx 바이트가 달라진다.**
//   그 docx 는 추적되므로 나무 해시가 달라지고, `apply_patch.sh` 의 바탕 선언(§129 · §130)이
//   **세 번 어긋났다.** 그때마다 나는 패치를 의심했는데 까닭은 여기 있었다.
// ★ §126 은 「docx 는 zip 이라 같은 입력에서 같은 바이트가 안 나온다」 고 적었다 —
//   **안 재고 적은 말이다.** 2026-10-14 에 재니 zip 항목 시각은 이미 고정돼 있고
//   **다른 것은 `docProps/core.xml` 의 두 줄뿐**이었다. 그 둘을 판 날짜로 못 박으면
//   같은 입력에서 **같은 바이트**가 나온다. 아래 자물쇠는 그래서 그대로 둔다 —
//   지문은 「다시 구웠나」 가 아니라 **「무엇으로 구웠나」** 를 적는 것이다.
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
  // ★ **표지에는 머리글도 쪽 번호도 없다.** `titlePage` 를 켜면 첫 쪽만 `first` 를 쓴다 —
  //   빈 것을 주면 표지가 깨끗해진다. 종전에는 제목 위에 「thoth · seshat 기획서 3.0」 이
  //   같이 찍혀 **표지가 제 이름을 두 번 말하고 있었다.**
  sections: [{
    properties: { titlePage: true, page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    headers: {
      first: new Header({ children: [new Paragraph({ children: [] })] }),
      default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [t(`thoth · seshat 기획서 ${판.이름}`, { size: 16, color: "888888" })] })] }) },
    footers: {
      first: new Footer({ children: [new Paragraph({ children: [] })] }),
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "888888" })] })] }) },
    children: [...cover, ...toc, ...s1, ...s2, ...part2, ...part3],
  }],
});
// ★ **산출물과 함께 입력의 지문을 적는다**(DECISIONS §126).
//   `tools/docx_check.py` 가 이것과 지금 생성기를 견주고, 어긋나면 배포가 멈춘다.
//   2026-10-03 까지 이 줄이 없어서 **배포본이 생성기보다 몇 주 뒤진 채로 초록이었다.**
// ★ §126 은 여기 「docx 는 zip 이라 같은 입력에서 같은 바이트가 안 나온다」 고 적어 뒀다.
//   **안 재고 적은 말이었고, 2026-10-14 에 재니 거짓이었다**(DECISIONS §189). 그래도
//   지문은 그대로 둔다 — 지문이 답하는 것은 「바이트가 같나」 가 아니라 **「무엇으로
//   구웠나」** 이고, 그 물음은 바이트가 같아져도 남는다.
const 자물쇠 = () => {
  const crypto = require("crypto");
  const 것 = ["build.js", "html.js", "lib.js", "facts.js", "part1.js", "part2.js", "part3.js",
            "figures/figlib.py", "figures/charts.py", "figures/diagrams.py", "figures/shots.py"];
  const 생성기 = {};
  for (const rel of 것) {
    const q = path.join(__dirname, rel);
    생성기[rel] = fs.existsSync(q)
      ? crypto.createHash("sha256").update(fs.readFileSync(q)).digest("hex").slice(0, 16)
      : "없다";
  }
  // ★ **그림 지문도 여기 적는다**(DECISIONS §189). 이것이 **재현성의 관문**이다 —
  //   그림이 다시 비결정적이 되면(애니메이션 한 줄이면 된다) **소스를 안 고쳐도 이 파일이
  //   매번 달라진다.** `build.lock.json` 은 추적되므로 `git status` 가 그 자리에서 운다.
  //   관문을 따로 세우는 대신 **이미 추적되는 파일을 증인으로 세운다.**
  // ★ `.build/` 는 gitignore 라 없을 수 있다 — 없으면 `없다` 를 적는다. **빈 칸이 아니라
  //   「못 쟀다」 를 적는 것**이 §59 다.
  // ★ **산출물에 실리는 것만 센다 — `f_` 로 시작하는 것들**(DECISIONS §191). 첫 판은
  //   `.build/fig/*.png` 를 **전부** 셌는데, 거기엔 `shot_preview.png` · `shot_popup_on.png` ·
  //   `shot_popup_off.png` 셋이 섞여 있다. 그 셋은 **기획서에 안 들어간다** — `shots.py` 가
  //   `crop(y<2050)` 하고 `trim()` 해서 `f_preview_a` · `f_popup` 을 만든 뒤 버리는 **중간
  //   산출물**이다. 그래서 **잘려 나가는 영역**이 브라우저 판에 따라 달라지면, 산출물은
  //   한 바이트도 안 변했는데 자물쇠만 달라진다.
  // ★ **2026-10-14 에 실제로 그렇게 됐다.** 크로미움 1243(내 기계)과 1248(그의 기계)에서
  //   `proposal.docx` · `site/proposal.html` 이 **바이트까지 같았는데** 자물쇠만 갈렸다.
  //   `f_` 19장의 지문 묶음은 양쪽이 `1cb0d107c9c7f024` 로 같았고, **다른 것은 저 셋뿐**이었다.
  // ★ **짖을 일이 없는데 짖는 개는 곧 무시된다**(§126). 증인은 **산출물에 도달하는 것**이어야
  //   한다 — 도달하지 않는 픽셀을 세면 관문이 아니라 소음이다.
  const 그림 = {};
  const 그림칸 = path.join(__dirname, ".build/fig");
  for (const f of fs.existsSync(그림칸) ? fs.readdirSync(그림칸).sort() : []) {
    if (!f.endsWith(".png") || !f.startsWith("f_")) continue;
    그림[f] = crypto.createHash("sha256").update(fs.readFileSync(path.join(그림칸, f))).digest("hex").slice(0, 16);
  }
  fs.writeFileSync(path.join(__dirname, "build.lock.json"),
  // ★ **`만든때` 를 뺐다**(DECISIONS §189). 이 줄은 아무도 안 읽는데 **매번 달라졌다** —
  //   §129 에 이미 적혀 있다. 「패치가 안 붙었는데 다시 구워 커밋했고 **바뀐 것은
  //   `만든때` 한 줄뿐**이었다」. 그때는 그것을 소음으로만 봤고, 그 소음이 곧 **나무를
  //   흔드는 손**이라는 것은 못 봤다. 언제 구웠는지는 git 이 안다.
    JSON.stringify({ 적는이: "docs/proposal/build.js", 판: 판.이름, 생성기,
                     그림: Object.keys(그림).length ? 그림 : "없다" }, null, 2) + "\n");
};

Packer.toBuffer(doc).then((b) => { const out = process.argv[2] || path.join(__dirname, "../proposal.docx");
  fs.writeFileSync(out, b); 자물쇠(); console.log("ok", out, b.length); })
  .finally(() => { globalThis.Date = 참Date; });
