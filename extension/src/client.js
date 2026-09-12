// 워커 계약 : POST /translate {texts[], target} -> {translations[], cached[], version}
globalThis.ST.DEFAULT_ENDPOINT = "http://127.0.0.1:8000/translate";
globalThis.ST.TIMEOUT_MS = 200000;   // 로컬 엔진의 ollama 타임아웃(180s)보다 길게

// 상태 코드를 실어 던진다. 브로커가 영구 실패와 일시 실패를 갈라야 하는데
// 문자열 메시지만 주면 갈 수 없다.
class WorkerError extends Error {
  constructor(status, code) {
    super(`worker ${status}${code ? " " + code : ""}`);
    this.status = status;
    this.code = code;
    // 4xx 는 같은 입력으로 재시도해도 결과가 같다. 5xx · 네트워크만 재시도한다.
    this.fatal = status >= 400 && status < 500;
  }
}
globalThis.ST.WorkerError = WorkerError;

globalThis.ST.translate = async function (texts) {
  const { stEndpoint } = await chrome.storage.local.get("stEndpoint");
  const url = stEndpoint || globalThis.ST.DEFAULT_ENDPOINT;

  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), globalThis.ST.TIMEOUT_MS);

  let res;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texts, target: "ko" }),
      signal: ctl.signal,
    });
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    let code = "";
    try { code = (await res.json()).error || ""; } catch { /* 본문 없음 */ }
    throw new WorkerError(res.status, code);
  }

  const data = await res.json();
  if (!Array.isArray(data.translations) || data.translations.length !== texts.length) {
    throw new WorkerError(502, "contract_violation");
  }
  return data.translations;
};
