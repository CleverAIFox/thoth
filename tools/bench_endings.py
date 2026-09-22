"""후처리의 어미 변환을 코퍼스로 잰다. **Kiwi 없이 돈다**(DECISIONS §107).

  python3 tools/bench_endings.py            부류별 표
  python3 tools/bench_endings.py --fails 20 틀린 줄을 20개까지
  python3 tools/bench_endings.py --gate     틀린 줄이 하나라도 있으면 1

★ **셋으로 가른다.**

  맞음    정답과 같다. 겹치는 줄(`ambiguous`)은 다른 정답 중 하나여도 맞음이다
  그대로  손대지 않았다. 해요체로 남았지만 **비문은 아니다**
  틀림    그 밖 전부. 비문을 만들었거나 합쇼체를 망가뜨렸다

  **틀림이 0 이어야 한다.** 그대로는 문체가 섞일 뿐이지만 틀림은 사용자가 비문을
  읽고, 쌍 로그의 `ko` 가 학습 목표이므로 **틀린 것을 가르치게 된다**(§97).

★ **맞음 비율은 목표가 아니다.** 확신이 없을 때 그대로 두는 후처리가 억지로 바꾸는
  후처리보다 낫다. 그래서 게이트는 틀림만 본다.

★ 후처리 전체(`postprocess`)를 부르되 영어 원문은 중립으로 준다. 물음표 뒤 자르기가
  괄호 안 문장을 지우지 않게 하기 위해서다 — 여기서 재는 것은 어미뿐이다.

  0  틀림 0 (또는 --gate 없이 돌았다)
  1  --gate 이고 틀림이 있다
  2  코퍼스가 없거나 깨졌다
"""
import argparse
import json
import os
import pathlib
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "worker"))
os.environ.setdefault("ENGINE", "echo")
os.environ.setdefault("CACHE", "memory")
from app.engine import postprocess  # noqa: E402

DIR = ROOT / "worker/tests/endings"


def load() -> list[dict]:
    rows = []
    for name, source in (("corpus.jsonl", "생성"), ("hand.jsonl", "손")):
        for line in (DIR / name).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("meta"):
                continue
            r["source"] = source
            r.setdefault("class", "손")
            r.setdefault("ambiguous", [])
            rows.append(r)
    return rows


def judge(r: dict, out: str) -> str:
    if out == r["tgt"] or out in r["ambiguous"]:
        return "맞음"
    if out == r["src"]:
        return "그대로"
    return "틀림"


def run(rows: list[dict], fix=postprocess) -> list[tuple[dict, str, str]]:
    return [(r, out, judge(r, out)) for r in rows for out in [fix("x", r["src"])]]


def table(results) -> list[str]:
    by = defaultdict(Counter)
    for r, _, v in results:
        by[(r["source"], r["class"])][v] += 1
    lines = [f"{'출처':<4} {'부류':<10} {'줄':>5} {'맞음':>5} {'그대로':>6} {'틀림':>5}"]
    total = Counter()
    for (src, cls), c in sorted(by.items()):
        n = sum(c.values())
        total.update(c)
        lines.append(f"{src:<4} {cls:<10} {n:>5} {c['맞음']:>5} {c['그대로']:>6} {c['틀림']:>5}")
    n = sum(total.values())
    lines.append(f"{'계':<4} {'':<10} {n:>5} {total['맞음']:>5} {total['그대로']:>6} {total['틀림']:>5}")
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--fails", type=int, default=0)
    a = ap.parse_args(argv)
    try:
        rows = load()
    except (OSError, ValueError) as e:
        print(f"코퍼스를 읽지 못했다 — {e}", file=sys.stderr)
        return 2
    results = run(rows)
    for line in table(results):
        print(line)
    wrong = [(r, out) for r, out, v in results if v == "틀림"]
    for r, out in wrong[: a.fails]:
        print(f"  {r['id']} [{r['class']}] {r['src']}  →  {out}   (정답 {r['tgt']})")
    return 1 if a.gate and wrong else 0


if __name__ == "__main__":
    sys.exit(main())
