"""Firehose 오류 객체를 가른다. `tools/pairs_check.sh` 가 부른다.

  aws s3 cp s3://.../errors/.../x - | python3 tools/pairs_errors.py
  → ctrl=1 real=0 unparsed=0

★ **jq 에 기대지 않는다.** 첫 판은 `jq` 로 갈랐고 jq 가 없는 기계에서 **셈이 비어
  `제어 메시지 0 · 쌍이 든 오류 0` 을 냈다.** 오류 객체가 분명히 하나 있었는데
  통과로 읽혔다 — 못 잰 것을 0 으로 적었다(DECISIONS §59 · §99). 파이썬은 이
  저장소의 전제이므로 여기서 가른다.

★ **못 읽은 것을 따로 센다.** 한 줄이 JSON 이 아니면 제어 메시지도 진짜 오류도
  아니다. 셋째 칸이 있어야 "0" 과 "못 잼" 이 갈린다.

★ 한 객체에 레코드가 여러 개일 수 있다. 줄바꿈이 있으면 줄로, 없으면 이어 붙은
  JSON 을 차례로 읽는다.

  0  진짜 오류도 못 읽은 것도 없다
  1  쌍이 든 오류가 있다
  3  못 읽은 것이 있다
"""
import json
import sys


def records(text: str) -> tuple[list[dict], int]:
    """(레코드, 못 읽은 조각 수)."""
    dec = json.JSONDecoder()
    out, bad, i, n = [], 0, 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        try:
            obj, end = dec.raw_decode(text, i)
        except ValueError:
            bad += 1
            nl = text.find("\n", i)
            i = n if nl == -1 else nl + 1      # 그 줄은 버리고 다음 줄부터
            continue
        if isinstance(obj, dict):
            out.append(obj)
        else:
            bad += 1
        i = end
    return out, bad


def classify(text: str) -> dict[str, int]:
    recs, bad = records(text)
    ctrl = sum(1 for r in recs if not (r.get("rawData") or "").strip())
    return {"ctrl": ctrl, "real": len(recs) - ctrl, "unparsed": bad}


def main() -> int:
    c = classify(sys.stdin.read())
    print(f"ctrl={c['ctrl']} real={c['real']} unparsed={c['unparsed']}")
    if c["real"]:
        return 1
    if c["unparsed"]:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
