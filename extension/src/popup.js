// 팝업. 판정은 state.js 가 하고 여기는 DOM 에 바르기만 한다.
//
// ★ **아이콘 클릭이 팝업 열기로 바뀌었다.** `default_popup` 이 있으면
//   `chrome.action.onClicked` 는 발화하지 않는다. 그래서 권한 요청과 주입이
//   background 에서 이리로 옮겨 왔다(DECISIONS §38).
//
// ★ 팝업은 콘텐츠 스크립트가 아니다. 재주입되지 않으므로 최상위 선언 금지
//   규약(DECISIONS §16)의 대상이 아니다.
import { healthLine, healthUrl, normalizeSettings, siteState,
         ORIGIN_GRANTED, ORIGIN_MISSING } from "./state.js";

const $ = (id) => document.getElementById(id);

// ★ 팝업이 **열릴 때** 미리 받아 둔다. 버튼을 누른 뒤에 조회하면 그 비동기
//   호출이 사용자 제스처를 끊어 권한 요청이 거부된다(DECISIONS §13).
//   크롬 문서도 UI 초기화 시점에 contains 를 부르라고 적는다.
let tab = null;
let site = { kind: "", origin: "" };

function paint() {
  const el = $("site-state");
  if (site.kind === ORIGIN_GRANTED) {
    el.textContent = "이 사이트에서 켜져 있다";
    el.dataset.level = "good";
    $("enable").hidden = true;
  } else if (site.kind === ORIGIN_MISSING) {
    el.textContent = "아직 권한이 없다";
    el.dataset.level = "warn";
    $("enable").hidden = false;
  } else {
    el.textContent = "이 탭에는 넣을 수 없다";
    el.dataset.level = "";
    $("enable").hidden = true;
  }
}

async function load() {
  const [t] = await chrome.tabs.query({ active: true, currentWindow: true });
  tab = t || null;
  const origin = tab ? tab.url : "";
  let granted = false;
  const pattern = origin && origin.startsWith("http")
    ? new URL(origin).origin + "/*" : "";
  if (pattern) {
    granted = await chrome.permissions.contains({ origins: [pattern] });
  }
  site = siteState(origin, granted);
  paint();

  const s = await chrome.storage.local.get(["stOff", "stEndpoint", "stToken"]);
  $("show").checked = !s.stOff;
  $("endpoint").value = s.stEndpoint || "";
  $("token").value = s.stToken || "";
}

// ---------- 권한 요청 ----------
//
// ★ 이 핸들러 안에서는 `await` 를 쓰지 않는다. 한 번이라도 대기하면 제스처
//   문맥을 잃고 요청이 거부된다. 콜백 형태로 부른다(DECISIONS §13).
$("enable").addEventListener("click", () => {
  if (!site.origin || !tab) return;
  chrome.permissions.request({ origins: [site.origin] }, (granted) => {
    if (chrome.runtime.lastError || !granted) {
      $("site-state").textContent = "권한이 거부됐다";
      $("site-state").dataset.level = "bad";
      return;
    }
    site = { ...site, kind: ORIGIN_GRANTED };
    paint();
    // 주입은 제스처가 필요 없다. 승인된 뒤에 background 에 맡긴다.
    chrome.runtime.sendMessage({ type: "inject", tabId: tab.id });
  });
});

// ---------- 표시 토글 ----------
//
// ★ `Alt+K` 와 같은 경로를 탄다. 브로커가 `stOff` 를 보고 `html.st-off` 를
//   전환하므로 여기서는 저장만 하고 열린 탭에도 같은 변화를 알린다.
$("show").addEventListener("change", async () => {
  const off = !$("show").checked;
  await chrome.storage.local.set({ stOff: off });
  if (tab && site.kind === ORIGIN_GRANTED) {
    try {
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        args: [off],
        func: (v) => document.documentElement.classList.toggle("st-off", v),
      });
    } catch { /* 주입되지 않은 탭이면 다음 방문에 반영된다 */ }
  }
});

// ---------- 연결 확인 ----------

$("check").addEventListener("click", async () => {
  const out = $("health");
  out.textContent = "확인 중…";
  out.dataset.level = "";
  $("check").disabled = true;

  const s = await chrome.storage.local.get(["stEndpoint", "stToken"]);
  const url = healthUrl(s.stEndpoint || "http://127.0.0.1:8000/translate");
  const headers = {};
  if (s.stToken) headers["X-Thoth-Token"] = s.stToken;

  let res = null;
  try {
    const r = await fetch(url, { headers });
    let body = null;
    try { body = await r.json(); } catch { /* 본문이 JSON 이 아니다 */ }
    res = { ok: r.ok, status: r.status, body };
  } catch {
    res = { ok: false };          // 네트워크 실패. status 가 없다
  }
  const line = healthLine(res);
  out.textContent = line.text;
  out.dataset.level = line.level;
  $("check").disabled = false;
});

// ---------- 설정 저장 ----------

$("save").addEventListener("click", async () => {
  const r = normalizeSettings({ endpoint: $("endpoint").value, token: $("token").value });
  const out = $("saved");
  if (r.error) {
    out.textContent = r.error;
    out.dataset.level = "bad";
    return;
  }
  await chrome.storage.local.set(r.value);
  out.textContent = "저장했다";
  out.dataset.level = "good";
});

load();
