// Layer 1 — ARIA · 폼 표준. 사이트 지식 0. group 을 채우는 것이 목적이다.
//
// ★ 어댑터는 배타 선택이다. 여기서 보기만 모으면 라디오그룹이 있는 페이지에서
//   문제 지문과 본문이 통째로 번역에서 빠진다. 자기 몫을 모으고 나머지는
//   Layer 0 에 위임한다(DECISIONS §11).
if (!globalThis.ST.adapters.some((a) => a.name === "standard"))
globalThis.ST.adapters.push({
  name: "standard",
  priority: 5,

  match: () =>
    document.querySelector("[role=radiogroup], [role=listbox], form input[type=radio]") !== null,

  // ★ 최상위 선언을 쓰지 않는다. 이 파일은 재주입되며 재선언은 SyntaxError 다
  //   (DECISIONS §16). 헬퍼도 어댑터 객체 안에 둔다.
  labelOf(input, root) {
    const own = input.closest("label");
    if (own) return own;
    if (!input.id) return null;
    // id 에 따옴표나 콜론이 들어간 페이지가 있다. 셀렉터로 넘기기 전에 감싼다.
    try {
      return root.querySelector(`label[for="${CSS.escape(input.id)}"]`);
    } catch {
      return null;
    }
  },

  collect(root) {
    const units = [];
    const grouped = [];
    const groups = root.querySelectorAll("[role=radiogroup],[role=listbox]");

    groups.forEach((grp, gi) => {
      grouped.push(grp);
      // label 은 [role=radio] 를 감싸거나 감싸일 수 있다. 둘 다 잡으면 같은
      // 텍스트가 두 번 수집되므로, 다른 후보를 품은 것은 버린다.
      const cand = [...grp.querySelectorAll("[role=radio],[role=option],label")];
      cand
        .filter((el) => !cand.some((o) => o !== el && el.contains(o)))
        .forEach((el, i) => {
          if (el.dataset.stDone || el.dataset.stFail) return;
          const t = (el.innerText || "").trim();
          if (!t) return;
          units.push({ id: `s${gi}-${i}`, text: t, el, anchor: el, group: `g${gi}` });
        });
    });

    // ★ ARIA role 없이 네이티브 라디오만 쓰는 폼이 더 흔하다. `match` 는 그것도
    //   보는데 위 순회는 role 만 보므로, 그런 페이지에서는 이 어댑터가 이기고도
    //   그룹을 하나도 만들지 못한다. **더 나쁜 것은 `genericCollect` 의 TAGS 에
    //   label 이 없어 보기 라벨을 아무도 수집하지 않는다는 점이다** — 상위
    //   계층이 하위보다 나빠지는 자리다(DECISIONS §11 · §39).
    //
    // ★ 같은 `name` 을 가진 라디오가 한 그룹이라는 것은 HTML 표준이다. 사이트
    //   지식이 아니므로 Layer 1 에 있어도 된다.
    const byName = new Map();
    for (const r of root.querySelectorAll("input[type=radio][name]")) {
      if (grouped.some((g) => g.contains(r))) continue;   // 위에서 이미 다뤘다
      const label = this.labelOf(r, root);
      if (!label || label.dataset.stDone || label.dataset.stFail) continue;
      const t = (label.innerText || "").trim();
      if (!t) continue;
      if (!byName.has(r.name)) byName.set(r.name, []);
      byName.get(r.name).push({ label, text: t });
    }

    let ni = 0;
    for (const items of byName.values()) {
      // 라디오가 하나뿐이면 묶을 것이 없다. 그룹을 만들지 않고 Layer 0 에 맡긴다.
      if (items.length < 2) continue;
      items.forEach(({ label, text }, i) => {
        grouped.push(label);
        units.push({ id: `r${ni}-${i}`, text, el: label, anchor: label, group: `r${ni}` });
      });
      ni++;
    }

    // 그룹 밖의 본문은 Layer 0 이 맡는다.
    return units.concat(globalThis.ST.genericCollect(root, { skip: grouped }));
  },
});
