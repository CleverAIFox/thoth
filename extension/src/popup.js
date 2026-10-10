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
  // ★ **칸이 비면 꺼진 쪽이다**(DECISIONS §177). 브로커의 기본값과 **같은 글자로**
  //   적는다 — 한쪽만 `!s.stOff` 면 팝업은 「번역 켬」 을 보여 주고 브로커는 수집만
  //   돈다. 그 어긋남은 **아무것도 안 터지고 거짓말만 한다**(§173).
  $("show").checked = s.stOff === undefined ? false : !s.stOff;
  $("endpoint").value = s.stEndpoint || "";
  $("token").value = s.stToken || "";
  // ★ **빈 칸의 흐린 글자는 「아무것도 안 넣으면 여기로 간다」 는 말이다**(DECISIONS §173).
  //   그런데 `127.0.0.1` 이 글자로 박혀 있어서, ext-build 처럼 기계 기본값이 파일에
  //   있는 판에서는 **거짓말을 하고 있었다.** 실제로 쓰는 값을 그대로 보여 준다.
  $("endpoint").placeholder = globalThis.ST.쓸주소("", false);
  if (!s.stToken && globalThis.ST.쓸토큰("", false)) $("token").placeholder = "파일에 있다";
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

// ---------- 번역 토글 ----------
//
// ★ **저장만 한다**(DECISIONS §177). 종전에는 여기서 `executeScript` 로 열린 탭의
//   `html.st-off` 를 **직접 뒤집었다** — 저장소와 DOM 두 길로 쓴 것이고, 끄기가
//   「상자 숨김」 이었던 동안은 그것으로 충분했다. 이제 끊는 자리가 **수집 바로
//   뒤**라 클래스만 뒤집으면 **워커를 계속 때린다.** 브로커가 `storage.onChanged`
//   를 듣고 제가 적용한다 — `Alt+K` 와 **같은 한 길**이다.
$("show").addEventListener("change", async () => {
  await chrome.storage.local.set({ stOff: !$("show").checked });
});

// ---------- 연결 확인 ----------

$("check").addEventListener("click", async () => {
  const out = $("health");
  out.textContent = "확인 중…";
  out.dataset.level = "";
  $("check").disabled = true;

  const s = await chrome.storage.local.get(["stEndpoint", "stToken"]);
  // ★ **재는 자가 도는 자와 같은 것을 봐야 한다**(DECISIONS §173). 종전에는 여기가
  //   제 사슬을 따로 들었고 **그 사슬이 한 칸 짧아서**(`config.local.js` 누락) 번역이
  //   멀쩡한데 「워커에 닿지 못했다」 가 떴다. 값을 맞추는 규칙 대신 **함수를 같이 쓴다.**
  const 주소 = globalThis.ST.쓸주소(s.stEndpoint, false);
  const url = healthUrl(주소);
  const headers = {};
  const 토큰 = globalThis.ST.쓸토큰(s.stToken, false);
  if (토큰) headers["X-Thoth-Token"] = 토큰;

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
