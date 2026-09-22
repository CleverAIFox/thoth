"""후처리 평가 코퍼스를 만든다. **자를 먼저 댄다**(DECISIONS §93 · §107).

  uv run --with kiwipiepy python tools/gen_endings.py

  worker/tests/endings/lexicon.json   용언 목록 — 부류마다 어간이 다르게 활용한다
        → worker/tests/endings/corpus.jsonl   (해요체 원문, 합쇼체 정답) 쌍
        → worker/tests/endings/review.tsv     사람이 검수할 표본

★ **활용은 Kiwi 가 한다.** 어간과 어미를 형태소로 주면 `join` 이 음운 규칙을 적용해
  한 어절로 붙인다 — `돕 + 어요 → 도와요`, `돕 + 습니다 → 돕습니다`. 불규칙 부류를
  손으로 적으면 §106 처럼 부류를 막지 못하고 사례만 막는다.

★ **순환이다. 그래서 사람이 본다.** 같은 분석기로 정답을 만들고 같은 분석기로 후처리
  하면 분석기가 틀린 자리는 코퍼스도 틀린다. `review.tsv` 는 부류 × 문형마다 표본을
  뽑아 사람이 판정하는 자리이고, `hand.jsonl` 은 Kiwi 를 거치지 않고 손으로 쓴 문장이다.
  둘이 순환을 끊는다.

★ **어절 단위로 붙인다.** `join` 에 문장 전체를 주면 `사용해야 해요` 가
  `사용해야해요` 가 된다 — 어미와 보조 용언 사이의 띄어쓰기를 버린다.

★ **겉모양이 같은데 정답이 다른 줄을 표시한다**(`ambiguous`). `걸어요` 는 `걷다` 의
  것이기도 `걸다` 의 것이기도 하다. 문맥 없이는 가를 수 없으므로 그 줄에서 후처리가
  할 수 있는 옳은 일은 **그대로 두거나 둘 중 하나를 고르는 것**이다.

★ **Kiwi 는 워커 의존성이 아니다**(아직). 이 도구와 검수만 쓴다. 코퍼스는 저장소에
  들어가므로 검사와 벤치는 Kiwi 없이 돈다.
"""
import hashlib
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIR = ROOT / "worker/tests/endings"
LEXICON = DIR / "lexicon.json"
CORPUS = DIR / "corpus.jsonl"
REVIEW = DIR / "review.tsv"

GENERATOR = 1

# (문형, 원문 어미, 문장부호, 원문 형태소, 정답 형태소, 붙는 품사)
# ★ **이 표가 후처리 규칙표의 거울이다.** 후처리가 무엇을 무엇으로 바꿔야 하는지를
#   여기서 정하고, 후처리 쪽 규칙표는 이것을 통과해야 한다.
# ★ 합쇼체 원문(`습니다` · `습니까` · `십시오`)은 **바뀌면 안 되는 줄**이다. 후처리가
#   손대지 말아야 할 자리를 재지 않으면 과잉 교정을 못 본다.
BOTH, VERB, ADJ = "VA", "V", "A"
PATTERNS = [
    ("평서", "어요", ".", [("어요", "EF")], [("습니다", "EF")], BOTH),
    ("평서-과거", "었어요", ".", [("었", "EP"), ("어요", "EF")], [("었", "EP"), ("습니다", "EF")], BOTH),
    ("평서-추측", "겠어요", ".", [("겠", "EP"), ("어요", "EF")], [("겠", "EP"), ("습니다", "EF")], BOTH),
    ("의문", "어요", "?", [("어요", "EF")], [("습니까", "EF")], BOTH),
    ("의문", "나요", "?", [("나요", "EF")], [("습니까", "EF")], BOTH),
    ("의문", "ㄹ까요", "?", [("ᆯ까요", "EF")], [("습니까", "EF")], BOTH),
    ("의문", "는가요", "?", [("는가요", "EF")], [("습니까", "EF")], VERB),
    ("의문", "ㄴ가요", "?", [("ᆫ가요", "EF")], [("습니까", "EF")], ADJ),
    ("의문-과거", "었나요", "?", [("었", "EP"), ("나요", "EF")], [("었", "EP"), ("습니까", "EF")], BOTH),
    # ★ **명령은 명령으로 간다**(DECISIONS §107). 옛 후처리는 `하십시오 → 합니다` 로
    #   명령을 평서로 바꿨다. `하십시오` 는 이미 합쇼체다.
    ("명령", "세요", ".", [("세요", "EF")], [("십시오", "EF")], VERB),
    ("합쇼-평서", "습니다", ".", [("습니다", "EF")], [("습니다", "EF")], BOTH),
    ("합쇼-의문", "습니까", "?", [("습니까", "EF")], [("습니까", "EF")], BOTH),
    ("합쇼-명령", "십시오", ".", [("십시오", "EF")], [("십시오", "EF")], VERB),
]

# 이다는 해요체가 `이에요 · 예요` 인데 Kiwi 의 join 은 `이어요` 를 낸다. 원문은 손으로
# 붙이고 정답만 join 한다.
COPULA = [
    ("평서", "이에요", ".", None, [("ᆸ니다", "EF")]),
    ("의문", "이에요", "?", None, [("ᆸ니까", "EF")]),
    ("의문", "인가요", "?", [("ᆫ가요", "EF")], [("ᆸ니까", "EF")]),
    ("의문", "일까요", "?", [("ᆯ까요", "EF")], [("ᆸ니까", "EF")]),
    ("합쇼-평서", "입니다", ".", [("ᆸ니다", "EF")], [("ᆸ니다", "EF")]),
]


def _jong(ch: str) -> int:
    return (ord(ch) - 0xAC00) % 28 if "가" <= ch <= "힣" else -1


def build(kiwi) -> list[dict]:
    lex = json.loads(LEXICON.read_text(encoding="utf-8"))
    join = lambda morphs: kiwi.join([tuple(m) for m in morphs])  # noqa: E731
    rows = []

    def sentence(pre, words, tail, mark):
        # 앞 어절은 그대로, 끝 어절에만 어미를 붙인다. 어절 사이는 공백 하나다.
        head = [join(w) for w in words[:-1]]
        return pre + " ".join(head + [join(words[-1] + tail)]) + mark

    for pr in lex["predicates"]:
        pos = pr["pos"]
        ask = pr.get("ask", "는가요" if pos == "V" else "ㄴ가요")
        for ptype, ending, mark, src, tgt, allow in PATTERNS:
            if pos not in allow and ending not in ("는가요", "ㄴ가요"):
                continue
            # ★ `-는가요` 와 `-(으)ㄴ가요` 는 품사가 아니라 낱말이 고른다. 있다 · 없다는
            #   형용사처럼 보여도 `있는가요` 다 — 품사로 가르면 `있은가요` 가 나왔다.
            if ending in ("는가요", "ㄴ가요") and ending != ask:
                continue
            if ptype == "명령" and pr.get("imperative") is False:
                continue          # `사용해야 하십시오` 는 명령이 아니다
            if ending in pr.get("skip", []):
                continue          # 정답이 확실하지 않은 꼴은 정답 세트에 넣지 않는다
            for pre in ("", pr.get("prefix", "그것을 " if pos == "V" else "그것이 ")):
                rows.append({
                    "src": sentence(pre, pr["words"], src, mark),
                    "tgt": sentence(pre, pr["words"], tgt, mark),
                    "base": pr["base"], "class": pr["class"], "type": ptype, "ending": ending,
                })

    for c in lex["copula"]:
        noun = (c["noun"], c["tag"])
        vowel = _jong(c["noun"][-1]) == 0
        for ptype, ending, mark, src, tgt in COPULA:
            if src is None:
                surface = c["noun"] + ("예요" if vowel else "이에요") + mark
            else:
                surface = join([noun, ("이", "VCP")] + src) + mark
            for pre in ("", "가장 알맞은 것은 "):
                rows.append({
                    "src": pre + surface,
                    "tgt": pre + join([noun, ("이", "VCP")] + tgt) + mark,
                    "base": c["noun"] + "이다", "class": "이다", "type": ptype,
                    "ending": ("예요" if vowel else "이에요") if src is None else ending,
                })

    # 겉모양이 같은데 정답이 다르면 문맥 없이 가를 수 없다.
    by_src: dict[str, set[str]] = {}
    for r in rows:
        by_src.setdefault(r["src"], set()).add(r["tgt"])
    seen, out = set(), []
    for r in rows:
        key = (r["src"], r["tgt"])
        if key in seen:
            continue                     # 같은 쌍이 두 부류에서 나오면 하나만 둔다
        seen.add(key)
        alts = sorted(by_src[r["src"]] - {r["tgt"]})
        r["ambiguous"] = alts
        out.append(r)
    for i, r in enumerate(out):
        r["id"] = f"e{i:04d}"
    return out


def meta(kiwi_version: str) -> dict:
    return {
        "meta": True,
        "generator": GENERATOR,
        "lexicon_sha": hashlib.sha256(LEXICON.read_bytes()).hexdigest()[:16],
        "kiwi": kiwi_version,
    }


def review_sample(rows: list[dict], per: int = 2, seed: int = 107) -> list[dict]:
    """부류 × 문형마다 몇 줄. **무작위지만 씨앗이 고정이다** — 다시 만들어도 같은
    줄을 보게 한다. 검수한 줄이 바뀌면 검수가 날아간다."""
    rng = random.Random(seed)
    buckets: dict[tuple, list] = {}
    for r in rows:
        buckets.setdefault((r["class"], r["type"]), []).append(r)
    out = []
    for key in sorted(buckets):
        b = buckets[key]
        out += rng.sample(b, min(per, len(b)))
    return out


def main() -> int:
    try:
        from kiwipiepy import Kiwi
        import kiwipiepy
    except ImportError:
        print("kiwipiepy 가 없다 — uv run --with kiwipiepy python tools/gen_endings.py", file=sys.stderr)
        return 2
    rows = build(Kiwi())
    lines = [json.dumps(meta(kiwipiepy.__version__), ensure_ascii=False)]
    lines += [json.dumps(r, ensure_ascii=False) for r in rows]
    CORPUS.write_text("\n".join(lines) + "\n", encoding="utf-8")

    sample = review_sample(rows)
    # ★ **손으로 쓴 줄도 사람이 본다.** 그것을 쓴 것도 사람이 아니라 모델이다.
    hand = [json.loads(line) for line in (DIR / "hand.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    tsv = ["id\t부류\t문형\t원문\t정답\t판정\t메모"]
    # ★ 빈 칸을 두지 않는다. 줄 끝 탭이 공백 오류로 잡히고, 빈 칸은 "안 봤다" 와
    #   "봤는데 적지 않았다" 를 가르지 못한다. `미정` 을 `O` · `X` 로 바꾼다.
    tsv += [f"{r['id']}\t{r['class']}\t{r['type']}\t{r['src']}\t{r['tgt']}\t미정\t-" for r in sample]
    tsv += [f"{r['id']}\t손\t{r['note']}\t{r['src']}\t{r['tgt']}\t미정\t-" for r in hand]
    REVIEW.write_text("\n".join(tsv) + "\n", encoding="utf-8")

    amb = sum(1 for r in rows if r["ambiguous"])
    print(f"코퍼스 {len(rows)} 줄 · 겹침 {amb} · 검수 {len(sample)} + 손 {len(hand)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
