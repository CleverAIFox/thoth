// 유데미 외 사이트: 아이콘 클릭 -> 해당 오리진 권한 요청 -> 브로커 주입.
// 한 번 승인하면 그 사이트는 이후 자동으로 동작한다(권한이 영구 부여됨).

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id || !tab.url?.startsWith("http")) return;

  const origin = new URL(tab.url).origin + "/*";
  const granted =
    (await chrome.permissions.contains({ origins: [origin] })) ||
    (await chrome.permissions.request({ origins: [origin] }));

  if (!granted) return;

  await chrome.scripting.insertCSS({ target: { tabId: tab.id }, files: ["content.css"] });
  await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["src/broker.js"] });
});

// 이미 승인된 사이트는 다음 방문부터 자동 주입.
chrome.tabs.onUpdated.addListener(async (tabId, info, tab) => {
  if (info.status !== "complete" || !tab.url?.startsWith("http")) return;

  const origin = new URL(tab.url).origin + "/*";
  if (!(await chrome.permissions.contains({ origins: [origin] }))) return;

  await chrome.scripting.insertCSS({ target: { tabId }, files: ["content.css"] });
  await chrome.scripting.executeScript({ target: { tabId }, files: ["src/broker.js"] });
});
