// 팝업 판정. 순수 함수라 브라우저도 jsdom 도 필요 없다.
//
// ★ 러너는 Node 내장 `node:test` 다. 러너를 고르는 일로 시작을 미루지 않으려고
//   골랐고, 이 파일은 여전히 의존성 없이 돈다. 어댑터와 브로커 검사가 jsdom 을
//   쓰지만 그것은 DOM 이 본체이기 때문이다(DECISIONS §47).
//
//   실행 : node --test "extension/tests/*.test.js"
//   (디렉터리 인자는 먹지 않는다. 글롭을 따옴표로 감싼다)
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  ORIGIN_GRANTED, ORIGIN_MISSING, ORIGIN_UNSUPPORTED,
  healthLine, healthUrl, normalizeSettings, originPattern, siteState,
} from "../src/state.js";

// ---------- 오리진 ----------

test("http 가 아닌 탭은 오리진을 만들지 않는다", () => {
  for (const url of ["chrome://extensions", "file:///tmp/a.html", "", undefined]) {
    assert.equal(originPattern(url), "");
  }
});

test("경로와 질의는 오리진에서 떨어진다", () => {
  assert.equal(originPattern("https://a.test/course/1?x=2#y"), "https://a.test/*");
});

test("포트는 오리진의 일부다", () => {
  assert.equal(originPattern("http://127.0.0.1:8000/x"), "http://127.0.0.1:8000/*");
});

// ---------- 화면 판정 ----------

test("주입할 수 없는 탭은 그렇게 말한다", () => {
  assert.equal(siteState("chrome://newtab", false).kind, ORIGIN_UNSUPPORTED);
});

test("권한이 없으면 켜기를 권한다", () => {
  const s = siteState("https://a.test/x", false);
  assert.equal(s.kind, ORIGIN_MISSING);
  assert.equal(s.origin, "https://a.test/*");
});

test("권한이 있으면 켜진 것으로 본다", () => {
  assert.equal(siteState("https://a.test/x", true).kind, ORIGIN_GRANTED);
});

// ---------- 연결 확인 ----------

test("닿지 못하면 엔드포인트를 가리킨다", () => {
  const r = healthLine({ ok: false });
  assert.equal(r.level, "bad");
  assert.match(r.text, /닿지 못했다/);
});

test("401 은 토큰을 가리킨다", () => {
  // ★ 워커 쪽에서 같은 실수를 했다. 실패를 뭉뚱그리면 사람이 엉뚱한 곳을
  //   고친다(DECISIONS §37).
  assert.match(healthLine({ ok: false, status: 401 }).text, /토큰/);
});

test("정상이면 엔진과 캐시를 보여준다", () => {
  const r = healthLine({ ok: true, body: { status: "ok", engine: "local", cache: "file" } });
  assert.equal(r.level, "good");
  assert.match(r.text, /워커 정상/);
  assert.match(r.text, /엔진 local/);
});

test("토큰이 켜졌는데 잔여가 없으면 불일치다", () => {
  // 워커는 인증되지 않은 /health 에 기동 정보만 준다(MASTER §12). 200 이어도
  // 잔여가 빠져 오면 토큰이 안 맞은 것이다.
  const r = healthLine({ ok: true, body: { status: "ok", engine: "echo", cache: "file", auth: true } });
  assert.match(r.text, /토큰 불일치/);
});

test("토큰이 맞으면 확인됐다고 한다", () => {
  const r = healthLine({
    ok: true,
    body: { status: "ok", engine: "echo", cache: "file", auth: true, chars_remaining: 10 },
  });
  assert.match(r.text, /토큰 확인됨/);
});

test("degraded 는 정상과 구분한다", () => {
  const r = healthLine({ ok: true, body: { status: "degraded", engine: "local", cache: "ddb" } });
  assert.equal(r.level, "warn");
});

// ---------- 설정 ----------

test("스킴이 없는 엔드포인트는 거절한다", () => {
  // 워커 계약과 같은 이유다. 스킴 없는 주소는 fetch 가 페이지 오리진으로 읽는다.
  assert.ok(normalizeSettings({ endpoint: "127.0.0.1:8000/translate" }).error);
});

test("빈 엔드포인트는 기본값으로 되돌린다는 뜻이다", () => {
  const r = normalizeSettings({ endpoint: "", token: "" });
  assert.equal(r.value.stEndpoint, "");
  assert.equal(r.value.stToken, "");
});

test("앞뒤 공백은 떼어 낸다", () => {
  const r = normalizeSettings({ endpoint: "  http://a.test/translate  ", token: "  t  " });
  assert.equal(r.value.stEndpoint, "http://a.test/translate");
  assert.equal(r.value.stToken, "t");
});

// ---------- /health 주소 ----------

test("translate 를 health 로 바꿔 끼운다", () => {
  assert.equal(healthUrl("http://127.0.0.1:8000/translate"), "http://127.0.0.1:8000/health");
  assert.equal(healthUrl("http://127.0.0.1:8000/translate/"), "http://127.0.0.1:8000/health");
});

test("translate 로 끝나지 않아도 health 를 붙인다", () => {
  assert.equal(healthUrl("https://a.test"), "https://a.test/health");
});

test("엔드포인트가 없으면 주소도 없다", () => {
  assert.equal(healthUrl(""), "");
});
