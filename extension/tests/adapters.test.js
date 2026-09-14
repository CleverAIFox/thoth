// 어댑터의 수집 구조를 본다(PLAN §2-1 #41).
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
