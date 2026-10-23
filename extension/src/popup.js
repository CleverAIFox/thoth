// 팝업. 판정은 state.js 가 하고 여기는 DOM 에 바르기만 한다.
//
// ★ **아이콘 클릭이 팝업 열기로 바뀌었다.** `default_popup` 이 있으면
//   `chrome.action.onClicked` 는 발화하지 않는다. 그래서 권한 요청과 주입이
//   background 에서 이리로 옮겨 왔다(DECISIONS §38).
//
// ★ 팝업은 콘텐츠 스크립트가 아니다. 재주입되지 않으므로 최상위 선언 금지
//   규약(DECISIONS §16)의 대상이 아니다.
import { healthLine, healthUrl, normalizeSettings, siteState, 호스트 } from "./state.js";

const $ = (id) => document.getElementById(id);

// ★ 팝업이 **열릴 때** 미리 받아 둔다. 버튼을 누른 뒤에 조회하면 그 비동기
//   호출이 사용자 제스처를 끊어 권한 요청이 거부된다(DECISIONS §13).
//   크롬 문서도 UI 초기화 시점에 contains 를 부르라고 적는다.
let tab = null;
let site = { kind: "", origin: "" };
let host = "";
let 지도 = {};

// ★ **열쇠 글자는 한 곳에서 온다**(DECISIONS §209 · §91). 종전에는 `"stOff"` 가
//   팝업과 브로커에 **글자로** 박혀 있었고, 그 둘이 갈리면 팝업이 「켬」 을 그리고
//   브로커는 수집만 도는 **거짓말**이 된다. `지문.js` 가 정본이다.
const { 사이트키, 차단키 } = globalThis.ST.사이트;

// ★ **권한이 아니라 「이 사이트에서 무엇이 도나」 를 적는다**(DECISIONS §209).
//   권한은 `<all_urls>` 라 언제나 있다 — 그것을 상태로 보여 주면 **아무 정보가
//   없는 줄**이고, 사람은 그 「켜져 있다」 를 **번역이 켜졌다**로 읽는다.
function paint() {
  const el = $("site-state");
  if (!host) {
    el.textContent = "이 탭에는 넣을 수 없다";
    el.dataset.level = "";
    return;
  }
  const 켬 = $("show").checked && !$("killall").checked;
  el.textContent = `${host} — ${켬 ? "번역 켬" : "수집만"}`;
  el.dataset.level = 켬 ? "good" : "warn";
}

async function load() {
  const [t] = await chrome.tabs.query({ active: true, currentWindow: true });
  tab = t || null;
  const origin = tab ? tab.url : "";
  host = 호스트(origin);
  site = siteState(origin, true);   // 권한은 `<all_urls>` 라 언제나 있다

  const s = await chrome.storage.local.get([차단키, 사이트키, "stEndpoint", "stToken"]);
  // ★ **지도를 읽을 뿐 판정을 다시 적지 않는다**(DECISIONS §209 · §91). 판정은
  //   `지문.js` 의 `번역할까` 하나이고, 여기는 **그 지도의 한 칸**을 그린다.
  //   `mode.test.js` 가 팝업이 그리는 것과 그 함수의 답이 같은지 붙든다.
  지도 = s[사이트키] || {};
  $("show").checked = !!host && 지도[host] === true;
  $("killall").checked = s[차단키] === true;
  paint();
  $("endpoint").value = s.stEndpoint || "";
  $("token").value = s.stToken || "";
  // ★ **빈 칸의 흐린 글자는 「아무것도 안 넣으면 여기로 간다」 는 말이다**(DECISIONS §173).
  //   그런데 `127.0.0.1` 이 글자로 박혀 있어서, ext-build 처럼 기계 기본값이 파일에
  //   있는 판에서는 **거짓말을 하고 있었다.** 실제로 쓰는 값을 그대로 보여 준다.
  $("endpoint").placeholder = globalThis.ST.쓸주소("", false);
  if (!s.stToken && globalThis.ST.쓸토큰("", false)) $("token").placeholder = "파일에 있다";
}

// ---------- 번역 토글 ----------
//
// ★ **저장만 한다**(DECISIONS §177). 종전에는 여기서 `executeScript` 로 열린 탭의
//   `html.st-off` 를 **직접 뒤집었다** — 저장소와 DOM 두 길로 쓴 것이고, 끄기가
//   「상자 숨김」 이었던 동안은 그것으로 충분했다. 이제 끊는 자리가 **수집 바로
//   뒤**라 클래스만 뒤집으면 **워커를 계속 때린다.** 브로커가 `storage.onChanged`
//   를 듣고 제가 적용한다 — `Alt+K` 와 **같은 한 길**이다.
$("show").addEventListener("change", async () => {
  if (!host) return;
  const s = await chrome.storage.local.get([사이트키]);
  const m = { ...(s[사이트키] || {}) };
  if ($("show").checked) m[host] = true; else delete m[host];
  await chrome.storage.local.set({ [사이트키]: m });
  paint();
});

// ★ **마스터 차단은 지도보다 세다**(DECISIONS §209). 사이트 지도를 안 지운다 —
//   끄고 켜면 켜 두었던 사이트가 그대로 돌아온다.
$("killall").addEventListener("change", async () => {
  await chrome.storage.local.set({ [차단키]: $("killall").checked });
  paint();
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

// ---------- 수집 장부 내보내기 ----------
//
// ★ **네트워크가 없다**(DECISIONS §183). 장부는 `chrome.storage.local` 에만 있고
//   여기서 클립보드로 나간다 — 주 35건짜리에 워커와 DB 를 짓지 않는다(§133).
// ★ **담긴 칸은 수뿐이다.** 글자도 경로도 안 담기므로 붙여 넣어도 새는 것이 없다.
$("export").addEventListener("click", async () => {
  const out = $("exported");
  const s = await chrome.storage.local.get(["st수집"]);
  const 장부 = Array.isArray(s.st수집) ? s.st수집 : [];
  if (!장부.length) {
    out.textContent = "아직 비었다";
    out.dataset.level = "";
    return;
  }
  const 글 = JSON.stringify(장부, null, 1);
  try {
    await navigator.clipboard.writeText(글);
    out.textContent = `${장부.length}건 복사했다`;
    out.dataset.level = "good";
  } catch {
    // ★ 클립보드가 막히는 자리가 있다. 조용히 지나가면 **눌렀는데 아무 일도 안 난
    //   것처럼** 보인다 — 콘솔로라도 내보낸다.
    console.info("[st] 수집 장부", 글);
    out.textContent = "클립보드가 막혔다 — 콘솔에 냈다";
    out.dataset.level = "warn";
  }
});

load();
