"""조사 교정 — `particle.fix` 와 그 족 가드.

★ **조사는 모델이 고를 일이 아니다**(DECISIONS §143). 받침 한 비트로 닫힌 규칙이
  정한다. 2026-10-03 실측에서 모델은 `Data Catalog이` 를 냈고(카탈로그는 받침이
  없다), **§139 의 되돌리기는 `DynamoDB Streams을` 을 만들었다** — 스트림(ㅁ)에
  맞춰 고른 조사를 스트림스(열림)에 그대로 붙였다.

★ **고치는 쪽이 반대로 틀릴 수 있다**(§138 의 `drop` 축 · §139 와 같은 물음).
  조사 아닌 글자를 조사로 보면 **멀쩡한 낱말을 뭉갠다** — `Lambda로그` 의 `로`,
  `Catalog이다` 의 `이`. 무는 시험과 **안 무는 시험**을 같은 수만큼 둔다.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import particle


# ── 무는가 ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("before,after", [
    # 모델이 틀린 자리 (실측)
    ("Data Catalog이 상태를 유지합니다.", "Data Catalog가 상태를 유지합니다."),
    # 되돌리기가 만든 자리 (§139 의 결함)
    ("DynamoDB Streams을 읽습니다.", "DynamoDB Streams를 읽습니다."),
    # 받침이 생기는 끝소리 — ㅁ · ㄴ · ㄹ · ㅇ
    ("IAM를 만듭니다.", "IAM을 만듭니다."),
    ("Lake Formation가 관리합니다.", "Lake Formation이 관리합니다."),
    ("CloudTrail를 켭니다.", "CloudTrail을 켭니다."),
    ("Fine-grained Access Control는", "Fine-grained Access Control은"),
    # 열리는 끝소리
    ("Athena을 씁니다.", "Athena를 씁니다."),
    ("Redshift을 씁니다.", "Redshift를 씁니다."),       # 레드시프트 — 자음 뒤 t
    # ★ 짧은 모음 뒤 무성파열음은 **받침이 된다** — 이 자리에서 내가 한 번 틀렸다.
    ("Bedrock를 호출합니다.", "Bedrock을 호출합니다."),  # 베드록 → ㄱ
])
def test_받침에_맞춰_고친다(before, after):
    assert particle.fix(before)[0] == after


def test_ㄹ_받침은_으로가_아니라_로다():
    # ★ 쌍 규칙의 단 하나의 예외다. 서울로 · CloudTrail로.
    got, 고친것 = particle.fix("CloudTrail으로 봅니다.")
    assert got == "CloudTrail로 봅니다."
    assert 고친것 == ["CloudTrail으로→로"]


def test_한_문장에_둘_있으면_둘_다_고친다():
    got, 고친것 = particle.fix("IAM를 만들고 Athena을 씁니다.")
    assert got == "IAM을 만들고 Athena를 씁니다."
    assert len(고친것) == 2


def test_꼬리_선언이_앞말이_붙어도_먹는다():
    # ★ `S3` 하나를 적으면 `Amazon S3` 가 함께 덮인다.
    assert particle.fix("Amazon S3을 씁니다.")[0] == "Amazon S3를 씁니다."


# ── 안 무는가 (음성 대조) ────────────────────────────────────────────────

@pytest.mark.parametrize("그대로", [
    "IAM으로 인증합니다.",            # ㅁ 받침 → `으로` 가 맞다
    "Athena를 씁니다.",               # 이미 맞다
    "Data Catalog가 채웁니다.",        # 이미 맞다
    "Lambda로그를 봅니다.",            # ★ `로` 가 낱말의 첫 글자다
    "Data Catalog이다.",               # ★ 서술격 `이다` — 조사가 아니다
    "Athena과정을 봅니다.",            # ★ `과` 가 낱말의 첫 글자다
    "Route 53을 씁니다.",              # ★ 규칙이 손 떼는 자리 — 추정하지 않는다
    "표를 Athena 에서 봅니다.",         # ★ 띄어쓰기가 있으면 그 말의 조사가 아니다
    "한국어만 있는 문장입니다.",
])
def test_건드리지_않는다(그대로):
    assert particle.fix(그대로) == (그대로, [])


def test_모르는_자리는_세고_넘어간다():
    before = dict(particle.UNSURE)
    got, 고친것 = particle.fix("Route 53을 씁니다.")
    assert (got, 고친것) == ("Route 53을 씁니다.", [])
    assert particle.UNSURE.get("Route 53", 0) == before.get("Route 53", 0) + 1


# ── 받침 도출 ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("en,닫혔나", [
    ("Catalog", False), ("Streams", False), ("Config", False),
    ("Inspector", False),   # ★ 끝 `r` 은 받침이 아니다 — 인스펙터
    ("Glue", False),        # ★ 묵음 e 앞이 모음이면 그 모음이 끝소리다 — 글루
    ("Route", False),       # ★ 묵음 e 가 모음을 늘인다 — 루트, 받침 아니다
    ("Lake", False),        # 레이크 — 같은 까닭
    ("Redshift", False),    # ★ 자음 뒤 파열음은 열린다 — 레드시프트
    ("Connect", False),     # 커넥트
    ("Mask", False),        # 마스크
    ("IAM", True), ("Amazon", True), ("Terraform", True),
    ("CloudTrail", True), ("Table", True),   # 테이블
    ("Zone", True),         # 존 — 묵음 e 를 떼면 n
    ("Learning", True),     # 러닝 — ㅇ
    ("Bedrock", True),      # ★ 짧은 모음 뒤 파열음은 받침이다 — 베드록(ㄱ)
    ("Budget", True),       # 버짓(ㅅ)
])
def test_끝소리로_받침이_갈린다(en, 닫혔나):
    assert bool(particle.영어받침(en)) is 닫혔나


def test_숫자로_끝나면_모른다고_한다(monkeypatch):
    # ★ `S3` 는 선언돼 있으니 선언을 빼고 규칙만 본다.
    monkeypatch.setattr(particle, "_선언", {})
    assert particle.영어받침("S3") is None
    assert particle.영어받침("Route 53") is None


def test_한글받침():
    assert particle.한글받침("그") == 0        # 카탈로그
    assert particle.한글받침("림") != 0        # 스트림
    assert particle.한글받침("A") is None


# ── 족 가드 ─────────────────────────────────────────────────────────────

def test_지금_저장소가_조용하다():
    assert particle.decl_fails() == []


def test_죽은_선언을_문다(monkeypatch):
    # ★ 묻는 것은 「이 값이 맞나」 가 아니라 **「규칙이 이미 같은 답을 내나」** 다.
    #   규칙이 좋아지면 선언은 저절로 쓸모가 없어지는데, 그것을 알려 주지 않으면
    #   선언이 쌓이면서 **규칙이 틀려도 선언이 가려 준다**(양방향 라쳇).
    monkeypatch.setattr(particle, "_선언", {"Athena": "없음"})
    assert any("죽은 선언" in x for x in particle.decl_fails())


def test_엉뚱한_받침_값을_문다(monkeypatch):
    monkeypatch.setattr(particle, "_선언", {"S3": "열림"})
    assert any("받침 값" in x for x in particle.decl_fails())


def test_선언이_살아_있는_것을_함께_본다(monkeypatch):
    # ★ 음성 대조 — 위 시험이 **언제나 참**이면 아무것도 안 재는 것이다.
    monkeypatch.setattr(particle, "_선언", {"S3": "없음"})
    assert particle.decl_fails() == []


def test_particle_json_이_주석_열쇠를_안_싣는다():
    raw = json.loads(particle.DECL_FILE.read_text(encoding="utf-8"))
    assert any(k.startswith("_") for k in raw), "주석이 사라졌다 — 까닭이 파일에 남아야 한다"
    assert not any(k.startswith("_") for k in particle._load_decl())


def test_모르는_자리를_글뭉치에서_찾아낸다():
    # ★ 이것이 선언을 **강제하는** 자리다. 규칙이 손 떼는 영어+조사가 재는 글에
    #   들어오면, 선언 없이 조용히 틀린 조사가 나간다.
    난것 = particle.unsure_in(["Route 53을 씁니다.", "Athena를 씁니다."])
    assert len(난것) == 1
    assert "Route 53" in 난것[0]


def test_선언된_것은_모르는_자리가_아니다():
    # ★ 음성 대조 — `S3` 는 숫자로 끝나지만 선언돼 있으므로 걸리지 않아야 한다.
    assert particle.unsure_in(["Amazon S3를 씁니다."]) == []


def test_조사_쌍에_중복이_없다():
    # ★ 같은 조사가 두 쌍에 들면 어느 쌍으로 갈지가 **선언 순서에 달린다.**
    알 = [a for 쌍 in particle.쌍들 for a in 쌍]
    assert len(알) == len(set(알)), "조사 알이 두 쌍에 걸쳐 있다"


# ── 엔진 배선 ────────────────────────────────────────────────────────────

def test_되돌리기가_만든_비문을_엔진이_고친다():
    # ★ **이것이 §139 가 만든 결함이다.** 되돌리기만 돌면 `Streams을` 이 남는다.
    from app import engine, glossary
    src = ("The pipeline consumes DynamoDB Streams records and writes them to "
           "the Data Catalog so that partition metadata stays current.")
    ko = "DynamoDB 스트림을 읽어 데이터 카탈로그에 적습니다."
    되돌린것만, _ = glossary.restore(src, ko)
    assert "Streams을" in 되돌린것만, "되돌리기가 조사를 안 틀렸다 — 시험의 전제가 늙었다"
    before = dict(engine.PARTICLE_FIXED)
    got = engine.postprocess(src, ko)
    assert "DynamoDB Streams를" in got
    assert "Streams을" not in got
    assert engine.PARTICLE_FIXED != before, "고친 것을 세지 않았다"
