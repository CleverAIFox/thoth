const ST_FILES = ["src/adapters/generic.js","src/adapters/standard.js","src/adapters/udemy.js","src/client.js","src/broker.js"];

// 유데미 외 사이트: 아이콘 클릭 -> 해당 오리진 권한 요청 -> 브로커 주입.
// 한 번 승인하면 그 사이트는 이후 자동으로 동작한다(권한이 영구 부여됨).

const inject = async (tabId) => {
  try {
    await chrome.scripting.insertCSS({ target: { tabId }, files: ["content.css"] });
    await chrome.scripting.executeScript({ target: { tabId }, files: ST_FILES });
  } catch (e) {
    // chrome:// · 웹스토어 · 파일 URL 등은 주입이 막혀 있다. 조용히 넘긴다.
    console.debug("[st] 주입 불가", e?.message);
  }
};

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id || !tab.url?.startsWith("http")) return;

  const origin = new URL(tab.url).origin + "/*";
  // ★ permissions.request 는 유저 제스처 안에서 불려야 한다. 앞에 await 를
  //   하나라도 두면 제스처가 끊겨 요청이 거부된다(DECISIONS §13).
  //   이미 가진 권한이면 request 가 즉시 true 로 해소되므로 contains 는 필요 없다.
  let granted = false;
  try {
    granted = await chrome.permissions.request({ origins: [origin] });
  } catch (e) {
    console.warn("[st] 권한 요청 실패", e?.message);
    return;
  }
  if (!granted) return;

  await inject(tab.id);
});

// 이미 승인된 사이트는 다음 방문부터 자동 주입.
// manifest content_scripts 가 이미 맡는 곳과 정확히 같은 패턴이어야 한다.
// 여기가 넓으면 그쪽이 안 닿는 호스트를 건너뛰어 아무도 안 맡는 구멍이 생긴다.
const ST_STATIC = [/^www\.udemy\.com$/];

chrome.tabs.onUpdated.addListener(async (tabId, info, tab) => {
  if (info.status !== "complete" || !tab.url?.startsWith("http")) return;

  let host, origin;
  try {
    const u = new URL(tab.url);
    host = u.hostname;
    origin = u.origin + "/*";
  } catch { return; }

  if (ST_STATIC.some((re) => re.test(host))) return;
  if (!(await chrome.permissions.contains({ origins: [origin] }))) return;

  await inject(tabId);
});
