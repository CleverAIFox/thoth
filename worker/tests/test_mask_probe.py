"""자리표시 치환 탐침 — 재는 자가 제 편을 들지 않는가 (DECISIONS §146 · §148).

★ **이 도구는 결정의 근거가 될 수를 만든다.** 그러면 **그 수가 조용히 틀릴 자리**가
  어디인지부터 봐야 한다. 둘이다.

    1. **겹치는 용어** — 짧은 용어가 긴 용어 안에 있으면 먼저 먹어 긴 쪽이 깨진다.
    2. **너그러운 소실 셈** — 뭉개진 자리표시(`[[ 1 ]]`)를 받아 주면 **소실률이 낮게
       나온다.** 그것은 치환 편을 들어 주는 자다.

★ **재는 자가 한쪽으로 기울면 그 수는 결정을 돕는 것이 아니라 결정을 가장한다.**
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("mp", ROOT / "tools" / "mask_probe.py")
mp = importlib.util.module_from_spec(_spec)
sys.modules["mp"] = mp
_spec.loader.exec_module(mp)

원문 = ("The crawler populates the Data Catalog nightly and the DynamoDB Streams "
      "records keep the bucket partitions current for the pipeline.")


# ── 치환 ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("arm", ["num_a", "num_u"])
def test_번호_갈래는_용어를_지운다(arm):
    바뀐것, 표 = mp.mask(원문, arm)
    assert len(표) == 2, 표
    for 정규 in 표.values():
        assert 정규 not in 바뀐것, f"{정규} 가 안 바뀌었다"


def test_뜻_갈래는_맨몸으로_남기지_않는다():
    # ★ `term_u` 는 **용어가 보이는 것이 설계다** — 모델이 그 자리의 의미를 봐야
    #   어순이 안 깨진다. 요구할 것은 「용어가 없다」 가 아니라 **「자리표시 밖에
    #   맨몸으로 남은 자리가 없다」** 다. 하나라도 남으면 복원이 그 자리를 못 본다.
    바뀐것, 표 = mp.mask(원문, "term_u")
    assert len(표) == 2, 표
    for 정규 in 표.values():
        맨몸 = re.findall(rf"(?<!\u27e6){re.escape(정규)}", 바뀐것)
        assert not 맨몸, f"{정규} 가 자리표시 밖에 남았다"


def test_none_은_아무것도_안_한다():
    assert mp.mask(원문, "none") == (원문, {})


def test_왕복하면_원문으로_돌아온다():
    # ★ 번역을 거치지 않으면 **글자까지 같아야** 한다. 여기서 안 맞으면
    #   뒤의 모든 수가 틀린다.
    for arm in ("num_a", "num_u", "term_u"):
        바뀐것, 표 = mp.mask(원문, arm)
        돌아온것, 잃음 = mp.unmask(바뀐것, 표)
        assert 돌아온것 == 원문, arm
        assert 잃음 == []


def test_겹치는_용어는_긴_것부터_바꾼다(monkeypatch):
    # ★ 가짜 용어집으로 **짧은 것이 긴 것 안에 든** 경우를 만든다.
    #
    # ★ **처음 시험은 안 물었다.** 「긴 용어가 글에 안 남았나」 를 물었는데, 짧은 것을
    #   먼저 바꿔도 긴 용어의 **앞부분만** 먹히므로 그 물음에는 통과한다 — 그리고
    #   왕복까지 맞는다. 깨지는 것은 **`Registry` 가 맨몸으로 번역에 노출되는 것**이다.
    #   물어야 할 것은 **「자리표시 수가 원문의 항등 용어 수와 같나」** 다.
    import app.glossary as g
    monkeypatch.setattr(g, "_books", {"t": {
        "data catalog": "Data Catalog",
        "data catalog registry": "Data Catalog Registry"}})
    src = "The Data Catalog Registry and the Data Catalog differ in the pipeline bucket partitions."
    바뀐것, 표 = mp.mask(src, "num_a")
    assert len(표) == 2, f"항등 용어 둘인데 자리표시가 {len(표)}개다 — 겹쳐서 먹혔다 {표}"
    assert "Registry" not in 바뀐것, "긴 용어의 뒤쪽이 맨몸으로 남았다"
    assert mp.unmask(바뀐것, 표)[0] == src


# ── 소실 셈 ─────────────────────────────────────────────────────────────

def test_글자_그대로_없는_용어는_표에_안_넣는다():
    # ★ **이것을 빠뜨리면 소실률이 부풀려진다** — 치환에 불리한 쪽으로 기운다.
    #   `_hits` 는 소문자로 맞히므로 원문이 `data catalog` 여도 용어가 잡힌다. 그때
    #   정규 표기 `Data Catalog` 는 글에 없으니 치환이 무위인데, 표에 넣으면
    #   **번역에 한 번도 간 적 없는 자리표시를 「잃었다」 로 센다.**
    src = ("The crawler populates the data catalog nightly and the bucket "
           "partitions stay current for the pipeline stream records.")
    바뀐것, 표 = mp.mask(src, "num_a")
    assert 표 == {}, f"글에 없는 용어를 표에 넣었다 {표}"
    assert 바뀐것 == src


def test_안_돌아온_자리표시를_센다():
    _, 표 = mp.mask(원문, "num_a")
    ko, 잃음 = mp.unmask("크롤러가 매일 밤 채웁니다.", 표)
    assert len(잃음) == len(표), "하나도 안 돌아왔는데 소실이 0 이다"


def test_뭉개진_꼴을_받아_주지_않는다():
    # ★ **이것이 가장 중요한 자리다.** `[[ 1 ]]` 를 「돌아온 것」 으로 세면
    #   소실률이 낮게 나오고, 그 수가 치환을 채택하는 근거가 된다.
    #
    # ★ **처음 시험은 표에 자리표시 둘을 두고 「소실이 하나라도 있나」 를 물었다.**
    #   그러면 **다른 자리표시의 소실이 이 자리의 성공을 가려 준다.** 표에 하나만 둔다.
    표 = {"[[1]]": "Data Catalog"}
    for 뭉갠것 in ("[[ 1 ]]", "[ [1] ]", "[[1]].", "〔〔1〕〕"):
        ko, 잃음 = mp.unmask(f"크롤러가 {뭉갠것} 채웁니다.", 표)
        if 뭉갠것 == "[[1]].":
            continue                 # 마침표가 붙은 것은 글자로는 들어 있다 — 소실이 아니다
        assert 잃음 == ["[[1]]"], f"{뭉갠것!r} 를 성공으로 셌다 — 소실률이 낮게 나온다"
        assert "Data Catalog" not in ko


def test_글자까지_같으면_성공이다():
    # ★ 음성 대조 — 위 시험이 **언제나 참**이면 아무것도 안 재는 것이다.
    표 = {"[[1]]": "Data Catalog"}
    ko, 잃음 = mp.unmask("크롤러가 [[1]] 를 채웁니다.", 표)
    assert 잃음 == []
    assert "Data Catalog" in ko


def test_돌아온_것은_안_센다():
    # ★ 음성 대조 — 전부 소실이라고 세는 자는 아무것도 안 재는 것이다.
    바뀐것, 표 = mp.mask(원문, "num_u")
    ko, 잃음 = mp.unmask(바뀐것, 표)
    assert 잃음 == []
    for 정규 in 표.values():
        assert 정규 in ko


# ── 갈래 ────────────────────────────────────────────────────────────────

def test_갈래마다_자리표시_꼴이_다르다():
    꼴 = {}
    for arm in ("num_a", "num_u", "term_u"):
        _, 표 = mp.mask(원문, arm)
        꼴[arm] = sorted(표)
    assert len({tuple(v) for v in 꼴.values()}) == 3, f"갈래가 같은 꼴을 낸다 {꼴}"


def test_뜻을_들고_가는_갈래는_용어를_품는다():
    _, 표 = mp.mask(원문, "term_u")
    assert any("Data Catalog" in 자리 for 자리 in 표), 표


def test_번호_갈래는_용어를_안_품는다():
    for arm in ("num_a", "num_u"):
        _, 표 = mp.mask(원문, arm)
        assert not any("Catalog" in 자리 for 자리 in 표), arm


# ── 대상 유닛 ───────────────────────────────────────────────────────────

def test_항등_용어가_든_유닛만_고른다():
    import app.glossary as g
    units = mp.유닛들()
    assert units, "고른 유닛이 없다 — 탐침이 아무것도 못 잰다"
    for u in units:
        _, terms = g.match([u["text"]])
        assert any(g.is_keep(en, ko) and ko in u["text"] for en, ko in terms.items()), u["id"]


# ── 치환이 용어집을 떨어뜨리는가 ────────────────────────────────────────

def test_불투명_자리표시는_용어집을_떨어뜨린다():
    # ★ **이것이 치환의 가장 큰 대가인데 「어순이 어색해진다」 로만 적혀 있었다.**
    #   용어집 판정은 **원문 글자**로 맞힌다 — 치환이 그 증거를 지우면 `MIN_HITS`
    #   아래로 떨어져 **그 문장의 모든 용어가 지침 없이 번역된다.**
    import app.glossary as g
    units = mp.유닛들()
    붙음 = {}
    for arm in mp.ARMS:
        붙음[arm] = sum(1 for u in units if g.match([mp.mask(u["text"], arm)[0]])[0])
    assert 붙음["none"] == len(units), 붙음
    assert 붙음["num_a"] < len(units) / 2, f"불투명 치환이 용어집을 안 떨어뜨린다 {붙음}"
    assert 붙음["num_u"] < len(units) / 2, 붙음


def test_뜻을_들고_가면_용어집이_그대로_붙는다():
    # ★ **이것이 §143 이 연 길이다.** 자리표시가 용어를 품으면 판정이 그대로 맞고,
    #   조사는 §143 이 결정적으로 고치므로 **치환의 대가 둘이 다 닫힌다.**
    #   남은 물음은 **마커가 살아 돌아오나** 하나다 — 그것은 모델을 불러야 안다.
    import app.glossary as g
    units = mp.유닛들()
    붙음 = sum(1 for u in units if g.match([mp.mask(u["text"], "term_u")[0]])[0])
    assert 붙음 == len(units), f"뜻 갈래에서도 용어집이 떨어졌다 {붙음}/{len(units)}"
