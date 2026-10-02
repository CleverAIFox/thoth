// 팝업이 무엇을 보여야 하는지 정하는 순수 함수들.
//
// ★ chrome API 를 부르지 않는다. 그래야 브라우저 없이 검증된다. 확장의 판정은
//   DOM 조작과 섞이면 브라우저 없이 검사할 수 없다. 판정을
//   DOM 조작에서 떼어내면 그 부분만이라도 기계가 본다.
//
// ★ 이 파일은 콘텐츠 스크립트로 주입되지 않는다. 팝업에서 import 로만 쓰므로
//   최상위 선언 금지 규약(DECISIONS §16)의 대상이 아니다. 그 규약은 재주입될
//   때 재선언이 SyntaxError 가 되는 파일에만 해당한다.

export const ORIGIN_UNSUPPORTED = "unsupported";
export const ORIGIN_MISSING = "missing";
export const ORIGIN_GRANTED = "granted";

/** 탭 URL 에서 권한 요청에 쓸 오리진 패턴. 만들 수 없으면 빈 문자열. */
export function originPattern(url) {
  if (typeof url !== "string" || !url.startsWith("http")) return "";
  try {
    return new URL(url).origin + "/*";
  } catch {
    return "";
  }
}

/**
 * 이 탭에서 무엇을 보여줄지.
 *
 * ★ `granted` 는 팝업이 **열릴 때** 미리 조회해 둔 값이다. 버튼을 누른 뒤에
 *   조회하면 그 비동기 호출이 사용자 제스처를 끊어 권한 요청이 거부된다
 *   (DECISIONS §13). 판정에 필요한 것을 미리 받아 두는 이유가 그것이다.
 */
export function siteState(url, granted) {
  const origin = originPattern(url);
  if (!origin) return { kind: ORIGIN_UNSUPPORTED, origin: "" };
  return { kind: granted ? ORIGIN_GRANTED : ORIGIN_MISSING, origin };
}

/**
 * `/health` 응답을 사람이 읽는 한 줄로.
 *
 * ★ 오늘 우리가 겪은 진단을 사용자도 겪는다. 번역이 안 될 때 워커가 죽었는지
 *   토큰이 틀렸는지 엔진이 안 떴는지 알 방법이 콘솔뿐이었다(DECISIONS §37).
 *   한 줄로 답하게 한다.
 */
export function healthLine(res) {
  if (!res || !res.ok) {
    const s = res && res.status;
    if (s === 401) return { level: "bad", text: "토큰이 거부됐다 — 고급에서 확인한다" };
    if (s) return { level: "bad", text: `워커가 ${s} 를 돌려줬다` };
    return { level: "bad", text: "워커에 닿지 못했다 — 엔드포인트와 기동을 본다" };
  }
  const b = res.body || {};
  const parts = [`엔진 ${b.engine || "?"}`, `캐시 ${b.cache || "?"}`];
  if (b.auth) {
    // 잔여가 빠져 왔으면 토큰이 안 맞은 것이다. 200 이어도 신호가 된다.
    parts.push(b.chars_remaining === undefined ? "토큰 불일치" : "토큰 확인됨");
  }
  const level = b.status === "ok" ? "good" : "warn";
  const head = b.status === "ok" ? "워커 정상" : `워커 ${b.status || "이상"}`;
  return { level, text: `${head} · ${parts.join(" · ")}` };
}

// ★ **되돌이 주소만 평문을 허락한다**(DECISIONS §125). 토큰은 요청에 실려 가고,
//   남의 호스트로 `http://` 로 보내면 **중간에서 그대로 읽힌다** — 그 토큰으로
//   남이 월 상한을 태운다(MASTER §12). 되돌이는 기계를 벗어나지 않으므로 밖이다.
// ★ `localhost` 를 목록에 넣는다. 사람이 거기를 먼저 치고, 막으면 로컬 개발이
//   선 자리에서 멈춘다 — **검사가 맞는 상태를 위반으로 잡으면 끄는 방법부터 찾는다.**
const 되돌이 = new Set(["127.0.0.1", "::1", "[::1]", "localhost"]);

/** 저장 전에 다듬는다. 빈 값은 지운다는 뜻이므로 그대로 둔다. */
export function normalizeSettings(raw) {
  const out = {};
  const ep = (raw.endpoint || "").trim();
  if (ep && !/^https?:\/\//.test(ep)) {
    return { error: "엔드포인트는 http:// 나 https:// 로 시작해야 한다" };
  }
  if (ep && ep.startsWith("http://")) {
    // ★ 호스트를 문자열로 자르지 않고 `URL` 에 묻는다. `http://a.test@127.0.0.1/`
    //   처럼 사용자 정보로 눈속임하는 주소를 손으로 가르면 틀린다.
    let host;
    try {
      host = new URL(ep).hostname;
    } catch {
      return { error: "엔드포인트를 주소로 읽을 수 없다" };
    }
    if (!되돌이.has(host)) {
      return { error: `${host} 로는 https:// 가 필요하다 — 평문으로 보내면 토큰이 읽힌다` };
    }
  }
  out.stEndpoint = ep;
  out.stToken = (raw.token || "").trim();
  return { value: out };
}

/** `/health` 주소. 엔드포인트가 `/translate` 로 끝나면 바꿔 끼운다. */
export function healthUrl(endpoint) {
  const ep = (endpoint || "").trim();
  if (!ep) return "";
  return ep.replace(/\/translate\/?$/, "") + "/health";
}
