// Layer 2 — Udemy. 채점 전후로 DOM 이 다르다. 계약은 MASTER 의 DOM 계약 절.
globalThis.ST_UDEMY_RICH =
  "div[data-purpose='safely-set-inner-html:rich-text-viewer:html']";

if (!globalThis.ST.adapters.some((a) => a.name === "udemy"))
globalThis.ST.adapters.push({
  name: "udemy",
  priority: 10,
  match: () => new URL(globalThis.ST.pageUrl()).hostname.endsWith("udemy.com"),

  // ★ **셀렉터를 한 자리에 둔다.** `collect` 와 `observe` 가 같은 문자열을 따로
  //   들면 한쪽만 고쳐졌을 때 관측이 **고친 뒤의 DOM 을 옛 셀렉터로** 재게 된다.
  SEL: {
    scope: ".quiz-page-content",
    prompt: "[id=question-prompt]",
    answerAfter: "[id=answer-text]",
    explanation: "[id=question-explanation]",
    answerBefore: `.ud-unstyled-list ${globalThis.ST_UDEMY_RICH}`,
  },

  // ★ **URL 은 DOM 보다 오래 산다.** 해시 클래스는 빌드마다 바뀌지만(MASTER §3-1)
  //   경로는 북마크와 공유 링크가 걸려 있어 쉽게 못 바꾼다. 그래서 "여기서 무엇이
  //   나와야 하는가" 를 DOM 이 아니라 경로로 정한다. DOM 으로 정하면 그 DOM 이
  //   깨졌을 때 기대도 같이 사라진다.
  //
  // ★ **이 패턴은 실측이 아니다.** 연습 시험 URL 이 `/learn/quiz/<id>` 꼴이라는
  //   기억에 기대고 있다. 실사이트 한 번이면 확인된다(DECISIONS §102).
  QUIZ_PATH: /\/learn\/quiz\//,

  collect(root) {
    const S = this.SEL;
    const scope = root.querySelector(S.scope);
    if (!scope) return [];

    // 두 화면의 셀렉터를 합집합으로 건다. 없는 쪽은 0개가 나온다.
    const els = [
      ...scope.querySelectorAll(S.prompt),          // 문제 (공통)
      ...scope.querySelectorAll(S.answerAfter),     // 보기 (채점 후)
      ...scope.querySelectorAll(S.explanation),     // 해설 (채점 후)
      ...scope.querySelectorAll(S.answerBefore),    // 보기 (채점 전)
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

  // 셀렉터마다 몇 개가 잡히는지. **판정하지 않는다** — 수만 센다(DECISIONS §102).
  //
  // ★ `stDone` 을 거르지 않는다. 이미 번역한 요소도 셀렉터가 잡는 것은 맞고,
  //   거르면 번역이 끝난 정상 페이지가 전부 0 으로 보인다.
  observe(root) {
    const S = this.SEL;
    const path = new URL(globalThis.ST.pageUrl()).pathname;
    const kind = this.QUIZ_PATH.test(path) ? "quiz" : "other";
    const scope = root.querySelector(S.scope);
    const count = (sel) => (scope ? scope.querySelectorAll(sel).length : 0);
    return {
      kind,
      expected: kind === "quiz",
      probes: {
        scope: scope ? 1 : 0,
        prompt: count(S.prompt),
        answer_before: count(S.answerBefore),
        answer_after: count(S.answerAfter),
        explanation: count(S.explanation),
      },
    };
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
