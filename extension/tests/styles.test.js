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
  const 바탕 = css.match(/\.st-translation\.st-translation \{([\s\S]*?)\n\}/)?.[1];
  const 비상구 = css.match(/\.st-translation--wide\.st-translation--wide \{([\s\S]*?)\n\}/)?.[1];
  assert.ok(바탕 && 비상구, "두 규칙 중 하나를 못 찾았다 — 검사가 아무것도 안 보고 있다");
  for (const [속성, 값] of [["display", "block"], ["width", "100%"],
                            ["white-space", "pre-wrap"], ["overflow-wrap", "break-word"]]) {
    assert.ok(new RegExp(`${속성}:\\s*${값}\\s*;`).test(바탕), `바탕에 ${속성}: ${값} 이 없다`);
    assert.ok(new RegExp(`${속성}:\\s*${값}\\s*!important`).test(비상구), `비상구에 ${속성}: ${값} 이 없다`);
  }
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
