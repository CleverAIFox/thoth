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

    // 그룹 밖의 본문은 Layer 0 이 맡는다.
    return units.concat(globalThis.ST.genericCollect(root, { skip: grouped }));
  },
});
