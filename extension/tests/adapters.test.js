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
