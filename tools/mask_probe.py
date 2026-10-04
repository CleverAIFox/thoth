"""자리표시 치환의 대가를 잰다 — **워커를 안 고치고**.

    python3 tools/mask_probe.py                    # 네 갈래를 다 돌린다
    python3 tools/mask_probe.py --arms none,term_u # 고른 갈래만
    python3 tools/mask_probe.py --runs 3           # 판을 늘려 분산을 본다

★ **재는 것과 고치는 것을 섞지 않는다**(DECISIONS §146 · §148). 치환을 엔진에 넣고 재면, 나온
  수가 「치환의 값」 인지 「내가 넣은 코드의 값」 인지 가를 수 없다. 여기서는 **바깥에서
  이미 치환된 글**을 워커에 던지고 돌아온 것을 본다 — 운영 경로는 손대지 않는다.

★ **무엇을 재는가.** §143 이 치환의 대가 ①(조사)을 닫았고, ②(마커 소실)는 **숫자가
  없다.** 숫자 없이 바꾸면 **지금 0 인 `keep` 위반을 마커 위반으로 옮기는 것**이다.

★ **갈래를 여럿 둔다. 마커 취약성은 마커마다 다르다** — §1 이 배치 마커 `§` 에서
  이미 겪었다. 한 모양만 재고 「치환은 된다/안 된다」 로 적으면 **모양의 값을 방식의
  값으로 적는 것**이다.

      none    치환하지 않는다 (대조군 — 지금 경로)
      num_a   [[1]]              ASCII 숫자
      num_u   ⟦1⟧                유니코드 숫자
      term_u  ⟦Data Catalog⟧     **뜻을 들고 간다** — 모델이 그 자리의 의미를 본다

★ **치환은 프롬프트도 바꾼다.** 원문에서 용어가 사라지므로 워커의 용어집 판정이
  달라진다 — keep 목록에서 빠지고, 맞은 용어 수가 줄어 도메인 자체가 안 붙을 수도
  있다. **그것이 치환의 진짜 조건이므로 숨기지 않고 함께 센다**(`용어수`).
"""
import argparse
import importlib.util
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "worker"))
from app import glossary

_spec = importlib.util.spec_from_file_location("bench", ROOT / "tools" / "bench_golden.py")
bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bench)

# 갈래 — (여는 꼴, 닫는 꼴, 속에 무엇을 넣나)
ARMS: dict[str, tuple[str, str, str]] = {
    "none":   ("", "", ""),
    "num_a":  ("[[", "]]", "번호"),
    "num_u":  ("⟦", "⟧", "번호"),
    "term_u": ("⟦", "⟧", "용어"),
}


def mask(text: str, arm: str) -> tuple[str, dict[str, str]]:
    """원문의 항등 용어를 자리표시로 바꾼다. (바뀐 글, 자리표시→원래말)."""
    열고, 닫고, 속 = ARMS[arm]
    if not 열고:
        return text, {}
    _, terms = glossary.match([text])
    keep = [정규 for en, 정규 in terms.items() if glossary.is_keep(en, 정규)]
    # ★ **긴 것부터 바꾼다.** 짧은 용어가 긴 용어 안에 들어 있으면 먼저 먹고, 긴
    #   용어의 뒤쪽이 **맨몸으로 번역에 노출된다.**
    #
    # ★ **이 줄은 오늘 중복이다** — `glossary.match` 가 이미 열쇠 길이 내림차순으로
    #   돌려주고, 항등 용어는 `en == 정규` 라 두 정렬이 같은 차례를 낸다. 그래서
    #   **돌연변이로 죽일 수 없다**(지우고 시험을 돌려도 통과한다).
    # ★ **그래도 둔다. 이것은 관문이 아니라 독립성이다** — 없으면 `mask` 가
    #   `match` 의 **내부 정렬 순서**에 말없이 기대게 되고, 그 기대를 적어 둔 데가
    #   아무 데도 없게 된다(§145 가 「두 데가 같은 것을 다르게 적으면 갈린다」 로
    #   겪은 자리). 죽은 가드를 지우는 것과 다른 물음이다.
    keep.sort(key=len, reverse=True)
    표: dict[str, str] = {}
    for i, 정규 in enumerate(keep, 1):
        if 정규 not in text:
            continue
        자리 = f"{열고}{i if 속 == '번호' else 정규}{닫고}"
        text = text.replace(정규, 자리)
        표[자리] = 정규
    return text, 표


def unmask(ko: str, 표: dict[str, str]) -> tuple[str, list[str]]:
    """자리표시를 원래말로 되돌린다. 안 돌아온 자리표시를 함께 센다.

    ★ **「안 돌아왔다」 는 글자 그대로 없는 것만 센다.** 모델이 뭉갠 꼴(`[[ 1 ]]`,
      `⟦1⟧.`)을 너그럽게 받아 주면 **소실률이 낮게 나온다** — 그것은 치환 편을
      들어 주는 자다. 복원이 결정적이려면 **글자까지 같아야** 한다.
    """
    잃음: list[str] = []
    for 자리, 정규 in 표.items():
        if 자리 in ko:
            ko = ko.replace(자리, 정규)
        else:
            잃음.append(자리)
    return ko, 잃음


def 유닛들() -> list[dict]:
    """항등 용어가 실제로 들어 있는 유닛만. 없는 유닛에서는 치환이 무위다."""
    out = []
    for 이름 in ("cases.json", "terms.json"):
        p = ROOT / "worker" / "tests" / "golden" / 이름
        for q in json.loads(p.read_text(encoding="utf-8")):
            for u in q.get("units", []):
                _, terms = glossary.match([u["text"]])
                if any(glossary.is_keep(en, ko) and ko in u["text"]
                       for en, ko in terms.items()):
                    out.append(u)
    return out


def 한판(arm: str, units: list[dict], url: str, book: dict[str, str]) -> dict:
    셈 = {"유닛": len(units), "마커": 0, "소실": 0, "용어수": 0, "용어집": 0,
          "keep": 0, "term": 0, "drop": 0, "조사": 0, "길이비": 0.0}
    보기: list[str] = []
    for u in units:
        보낼것, 표 = mask(u["text"], arm)
        이름, terms = glossary.match([보낼것])
        셈["용어수"] += len(terms)
        # ★ **치환은 용어집 자체를 떨어뜨릴 수 있다.** 판정이 **원문 글자**로
        #   맞히는데 치환이 그 증거를 지우기 때문이다. 그러면 치환한 용어만
        #   잃는 것이 아니라 **그 문장의 모든 용어가 지침 없이 번역된다.**
        셈["용어집"] += 1 if 이름 else 0
        셈["마커"] += len(표)
        ko = bench.translate(url, [보낼것], 120)[0][0]
        ko, 잃음 = unmask(ko, 표)
        셈["소실"] += len(잃음)
        if 잃음 and len(보기) < 5:
            보기.append(f"[{u['id']}] 잃은 자리표시 {잃음} → {ko[:70]}")
        for x in bench.check(u, ko, book):
            갈래 = x.split(":")[0]
            if 갈래 in 셈:
                셈[갈래] += 1
        셈["길이비"] += len(ko) / max(len(u["text"]), 1)
    셈["길이비"] = round(셈["길이비"] / max(len(units), 1), 3)
    셈["보기"] = 보기
    return 셈


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--url", default=os.environ.get("WORKER_URL", "http://127.0.0.1:8000") + "/translate")
    a = ap.parse_args()

    units = 유닛들()
    book = bench.load_terms()
    print(f"항등 용어가 든 유닛 {len(units)}개 · 판 {a.runs} "
          f"· 갈래마다 마커 {len(units) * a.runs}개 남짓")
    if len(units) * a.runs < 40:
        print("  ※ 표본이 작다 — --runs 를 올려야 소실률이 말을 한다")
    print()
    머리 = (f"{'갈래':<8}{'마커':>5}{'소실':>5}{'소실률':>8}{'용어집':>8}"
          f"{'keep':>6}{'term':>6}{'drop':>6}{'조사':>6}{'용어수':>7}{'길이비':>7}")
    print(머리)
    print("-" * 78)
    for arm in a.arms.split(","):
        if arm not in ARMS:
            print(f"모르는 갈래 : {arm}", file=sys.stderr)
            return 2
        합 = None
        보기: list[str] = []
        for _ in range(a.runs):
            r = 한판(arm, units, a.url, book)
            보기 += r.pop("보기")
            합 = r if 합 is None else {k: 합[k] + r[k] for k in r}
        율 = f"{합['소실'] / 합['마커'] * 100:.1f}%" if 합["마커"] else "—"
        붙음 = f"{합['용어집']}/{len(units) * a.runs}"
        print(f"{arm:<8}{합['마커']:>5}{합['소실']:>5}{율:>8}{붙음:>8}{합['keep']:>6}"
              f"{합['term']:>6}{합['drop']:>6}{합['조사']:>6}{합['용어수']:>7}"
              f"{합['길이비'] / a.runs:>7.3f}")
        for x in 보기[:5]:
            print(f"    {x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
