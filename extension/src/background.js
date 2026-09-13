const ST_FILES = ["src/adapters/generic.js","src/adapters/standard.js","src/adapters/udemy.js","src/client.js","src/broker.js"];

// 유데미 외 사이트: 아이콘 클릭 -> 해당 오리진 권한 요청 -> 브로커 주입.
// 한 번 승인하면 그 사이트는 이후 자동으로 동작한다(권한이 영구 부여됨).

const inject = async (tabId) => {
  // ★ 이미 돌고 있으면 주입하지 않는다. 콘텐츠 스크립트는 재주입 시 전부
  //   다시 평가되고, 최상위 선언이 하나라도 있으면 SyntaxError 로 그 파일이
  //   통째로 죽는다(DECISIONS §16).
  try {
    const [r] = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => Boolean(globalThis.ST?.__running),
    });
    if (r?.result) { console.log("[st] 이미 동작 중 — 탭", tabId); return true; }
  } catch { /* 주입 불가 탭이면 아래에서 다시 걸린다 */ }

  try {
    await chrome.scripting.insertCSS({ target: { tabId }, files: ["content.css"] });
    await chrome.scripting.executeScript({ target: { tabId }, files: ST_FILES });
  } catch (e) {
    // chrome:// · 웹스토어 · 파일 URL 등은 주입이 막혀 있다. 다만 조용히
    // 넘기지 않는다 — debug 레벨은 기본 필터에서 안 보여 실패가 숨는다.
    console.warn("[st] 주입 실패", e?.message);
    return false;
  }
  console.log("[st] 주입 완료 —", tabId);
  return true;
};

// ★ 리스너를 async 로 두지 않는다. permissions.request 는 유저 제스처
//   안에서 불려야 하는데, async 함수 본문은 마이크로태스크로 넘어가 제스처
//   문맥을 잃는다. 동기 리스너에서 콜백 형태로 부른다(DECISIONS §13).
chrome.action.onClicked.addListener((tab) => {
  if (!tab.id) return;
  // activeTab 이 있어도 URL 이 비어 오는 경우가 있다. 그때는 조용히 죽지 말고
  // 무엇이 없는지 남긴다. 이 한 줄이 없어서 원인 찾는 데 오래 걸렸다.
  if (!tab.url) { console.warn("[st] tab.url 이 비었다 — 탭", tab.id); return; }
  if (!tab.url.startsWith("http")) { console.warn("[st] http 아님 —", tab.url); return; }

  let origin;
  try {
    origin = new URL(tab.url).origin + "/*";
  } catch { return; }

  chrome.permissions.request({ origins: [origin] }, (granted) => {
    const err = chrome.runtime.lastError?.message;
    if (err) { console.warn("[st] 권한 요청 실패 —", err); return; }
    if (!granted) { console.warn("[st] 권한 거부 —", origin); return; }
    console.log("[st] 권한 승인 —", origin);
    inject(tab.id);
  });
});

// 이미 승인된 사이트는 다음 방문부터 자동 주입.
//
// ★ 사이트 목록을 코드에 들지 않는다. 전에는 Udemy 만 content_scripts 로
//   자동 주입하고 여기서 제외 목록으로 걸렀는데, 같은 사실이 manifest 두
//   곳과 이 파일 세 군데에 다른 문법으로 살았다. 한쪽만 고치면 조용히
//   어긋난다. Udemy 도 다른 사이트와 같이 한 번 승인받는다(DECISIONS §14).

chrome.tabs.onUpdated.addListener(async (tabId, info, tab) => {
  if (info.status !== "complete" || !tab.url?.startsWith("http")) return;

  let origin;
  try {
    origin = new URL(tab.url).origin + "/*";
  } catch { return; }

  if (!(await chrome.permissions.contains({ origins: [origin] }))) return;

  await inject(tabId);
});
