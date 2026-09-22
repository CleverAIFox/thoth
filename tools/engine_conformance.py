"""번역 서버가 `ENGINE=http` 계약을 지키는지 본다(MASTER §7-4 · DECISIONS §109).

  python3 tools/engine_conformance.py http://127.0.0.1:8100
  python3 tools/engine_conformance.py URL --token T --model seshat-0.1

★ **쓰는 쪽이 계약을 정하고 쓰는 쪽이 잰다.** 자체 모델 저장소가 무엇으로 서빙
  하든(CTranslate2 · llama.cpp · vLLM) 토트가 보는 것은 이 다섯 줄이다. 이것을
  통과하면 `ENGINE=http` 로 끼워도 워커 계약이 깨지지 않는다. **번역 품질은 보지
  않는다** — 그것은 모델 저장소의 벤치가 잰다.

★ 순서는 숫자로 본다. 보기마다 다른 숫자를 넣고 번역에 그 숫자가 제자리에 남는지
  본다. 의미를 읽지 않고도 "1번 보기에 2번 번역이 붙는" 결함(DECISIONS §1)을 잡는다.

★ 의존성이 없다. 표준 라이브러리만 쓴다 — 모델 저장소가 이 파일 하나를 복사해
  CI 에서 돌릴 수 있게 한다.

  0  전부 통과
  1  하나라도 실패
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

BATCH = [f"Option {i}: Increase the shard count to {i}." for i in range(1, 10)]


def _call(url: str, path: str, token: str, payload: dict | None, timeout: float):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url.rstrip("/") + path, data=data, headers=headers)
    t = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    ms = (time.monotonic() - t) * 1000
    try:
        body = json.loads(raw)
    except ValueError:
        body = None
    return status, body, ms


def _translations(body, n):
    tr = body.get("translations") if isinstance(body, dict) else None
    if not isinstance(tr, list) or not all(isinstance(t, str) for t in tr):
        return None, "translations 가 문자열 배열이 아니다"
    if len(tr) != n:
        return None, f"길이 {len(tr)} ≠ {n}"
    if any(not t.strip() for t in tr):
        return None, "빈 번역이 있다"
    return tr, ""


def run(url: str, token: str = "", model: str = "", timeout: float = 50) -> list[tuple[str, bool, str]]:
    """(검사, 통과, 사실) 목록. 판정과 표현을 나눈다 — 테스트가 이것을 본다."""
    out = []

    try:
        st, body, _ = _call(url, "/health", token, None, 5)
    except (urllib.error.URLError, OSError) as e:
        return [("health", False, f"응답 없음 — {e}")]
    served = body.get("model") if isinstance(body, dict) else None
    if st != 200 or not isinstance(served, str) or not served:
        out.append(("health", False, f"{st} · model={served!r}"))
    elif model and served != model:
        out.append(("health", False, f"선언 {model} ≠ 서버 {served}"))
    else:
        out.append(("health", True, f"model={served}"))

    base = {"source": "en", "target": "ko", "terms": {}}

    st, body, ms = _call(url, "/translate", token, {**base, "texts": ["What is a shard?"]}, timeout)
    tr, why = _translations(body, 1) if st == 200 else (None, f"{st}")
    out.append(("single", tr is not None, why or f"{ms:.0f}ms"))

    st, body, ms = _call(url, "/translate", token, {**base, "texts": BATCH}, timeout)
    tr, why = _translations(body, len(BATCH)) if st == 200 else (None, f"{st}")
    out.append(("batch", tr is not None, why or f"{len(BATCH)}건 {ms:.0f}ms · 건당 {ms / len(BATCH):.0f}ms"))
    if tr is not None:
        moved = [i + 1 for i, t in enumerate(tr) if str(i + 1) not in t]
        out.append(("order", not moved, f"숫자가 빠진 자리 {moved}" if moved else "숫자가 제자리다"))

    # 용어집을 싣는다. 모델이 쓰지 않아도 되지만 받아서 죽으면 안 된다.
    terms = {"shard": "샤드", "Kinesis Data Streams": "Kinesis Data Streams"}
    st, body, _ = _call(url, "/translate", token,
                        {**base, "terms": terms, "texts": ["Kinesis Data Streams uses a shard."]}, timeout)
    tr, why = _translations(body, 1) if st == 200 else (None, f"{st}")
    out.append(("terms", tr is not None, why or "terms 를 받는다"))

    st, body, _ = _call(url, "/translate", token, {**base, "texts": ["Line one.\nLine two?"]}, timeout)
    tr, why = _translations(body, 1) if st == 200 else (None, f"{st}")
    out.append(("newline", tr is not None, why or "개행이 든 원문을 받는다"))

    if token:
        st, _, _ = _call(url, "/translate", "", {**base, "texts": ["x"]}, timeout)
        out.append(("auth", st in (401, 403), f"토큰 없이 {st}"))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--token", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--timeout", type=float, default=50)
    a = ap.parse_args(argv)
    results = run(a.url, a.token, a.model, a.timeout)
    for name, ok, fact in results:
        print(f"  {'OK  ' if ok else 'FAIL'} {name:<8} {fact}")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
