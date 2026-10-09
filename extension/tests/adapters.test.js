// 어댑터의 수집 구조를 본다.
//
// ★ **검사 대상은 구조다.** 무엇이 몇 개 모였는지 · 어떻게 묶였는지 · 어디에
//   위임했는지를 본다. 텍스트가 정확히 무엇인지는 보지 않는다 — 하네스의
//   `innerText` 대체가 브라우저와 다르기 때문이다(harness.js 머리말).
//
// ★ jsdom 이 없으면 이 파일 전체를 건너뛴다. `doctor` 가 그것을 WARN 으로
//   알린다 — 조용히 0건으로 통과하는 것이 가장 나쁘다(DECISIONS §21 · §46).
import assert from "node:assert/strict";
import { test } from "node:test";

let harness = null;
try {
  harness = await import("./harness.js");
} catch {
  // jsdom 미설치. 아래에서 전부 skip 한다.
}
const need = { skip: harness ? false : "jsdom 이 없다 — npm install (extension/)" };

test("standard 가 ARIA 라디오그룹을 한 묶음으로 모은다", need, async () => {
  const { loadAdapters, makeDoc, groupSizes } = harness;
  const ST = await loadAdapters(["generic", "standard"]);
  const doc = makeDoc(`
    <div role="radiogroup">
      <div role="radio">The first option is long enough to be collected here.</div>
      <div role="radio">The second option is also long enough to be collected.</div>
      <div role="radio">The third option is long enough as well for this test.</div>
    </div>`);
  const std = ST.adapters.find((a) => a.name === "standard");
  assert.ok(std.match(doc), "라디오그룹이 있으면 match 한다");

  const sizes = groupSizes(std.collect(doc));
  assert.equal(sizes.size, 1, "그룹이 하나여야 한다");
  assert.equal([...sizes.values()][0], 3, "보기 셋이 한 묶음이다");
});

test("같은 name 을 가진 네이티브 라디오가 한 묶음이다", need, async () => {
  // ★ 이것이 §39 에서 고친 자리다. `match` 는 네이티브 라디오도 보는데
  //   `collect` 가 ARIA 만 순회해, 그런 폼에서 이기고도 그룹을 만들지 못했다.
  const { loadAdapters, makeDoc, groupSizes } = harness;
  const ST = await loadAdapters(["generic", "standard"]);
  const doc = makeDoc(`
    <form>
      <label><input type="radio" name="q1"> The first choice is long enough here.</label>
      <label><input type="radio" name="q1"> The second choice is long enough too.</label>
      <label><input type="radio" name="q1"> The third choice is also long enough.</label>
    </form>`);
  const std = ST.adapters.find((a) => a.name === "standard");
  assert.ok(std.match(doc));

  const sizes = groupSizes(std.collect(doc));
  const grouped = [...sizes.entries()].filter(([k]) => k !== null);
  assert.equal(grouped.length, 1, "그룹이 하나여야 한다");
  assert.equal(grouped[0][1], 3, "라벨 셋이 한 묶음이다");
});

test("label[for] 로 연결된 라디오도 묶는다", need, async () => {
  const { loadAdapters, makeDoc, groupSizes } = harness;
  const ST = await loadAdapters(["generic", "standard"]);
  const doc = makeDoc(`
    <form>
      <input type="radio" name="q2" id="a">
      <label for="a">The first option is long enough to be collected here.</label>
      <input type="radio" name="q2" id="b">
      <label for="b">The second option is long enough to be collected too.</label>
    </form>`);
  const std = ST.adapters.find((a) => a.name === "standard");
  const grouped = [...groupSizes(std.collect(doc)).entries()].filter(([k]) => k !== null);
  assert.equal(grouped.length, 1);
  assert.equal(grouped[0][1], 2);
});

test("name 이 다르면 다른 묶음이다", need, async () => {
  const { loadAdapters, makeDoc, groupSizes } = harness;
  const ST = await loadAdapters(["generic", "standard"]);
  const doc = makeDoc(`
    <form>
      <label><input type="radio" name="x"> Question one first choice goes here now.</label>
      <label><input type="radio" name="x"> Question one second choice goes here now.</label>
      <label><input type="radio" name="y"> Question two first choice goes here now.</label>
      <label><input type="radio" name="y"> Question two second choice goes here now.</label>
    </form>`);
  const std = ST.adapters.find((a) => a.name === "standard");
  const grouped = [...groupSizes(std.collect(doc)).entries()].filter(([k]) => k !== null);
  assert.equal(grouped.length, 2, "묶음이 둘이어야 한다");
  assert.deepEqual(grouped.map(([, n]) => n).sort(), [2, 2]);
});

test("라디오가 하나뿐이면 묶지 않는다", need, async () => {
  // 묶을 것이 없는데 그룹을 만들면 배치 번역이 얻는 것 없이 형태만 남는다.
  const { loadAdapters, makeDoc, groupSizes } = harness;
  const ST = await loadAdapters(["generic", "standard"]);
  const doc = makeDoc(`
    <form>
      <label><input type="radio" name="lonely"> A single radio has nothing to group with here.</label>
    </form>`);
  const std = ST.adapters.find((a) => a.name === "standard");
  const grouped = [...groupSizes(std.collect(doc)).entries()].filter(([k]) => k !== null);
  assert.equal(grouped.length, 0, "그룹을 만들지 않는다");
});

test("그룹 밖 본문은 Layer 0 에 위임한다", need, async () => {
  // ★ 상위 계층이 이기면 하위는 돌지 않는다. 위임하지 않으면 본문이 통째로
  //   빠진다(DECISIONS §11).
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic", "standard"]);
  const doc = makeDoc(`
    <p>This paragraph belongs to the fallback layer and should still be collected.</p>
    <div role="radiogroup">
      <div role="radio">The only option here is long enough to be collected.</div>
      <div role="radio">The second option here is long enough to be collected.</div>
    </div>`);
  const std = ST.adapters.find((a) => a.name === "standard");
  const units = std.collect(doc);
  assert.ok(units.some((u) => u.el.tagName.toLowerCase() === "p"),
            "본문 문단이 수집돼야 한다");
});

test("같은 문장을 두 번 모으지 않는다", need, async () => {
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic", "standard"]);
  const doc = makeDoc(`
    <div role="radiogroup">
      <label><span>The wrapped option is long enough to be collected here.</span></label>
      <label><span>The second wrapped option is long enough as well now.</span></label>
    </div>`);
  const std = ST.adapters.find((a) => a.name === "standard");
  const texts = std.collect(doc).map((u) => u.text.trim());
  assert.equal(new Set(texts).size, texts.length, "중복 수집이 없어야 한다");
});

test("이미 처리한 요소는 다시 모으지 않는다", need, async () => {
  // 브로커가 순회할 때마다 다시 걷으면 같은 문장을 계속 번역한다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic", "standard"]);
  const doc = makeDoc(`
    <form>
      <label><input type="radio" name="d"> The first option is long enough here now.</label>
      <label><input type="radio" name="d"> The second option is long enough here now.</label>
    </form>`);
  const std = ST.adapters.find((a) => a.name === "standard");
  const first = std.collect(doc);
  assert.ok(first.length > 0);
  first.forEach((u) => { u.el.dataset.stDone = "1"; });
  assert.equal(std.collect(doc).length, 0, "두 번째 순회에서는 비어야 한다");
});

test("generic 은 언제나 match 한다", need, async () => {
  // Layer 0 이 항상 참이므로 어댑터가 없는 사이트에서도 번역이 동작한다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const gen = ST.adapters.find((a) => a.name === "generic");
  assert.ok(gen.match(makeDoc("<p>anything</p>")));
  assert.ok(gen.match(makeDoc("")));
});

test("standard 가 라디오 없는 문서에서는 match 하지 않는다", need, async () => {
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic", "standard"]);
  const std = ST.adapters.find((a) => a.name === "standard");
  assert.ok(!std.match(makeDoc("<p>본문만 있는 문서다.</p>")));
});

test("udemy 가 udemy.com 으로 끝나는 남의 도메인에 붙지 않는다", need, async () => {
  // ★ 2026-10-02. `hostname.endsWith("udemy.com")` 이었다 — `freeudemy.com` 이
  //   통과했다. 강의 유출 사이트가 실제로 쓰는 작명이라 가상의 공격이 아니다.
  //   CodeQL 이 잡아준 것이지만 운은 강제자가 아니다. 이 검사가 강제자다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic", "udemy"]);
  const ud = ST.adapters.find((a) => a.name === "udemy");
  const doc = makeDoc("<div></div>");
  const 봤다 = (url) => { ST.pageUrl = () => url; return ud.match(doc); };

  assert.ok(봤다("https://www.udemy.com/course/x/"), "진짜 Udemy 는 붙는다");
  assert.ok(봤다("https://udemy.com/course/x/"), "서브도메인 없이도 붙는다");
  assert.ok(!봤다("https://freeudemy.com/course/x/"), "앞에 이어 붙인 도메인은 남이다");
  assert.ok(!봤다("https://udemy.com.evil.net/x"), "뒤에 이어 붙인 도메인은 남이다");
});

// ── 메일 본문의 모양(DECISIONS §160) ────────────────────────────────────────
//
// ★ **109 시험이 전부 초록인 채로 다섯 꼴이 사각이었다.** 2026-10-05 지메일에서 본문이
//   통째로 안 번역됐고, 재 보니 `div` 가 후보 목록에 없었다. **통과는 검사가 작동한다는
//   증거가 아니다**(DECISIONS §21) — 그 109 중 어느 것도 메일 꼴을 물지 않았다.
// ★ **꼴을 표로 둔다.** 하나씩 적으면 다음 꼴이 늘 때 빠뜨린다.

const 긴글 = "Effective December 31, 2026, AWS CloudTrail will no longer emit ListRegions events.";

const 메일꼴 = [
  ["td > p            표 메일 · 문단", `<table><tr><td><p>${긴글}</p></td></tr></table>`],
  ["td > div > 글     표 메일 · div 포장", `<table><tr><td><div>${긴글}</div></td></tr></table>`],
  ["td > div > p      표 메일 · 두 겹", `<table><tr><td><div><p>${긴글}</p></div></td></tr></table>`],
  ["div > 글          지메일 본문", `<div>${긴글}</div>`],
  ["div > div > 글    지메일 두 겹", `<div><div>${긴글}</div></div>`],
  ["td > 글           표 메일 · 맨 td", `<table><tr><td>${긴글}</td></tr></table>`],
  ["td > div > span   버튼 포장", `<table><tr><td><div><span>${긴글}</span></div></td></tr></table>`],
  ["li > p            목록", `<ul><li><p>${긴글}</p></li></ul>`],
];

for (const [이름, html] of 메일꼴) {
  test(`메일 꼴을 꼭 한 번 모은다 — ${이름}`, need, async () => {
    const { loadAdapters, makeDoc } = harness;
    const ST = await loadAdapters(["generic"]);
    const 것 = ST.genericCollect(makeDoc(html).body);
    assert.equal(것.length, 1, `${이름} 에서 ${것.length}건 — 0 이면 사각, 2 이상이면 중복이다`);
  });
}

test("표 안의 표에서 같은 글을 두 번 모으지 않는다", need, async () => {
  // ★ **이것이 2026-10-05 의 중복이다.** HTML 메일은 표 안의 표로 짠다. `td` 가 `BLOCK` 에
  //   없으면 바깥 `td` 도 말단으로 세어져 **같은 글이 두 번** 모이고, 앵커가 둘 다 `td` 라
  //   셀 안에 상자가 겹쳐 꽂힌다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const html = `<table><tr><td><table><tr><td>${긴글}</td></tr></table></td></tr></table>`;
  const 것 = ST.genericCollect(makeDoc(html).body);
  assert.equal(것.length, 1, `중첩 td 에서 ${것.length}건 — 안쪽 하나만 모아야 한다`);
  assert.equal(것[0].anchor.closest("table").parentElement.tagName, "TD", "안쪽 표의 칸이다");
});

test("껍데기의 짧은 div 는 안 딸려 온다", need, async () => {
  // ★ `div` 를 후보에 넣으면 지메일 UI 가 통째로 올까 봐 **재 봤다.** 길이 문턱이 거른다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const html = `<div><div>받은편지함</div><div>보낸편지함</div><div>답장</div>
                <div><p>${긴글}</p></div></div>`;
  const 것 = ST.genericCollect(makeDoc(html).body);
  assert.equal(것.length, 1, `껍데기까지 ${것.length}건 모았다`);
});

test("메일 한 통에서 본문 세 토막을 다 모은다", need, async () => {
  // ★ 꼴 하나씩 보는 것과 **한 통을 통째로** 보는 것은 다르다. 2026-10-05 실물에서는
  //   셋 중 하나(`td > div > 글`)만 빠졌고, 그 하나가 본문의 절반이었다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const 둘째 = "If you have mechanisms that depend on these events, please update them by then.";
  const html = `<div class="app"><div class="nav"><div>받은편지함</div></div>
    <div class="msg"><table><tr><td><table>
      <tr><td><div><p>${긴글}</p></div></td></tr>
      <tr><td><div>${둘째}</div></td></tr>
      <tr><td><a href="#">View details in the service console now</a></td></tr>
    </table></td></tr></table></div></div>`;
  const 것 = ST.genericCollect(makeDoc(html).body);
  assert.equal(것.length, 3, `본문 셋 중 ${것.length}건만 모았다`);
});

// ── 한 행 안의 포함 관계(DECISIONS §165) ─────────────────────────────────────

test("한 행 안에서 남의 글을 통째로 품은 것은 안 모은다", need, async () => {
  // ★ **2026-10-05 지메일 받은편지함의 실물 꼴이다.** 한 행에 상자가 둘 떴다 —
  //   하나는 제목만, 하나는 `보낸사람 + 제목 + 시각 + 본문 앞머리` 를 통째로.
  //   §160 이 막은 것은 **조상-자손**이고 이 둘은 **형제**라 그 가름으로는 안 보였다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const doc = makeDoc(`
    <table role="grid"><tbody>
      <tr role="row">
        <td role="gridcell"><div>Action may be required CloudTrail event source change.</div></td>
        <td role="gridcell"><div>health@aws.com, Action may be required CloudTrail event source change. 4:36 PM</div></td>
      </tr>
    </tbody></table>`);
  const units = ST.genericCollect(doc.body);
  assert.equal(units.length, 1, "품은 쪽을 버려 하나만 남는다");
  assert.ok(!units[0].text.includes("4:36 PM"), "보낸사람·시각이 섞인 쪽을 버린다");
});

test("행이 다르면 같은 글이라도 둘 다 모은다", need, async () => {
  // ★ **울타리가 행이다.** 행 밖까지 묻으면 목록에서 같은 제목 둘 중 하나가 사라진다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const doc = makeDoc(`
    <table role="grid"><tbody>
      <tr role="row"><td><div>The quarterly report is attached for your review.</div></td></tr>
      <tr role="row"><td><div>The quarterly report is attached for your review.</div></td></tr>
    </tbody></table>`);
  assert.equal(ST.genericCollect(doc.body).length, 2);
});

test("행이 없으면 아무것도 안 버린다", need, async () => {
  // ★ **문서 본문에서 같은 문장이 두 번 나오는 것은 정상이다.** 지우면 글이 사라진다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const doc = makeDoc(`
    <section><p>The quarterly report is attached for your review here.</p></section>
    <section><p>The quarterly report is attached for your review here. And more text follows.</p></section>`);
  assert.equal(ST.genericCollect(doc.body).length, 2);
});

test("다른 행이 품은 것은 안 버린다", need, async () => {
  // ★ **울타리가 행이라는 것을 이 시험이 붙든다**(DECISIONS §165). 긴 제목 하나가 짧은
  //   제목을 **우연히 품는 것**은 목록에서 흔하다 — 행 밖까지 묻으면 **긴 쪽이 통째로
  //   사라진다.** 「같은 글이 둘」 만 보는 시험으로는 이 가름이 안 잡힌다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const doc = makeDoc(`
    <table role="grid"><tbody>
      <tr role="row"><td><div>The quarterly report is attached for your review. Please read it before Friday.</div></td></tr>
      <tr role="row"><td><div>The quarterly report is attached for your review.</div></td></tr>
    </tbody></table>`);
  assert.equal(ST.genericCollect(doc.body).length, 2, "다른 행이면 품어도 안 버린다");
});

// ── 단위를 구조로 고른다 (DECISIONS §174) ───────────────────────────────────
//
// ★ **정본은 모질라의 페이지 번역이다.** 「무슨 태그인가」 도 「몇 글자인가」 도 아니고
//   직계 자식을 세어 **「문단인가, 문단을 담는 상자인가」** 를 묻는다.

test("안이글인가 — 수로만 가른다", need, async () => {
  // ★ **순수 함수다.** 합성 노드를 먹여 본다 — 레이아웃도 사이트도 필요 없다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const doc = makeDoc("<div></div>");
  const 만 = (html) => { const d = doc.createElement("div"); d.innerHTML = html; return d; };

  assert.equal(ST.안이글인가(만("글")), true, "글 노드만 있으면 문단이다");
  assert.equal(ST.안이글인가(만("<b>굵게</b> 그리고 글")), true, "인라인은 글이다");
  assert.equal(ST.안이글인가(만("<a href='#'>링크</a> 와 글")), true, "글 속 링크는 인라인이다");
  assert.equal(ST.안이글인가(만("<p>하나</p><p>둘</p>")), false, "문단 둘을 담은 상자다");
  assert.equal(ST.안이글인가(만("<div><p>속</p></div>")), false, "블록 하나도 상자다");
  // ★ 같으면 글 쪽으로 본다 — 덜 쪼갠다.
  assert.equal(ST.안이글인가(만("글 그리고 <p>문단</p>")), true, "하나 대 하나면 문단이다");
});

test("태그 목록에 없던 꼴도 모은다 — §160 이 그 목록의 필연이었다", need, async () => {
  // ★ **`div` 가 후보에 없어 본문이 통째로 사각이었다**(§160). 목록을 늘리는 것은
  //   **다음 사이트까지만** 맞다. 구조로 물으면 목록이 없다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  for (const 꼴 of ["article", "section", "figcaption", "dt", "main", "summary", "label"]) {
    const html = `<${꼴}>${긴글}</${꼴}>`;
    const 것 = ST.genericCollect(makeDoc(html).body);
    assert.equal(것.length, 1, `<${꼴}> 에서 ${것.length}건 — 옛 목록에 없던 꼴이다`);
  }
});

test("웹 표준이 번역하지 말라는 자리를 지킨다", need, async () => {
  // ★ **구글 번역도 지키는 신호다.** 공짜로 따라오고, 지금까지 하나도 안 보고 있었다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  for (const [이름, html] of [
    ["translate=no", `<div translate="no">${긴글}</div>`],
    ["notranslate", `<div class="notranslate">${긴글}</div>`],
    ["lang=ko", `<div lang="ko">${긴글}</div>`],
    ["lang=ko-KR", `<div lang="ko-KR">${긴글}</div>`],
    ["contenteditable", `<div contenteditable>${긴글}</div>`],
    ["pre", `<pre>${긴글}</pre>`],
    ["button", `<button>${긴글}</button>`],
  ]) assert.equal(ST.genericCollect(makeDoc(html).body).length, 0, `${이름} 를 모았다`);

  // ★ **음성 대조** — 같은 글이 그냥 있으면 모은다. 안 그러면 「전부 0」 이 통과한다.
  assert.equal(ST.genericCollect(makeDoc(`<div>${긴글}</div>`).body).length, 1);
  // ★ **대상 언어가 아닌 `lang` 은 안 막는다.** 영어 표시가 붙은 글이 번역 대상이다.
  assert.equal(ST.genericCollect(makeDoc(`<div lang="en">${긴글}</div>`).body).length, 1);
});

test("짧다고 버리지 않고 그 아래를 더 판다", need, async () => {
  // ★ **길이는 「문단인가」 와 상관이 없다.** 짧은 포장 안에 긴 글이 든 꼴이 메일에 흔하다 —
  //   짧으면 **버리는** 것이 아니라 **더 파는** 것이 맞다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const html = `<div>짧</div>`;
  assert.equal(ST.genericCollect(makeDoc(html).body).length, 0, "짧은 토막은 안 모은다");
  // 포장이 짧아 보여도(innerText 가 아니라 textContent 로 재므로 실제로는 길다) 안쪽을 찾는다
  const 포장 = `<div><span>·</span><div><div>${긴글}</div></div></div>`;
  assert.equal(ST.genericCollect(makeDoc(포장).body).length, 1, "포장 안의 글을 못 찾았다");
});

test("처리된 노드의 **아래**는 계속 본다", need, async () => {
  // ★ **종전에는 셀렉터에서 통째로 뺐다**(`:not([data-st-done])`). 그래서 처리된 포장
  //   **아래가 영영 안 보였고**, 순회를 넘어선 판단이 원천적으로 불가능했다 —
  //   그것이 지메일 행 중복의 진짜 원인이다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const 둘째 = "If you have mechanisms that depend on these events, please update them now.";
  const doc = makeDoc(`<div id="w"><div>${긴글}</div><div>${둘째}</div></div>`);
  doc.getElementById("w").dataset.stDone = "1";     // 포장이 처리된 척
  assert.equal(ST.genericCollect(doc.body).length, 2, "처리된 포장 아래를 못 본다");
});

// ── 한 행에 번역은 하나 (DECISIONS §174) ────────────────────────────────────

test("행에 상자가 이미 서 있으면 그 행은 더 안 모은다", need, async () => {
  // ★ **이것은 「중복인가」 를 묻는 규칙이 아니다** — 글자를 비교하지 않는다.
  //   목록 행은 훑는 자리라 번역을 둘 받으면 격자가 깨진다. **표시 정책**이다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const doc = makeDoc(`
    <table role="grid"><tbody>
      <tr role="row">
        <td><div class="st-translation">이미 선 번역</div></td>
        <td><div>${긴글}</div></td>
      </tr>
    </tbody></table>`);
  assert.equal(ST.genericCollect(doc.body).length, 0, "행에 둘째 상자를 세운다");
});

test("행 다음 줄에 선 상자도 센다", need, async () => {
  // ★ §165 가 행 **다음 줄**에 꽂게 했다. 행 안만 보면 그것을 못 본다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const doc = makeDoc(`
    <table role="grid"><tbody>
      <tr role="row"><td><div>${긴글}</div></td></tr>
      <tr class="st-translation-row"><td><div class="st-translation">이미 선 번역</div></td></tr>
    </tbody></table>`);
  assert.equal(ST.genericCollect(doc.body).length, 0, "다음 줄의 상자를 못 본다");
});

test("행이 없으면 한행에하나가 아무것도 안 한다 — 수미상관을 안 버린다", need, async () => {
  // ★ **네가 물은 그 자리다.** 같은 글이 두 번 나오는 것은 **버릴 일이 아니다.**
  //   행 밖에서는 이 규칙이 아무 일도 안 한다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const doc = makeDoc(`<section><p>${긴글}</p></section><section><p>${긴글}</p></section>`);
  assert.equal(ST.genericCollect(doc.body).length, 2, "수미상관을 버렸다");
});

test("단위는 인라인이 아니라 그 포장이다 — 앵커가 span 이 되면 안 된다", need, async () => {
  // ★ **개수만 보면 이 가름이 안 잡힌다.** `span` 을 블록으로 세면 단위가 `div` 에서
  //   `span` 으로 바뀌는데 **개수는 그대로 1** 이다 — 돌연변이가 그 틈으로 살아 나왔다.
  // ★ **왜 중요한가**(DECISIONS §168) : 인라인 요소는 **레이아웃이 멀쩡해도
  //   `clientWidth` 가 0** 이다. 앵커가 `span` 이면 꽂을 자리를 고르는 자가 헛본다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const 것 = ST.genericCollect(
    makeDoc(`<table><tr><td><div><span>${긴글}</span></div></td></tr></table>`).body);
  assert.equal(것.length, 1);
  assert.equal(것[0].el.tagName, "DIV", "앵커가 인라인이 됐다 — 폭을 못 잰다");

  // ★ 글 속 링크도 같다 — `<a>` 가 단위가 되면 버튼 하나가 문단 행세를 한다.
  const 링크 = ST.genericCollect(
    makeDoc(`<div>Please <a href="#">read the full policy document</a> before Friday arrives.</div>`).body);
  assert.equal(링크.length, 1);
  assert.equal(링크[0].el.tagName, "DIV", "링크가 단위가 됐다");
});

test("품은 쪽이 먼저 와도 품은 쪽을 버린다", need, async () => {
  // ★ **§174 가 §165 의 가드를 가렸다.** `한행에하나` 가 뒤에 돌면서 **문서 순서로 첫째**를
  //   남긴다 — 기존 픽스처는 깨끗한 쪽이 먼저라, 포함 규칙을 **꺼도 우연히 맞는 답**이
  //   나왔다. 돌연변이 `포함 관계를 안 뺀다` 가 그 틈으로 살아 나왔다.
  // ★ **순서에 안 기대는 것이 그 규칙의 존재 이유다.** 지메일이 어느 칸을 먼저 그리는지는
  //   우리가 정하지 않는다 — **뒤집은 꼴로 묻는다.**
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const doc = makeDoc(`
    <table role="grid"><tbody>
      <tr role="row">
        <td role="gridcell"><div>health@aws.com, Action may be required CloudTrail event source change. 4:36 PM</div></td>
        <td role="gridcell"><div>Action may be required CloudTrail event source change.</div></td>
      </tr>
    </tbody></table>`);
  const units = ST.genericCollect(doc.body);
  assert.equal(units.length, 1, "하나만 남아야 한다");
  assert.ok(!units[0].text.includes("4:36 PM"),
            "먼저 왔다고 품은 쪽을 남겼다 — 순서에 기대고 있다");
});

// ── 재는 자리와 도는 자리 (DECISIONS §176) ──────────────────────────────────

test("브로커처럼 document 에서 시작해도 같은 것을 모은다", need, async () => {
  // ★ **이 시험들이 전부 `.body` 에서 시작하고 브로커는 `document` 에서 시작한다.**
  //   그 한 칸 차이에 `<html>` 이 있고, 2026-10-09 지메일에서 **거기서 끊겨 0건**이었다.
  //   재는 자리와 도는 자리가 다르면 **초록이 아무것도 보증하지 않는다**(§171 · §172 · §173
  //   에 이어 **네 번째**다).
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  for (const [이름, html] of 메일꼴) {
    const doc = makeDoc(html);
    assert.equal(ST.genericCollect(doc).length,
                 ST.genericCollect(makeDoc(html).body).length,
                 `${이름} — document 와 body 가 다른 답을 준다`);
  }
});

test("앱 껍데기의 lang 이 문서를 통째로 죽이지 않는다", need, async () => {
  // ★ **2026-10-09 실물이다.** 지메일 UI 가 한국어라 `<html lang="ko">` 이고, 영어 메일
  //   본문은 제 `lang` 이 없어 그것을 뒤집어쓴다. 가지째 자르니 **수집이 0건**이었다.
  // ★ **모질라에서 베끼며 뜻을 뒤집었다** — 그쪽은 「출발어와 다른 lang 을 제외」 이고
  //   전체 페이지 번역이라 `html lang` 이 곧 출발어다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  const doc = makeDoc(`<div>${긴글}</div>`);
  doc.documentElement.setAttribute("lang", "ko");
  assert.equal(ST.genericCollect(doc).length, 1, "껍데기 lang 이 본문을 죽였다");

  // ★ **그래도 단위의 `lang` 은 지킨다** — 이미 한국어인 토막은 안 모은다.
  const doc2 = makeDoc(`<div lang="ko">이미 한국어로 적혀 있는 문단이라 번역할 까닭이 없습니다.</div>`);
  doc2.documentElement.setAttribute("lang", "ko");
  assert.equal(ST.genericCollect(doc2).length, 0, "단위의 lang 을 안 본다");

  // ★ **음성 대조** — 껍데기 lang 이 없어도 답이 같아야 한다. 안 그러면 「언제나 1」 이다.
  assert.equal(ST.genericCollect(makeDoc(`<div>${긴글}</div>`)).length, 1);
});

test("가지째 자르는 것과 단위에서만 묻는 것을 가른다", need, async () => {
  // ★ **`translate=no` 와 `.notranslate` 는 가지째다** — 「이 안을 건드리지 말라」 는 말이다.
  //   **`lang` 은 그 글 자신의 언어**라 자손에게 물려줄 수 없다. 둘을 같은 자리에 두면
  //   §176 이 돌아온다.
  const { loadAdapters, makeDoc } = harness;
  const ST = await loadAdapters(["generic"]);
  assert.equal(ST.genericCollect(makeDoc(`<div translate="no"><div>${긴글}</div></div>`).body).length, 0,
               "translate=no 가 가지째 안 막는다");
  assert.equal(ST.genericCollect(makeDoc(`<div class="notranslate"><div>${긴글}</div></div>`).body).length, 0,
               "notranslate 가 가지째 안 막는다");
  assert.equal(ST.genericCollect(makeDoc(`<div lang="ko"><div>${긴글}</div></div>`).body).length, 1,
               "lang 이 가지째 막는다 — 그것이 §176 의 병이다");
});
