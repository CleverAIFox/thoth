"""항등 용어 되돌리기 — `glossary.restore` 와 그 족 가드.

★ **지시로 안 되는 자리가 있다**(DECISIONS §139). `Data Catalog` 는 keep 목록에
  실리고 지시문이 「보통명사처럼 보여도 절대 한국어로 옮기지 마라」 까지 적는데도
  긴 배치에서 깨진다. 뒤에서 되돌린다 — **모델에게 아무것도 묻지 않는다**(§66).

★ **고치는 쪽이 반대 방향으로 틀릴 수 있다**(§138 의 `drop` 축과 같은 물음).
  되돌리기가 넓으면 **멀쩡한 보통명사까지 영어로 만든다.** 무는 시험과 **안 무는
  시험**을 같은 수만큼 둔다.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import glossary

원문 = ("The crawler populates the Data Catalog nightly so that the bucket "
      "partitions stay current for the stream.")


# ── 무는가 ──────────────────────────────────────────────────────────────

def test_번역돼_나오면_되돌린다():
    ko, 고친것 = glossary.restore(원문, "크롤러가 매일 밤 데이터 카탈로그를 채웁니다.")
    assert "Data Catalog" in ko
    assert "데이터 카탈로그" not in ko
    assert 고친것 == ["Data Catalog"]


def test_조사가_붙어_있어도_되돌린다():
    # ★ 조사는 명사 뒤에 붙으므로 명사만 바꾸면 그대로 산다.
    for 조사 in ("를", "에", "의", "는", "와"):
        ko, _ = glossary.restore(원문, f"크롤러가 데이터 카탈로그{조사} 채웁니다.")
        assert f"Data Catalog{조사}" in ko


def test_띄어쓰기_없는_꼴도_되돌린다():
    ko, 고친것 = glossary.restore(원문, "크롤러가 데이터카탈로그를 채웁니다.")
    assert "Data Catalog를" in ko
    assert 고친것 == ["Data Catalog"]


def test_반쯤_번역된_꼴도_되돌린다():
    ko, _ = glossary.restore(원문, "크롤러가 Data 카탈로그를 채웁니다.")
    assert "Data Catalog를" in ko


def test_한_문장에_두_꼴이_섞이면_둘_다_되돌린다():
    # ★ **돌연변이 시험이 찾은 자리다.** 「이미 지켜졌으면 건너뛴다」 가 있으면
    #   이 문장을 통째로 지나간다 — 한 꼴이 맞았다고 다른 꼴이 맞은 것이 아니다.
    ko, 고친것 = glossary.restore(
        원문, "크롤러가 Data Catalog를 채우고, 데이터 카탈로그는 매일 갱신됩니다.")
    assert "데이터 카탈로그" not in ko
    assert ko.count("Data Catalog") == 2
    assert 고친것 == ["Data Catalog"]


# ── 안 무는가 (음성 대조) ────────────────────────────────────────────────

def test_이미_지켜졌으면_손대지_않는다():
    before = "크롤러가 매일 밤 Data Catalog를 채웁니다."
    ko, 고친것 = glossary.restore(원문, before)
    assert ko == before
    assert 고친것 == []


def test_맨_카탈로그는_건드리지_않는다():
    # ★ **이것이 가장 중요한 음성 대조다.** 원문의 소문자 `catalog` 를 올바르게
    #   옮긴 자리를 되돌리면 **고친 것이 아니라 망가뜨린 것**이다.
    before = "크롤러가 매일 밤 카탈로그를 채웁니다."
    ko, 고친것 = glossary.restore(원문, before)
    assert ko == before
    assert 고친것 == []


def test_원문이_소문자면_넣지_않는다():
    # ★ **돌연변이 시험이 찾은 둘째 자리다.** `_hits` 는 소문자 `data catalog` 도
    #   잡는다 — 그때 「데이터 카탈로그」 는 **맞는 번역**이고, 되돌리면 보통명사를
    #   고유명사로 둔갑시킨다. 정규 표기가 원문에 **그 꼴 그대로** 있을 때만 건다.
    src = "The crawler populates the data catalog nightly for the bucket partitions."
    before = "크롤러가 매일 밤 버킷 파티션의 데이터 카탈로그를 채웁니다."
    ko, 고친것 = glossary.restore(src, before)
    assert ko == before, "소문자 보통명사를 고유명사로 되돌렸다"
    assert 고친것 == []


def test_원문에_없으면_넣지_않는다():
    # ★ 없는 것을 넣으면 그것이 환각이다.
    src = "The crawler populates the catalog nightly for the bucket partitions."
    before = "크롤러가 매일 밤 데이터 카탈로그를 채웁니다."
    ko, 고친것 = glossary.restore(src, before)
    assert ko == before
    assert 고친것 == []


def test_용어집이_안_붙는_문장은_그대로다():
    src = "The quick brown fox jumps over the lazy dog every single morning."
    before = "빠른 갈색 여우가 매일 아침 게으른 개를 뛰어넘습니다."
    assert glossary.restore(src, before) == (before, [])


# ── 족 가드 ─────────────────────────────────────────────────────────────

def test_지금_저장소가_조용하다():
    assert glossary.restore_fails() == []


def test_선언_안_된_항등_항목을_문다(monkeypatch):
    # ★ 묻는 것은 「이 값이 맞나」 가 아니라 **「선언 안 된 항등 항목이 있나」** 다.
    #   새 항등 항목이 들어오면 되돌리기 없이 조용히 지나가면 안 된다.
    books = dict(glossary._load())
    books["합성"] = {"step functions": "Step Functions"}
    monkeypatch.setattr(glossary, "_books", books)
    난것 = glossary.restore_fails()
    assert any("Step Functions" in x and "되돌리기 목록이 없다" in x for x in 난것)


def test_번역값과_같은_꼴을_문다(monkeypatch):
    t = dict(glossary._load_restore())
    t["Data Catalog"] = ["카탈로그"]
    monkeypatch.setattr(glossary, "_restore", t)
    assert any("번역 값과 같다" in x for x in glossary.restore_fails())


def test_너무_짧은_꼴을_문다(monkeypatch):
    t = dict(glossary._load_restore())
    t["Data Catalog"] = ["데이터"]
    monkeypatch.setattr(glossary, "_restore", t)
    assert any("미만이다" in x for x in glossary.restore_fails())


def test_죽은_선언을_문다(monkeypatch):
    t = dict(glossary._load_restore())
    t["Nonexistent Term"] = ["없는 용어 꼴"]
    monkeypatch.setattr(glossary, "_restore", t)
    assert any("항등 항목이 아니다" in x for x in glossary.restore_fails())


def test_restore_json_이_주석_열쇠를_안_싣는다():
    raw = json.loads(glossary.RESTORE_FILE.read_text(encoding="utf-8"))
    assert any(k.startswith("_") for k in raw), "주석이 사라졌다 — 까닭이 파일에 남아야 한다"
    assert not any(k.startswith("_") for k in glossary._load_restore())


def test_되돌린_것을_센다():
    # ★ **누계는 프로세스 단위다.** 재적재하지 않고 증분만 본다 — 다른 시험이
    #   먼저 돌아 수가 0 이 아닐 수 있다.
    from app import engine
    before = dict(engine.RESTORED)
    engine.postprocess(원문, "크롤러가 매일 밤 데이터 카탈로그를 채웁니다.")
    assert engine.RESTORED.get("Data Catalog", 0) == before.get("Data Catalog", 0) + 1
