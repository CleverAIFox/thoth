// 기계별 기본값. **저장소에는 빈 채로 둔다.**
//
// ★ `tools/sync_ext.sh` 가 `.env` 의 `WORKER_URL` · `WORKER_TOKEN` 을 읽어
//   ext-build 쪽 사본에만 값을 써 넣는다. 저장소의 이 파일은 언제나 비어
//   있으므로 **공개 저장소에 엔드포인트도 토큰도 나가지 않는다**(§84).
//
// ★ 파일 자체는 지우지 않는다. `background.js` 의 주입 목록에 들어 있어
//   없으면 주입이 통째로 실패한다.
//
// ★ **`chrome.storage` 가 이것을 이긴다.** 팝업에서 넣은 값이 항상 우선이고
//   이것은 아무것도 넣지 않았을 때의 출발점이다.
globalThis.ST ??= {};
globalThis.ST.CONFIG ??= { endpoint: "", token: "" };
