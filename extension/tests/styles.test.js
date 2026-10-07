// 스타일이 한 곳에만 사는가(DECISIONS §132).
//
// ★ **묻는 것은 「이 값이 맞나」 가 아니라 「값이 두 곳에 있나」 다**(족 가드).
//   전자로 적으면 새로 들어온 인라인 스타일이 검사를 비켜 간다. 2026-09-16 에
//   `udemy.js` 가 세 값을 CSS 와 함께 들고 있었고, `MASTER §10` 이 「양쪽 값이
//   같아야 한다」 를 **규칙으로** 적고 있었다 — 규칙으로 지키는 일관성은
//   언젠가 한쪽만 고쳐진다(§91).
//
// ★ **jsdom 이 필요 없다.** 파일을 글자로 읽는다. DOM 이 본체가 아니라
//   **어디에 적혔는가**가 본체다.
import assert from "node:assert/strict";
import { test } from "node:test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const 뿌리 = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const css = fs.readFileSync(path.join(뿌리, "content.css"), "utf8");

function 소스들() {
  const 것 = [];
  (function 걷는다(d) {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) 걷는다(p);
      else if (e.name.endsWith(".js")) 것.push([path.relative(뿌리, p), fs.readFileSync(p, "utf8")]);
    }
  })(path.join(뿌리, "src"));
  return 것;
}

test("어댑터가 스타일 값을 JS 에 적지 않는다", () => {
  const 난것 = [];
  for (const [rel, 글] of 소스들()) {
    if (!rel.includes("adapters")) continue;
    글.split("\n").forEach((l, i) => {
      if (/\.style\.setProperty\(|\.style\.[A-Za-z]+\s*=|\.style\.cssText/.test(l))
        난것.push(`${rel}:${i + 1}  ${l.trim()}`);
    });
  }
  assert.deepEqual(난것, [], "값은 content.css 에 적고 JS 는 클래스만 붙인다(§132)");
});

test("검사가 진짜로 무는가", () => {
  // ★ **0 건이 목표인 검사는 0 건을 성공으로만 읽으면 안 된다.** 합성 줄로 물어본다.
  const 합성 = ['node.style.setProperty("width", "100%", "important");',
                "node.style.display = \"block\";",
                "node.style.cssText = \"x\";"];
  for (const l of 합성)
    assert.ok(/\.style\.setProperty\(|\.style\.[A-Za-z]+\s*=|\.style\.cssText/.test(l), `못 잡는다 — ${l}`);
  assert.ok(!/\.style\.setProperty\(|\.style\.[A-Za-z]+\s*=|\.style\.cssText/.test('node.classList.add("st-translation--wide");'),
    "클래스를 붙이는 줄까지 잡는다 — 그러면 고칠 길이 없다");
});

test("JS 가 붙이는 st 클래스가 CSS 에 전부 있다", () => {
  // ★ **클래스 이름은 두 곳에 사는 글자다.** 한쪽만 고치면 스타일이 조용히 안 먹는다 —
  //   아무도 안 터지고 박스만 이상해진다. 그것이 가장 늦게 발견되는 종류다.
  const 붙인것 = new Set();
  for (const [, 글] of 소스들())
    for (const m of 글.matchAll(/classList\.add\(\s*["'`]([^"'`]+)["'`]/g))
      for (const c of m[1].split(/\s+/)) if (c.startsWith("st-")) 붙인것.add(c);
  assert.ok(붙인것.size > 0, "classList.add 를 하나도 못 찾았다 — 검사가 아무것도 안 보고 있다");
  const 없는것 = [...붙인것].filter((c) => !css.includes(`.${c}`));
  assert.deepEqual(없는것, [], "content.css 에 없는 클래스를 붙인다");
});

test("비상구의 값이 바탕 규칙과 같다", () => {
  // ★ **값이 한 파일 안에 두 번 적힌다** — 비상구는 세기만 올리는 자리라 피할 수 없다.
  //   그러면 검사가 둘을 묶는다(DECISIONS §131 의 태그 이름과 같은 처방).
  //
  // ★ **목록을 손으로 들지 않는다**(DECISIONS §169 — 손으로 든 목록이 짧아서 열일곱을
  //   못 봤다). 바탕 규칙이 선언한 것을 **읽어서** 비상구에 그대로 있는지 본다.
  //   `margin` 과 사용자 지정 속성은 「깨지는 쪽」 이 아니라 취향이라 뺀다.
  const 바탕 = css.match(/\.st-translation\.st-translation \{([\s\S]*?)\n\}/)?.[1];
  const 비상구 = css.match(/\.st-translation--wide\.st-translation--wide \{([\s\S]*?)\n\}/)?.[1];
  assert.ok(바탕 && 비상구, "두 규칙 중 하나를 못 찾았다 — 검사가 아무것도 안 보고 있다");

  const 뺀다 = new Set(["margin"]);
  const 짝 = [...바탕.matchAll(/\n\s*([a-z-]+):\s*([^;]+);/g)]
    .map(([, k, v]) => [k, v.trim()])
    .filter(([k]) => !k.startsWith("--") && !뺀다.has(k));
  assert.ok(짝.length >= 4, `바탕 선언을 ${짝.length} 개밖에 못 읽었다 — 정규식이 늙었다`);
  for (const [속성, 값] of 짝)
    assert.match(비상구, new RegExp(`\\n\\s*${속성}:\\s*${값.replace(/[(){}[\]*+?.\\^$|]/g, "\\$&")}\\s*!important`),
      `비상구에 ${속성}: ${값} 이 없다 — 바탕이 지면 받을 자리가 없다`);
});

test("선언 전부가 페이지 아니면 섀도 한쪽에 속한다", () => {
  // ★ **이것이 §169 의 족 가드다.** 재는 자(`CSS_EXPECT`)가 **다섯**을 들고 있을 때
  //   바탕 규칙은 **스물둘**을 선언했다 — `padding` · `border-radius` · `background` ·
  //   `box-shadow` · `font-size` · `line-height` · `color` 는 **아무도 안 보고 있었다.**
  //   그래서 지메일에서 박스가 싼티나게 깨져 있는데 콘솔은 조용했다.
  //
  // ★ **고친 길은 목록을 늘리는 것이 아니라 자리를 가른 것이다.** 꾸밈은 섀도 뒤로
  //   갔고 거기서는 질 수가 없다. 페이지에 남은 것만 재면 된다. **그 분류가
  //   빠짐없는지를 여기서 묻는다** — 손으로 든 목록은 또 짧아진다.
  //
  // ★ **묻는 것은 「이 값이 맞나」 가 아니라 「분류 안 된 규칙이 있나」 다.**
  // ★ **섀도인지 먼저 묻는다.** `:host(.st-translation--띠)` 처럼 섀도 규칙도 호스트
  //   클래스 이름을 **인자로** 들기 때문에, 이름만 찾으면 양쪽에 걸친 것처럼 보인다.
  //   가르는 기준은 **어디에 적용되는가**이고 그것은 `:host` · `.st-몸` 의 유무다.
  const 섀도인가 = (s) => s.includes(":host") || s.includes(".st-몸");
  const 페이지틀 = [".st-translation", ".st-translation-row", "html.st-off"];
  const 규칙 = [...css.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/([^{}]+)\{[^{}]*\}/g)]
    .map((m) => m[1].trim())
    .filter((s) => s && !s.startsWith("@") && !/^\d+%/.test(s));
  assert.ok(규칙.length >= 10, `규칙을 ${규칙.length} 개밖에 못 읽었다 — 정규식이 늙었다`);
  assert.ok(규칙.some(섀도인가), "섀도 규칙이 하나도 없다 — 경계가 사라졌다");
  assert.ok(규칙.some((s) => !섀도인가(s)), "페이지 규칙이 하나도 없다 — 호스트가 맨몸이다");

  // ★ **페이지 쪽 규칙은 우리가 아는 세 틀 중 하나여야 한다.** 그 밖의 선택자는
  //   **사이트 요소를 우리가 꾸미고 있다는 뜻**이다 — 번역 박스의 일이 아니다.
  const 낯선것 = 규칙.filter((s) => !섀도인가(s) && !페이지틀.some((p) => s.includes(p)));
  assert.deepEqual(낯선것, [], "페이지 쪽에 낯선 선택자가 있다 — 남의 요소를 꾸민다");

  // ★ **페이지 규칙이 `.st-몸` 을 가리키면 아무것도 안 맞는다.** 경계 밖에서
  //   안쪽을 고르려는 줄이고, **조용히 아무 일도 안 하는 선언**이 된다.
  //   (위 `섀도인가` 가 그런 규칙을 섀도로 분류하므로 여기서는 반대로 묻는다 —
  //   섀도 규칙이 `html` 로 시작하면 섀도 안에서는 영영 안 맞는다.)
  const 밖을고르는것 = 규칙.filter((s) => 섀도인가(s) && /(^|,)\s*html/.test(s));
  assert.deepEqual(밖을고르는것, [],
    "섀도 규칙이 밖의 html 을 고른다 — 섀도 선택자는 조상을 볼 수 없다");
});

test("섀도 구역에서는 명시도를 올리지 않는다", () => {
  // ★ **없는 적수와 싸우는 것도 같은 값으로 틀렸다**(§133 의 반대쪽). 섀도 안에는
  //   사이트 CSS 가 **들어올 수 없다** — 거기서 명시도를 올리는 것은 **아무것도
  //   안 하면서 「여기도 위험하다」 고 말하는 줄**이다. 다음 사람이 그것을 보고
  //   경계가 새는 줄 안다.
  const 규칙 = [...css.replace(/\/\*[\s\S]*?\*\//g, "").matchAll(/([^{}]+)\{([^{}]*)\}/g)]
    .map((m) => [m[1].trim(), m[2]])
    .filter(([s]) => s.includes(":host") || s.includes(".st-몸"));
  assert.ok(규칙.length >= 5, `섀도 규칙을 ${규칙.length} 개밖에 못 읽었다`);
  const 센것 = 규칙.filter(([, b]) => b.includes("!important"));
  assert.deepEqual(센것.map(([s]) => s), [], "섀도 안에서 `!important` 를 쓴다");
  // `.st-몸.st-몸` 꼴 — 같은 클래스를 두 번 적어 명시도를 올리는 짓
  const 겹친것 = 규칙.filter(([s]) => /\.st-몸\.st-몸|\.(st-[^\s.,)]+)\.\1/.test(s));
  assert.deepEqual(겹친것.map(([s]) => s), [], "섀도 안에서 클래스를 두 번 적는다");
});

test("브로커가 붙이는 몸 클래스가 CSS 에 있다", () => {
  // ★ **`classList.add(ST.몸클래스)` 는 글자가 아니라 변수다** — 위의 「JS 가 붙이는
  //   st 클래스가 CSS 에 전부 있다」 가 **못 본다.** 변수로 둔 까닭은 이름이 두 파일에
  //   살지 않게 하려는 것이고, 그러면 **그 변수를 따로 묶어야 한다**(§131).
  const audit = fs.readFileSync(path.join(뿌리, "src/cssaudit.js"), "utf8");
  new Function(audit)();
  const 이름 = globalThis.ST.몸클래스;
  assert.ok(이름, "ST.몸클래스 가 없다");
  assert.ok(이름.startsWith("st-"), `몸 클래스가 st- 로 시작하지 않는다 — ${이름}`);
  assert.ok(css.includes(`.${이름}`), `content.css 에 .${이름} 이 없다`);
  const broker = fs.readFileSync(path.join(뿌리, "src/broker.js"), "utf8");
  assert.match(broker, /classList\.add\(ST\.몸클래스\)/,
               "브로커가 ST.몸클래스 를 안 쓴다 — 이름이 두 곳에 살고 있다");
});

test("뼈대 줄 수가 재서 갈린다", () => {
  // ★ **`min-height: 104px` 를 박고 있었다**(DECISIONS §170). 스물두 자 토막도 백네
  //   픽셀을 잡았고 메일 목록이 회색 슬래브 바둑판이 됐다.
  // ★ **순수 함수라 브라우저 없이 전부 먹여 본다**(`cssFaults` · `고른다` 와 같은 꼴).
  const audit = fs.readFileSync(path.join(뿌리, "src/cssaudit.js"), "utf8");
  new Function(audit)();
  const { 줄수, 줄상한 } = globalThis.ST;

  // 짧은 토막 — 한 줄이면 된다. 전에는 넷(104px) 을 잡았다.
  assert.equal(줄수(22, 600, "카드"), 1, "스물두 자가 한 줄이 아니다");
  // 골든셋 중앙값 382자 · 폭 600 → 번역 약 200자 · 한 줄 42자 → 다섯 줄이지만 상한에 걸린다
  assert.equal(줄수(382, 600, "카드"), 줄상한);
  // 같은 글이 좁은 자리에서는 더 많은 줄이다 — **폭을 안 보면 이 둘이 같아진다**
  assert.ok(줄수(200, 300, "카드") > 줄수(200, 694, "카드"), "폭을 보지 않는다");
  // ★ **띠는 글자가 작아 같은 폭에 더 들어간다.** `<=` 로 적으면 **두 글자폭이 같아도
  //   통과한다** — 돌연변이가 그 자리로 살아 나왔다. 상한에 안 걸리고 갈리는 수를
  //   골라 **다르다**를 묻는다 (폭 300 · 원문 85자 → 카드 3줄 · 띠 2줄).
  assert.equal(줄수(85, 300, "카드"), 3);
  assert.equal(줄수(85, 300, "띠"), 2, "띠와 카드의 글자폭이 같아졌다");
  // ★ **못 재면 셋이다**(§59). 0 을 「한 줄」 로 읽으면 자리가 모자라 글자가 튄다.
  assert.equal(줄수(500, 0, "카드"), 3, "폭을 못 쟀는데 판정한다");
  assert.equal(줄수(500, -1, "카드"), 3);
  // 상한과 하한
  assert.equal(줄수(100000, 600, "카드"), 줄상한);
  assert.equal(줄수(1, 600, "카드"), 1);
  // ★ **CSS 에 칸이 전부 있는가** — 함수가 넷을 돌려주는데 CSS 에 셋만 있으면
  //   네 줄짜리는 조용히 기본값(셋)으로 선다.
  for (let i = 1; i <= 줄상한; i++)
    assert.ok(css.includes(`.st-translation--줄${i})`),
              `content.css 에 --줄${i} 칸이 없다`);
});

test("재는 기대값이 CSS 가 선언한 값과 같다", () => {
  // ★ **같은 사실이 두 파일에 산다** — `content.css` 가 선언하고 `cssaudit.js` 가
  //   그것을 기대한다. 피할 수 없으면 **검사가 둘을 묶는다**(DECISIONS §131 · §135).
  //   한쪽만 고치면 자가 신고가 **멀쩡한 박스를 졌다고 말하거나 진 박스를 놓친다.**
  const 바탕 = css.match(/\.st-translation\.st-translation \{([\s\S]*?)\n\}/)?.[1];
  const audit = fs.readFileSync(path.join(뿌리, "src/cssaudit.js"), "utf8");
  const 기대 = audit.match(/CSS_EXPECT\s*=\s*\{([\s\S]*?)\}/)?.[1];
  assert.ok(바탕 && 기대, "둘 중 하나를 못 찾았다 — 검사가 아무것도 안 보고 있다");

  // camelCase → kebab-case. CSS 는 `overflow-wrap`, JS 는 `overflowWrap` 이다.
  const 짝 = [...기대.matchAll(/(\w+)\s*:\s*"([^"]+)"/g)]
    .map(([, k, v]) => [k.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`), v]);
  assert.ok(짝.length >= 3, `기대값을 ${짝.length} 개밖에 못 읽었다 — 정규식이 늙었다`);
  for (const [속성, 값] of 짝)
    assert.match(바탕, new RegExp(`\\n\\s*${속성}:\\s*${값}\\s*;`),
      `content.css 의 바탕 규칙에 ${속성}: ${값} 이 없다 — cssaudit 이 기대하는 값이다`);
});

test("판정 함수가 무는 것과 안 무는 것", async () => {
  // ★ **DOM 을 안 읽는 함수라 브라우저도 jsdom 도 없이 돈다**(§21). 캐스케이드 자체는
  //   `tools/cascade_check.py` 가 진짜 엔진으로 재고, 여기서는 **판정의 갈래**를 본다.
  const src = fs.readFileSync(path.join(뿌리, "src/cssaudit.js"), "utf8");
  new Function(src)();
  const { cssFaults, CSS_EXPECT } = globalThis.ST;
  const 맞는것 = { ...CSS_EXPECT };

  assert.deepEqual(cssFaults(맞는것, 580, 580), [], "맞는 박스를 졌다고 한다");
  assert.deepEqual(cssFaults({ ...맞는것, display: "inline" }, 580, 580), ["display"]);
  assert.deepEqual(cssFaults(맞는것, 60, 580), ["width"], "폭이 갈렸는데 조용하다");
  assert.deepEqual(cssFaults(맞는것, 580.4, 580), [], "1px 안쪽 반올림에 운다");
  // ★ 음성 대조 — **못 잰 것을 틀렸다고 적지 않는다.** 부모가 inline 이면 0 이 온다.
  assert.deepEqual(cssFaults(맞는것, 60, 0), [], "그릇 폭을 못 쟀는데 폭을 판정한다");
  assert.deepEqual(cssFaults(맞는것, 60, -20), [], "그릇 폭이 음수인데 폭을 판정한다");
});
