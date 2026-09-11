// 워커 계약 : POST /translate {texts[], target} -> {translations[], cached[], version}
globalThis.ST.DEFAULT_ENDPOINT = "http://127.0.0.1:8000/translate";

globalThis.ST.translate = async function (texts) {
  const { stEndpoint } = await chrome.storage.local.get("stEndpoint");
  const url = stEndpoint || globalThis.ST.DEFAULT_ENDPOINT;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texts, target: "ko" }),
  });
  if (!res.ok) throw new Error(`worker ${res.status}`);

  const data = await res.json();
  if (!Array.isArray(data.translations) || data.translations.length !== texts.length) {
    throw new Error("worker contract violation");
  }
  return data.translations;
};
