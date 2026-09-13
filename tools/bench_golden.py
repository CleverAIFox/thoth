"""골든셋을 임의 엔진에 돌려 불변식 위반을 센다.

★ 번역의 '정확도' 를 재지 않는다. 측정할 수 없는 목표는 세우지 않는다
  (MASTER §8). 여기서 재는 것은 검증 가능한 불변식뿐이다.

★ 워커를 HTTP 로 때린다. 엔진을 import 하지 않는 이유는 캐시 · 가드 · 용어집을
  포함한 서빙 경로 전체가 측정 대상이기 때문이다. TestClient 로는 그 경로가
  검증되지 않는다(DECISIONS §10 의 연장).

  bash tools/run_worker.sh &          # 재려는 ENGINE 으로
  python3 tools/bench_golden.py
  python3 tools/bench_golden.py --json out.json    # 비교용 기록
"""
import argparse
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES = ROOT / "worker/tests/golden/cases.json"
GLOSSARY = ROOT / "worker/app/glossary"

HANGUL = re.compile(r"[가-힣]")
POLITE = re.compile(r"(니다|입니다|합니다|됩니다)[.!?)\"']*\s*$")


def load_terms() -> dict[str, str]:
    out: dict[str, str] = {}
    for f in sorted(GLOSSARY.glob("*.json")):
        out.update(json.loads(f.read_text(encoding="utf-8")))
    return out


def translate(url: str, texts: list[str], timeout: int) -> tuple[list[str], float]:
    body = json.dumps({"texts": texts, "target": "ko"}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    return data["translations"], time.monotonic() - t0


def check(unit: dict, ko: str, book: dict[str, str]) -> list[str]:
    """불변식 위반 목록. 빈 리스트가 통과다."""
    src, bad = unit["text"], []

    # 1. 고유명사 · API명은 영어로 남는다 (MASTER §7-2 규칙 1)
    for tok in unit.get("keep", []):
        if tok not in ko:
            bad.append(f"keep:{tok}")

    # 2. 등재 용어는 등재된 한국어 표기를 쓴다 (MASTER §8)
    for en in unit.get("terms", []):
        want = book.get(en)
        if want and want not in ko:
            bad.append(f"term:{en}→{want}")

    # 3. 물음표 보존. 원문이 물으면 번역도 물어야 한다 (PLAN §2-2 #14)
    if src.rstrip().endswith("?") and not ko.rstrip().endswith("?"):
        bad.append("물음표 소실")

    # 4. 길이 비율. 출력이 과하게 길면 환각 신호다
    ratio = len(ko) / max(len(src), 1)
    if ratio > unit["ratio_max"]:
        bad.append(f"길이 {ratio:.2f}배")

    # 5. 합니다체 (MASTER §7-2 규칙 3)
    if not POLITE.search(ko):
        bad.append("합니다체 아님")

    # 6. 번역이 되긴 했는가. echo 엔진은 여기서 전부 걸린다
    if not HANGUL.search(ko):
        bad.append("한글 없음")

    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000/translate")
    ap.add_argument("--batch", type=int, default=9,
                    help="한 요청에 실을 유닛 수. 9 는 실사용 한 문항")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--json", help="결과를 이 경로에 기록한다")
    a = ap.parse_args()

    book = load_terms()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    units = [u for q in cases for u in q["units"]]
    if not units:
        print("케이스가 없다"); return 1

    rows, elapsed, chars = [], 0.0, 0
    for i in range(0, len(units), a.batch):
        chunk = units[i:i + a.batch]
        try:
            out, dt = translate(a.url, [u["text"] for u in chunk], a.timeout)
        except urllib.error.URLError as e:
            print(f"워커에 닿지 못했다: {e}\n  bash tools/run_worker.sh & 로 띄운다")
            return 1
        elapsed += dt
        for u, ko in zip(chunk, out):
            chars += len(u["text"])
            rows.append({"id": u["id"], "kind": u["kind"], "ko": ko,
                         "bad": check(u, ko, book)})
        print(f"  {i + len(chunk):>3}/{len(units)}  {dt:6.1f}s", flush=True)

    # ---- 보고 ----
    fail = [r for r in rows if r["bad"]]
    print(f"\n{'=' * 60}\n유닛 {len(rows)} · 통과 {len(rows) - len(fail)} · 위반 {len(fail)}")
    print(f"총 {elapsed:.1f}s · {chars}자 · {chars / max(elapsed, 1e-9):.0f}자/초")

    tally: dict[str, int] = {}
    for r in fail:
        for b in r["bad"]:
            tally[b.split(":")[0]] = tally.get(b.split(":")[0], 0) + 1
    if tally:
        print("\n위반 종류")
        for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
            print(f"  {k:12} {v}")

    if fail:
        print("\n상세 (앞 8건)")
        for r in fail[:8]:
            print(f"  [{r['id']}] {', '.join(r['bad'])}")
            print(f"    {r['ko'][:90]}")

    if a.json:
        pathlib.Path(a.json).write_text(
            json.dumps({"units": len(rows), "fail": len(fail),
                        "seconds": round(elapsed, 1), "chars": chars,
                        "rows": rows}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"\n기록 → {a.json}")

    return 0 if not fail else 2


if __name__ == "__main__":
    sys.exit(main())
