// 워커 계약 : POST /translate {texts[], target} -> {translations[], cached[], version}
globalThis.ST.DEFAULT_ENDPOINT = "http://127.0.0.1:8000/translate";
globalThis.ST.TIMEOUT_MS = 200000;   // 로컬 엔진의 ollama 타임아웃(180s)보다 길게

// 상태 코드를 실어 던진다. 브로커가 영구 실패와 일시 실패를 갈라야 하는데
// 문자열 메시지만 주면 갈 수 없다.
//
// ★ 최상위 class 선언을 쓰지 않는다. class 는 const 와 같아 재선언이
//   SyntaxError 이고, 이 파일은 아이콘 클릭·onUpdated 로 재주입된다.
//   한 번 터지면 파일 전체가 죽어 ST.translate 가 갱신되지 않는다
//   (MASTER §9, DECISIONS §16).
globalThis.ST.WorkerError ??= class WorkerError extends Error {
  constructor(status, code) {
    super(`worker ${status}${code ? " " + code : ""}`);
    this.name = "WorkerError";
    this.status = status;
    this.code = code;
    // 4xx 는 같은 입력으로 재시도해도 결과가 같다. 5xx · 네트워크만 재시도한다.
    this.fatal = status >= 400 && status < 500;
  }
};

globalThis.ST.translate = async function (texts) {
  const { stEndpoint, stToken } = await chrome.storage.local.get(["stEndpoint", "stToken"]);
  const url = stEndpoint || globalThis.ST.DEFAULT_ENDPOINT;

  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), globalThis.ST.TIMEOUT_MS);

  // ★ 토큰이 없으면 헤더를 아예 붙이지 않는다. 빈 값으로 보내면 토큰을 끈
  //   로컬 워커에서도 preflight 가 도는데, 얻는 것 없이 왕복만 는다.
  const headers = { "Content-Type": "application/json" };
  if (stToken) headers["X-Thoth-Token"] = stToken;

  let res;
  try {
    res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({ texts, target: "ko" }),
      signal: ctl.signal,
    });
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    let code = "";
    try { code = (await res.json()).error || ""; } catch { /* 본문 없음 */ }
    throw new globalThis.ST.WorkerError(res.status, code);
  }

  const data = await res.json();
  if (!Array.isArray(data.translations) || data.translations.length !== texts.length) {
    throw new globalThis.ST.WorkerError(502, "contract_violation");
  }
  // ★ 배열이 아니라 객체를 돌려준다. 부분 응답에서는 '무엇이 왔는가' 와
  //   '왜 나머지가 없는가' 가 둘 다 필요하고, 배열 하나로는 후자를 실을 수
  //   없다. 못 채운 자리는 null 이며 브로커가 그 자리만 회수한다.
  return { translations: data.translations, partial: data.partial || "" };
};
