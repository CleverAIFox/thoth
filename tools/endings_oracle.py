#!/usr/bin/env python3
r"""**어미 표를 두 엔진으로 좁힌다 — 만든 엔진이 아닌 쪽이 증인이다**(§196 · PLAN #66).

    . tools/lib/morph.sh
    uv run --with "$KIWI_PIN" --with "$MECAB_PIN" python3 tools/endings_oracle.py
    … --json       기계가 읽을 꼴
    … --selftest   판별식이 살아 있나

★ **순환을 피하는 것이 설계 전부다.** `worker/tests/endings/review.tsv` 의 `정답` 칸은
  **`tools/gen_endings.py` 가 Kiwi 의 `join` 으로 만든 것**이다. 그 머리말이 이미
  「순환이다. 그래서 사람이 본다」 고 적었다. 그러므로 **Kiwi 로 채점하면 아무것도 안
  잰다** — Kiwi 가 제 출력을 제가 읽는다는 것만 보인다. 그래서 **mecab-ko** 를 증인으로
  세운다 : 사전도 분절도 다른 엔진이고, **이 표를 만드는 데 관여하지 않았다.**
★ **Kiwi 도 같이 읽힌다.** 둘이 **같은 판정을 내릴 때만** 「맞다」 로 걷어 낸다.
  한쪽만 읽히거나 둘이 갈리면 **사람에게 간다** — 증인이 둘인데 말이 다르면 그것이
  바로 사람이 볼 자리다.

★ **이 자는 판정하지 않는다 — 좁힌다.** `판정` 칸은 사람의 것이고 이 도구는 **아무것도
  쓰지 않는다.** `MASTER §7-3` 이 「검수가 순환을 끊는다」 로 그 칸에 기대어 논증하므로,
  기계가 채우면 **고리가 도로 닫힌다.** 2026-10-19 실측 : 283줄 → 사람이 볼 줄 **22**(한 엔진이 못 읽은 19 · 둘이
  갈린 3 — DECISIONS §196). **이 수는 여기 말고 `doctor` 의 `== 어미 표 ==` 가 찍는다** —
  한동안 여기만 **32** 로 남아 PLAN · doctor 와 갈렸다(§91).

★ **이 눈 밖 — 어간이 같은 동사인지는 안 묻는다.** 두 엔진 다 불규칙 어간을 기본형으로
  못 돌린다(`삽니다`→`사다` · `아세요`→감탄사). 어간을 맞추려면 불규칙 교체 규칙을
  **이 저장소에 다시 적어야** 하고, 그러면 순환이 돌아온다. 묻는 것은 **체 · 시제 ·
  높임** 셋뿐이다. 어간은 사람 몫이고 그것이 PLAN #66 이다.

★ **종료 코드가 상태를 든다**(DECISIONS §21 · §127).
    0  사람이 볼 줄이 없다
    1  **사람이 볼 줄이 있다**
    2  엔진이 없거나 판별식이 죽었다. **통과로 세지 않는다**(§59)
"""
from __future__ import annotations

import collections
import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
표 = ROOT / "worker/tests/endings/review.tsv"

# ★ **목록의 정본은 어문 규범이지 이 자료가 아니다.** 통과율이 올라갈 때까지 늘리면
#   오라클이 아니라 **거울**이 된다 — 제 자료에 맞춰 깎은 자는 아무것도 안 잰다.
#
# ★ **엔진마다 자모 꼴이 다르다 — 재서 알았다**(2026-10-19). 같은 `봅니다` 를 kiwi 는
#   종성 `ᆸ니다`(U+11B8), mecab 은 초성 `ᄇ니다`(U+1107) 로 낸다. `봐요` 는 mecab 이
#   **호환 자모** `ㅏ요`(U+314F) 로 낸다. 꼴을 전부 적는 대신 **앞에 붙은 자모를
#   떼어 맞춘다** — 이것은 엔진의 표기 차이를 지우는 것이지 판정을 무르게 하는 것이
#   아니다. 카나리아가 이 구멍을 바로 물었다.
_자모 = re.compile(r"^[\u1100-\u11FF\u3130-\u318E]+")


def 표준(어미: str | None) -> str | None:
    return None if 어미 is None else _자모.sub("", 어미)


합쇼체 = frozenset({"습니다", "니다", "습니까", "니까",
                    "십시오", "시오", "읍시다", "시다", "습디다"})
해요체 = frozenset({"어요", "아요", "요", "여요", "에요", "예요", "이어요",
                    "세요", "으세요", "셔요", "으셔요",
                    "나요", "으나요", "가요", "은가요", "는가요",
                    "까요", "을까요", "래요", "네요"})
# ★ `세요`·`십시오` 류는 **그 자체가 `시`를 품는다.** 형태소로 안 떼는 엔진이 있어
#   높임이 한쪽에만 있는 것처럼 보인다 — 2026-10-19 에 그 하나로 23줄이 샜다.
높임품은어미 = frozenset({"세요", "으세요", "셔요", "으셔요", "십시오", "시오"})
높임앞말 = frozenset({"시", "으시"})
과거앞말 = frozenset({"었", "았", "였"})


def 엔진들(만든다=None):
    """`{이름: 읽는 함수}`. 하나라도 없으면 `None` — **「없다」 와 「통과」 는 다른 말이다**."""
    if 만든다 is not None:
        return 만든다()
    try:
        from kiwipiepy import Kiwi
        import mecab
    except ImportError:
        return None
    k, m = Kiwi(), mecab.MeCab()

    def kiwi로(s: str):
        t = k.tokenize(s)
        끝 = [x.form for x in t if x.tag == "EF"]
        앞 = {x.form for x in t if x.tag == "EP"}
        return (끝[-1] if 끝 else None), 앞

    def mecab으로(s: str):
        어미, 앞 = None, set()
        for tok in m.parse(s):
            펼침 = getattr(tok.feature, "expression", None)
            쪼갠것 = []
            if 펼침:
                for 조각 in 펼침.split("+"):
                    칸 = 조각.split("/")
                    if len(칸) >= 2:
                        쪼갠것.append((칸[0], 칸[1]))
            else:
                쪼갠것 = [(tok.surface, tok.feature.pos)]
            for 꼴, 품사 in 쪼갠것:
                if 품사 == "EF":
                    어미 = 꼴
                elif 품사 == "EP":
                    앞.add(꼴)
        return 어미, 앞

    return {"kiwi": kiwi로, "mecab": mecab으로}


def 체(어미: str | None, 앞말: set) -> tuple | None:
    """`(체, 높임, 과거)`. 어미를 모르면 `None` — **모르는 것은 통과가 아니다**."""
    끝 = 표준(어미)
    if 끝 is None or (끝 not in 합쇼체 and 끝 not in 해요체):
        return None
    return ("합쇼" if 끝 in 합쇼체 else "해요",
            bool(앞말 & 높임앞말) or 끝 in 높임품은어미,
            bool(앞말 & 과거앞말))


def 본다(엔진: dict, 원문: str, 정답: str) -> tuple[str, str]:
    """`(갈래, 까닭)` — `맞다` · `그대로` · `다르다` · `모른다` · `엔진이갈린다`."""
    if 원문.strip() == 정답.strip():
        return "그대로", ""
    읽은것 = {이름: (체(*읽기(원문)), 체(*읽기(정답)))
              for 이름, 읽기 in 엔진.items()}
    못읽은 = [이름 for 이름, (a, b) in 읽은것.items() if a is None or b is None]
    if 못읽은:
        return "모른다", f"{' · '.join(못읽은)} 가 어미를 모른다"
    쪽들 = list(읽은것.values())
    if len(set(쪽들)) != 1:
        말 = " / ".join(f"{이름}{v}" for 이름, v in 읽은것.items())
        return "엔진이갈린다", 말
    앞, 뒤 = 쪽들[0]
    if 앞[0] != "해요" or 뒤[0] != "합쇼":
        return "다르다", f"체가 {앞[0]} → {뒤[0]} 다"
    if 앞[1:] != 뒤[1:]:
        return "다르다", f"높임·시제가 갈린다 {앞[1:]} ≠ {뒤[1:]}"
    return "맞다", ""


def 줄들(path: pathlib.Path | None = None) -> list[dict]:
    with (path or 표).open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def 훑는다(엔진, rows):
    셈, 남은것 = collections.Counter(), []
    for r in rows:
        갈래, 까닭 = 본다(엔진, r["원문"], r["정답"])
        셈[갈래] += 1
        if 갈래 not in ("맞다", "그대로"):
            남은것.append((갈래, 까닭, r))
    return 셈, 남은것


# ★ **판별식이 사나**(§171 집안). `본다` 가 늘 「맞다」 면 이 검사는 **꺼진 채 초록**이다.
_카나리아 = [
    ("맞다", "그것을 봐요.", "그것을 봅니다."),
    ("그대로", "봅니다.", "봅니다."),
    ("다르다", "봐요.", "봐요!"),            # 정답이 합쇼체가 아니다
    ("다르다", "봤어요.", "봅니다."),        # 시제가 갈린다
]


def _카나리아검사(엔진) -> None:
    for 바람, 원문, 정답 in _카나리아:
        난것, 까닭 = 본다(엔진, 원문, 정답)
        if 난것 != 바람:
            print(f"    ★ 카나리아가 죽었다 — '{원문}' → '{정답}' 가 {바람} 가 아니라 "
                  f"{난것} 다 ({까닭})", file=sys.stderr)
            sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    엔진 = 엔진들()
    if 엔진 is None:
        print("  형태소 엔진이 없다 — **못 보는 것은 통과가 아니다**")
        print('      . tools/lib/morph.sh && uv run --with "$KIWI_PIN" '
              '--with "$MECAB_PIN" python3 tools/endings_oracle.py')
        return 2
    _카나리아검사(엔진)
    if "--selftest" in args:
        print(f"  프로브 살아 있다 — 엔진 {' · '.join(엔진)} 둘이 서로를 본다")
        return 0
    rows = 줄들()
    셈, 남은것 = 훑는다(엔진, rows)
    if "--json" in args:
        import json
        print(json.dumps({"셈": dict(셈),
                          "남은것": [{"갈래": g, "까닭": w, "id": r["id"]}
                                     for g, w, r in 남은것]}, ensure_ascii=False))
        return 1 if 남은것 else 0
    print(f"  어미 표 {len(rows)}줄 — 두 엔진이 같이 읽은 {셈['맞다']} · "
          f"그대로 {셈['그대로']} · **사람이 볼 줄 {len(남은것)}**")
    for 갈래, 까닭, r in 남은것:
        print(f"    · [{갈래}] {r['id']} {r['부류']} · {r['문형']}")
        print(f"        {r['원문']}  →  {r['정답']}")
        print(f"        {까닭}")
    if 남은것:
        print("  이 줄들의 `판정` 칸은 **사람이 채운다** — 이 도구는 아무것도 안 쓴다")
    return 1 if 남은것 else 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 없음(2)을 다른 코드로 끝낸다(DECISIONS §21 · §127).
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("    ✗ 도구가 깨졌다 — 위 역추적이 자리를 든다", file=sys.stderr)
        raise SystemExit(2) from None
