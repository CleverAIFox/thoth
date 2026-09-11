// Layer 1 — ARIA · 폼 표준. 사이트 지식 0. group 을 채우는 것이 목적이다.
globalThis.ST.adapters.push({
  name: "standard",
  priority: 5,

  match: () =>
    document.querySelector("[role=radiogroup], [role=listbox], form input[type=radio]") !== null,

  collect(root) {
    const units = [];
    const groups = root.querySelectorAll("[role=radiogroup],[role=listbox]");
    groups.forEach((grp, gi) => {
      grp.querySelectorAll("[role=radio],[role=option],label").forEach((el, i) => {
        const t = (el.innerText || "").trim();
        if (!t || el.dataset.stDone) return;
        units.push({ id: `s${gi}-${i}`, text: t, el, anchor: el, group: `g${gi}` });
      });
    });
    return units;
  },
});
