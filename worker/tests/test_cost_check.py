"""`tools/cost_check.py` — **과금을 재는 자**(DECISIONS §180 · §181).

★ **이 저장소는 코드·문서·인프라·CI·CSS·주석까지 다 재면서 돈만 안 쟀다.** 그 사각이
  이미 한 번 물었다 — §177 전까지 **꺼 둔 줄 알고 Bedrock 요청이 계속 나갔고 아무도 안
  울었다.** 목표가 「무과금 개인용 확장」 이므로 **과금 의존이 곧 빚**이다.

★ **네트워크 없이 전부 먹인다.** 판정은 순수 함수라 합성으로 가른다(§132 와 같은 꼴).
  `--재다` 는 **공짜 경로만** 쓰고(§181), `--서비스별` 만 Cost Explorer 를 부르며
  **`doctor` 는 둘 다 안 들어간다** — 관문이 과금이 되면 안 된다.

★ **12자리를 글자로 적지 않는다.** `계정흠` 이 추적 파일 전체를 훑으므로 **이 시험 파일
  자신이 걸린다** — 「글을 코드로 읽는 검사는 글부터 지운다」 집안(§168)의 아홉 번째다.
  그래서 **지어서** 먹인다(`"7" * 12`).
"""
import datetime as d
import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("cost_check", ROOT / "tools/cost_check.py")
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)

오늘 = d.date(2026, 10, 10)
남계정 = "7" * 12          # ★ 글자로 안 적는다 — 위 머리말을 본다


def _선언(**덮):
    것 = {"잰날": "2026-10-10", "낡음일수": 30,
          "임계": {"월경고": 5.0, "월막음": 20.0, "유예경고일": 30},
          "유예": {},
          "덮임": {"값": 0.0},
          "크레딧": {"남은것": 139.84, "만료": "2027-08-27"},
          # ★ **잰달을 지난 달로 둔다.** 「진행 중인 달」 가지가 임계를 늘려 재므로
          #   그것을 재려는 시험이 아니면 끼어들지 않게 둔다(§182).
          "서비스": {"Amazon DynamoDB": {"월": 0.001, "잰달": "2026-09",
                                          "갈래": "과금", "자원": "세운다"}}}
    것.update(덮)
    # ★ **청구 지표를 선언에서 짓는다.** 두 곳에 손으로 적으면 `서비스` 를 갈아끼운
    #   시험마다 「지표에 뜨는데 선언에 없다」 가 따라붙는다 — 픽스처도 정본이 하나다.
    것.setdefault("청구지표", {"서비스": sorted(
        짧 for 짧, 긴 in cc.청구별칭.items() if 긴 in 것["서비스"])})
    return 것


def _표(본문):
    return [("aws_dynamodb_table", "t", 본문)]


# ── 판정 ────────────────────────────────────────────────────────────────

def test_맞는_선언은_조용하다():
    assert cc.흠(_선언(), {"Amazon DynamoDB"}, [], 오늘) == ([], [], [])


def test_선언에_없는_자원을_문다():
    """★ **선언하지 않은 자원은 과금이 나도 아무도 안 본다.**"""
    막, _, _ = cc.흠(_선언(), {"Amazon DynamoDB", "Amazon Kinesis Firehose"}, [], 오늘)
    assert len(막) == 1 and "Kinesis Firehose" in 막[0]


def test_이름을_못_붙인_자원_종류를_문다():
    """★ **모르는 것을 조용히 넘기면 새 과금 자원이 생겨도 초록이다**(§21)."""
    막, _, _ = cc.흠(_선언(), {"Amazon DynamoDB"}, ["aws_새서비스_thing"], 오늘)
    assert len(막) == 1 and "aws_새서비스_thing" in 막[0]


def test_자원_칸이_없으면_문다():
    막, _, _ = cc.흠(_선언(서비스={"X": {"월": 0.1, "갈래": "과금"}}), set(), [], 오늘)
    assert any("`자원` 칸이 없다" in x for x in 막)


def test_부르는_서비스는_terraform_에_없어도_안_문다():
    """★ **첫 판이 이 가지 없이 돌았고 Bedrock · Athena 를 「손으로 만든 자원」 으로
    물었다 — 거짓 양성 둘**(DECISIONS §180). **자원을 세우고 쓰는 것과 불러서 쓰는 것은
    다르다.** Bedrock 에는 세울 자원이 없다."""
    것 = _선언(서비스={"Amazon Bedrock": {"월": 0.1582, "잰달": "2026-09",
                                           "갈래": "과금", "자원": "부른다"}})
    assert cc.흠(것, set(), [], 오늘) == ([], [], [])


def test_세우는_서비스가_terraform_밖에서_과금되면_알린다():
    """★ 2026-10-10 에 `AWS Secrets Manager` 가 그랬다. `deploy_drift` 도 `check_infra` 도
    **IaC 안만** 보므로 **손으로 만든 과금 자원은 어느 자도 못 봤다.**"""
    것 = _선언(서비스={"AWS Secrets Manager": {"월": 0.0001, "잰달": "2026-09",
                                                "갈래": "과금", "자원": "세운다"}})
    막, 알, _ = cc.흠(것, set(), [], 오늘)
    assert 막 == []
    assert len(알) == 1 and "Secrets Manager" in 알[0]


def test_과금이_0_이면_terraform_밖이어도_안_알린다():
    """★ 음성 대조. 쓰지 않는 서비스까지 짖으면 그 경고는 곧 안 읽힌다(§133).
    2026-10-11 에 전 리전 0개를 재서 이 가지로 닫았다 — **손으로 지우지 않았다.**"""
    것 = _선언(서비스={"AWS Secrets Manager": {"월": 0.0, "잰달": "2026-09",
                                                "갈래": "과금", "자원": "세운다"}})
    assert cc.흠(것, set(), [], 오늘) == ([], [], [])


# ── 잰 달 : 「수」 와 「언제 잰 수」 는 한 몸이다 ─────────────────────────

def test_잰달이_없는_수를_문다():
    """★ 179 의 선언에는 **9월 값과 10월 값이 섞여** 있었고 어느 것이 어느 달인지
    적힌 곳이 없었다 — 읽을 수 없는 수다(DECISIONS §181)."""
    것 = _선언(서비스={"A": {"월": 0.5, "갈래": "과금", "자원": "부른다"}})
    막, _, _ = cc.흠(것, set(), [], 오늘)
    assert any("`잰달` 이 없다" in x for x in 막)


def test_0_인_수는_잰달을_안_물린다():
    """★ 음성 대조 — 0 에는 달이 없어도 읽을 수 있다. 넓으면 끄는 법부터 찾는다(§46)."""
    것 = _선언(서비스={"A": {"월": 0.0, "갈래": "과금", "자원": "부른다"}})
    assert cc.흠(것, set(), [], 오늘) == ([], [], [])


# ── 「못 쟀다」 는 셋째 묶음이다 (DECISIONS §59 · §181) ──────────────────

def test_달러를_못_잰_서비스는_못쟀다로_든다():
    """★ 179 는 `월` 이 없으면 **0 으로 읽어 합에 안 보탰다** — 안 잰 것이 **싼 것**으로
    보이는 자리였다. 2026-10-11 에 청구 지표에서 다섯 서비스가 그 꼴로 나왔다."""
    것 = _선언(서비스={"awskms2": {"월": None, "갈래": "모름", "자원": "부른다"}})
    막, 알, 못 = cc.흠(것, set(), [], 오늘)
    assert 막 == [] and 알 == []
    assert len(못) == 1 and "못 쟀다" in 못[0]


def test_갈래를_안_정한_것은_달러를_못_잰_것과_다르다():
    """★ **181 은 그 둘을 한 말로 뭉갰다**(DECISIONS §182). `AWS Cost Explorer` 가
    **$0.02 로 멀쩡히 재져 있는데** 관문이 「달러를 못 쟀다」 고 말했다 — 할 일이
    다르다. 앞은 재는 일(기계)이고 뒤는 정하는 일(사람)이다."""
    것 = _선언(서비스={"X": {"월": 0.02, "잰달": "2026-09", "갈래": "모름", "자원": "부른다"}})
    막, 알, 못 = cc.흠(것, set(), [], 오늘)
    assert 막 == [] and 알 == []
    assert len(못) == 1
    assert "갈래를 안 정했다" in 못[0] and "$0.0200" in 못[0]
    assert "달러를 못 쟀다" not in 못[0], "★ 재진 달러를 못 쟀다고 말한다"


def test_실물_선언에_모름이_없다():
    """★ **「모름」 은 사람이 할 일이 남았다는 뜻이고, 2026-10-11 에 다 정했다**(§182).
    다시 늘면 관문이 종료 코드 2 로 들고, 그때 **정하는 것이 일**이다."""
    모름 = [이름 for 이름, s in (cc.선언().get("서비스") or {}).items()
            if s.get("갈래") == "모름"]
    assert 모름 == [], f"갈래를 안 정한 서비스 : {모름}"


# ── 달이 섞인 합은 거짓이다 (DECISIONS §182) ────────────────────────────

def test_잰_달이_섞이면_막는다():
    """★ **181 은 「잰달」 로 섞임을 *보이게* 만들었고 섞임 자체는 안 고쳤다.**
    `--서비스별` 이 CE 가 **돌려준 것만** 갱신했으므로 CE 가 생략한 서비스는 **옛 달
    값을 그대로 든 채 합계에 들어갔다** — 2026-10-11 에 `Amazon Athena` 가 9월
    $0.0003 을 들고 10월 합계에 섞였고, 그 꼬리가 합 $0.0737 의 마지막 자리였다."""
    # ★ **실제 모양 그대로 먹인다** — 여럿이 새 달이고 **하나가 뒤진다.** 반반으로
    #   먹이면 「적은 쪽」 이 동점이라 무엇을 짚든 통과하고, 그러면 **짚는 일을 안 재는
    #   시험**이 된다.
    것 = _선언(서비스={
        "A": {"월": 0.05, "잰달": "2026-10", "갈래": "과금", "자원": "부른다"},
        "B": {"월": 0.02, "잰달": "2026-10", "갈래": "과금", "자원": "부른다"},
        "뒤진것": {"월": 0.0003, "잰달": "2026-09", "갈래": "과금", "자원": "부른다"}})
    막, _, _ = cc.흠(것, set(), [], 오늘)
    assert any("섞였다" in x for x in 막)
    # ★ **적은 쪽을 짚어 준다** — 열다섯 중 하나가 뒤진 것이 실제 모양이었다
    assert any("2026-09" in x and "뒤진것" in x for x in 막), 막


def test_잰_달이_하나면_조용하다():
    assert cc.흠(_선언(), {"Amazon DynamoDB"}, [], 오늘) == ([], [], [])


def test_잰_달이_없는_0_들은_안_섞는다():
    """★ 음성 대조. `월 0` 에는 달이 없어도 되므로 그것까지 섞임으로 세면 안 된다."""
    것 = _선언(서비스={
        "A": {"월": 0.05, "잰달": "2026-09", "갈래": "과금", "자원": "부른다"},
        "B": {"월": 0.0, "갈래": "항상무료", "자원": "세운다"}})
    막, _, _ = cc.흠(것, set(), [], 오늘)
    assert not any("섞였다" in x for x in 막)


# ── 진행 중인 달 ────────────────────────────────────────────────────────

def test_진행_중인_달은_달_끝까지_늘려_묻는다():
    """★ 2026-10-11 의 $0.0737 은 달의 **1/3** 이다. 그대로 월 임계와 맞대면
    **과소 평가**고, 임계가 뜻을 잃는다(§182)."""
    # 10일째에 $2 → 달 끝 $6 이라 경고선 $5 를 넘는다. 생값으로는 안 넘는다.
    것 = _선언(서비스={"A": {"월": 2.0, "잰달": "2026-10", "갈래": "과금", "자원": "부른다"}})
    막, 알, _ = cc.흠(것, set(), [], 오늘)
    assert 막 == []
    assert any("경고선" in x and "늘렸다" in x for x in 알), 알


def test_진행_중이어도_임계_아래면_조용하다():
    """★ **「진행 중이다」 는 그 달 내내 참이다.** 알림으로 내면 한 달 중 서른 날이
    `·` 한 줄이고, 그러면 `·` 를 안 읽게 된다(§46 · §133). **넘길 때만** 말한다."""
    것 = _선언(서비스={"A": {"월": 0.05, "잰달": "2026-10", "갈래": "과금", "자원": "부른다"}})
    assert cc.흠(것, set(), [], 오늘) == ([], [], [])


def test_지난_달_값은_늘리지_않는다():
    """★ 끝난 달을 늘리면 **있지도 않은 돈**으로 임계를 넘긴다."""
    것 = _선언(서비스={"A": {"월": 2.0, "잰달": "2026-09", "갈래": "과금", "자원": "부른다"}})
    assert cc.흠(것, set(), [], 오늘) == ([], [], [])


def test_잰날이_없으면_막는다():
    것 = _선언()
    del 것["잰날"]
    막, _, _ = cc.흠(것, {"Amazon DynamoDB"}, [], 오늘)
    assert any("`잰날` 이 없다" in x for x in 막)


def test_선언이_낡으면_못쟀다에_든다():
    """★ **알림이 아니라 못쟀다다.** 179 는 이것을 알림에 넣고 `main` 에서
    `any("일 됐다" in x ...)` 로 **문구를 되읽어** 종료 코드를 정했다 — 문구를 다듬으면
    조용히 0 이 되는 자리였다(§168 집안)."""
    것 = _선언(잰날="2026-08-01")
    막, 알, 못 = cc.흠(것, {"Amazon DynamoDB"}, [], 오늘)
    assert 막 == [] and 알 == []
    assert any("일 됐다" in x for x in 못)


# ── 덮임 : `EstimatedCharges` 는 달러가 아니라 신호다 ───────────────────

def test_덮임이_0_이_아니면_막는다():
    """★ **이 지표는 크레딧 적용 *후* 다**(2026-10-11 실측 : 지표 0.0 · 콘솔 $0.05).
    그래서 **0 이 아니게 되는 날 = 내 돈이 나가기 시작한 날**이고, 그날이 막는 날이다."""
    막, _, _ = cc.흠(_선언(덮임={"값": 0.01}), {"Amazon DynamoDB"}, [], 오늘)
    assert any("네 돈" in x for x in 막)


def test_덮임이_없으면_못쟀다다():
    것 = _선언()
    del 것["덮임"]
    _, _, 못 = cc.흠(것, {"Amazon DynamoDB"}, [], 오늘)
    assert any("덮임" in x for x in 못)


# ── 청구 지표 : 공짜로 재는 「돈이 걸린 표면」 ──────────────────────────

def test_청구_지표에_있고_선언에_없으면_막는다():
    """★ **terraform 에도 CE 에도 안 보이는 것이 여기 뜬다.** 2026-10-11 에 다섯이
    그랬다 — KMS · 데이터 전송 · SQS · SNS · Marketplace(DECISIONS §181)."""
    것 = _선언(청구지표={"서비스": ["AmazonDynamoDB", "awskms"]})
    막, _, _ = cc.흠(것, {"Amazon DynamoDB"}, [], 오늘)
    assert any("Key Management" in x for x in 막)


def test_청구별칭에_없는_이름을_막는다():
    것 = _선언(청구지표={"서비스": ["AmazonDynamoDB", "AWSNewThing"]})
    막, _, _ = cc.흠(것, {"Amazon DynamoDB"}, [], 오늘)
    assert any("AWSNewThing" in x and "청구별칭" in x for x in 막)


def test_청구_지표가_없으면_못쟀다다():
    것 = _선언()
    del 것["청구지표"]
    _, _, 못 = cc.흠(것, {"Amazon DynamoDB"}, [], 오늘)
    assert any("청구지표" in x for x in 못)


def test_선언한_청구별칭이_전부_실물_서비스를_가리킨다():
    """★ **족 가드.** 별칭의 값이 선언에 없는 이름이면 그 별칭은 **아무 일도 안 한다** —
    `흠` 이 그 서비스를 「선언에 없다」 로 물 때만 쓸모가 생기므로, 거꾸로도 맞춰 둔다."""
    선언된 = set((cc.선언().get("서비스") or {}))
    지표 = set((cc.선언().get("청구지표") or {}).get("서비스") or [])
    for 짧은 in 지표:
        assert 짧은 in cc.청구별칭, f"청구 지표의 {짧은} 에 이름이 안 붙어 있다"
        assert cc.청구별칭[짧은] in 선언된, f"{짧은} → {cc.청구별칭[짧은]} 가 선언에 없다"


# ── 크레딧 ──────────────────────────────────────────────────────────────

def test_크레딧이_바닥나면_막는다():
    막, _, _ = cc.흠(_선언(크레딧={"남은것": 0.0, "만료": "2027-08-27"}),
                     {"Amazon DynamoDB"}, [], 오늘)
    assert any("바닥났다" in x for x in 막)


def test_크레딧이_없으면_못쟀다다():
    """★ **0 과 「안 재 봤다」 는 다른 말이다**(§59). 0 이면 막고, 없으면 다시 잰다."""
    것 = _선언()
    del 것["크레딧"]
    막, _, 못 = cc.흠(것, {"Amazon DynamoDB"}, [], 오늘)
    assert 막 == [] and any("크레딧" in x and "공짜" in x for x in 못)


def test_크레딧_만료일이_유예로_들어온다():
    """★ **같은 수를 두 곳에 안 적는다**(§91). 179 는 `유예.크레딧만료` 를 손으로 적었다 —
    `크레딧` 블록이 정본이고 `흠` 이 거기서 읽는다."""
    것 = _선언(크레딧={"남은것": 10.0, "만료": "2026-10-20"})
    막, 알, _ = cc.흠(것, {"Amazon DynamoDB"}, [], 오늘)
    assert 막 == [] and any("D-10" in x for x in 알)


def test_유예가_지났으면_막는다():
    것 = _선언(유예={"무료플랜끝": "2026-09-30"})
    막, _, _ = cc.흠(것, {"Amazon DynamoDB"}, [], 오늘)
    assert any("지났다" in x for x in 막)


def test_먼_유예는_조용하다():
    assert cc.흠(_선언(), {"Amazon DynamoDB"}, [], 오늘) == ([], [], [])


def test_크레딧파싱이_서비스_모델_꼴을_읽는다():
    """★ **필드 이름을 짐작하지 않았다.** botocore 의 `billing/2023-09-07` 서비스
    모델에서 읽었다 — `remainingAmount.currencyAmount` 는 **문자열**이다."""
    것 = {"credits": [
        {"creditStatus": "ENABLED", "endDate": "2027-08-27T00:00:00+00:00",
         "remainingAmount": {"currencyCode": "USD", "currencyAmount": "99.84"}},
        {"creditStatus": "ENABLED", "endDate": "2027-01-31T00:00:00+00:00",
         "remainingAmount": {"currencyCode": "USD", "currencyAmount": "40.00"}},
    ]}
    블록, 까닭 = cc.크레딧파싱(것)
    assert 까닭 == ""
    assert 블록["남은것"] == 139.84 and 블록["센것"] == 2
    # ★ **가장 먼저 만료되는 것**이 다음 절벽이다 — 늦은 쪽을 적으면 절벽을 늦게 본다
    assert 블록["만료"] == "2027-01-31"


def test_꺼진_크레딧은_안_센다():
    것 = {"credits": [
        {"creditStatus": "DISABLED", "endDate": "2027-08-27",
         "remainingAmount": {"currencyAmount": "500"}},
        {"creditStatus": "ENABLED", "endDate": "2027-08-27",
         "remainingAmount": {"currencyAmount": "1.5"}},
    ]}
    블록, _ = cc.크레딧파싱(것)
    assert 블록["남은것"] == 1.5 and 블록["센것"] == 1


def test_모르는_꼴을_0_으로_안_읽는다():
    """★ **0 은 「크레딧이 없다」 는 뜻이고 그러면 이 관문이 막아 버린다.** 「못 쟀다」 와
    「없다」 는 다른 말이다(§59) — 꼴을 못 알아보면 `None` 과 까닭을 돌려준다."""
    for 것 in (None, {}, {"credits": "글자"},
               {"credits": [{"endDate": "2027-08-27"}]},
               {"credits": [{"remainingAmount": {"currencyAmount": "많이"}}]},
               {"credits": []}):
        블록, 까닭 = cc.크레딧파싱(것)
        assert 블록 is None and 까닭, f"{것!r} 를 통과시켰다"


def test_epoch_도_ISO_도_읽는다():
    """CLI 는 ISO 로, SDK 는 epoch 으로 준다."""
    assert cc._날짜(1787788800) == d.date(2026, 8, 27)
    assert cc._날짜("2027-08-27") == d.date(2027, 8, 27)
    assert cc._날짜("2027-08-27T00:00:00Z") == d.date(2027, 8, 27)
    assert cc._날짜("언제") is None and cc._날짜(None) is None


# ── 임계 ────────────────────────────────────────────────────────────────

def test_경고선과_막음선이_다른_일을_한다():
    적음 = _선언(서비스={"A": {"월": 7.0, "잰달": "2026-09", "갈래": "과금", "자원": "부른다"}})
    막, 알, _ = cc.흠(적음, set(), [], 오늘)
    assert 막 == [] and any("경고선" in x for x in 알)

    많음 = _선언(서비스={"A": {"월": 25.0, "잰달": "2026-09", "갈래": "과금", "자원": "부른다"}})
    막, _, _ = cc.흠(많음, set(), [], 오늘)
    assert any("바닥" in x for x in 막)


# ── DynamoDB 무료 용량 (DECISIONS §181) ─────────────────────────────────

def test_온디맨드_테이블을_막는다():
    """★ **「거의 0」 은 0 이 아니다.** 온디맨드에는 요청 무료분이 **아예 없어서** 실측
    월 $0.001 이 영구히 깔린다. 179 는 「측정 아래라 값어치가 없다」 고 적었다."""
    난것 = cc.용량흠(_표('billing_mode = "PAY_PER_REQUEST"'))
    # ★ **`"PROVISIONED" in x` 로 물으면 거짓 초록이다.** 판정을 지우면 아래 「용량이 안
    #   적혀 있다」 가지로 떨어지고 **그 말에도 `PROVISIONED` 가 들어 있다** — 돌연변이
    #   `[무료용량] 온디맨드를 그냥 둔다` 가 그걸로 살아남았다. 겨냥을 좁힌다.
    assert any("PAY_PER_REQUEST" in x and "요청 프리티어" in x for x in 난것)


def test_프로비전드_25_는_조용하다():
    것 = _표('billing_mode = "PROVISIONED"\n read_capacity = 25\n write_capacity = 25')
    assert cc.용량흠(것) == []


def test_모드가_안_적혀_있으면_막는다():
    assert any("billing_mode" in x for x in cc.용량흠(_표("hash_key = \"h\"")))


def test_용량이_안_적혀_있으면_막는다():
    assert any("용량이 안 적혀" in x for x in cc.용량흠(_표('billing_mode = "PROVISIONED"')))


def test_테이블_합이_25_를_넘으면_막는다():
    """★ **25 는 계정·리전 몫이고 테이블들이 나눠 쓴다.** 테이블 하나씩 보면 둘 다 25 라
    조용하고 청구서는 두 배다 — 수집 적재지가 붙는 것이 다음 패치다(PLAN #70)."""
    몸 = 'billing_mode = "PROVISIONED"\n read_capacity = 25\n write_capacity = 25'
    것 = [("aws_dynamodb_table", "a", 몸), ("aws_dynamodb_table", "b", 몸)]
    난것 = cc.용량흠(것)
    assert any("읽기 RCU" in x for x in 난것) and any("쓰기 WCU" in x for x in 난것)


def test_인덱스_용량도_합에_센다():
    """★ GSI 는 **자기 용량을 따로 든다.** 표 수준만 보면 무료 몫을 넘겨도 조용하다."""
    몸 = ('billing_mode = "PROVISIONED"\n read_capacity = 25\n write_capacity = 25\n'
          ' global_secondary_index {\n read_capacity = 5\n write_capacity = 5\n }')
    assert cc.용량흠(_표(몸)) != []


def test_자동_확장을_막는다():
    """★ **넘치면 조르는 쪽으로 진다.** 자동 확장은 25 를 **넘겨서** 과금되므로, 그것이
    붙는 것이 곧 이 상환을 되돌리는 것이다 — 조름은 시간이고 과금은 돈이다."""
    몸 = 'billing_mode = "PROVISIONED"\n read_capacity = 25\n write_capacity = 25'
    것 = _표(몸) + [("aws_appautoscaling_target", "ddb", "max_capacity = 100")]
    assert any("자동 확장" in x for x in cc.용량흠(것))


def test_금지자원이_전부_물린다():
    """★ **족 가드.** 선언한 금지 자원마다 가지가 하나씩 있나 — 목록만 늘고 판정이
    안 늘면 그 줄은 **글일 뿐**이다(§123)."""
    for 종류 in cc.금지자원:
        assert cc.용량흠([(종류, "x", "")]), f"{종류} 를 선언만 하고 안 문다"


def test_표가_없으면_금지자원만_본다():
    assert cc.용량흠([]) == []


# ── 계정 번호 (§131) ────────────────────────────────────────────────────

def test_계정_번호를_문다():
    """★ `billing get-credits` 가 `--account-id` 를 **요구한다**(botocore 서비스 모델).
    쥐는 손 옆에 관문을 둔다 — 약속을 사람의 기억에 맡기지 않는다."""
    난것 = cc.계정흠({"a.md": f"arn:aws:iam::{남계정}:root"})
    assert len(난것) == 1 and "a.md" in 난것[0]
    assert 남계정 not in "".join(난것), "★ 문면서 번호를 다시 적으면 그 자리가 새 누출이다"


def test_문서_예시_계정은_안_문다():
    """★ 음성 대조. 이 저장소의 `test_deploy_drift` · `test_preflight` 가 그것을 쓴다 —
    넓으면 시험 픽스처를 못 쓰게 되고, 그러면 관문을 끈다(§46)."""
    글 = " ".join(f"arn:aws:iam::{n}:root" for n in cc.문서계정)
    assert cc.계정흠({"t.py": 글}) == []


def test_16진수_지문과_잠금_파일을_안_문다():
    """★ **묶지 않은 식은 20줄 넘게 물었다**(2026-10-11 실측). sha256 과 `uv.lock` 이
    12자리 수열을 안에 들고 있다 — 양쪽을 숫자·글자 아닌 것으로 묶어서 갈랐다."""
    것 = {"docseal.json": '"지문": "186482411849dbf5"',
          "uv.lock": 'size = 4013555, hash = "sha256:' + "a" * 8 + "1" * 12 + 'bc"'}
    assert cc.계정흠(것) == []


def test_실물_저장소에_계정_번호가_없다():
    """★ **이 시험이 §131 의 유일한 기계적 보증**이다."""
    글들 = cc.추적파일글()
    assert 글들, "`git ls-files` 를 못 읽었다 — 못 쟀다는 뜻이지 통과가 아니다"
    assert cc.계정흠(글들) == []


# ── 실물 ────────────────────────────────────────────────────────────────

def test_infra_의_자원_종류가_전부_이름을_가진다():
    """★ **족 가드다.** 새 자원 종류가 `infra/` 에 생기면 **자동으로 걸린다** — 손으로
    만든 목록이 아니라 실물에서 뽑아 맞댄다(§123)."""
    _, 모름 = cc.쓰는서비스(cc.자원들())
    assert 모름 == [], f"`cost_check.자원서비스` 에 없는 자원 종류 : {모름}"


def test_실물_선언이_실물_인프라와_맞는다():
    막, _, _ = cc.흠(cc.선언(), *cc.쓰는서비스(cc.자원들()), 오늘)
    assert 막 == []


def test_실물_테이블이_무료_용량_안이다():
    """★ **이 시험이 `PROVISIONED` 상환을 붙들고 있다.** 되돌리면 여기서 문다."""
    assert cc.용량흠(cc.자원블록들()) == []


def test_자원블록들이_본문을_같이_든다():
    블록들 = cc.자원블록들()
    assert 블록들, "`infra/*.tf` 에서 자원을 못 뽑았다"
    표 = [본문 for 종류, _이름, 본문 in 블록들 if 종류 == "aws_dynamodb_table"]
    assert len(표) == 1 and "billing_mode" in 표[0]
    # ★ **넉넉하게 자르므로 다음 선언을 먹지 않는지** 본다 — 먹으면 합이 부풀어
    #   거짓 양성이 되고, 덜 자르면 용량을 못 보고 거짓 음성이 된다.
    assert "resource" not in 표[0].split("\n", 1)[1]


def test_모든_서비스가_갈래와_상환을_든다():
    """★ **「나중에 생각한다」 는 적을 수 없다.** 과금 자원마다 **어떻게 0 으로 내려가는지**
    가 적혀 있어야 하고, 안 내려가는 것은 그 까닭이 적혀 있어야 한다.
    ★ `모름` 이 어휘에 든 까닭 : 2026-10-11 에 **청구 지표에는 뜨는데 달러를 못 잰**
    서비스가 다섯 있었다. 그것을 `과금 0` 으로 적으면 **안 잰 것이 싼 것**이 된다(§59)."""
    for 이름, s in (cc.선언().get("서비스") or {}).items():
        assert s.get("갈래") in ("과금", "항상무료", "모름"), f"{이름} 의 갈래가 어휘 밖이다"
        assert s.get("자원") in ("세운다", "부른다"), f"{이름} 에 자원 칸이 없다"
        assert s.get("상환"), f"{이름} 에 상환이 안 적혀 있다"
        assert s.get("프리티어"), f"{이름} 에 프리티어가 안 적혀 있다"
        if s.get("갈래") == "모름":
            assert s.get("월") is None, f"{이름} 이 모름인데 수를 들었다"
        else:
            assert s.get("월") is not None, f"{이름} 에 월이 없다"


def test_잰달이_적힌_달러만_있다():
    for 이름, s in (cc.선언().get("서비스") or {}).items():
        if float(s.get("월") or 0) > 0:
            assert s.get("잰달"), f"{이름} 에 잰달이 없다"


# ── 종료 코드 ───────────────────────────────────────────────────────────

def _갈아끼운다(monkeypatch, tmp_path, 선언값):
    f = tmp_path / "cost.json"
    f.write_text(json.dumps(선언값, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(cc, "선언파일", f)
    # ★ **실물 인프라를 같이 보면 흠(1)이 나서 낡음(2)을 못 가른다.** 재려는 것 하나만
    #   남긴다 — 「무엇을 재는 중인가」 를 시험이 밝혀 적는다.
    몸 = 'billing_mode = "PROVISIONED"\n read_capacity = 25\n write_capacity = 25'
    monkeypatch.setattr(cc, "자원블록들", lambda *a, **k: [("aws_dynamodb_table", "t", 몸)])
    monkeypatch.setattr(cc, "추적파일글", lambda *a, **k: {"x": "글"})
    monkeypatch.setattr(sys, "argv", ["cost_check.py"])
    return f


def test_낡으면_종료코드가_2_다(monkeypatch, tmp_path):
    """★ **낡은 값으로 초록을 내면 그 관문은 꺼진 채 사는 것이다.**"""
    f = _갈아끼운다(monkeypatch, tmp_path, _선언(잰날="2026-01-01"))
    assert cc.main() == 2
    # 음성 대조 — 안 낡으면 0 이다. 아니면 이 검사는 **늘 2** 를 보고 통과한다.
    f.write_text(json.dumps(_선언(잰날=d.date.today().isoformat()), ensure_ascii=False),
                 encoding="utf-8")
    assert cc.main() == 0


def test_막을_것이_못쟀다를_이긴다(monkeypatch, tmp_path):
    """★ **1 과 2 의 차례를 정한다.** 둘이 같이 나면 **흠이 먼저**다 — 「못 쟀다」 는
    다시 재면 되고 흠은 사람이 고쳐야 한다."""
    것 = _선언(잰날="2026-01-01", 덮임={"값": 1.0})
    _갈아끼운다(monkeypatch, tmp_path, 것)
    assert cc.main() == 1


def test_계정_번호를_못_훑으면_2_다(monkeypatch, tmp_path):
    _갈아끼운다(monkeypatch, tmp_path, _선언(잰날=d.date.today().isoformat()))
    monkeypatch.setattr(cc, "추적파일글", lambda *a, **k: {})
    assert cc.main() == 2


def test_main_이_용량을_본다(monkeypatch, tmp_path):
    """★ **판정이 살아 있어도 `main` 이 안 부르면 꺼진 것이다.** 돌연변이
    `[과금선언] 용량을 아예 안 본다` 가 여기 없어서 살아남았다 — 판정만 시험하면
    **배선이 사각**이 된다(§21)."""
    _갈아끼운다(monkeypatch, tmp_path, _선언(잰날=d.date.today().isoformat()))
    monkeypatch.setattr(cc, "자원블록들",
                        lambda *a, **k: [("aws_dynamodb_table", "t",
                                          'billing_mode = "PAY_PER_REQUEST"')])
    assert cc.main() == 1


def test_main_이_계정_번호를_훑는다(monkeypatch, tmp_path):
    """★ 위와 같은 까닭 — `[과금선언] 계정 번호를 아예 안 훑는다` 가 살아남았던 자리다."""
    _갈아끼운다(monkeypatch, tmp_path, _선언(잰날=d.date.today().isoformat()))
    monkeypatch.setattr(cc, "추적파일글",
                        lambda *a, **k: {"a.md": "arn:aws:iam::" + "7" * 12 + ":root"})
    assert cc.main() == 1


def test_선언을_못_읽으면_2_다(monkeypatch, tmp_path):
    monkeypatch.setattr(cc, "선언파일", tmp_path / "없다.json")
    monkeypatch.setattr(sys, "argv", ["cost_check.py"])
    assert cc.main() == 2


# ── 배선 ────────────────────────────────────────────────────────────────

def test_doctor_가_이_관문을_본다():
    sh = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    assert "tools/cost_check.py" in sh, "doctor 가 과금을 안 본다"


def test_doctor_가_재는_길을_안_부른다():
    """★ **관문이 과금이면 안 된다.** Cost Explorer 는 **호출당 $0.01** 이고 `doctor` 는
    하루에 열 번도 돈다 — **재는 자가 재려는 것을 늘린다.**
    ★ `--재다` 는 이제 공짜지만 **네트워크는 여전히 네트워크다** — `doctor` 는 기계가
    오프라인이어도 끝까지 돌아야 한다. 그래서 둘 다 막는다."""
    # ★ **글자로 찾으면 안내문에 걸린다.** `skip "… --재다"` 는 **부르는 것이 아니라
    #   사람에게 알려 주는 말**이다 — 첫 판이 거기 걸렸다(§178 과 같은 모양 : 글을 코드로
    #   읽었다). **부름만 본다** — 명령 치환 안의 `cost_check.py` 를 센다.
    import re as _re
    sh = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    부름 = _re.findall(r"\$\([^)]*cost_check\.py[^)]*\)", sh)
    assert 부름, "doctor 가 cost_check.py 를 아예 안 부른다"
    for x in 부름:
        for 깃발 in ("--재다", "--서비스별"):
            assert 깃발 not in x, f"doctor 가 `{깃발}` 를 부른다 : {x}"
    src = (ROOT / "tools/cost_check.py").read_text(encoding="utf-8")
    본 = "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("#"))
    # ★ **「네트워크가 없다」 를 `subprocess.run` 의 없음으로 묻지 않는다.** 180 에서
    #   `추적파일글` 이 `git ls-files` 를 부르면서 그 식이 거짓이 됐다 — git 은 공짜고
    #   오프라인이다. 묻고 싶은 것은 **AWS 를 부르나**이고, AWS 는 `_aws` 하나로만 나간다.
    # 평소 경로 = `_aws` 가 정의되기 **전**(판정자들) + `main`. 그 사이가 재는 길이다.
    머리 = 본.split("def _aws(", 1)[0] + 본.split("def main(", 1)[1]
    for 줄 in 머리.split("\n"):
        if "subprocess.run" in 줄:
            assert '"git"' in 줄, f"평소 경로가 git 아닌 것을 부른다 : {줄.strip()}"
    부름 = [줄 for 줄 in 머리.split("\n")
            if _re.search(r"(?<![0-9A-Za-z_])_aws\(", 줄) and "def " not in 줄]
    assert 부름 == [], f"평소 경로에서 AWS 를 부른다 : {부름}"


def test_재다가_공짜_길만_쓴다():
    """★ **`--재다` 자체가 과금이었다**(DECISIONS §181). 「사람이 손으로 한다」 로 막은
    것은 **빈도**일 뿐이고, 목표가 「무과금」 인 저장소에 $0.01 짜리 측정자가 서 있는
    것은 그대로 빚이다. 공짜 셋만 쓰는지 **몸을 잘라서** 본다."""
    src = (ROOT / "tools/cost_check.py").read_text(encoding="utf-8")
    본 = "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("#"))
    몸 = 본[본.index("def 재다("):본.index("def 서비스별(")]
    assert "list-metrics" in 몸 and "get-metric-statistics" in 몸 and "get-credits" in 몸
    assert "get-cost-and-usage" not in 몸, "`--재다` 가 Cost Explorer 를 부른다 — $0.01 이다"
    # ★ **무료에서 빠지는 두 부름**을 안 쓰는지. CloudWatch 무료 100만 요청에서
    #   `GetMetricData` 와 `GetMetricWidgetImage` 만 빠진다.
    for 비싼 in ("get-metric-data", "get-metric-widget-image"):
        assert 비싼 not in 몸, f"`{비싼}` 는 CloudWatch 무료 몫 밖이다"


def test_서비스별이_CE_가_생략한_것도_0_으로_적는다(monkeypatch, tmp_path):
    """★ **「안 온다」 가 「모른다」 가 아닌 근거**(DECISIONS §182) : CE 는 그 달에 **쓴
    적이 있으면** $0.0000 이라도 레코드를 준다(2026-10 실측 : Glue · Lambda · KMS · SNS ·
    SQS · Tax · Firehose · CloudWatch **여덟이 0.0000 으로 왔다**). 아예 안 오는 것은
    **그 달에 쓴 적이 없다**는 뜻이고, 쓴 적이 없으면 과금도 없다.
    ★ 181 판은 **돌려준 것만** 갱신해서, CE 가 생략한 `Amazon Athena` 가 **9월 값을 든
    채** 10월 합계에 남았다. 그 꼬리가 합 $0.0737 의 마지막 자리였다."""
    f = tmp_path / "cost.json"
    f.write_text(json.dumps({"서비스": {
        "온것": {"월": 9.9, "잰달": "2026-08", "갈래": "과금", "자원": "부른다"},
        "안온것": {"월": 0.0003, "잰달": "2026-08", "갈래": "과금", "자원": "부른다"},
    }}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(cc, "선언파일", f)
    monkeypatch.setattr(cc, "_aws", lambda a: {"ResultsByTime": [{
        "TimePeriod": {"Start": "2026-10-01"},
        "Groups": [{"Keys": ["온것"],
                    "Metrics": {"UnblendedCost": {"Amount": "0.0527"}}}]}]})
    assert cc.서비스별() == 0
    난것 = json.loads(f.read_text(encoding="utf-8"))["서비스"]
    assert 난것["온것"]["월"] == 0.0527
    assert 난것["안온것"]["월"] == 0.0, "CE 가 생략한 것이 옛 달 값을 들고 남았다"
    # ★ **두 칸이 같은 달이어야** 합계가 참말이 된다 — 그것이 이 가지의 목적이다
    assert 난것["온것"]["잰달"] == 난것["안온것"]["잰달"] == "2026-10"
    assert "_빠짐" in 난것["안온것"] and "_빠짐" not in 난것["온것"]


def test_서비스별_뒤에는_달이_하나다(monkeypatch, tmp_path):
    """★ **갚았는지를 관문으로 묻는다.** 위 시험이 칸을 보는 것이고, 이것은 **그 결과가
    섞임 가드를 통과하는지**를 본다 — 둘은 다른 물음이다(§152)."""
    f = tmp_path / "cost.json"
    f.write_text(json.dumps({
        "잰날": d.date.today().isoformat(), "낡음일수": 30,
        "임계": {}, "유예": {}, "덮임": {"값": 0.0},
        "크레딧": {"남은것": 1.0, "만료": "2027-08-27"},
        "청구지표": {"서비스": []},
        "서비스": {
            "온것": {"월": 1.0, "잰달": "2026-08", "갈래": "과금", "자원": "부른다"},
            "안온것": {"월": 0.1, "잰달": "2026-08", "갈래": "과금", "자원": "부른다"}},
    }, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(cc, "선언파일", f)
    monkeypatch.setattr(cc, "_aws", lambda a: {"ResultsByTime": [{
        "TimePeriod": {"Start": "2026-10-01"},
        "Groups": [{"Keys": ["온것"],
                    "Metrics": {"UnblendedCost": {"Amount": "1.0"}}}]}]})
    cc.서비스별()
    막, _, _ = cc.흠(cc.선언(f), set(), [], 오늘)
    assert not any("섞였다" in x for x in 막), 막


def test_서비스별이_크레딧을_뺀다():
    """★ **크레딧을 빼야 「크레딧이 없으면 얼마 나가나」 가 보인다**(DECISIONS §180).
    안 빼면 Bedrock $0.1582 + 크레딧 −$0.1582 = **$0.00** 이고, 크레딧이 끝나는 날
    갑자기 숫자가 뜬다. 그건 측정이 아니라 지뢰다."""
    src = (ROOT / "tools/cost_check.py").read_text(encoding="utf-8")
    본 = "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("#"))
    몸 = 본[본.index("def 서비스별("):본.index("def main(")]
    assert "RECORD_TYPE" in 몸 and '"Credit"' in 몸, "CE 질의가 크레딧을 안 뺀다"
    assert "잰달" in 몸, "서비스별이 잰 달을 안 적는다"


def test_계정_번호를_선언에_안_적는다():
    """★ `--재다` 가 `sts get-caller-identity` 로 번호를 **쥐지만**, 쓰는 것은
    `청구지표` · `덮임` · `크레딧` 뿐이다. 번호가 선언으로 새는 가지가 없는지 본다."""
    src = (ROOT / "tools/cost_check.py").read_text(encoding="utf-8")
    본 = "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("#"))
    몸 = 본[본.index("def 재다("):본.index("def 서비스별(")]
    번호줄 = [l for l in 몸.split("\n") if "번호" in l]
    assert 번호줄, "계정 번호를 아예 안 읽는다"
    for l in 번호줄:
        assert "d[" not in l and "선언파일" not in l, f"번호가 선언으로 새는 줄 : {l.strip()}"


def test_정말_도는가():
    """★ **글자로 본 것과 돌려 본 것은 다르다**(§152)."""
    r = subprocess.run([sys.executable, "tools/cost_check.py"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode in (0, 1, 2), f"{r.returncode} / {r.stderr[-300:]}"
    assert r.stdout.strip(), "아무 말도 안 한다"


def test_카나리아가_산다():
    r = subprocess.run([sys.executable, "tools/cost_check.py", "--selftest"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0 and "프로브 살아 있다" in r.stdout
