// Layer 2 — Udemy. 채점 전후로 DOM 이 다르다. 계약은 MASTER 의 DOM 계약 절.
const ST_UDEMY_RICH =
  "div[data-purpose='safely-set-inner-html:rich-text-viewer:html']";

globalThis.ST.adapters.push({
  name: "udemy",
  priority: 10,
  match: () => location.hostname.endsWith("udemy.com"),

  collect(root) {
    const scope = root.querySelector(".quiz-page-content");
    if (!scope) return [];

    // 두 화면의 셀렉터를 합집합으로 건다. 없는 쪽은 0개가 나온다.
    const els = [
      ...scope.querySelectorAll("[id=question-prompt]"),          // 문제 (공통)
      ...scope.querySelectorAll("[id=answer-text]"),              // 보기 (채점 후)
      ...scope.querySelectorAll("[id=question-explanation]"),     // 해설 (채점 후)
      ...scope.querySelectorAll(`.ud-unstyled-list ${ST_UDEMY_RICH}`), // 보기 (채점 전)
    ];

    return [...new Set(els)]
      .filter((el) => !el.dataset.stDone && (el.innerText || "").trim())
      .map((el, i) => ({
        id: "u" + i,
        text: el.innerText.trim(),
        el,
        anchor: this.anchorFor(el),
        group: "quiz",   // 한 배치로 번역해 용어를 맞춘다
      }));
  },

  anchorFor(el) {
    // 채점 전: 좁은 grid 칸이라 한 단계 위. 채점 후: answer-body.
    return (
      el.closest("[class*=answer-inner]") ||
      el.closest("[data-purpose=answer-body]") ||
      el
    );
  },

  decorate(node) {
    node.style.setProperty("width", "100%", "important");
    node.style.setProperty("white-space", "normal", "important");
    node.style.setProperty("overflow-wrap", "break-word", "important");
  },
});
