const ST_FILES = ["src/config.local.js","src/adapters/generic.js","src/adapters/standard.js","src/adapters/udemy.js","src/client.js","src/cssaudit.js","src/broker.js"];

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
    // ★ **같은 파일을 섀도 안에도 넣어야 한다**(DECISIONS §169). 번역 박스의 꾸밈은
    //   섀도 경계 뒤에 있고, `insertCSS` 는 **페이지**에만 넣는다.
    //
    // ★ **브로커가 제 손으로 받지 않는다.** 콘텐츠 스크립트에서 `fetch` 로 확장
    //   리소스를 받으려면 `web_accessible_resources` 가 필요하고 — 그러면 **모든
    //   사이트가 우리 CSS 를 읽을 수 있다** — 페이지 CSP 에 걸릴 수도 있다.
    //   **서비스 워커는 제 리소스를 아무 제약 없이 읽는다.** 글자로 밀어 넣는다.
    //
    // ★ **ST_FILES 보다 먼저다.** `broker.js` 는 올라가는 순간 첫 순회를 돌린다 —
    //   뒤에 넣으면 **첫 순회의 박스들만 맨몸으로** 서고, 그것이 가장 늦게
    //   발견되는 종류다(§169).
    const 글 = await (await fetch(chrome.runtime.getURL("content.css"))).text();
    await chrome.scripting.executeScript({
      target: { tabId },
      func: (s) => { (globalThis.ST ??= {}).상자CSS = s; },
      args: [글],
    });
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

// ★ **아이콘 클릭 리스너를 두지 않는다.** `default_popup` 이 있으면
//   `chrome.action.onClicked` 는 발화하지 않는다. 발화하지 않는 코드를
//   남기면 다음 사람이 그것이 도는 줄 안다(DECISIONS §38).
//
//   권한 요청은 팝업의 버튼 클릭 핸들러로 옮겼다. 팝업의 클릭도 사용자
//   제스처이므로 `permissions.request` 가 거기서 성립한다. 대기 한 번에
//   문맥을 잃는다는 제약은 그대로다(DECISIONS §13).

// 팝업이 권한을 받아낸 뒤 주입을 맡긴다. 주입 자체는 제스처가 필요 없다.
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "inject" || !msg.tabId) return;
  inject(msg.tabId).then(sendResponse);
  return true;          // 비동기 응답을 쓰겠다는 표시. 없으면 채널이 먼저 닫힌다
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
