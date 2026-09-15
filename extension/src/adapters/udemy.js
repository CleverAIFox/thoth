// Layer 2 — Udemy. 채점 전후로 DOM 이 다르다. 계약은 MASTER 의 DOM 계약 절.
globalThis.ST_UDEMY_RICH =
  "div[data-purpose='safely-set-inner-html:rich-text-viewer:html']";

if (!globalThis.ST.adapters.some((a) => a.name === "udemy"))
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
      .filter((el) => !el.dataset.stDone && !el.dataset.stFail && (el.innerText || "").trim())
      .map((el, i) => ({
        id: "u" + i,
        text: el.innerText.trim(),
        el,
        anchor: this.anchorFor(el),
        group: "quiz",   // 같은 묶음으로 둔다. 실제로 한 요청에 함께
                         // 실리는 것은 브로커의 MAX_BATCH 를 되돌린 뒤다
                         // (DECISIONS §80)
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
    node.style.setProperty("white-space", "pre-wrap", "important");
    node.style.setProperty("overflow-wrap", "break-word", "important");
  },
});
