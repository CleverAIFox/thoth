"""`tools/cost_check.py` — **과금을 재는 자**(DECISIONS §180).

★ **이 저장소는 코드·문서·인프라·CI·CSS·주석까지 다 재면서 돈만 안 쟀다.** 그 사각이
  이미 한 번 물었다 — §177 전까지 **꺼 둔 줄 알고 Bedrock 요청이 계속 나갔고 아무도 안
  울었다.** 목표가 「무과금 개인용 확장」 이므로 **과금 의존이 곧 빚**이다.

★ **네트워크 없이 전부 먹인다.** 판정은 순수 함수라 합성으로 가른다(§132 와 같은 꼴).
  `--재다` 만 AWS 를 부르고, 그 자리는 **`doctor` 가 절대 안 들어간다** — Cost Explorer 가
  **호출당 $0.01** 이라 관문이 과금이 되면 안 된다.
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


def _선언(**덮):
    것 = {"잰날": "2026-10-10", "낡음일수": 30,
          "임계": {"월경고": 5.0, "월막음": 20.0, "유예경고일": 30},
          "유예": {},
          "서비스": {"Amazon DynamoDB": {"월": 0.001, "갈래": "과금", "자원": "세운다"}}}
    것.update(덮)
    return 것


# ── 판정 ────────────────────────────────────────────────────────────────

def test_맞는_선언은_조용하다():
    assert cc.흠(_선언(), {"Amazon DynamoDB"}, [], 오늘) == ([], [])


def test_선언에_없는_자원을_문다():
    """★ **선언하지 않은 자원은 과금이 나도 아무도 안 본다.**"""
    막, _ = cc.흠(_선언(), {"Amazon DynamoDB", "Amazon Kinesis Firehose"}, [], 오늘)
    assert len(막) == 1 and "Kinesis Firehose" in 막[0]


def test_이름을_못_붙인_자원_종류를_문다():
    """★ **모르는 것을 조용히 넘기면 새 과금 자원이 생겨도 초록이다**(§21)."""
    막, _ = cc.흠(_선언(), {"Amazon DynamoDB"}, ["aws_새서비스_thing"], 오늘)
    assert len(막) == 1 and "aws_새서비스_thing" in 막[0]


def test_자원_칸이_없으면_문다():
    막, _ = cc.흠(_선언(서비스={"X": {"월": 0.1, "갈래": "과금"}}), set(), [], 오늘)
    assert any("`자원` 칸이 없다" in x for x in 막)


def test_부르는_서비스는_terraform_에_없어도_안_문다():
    """★ **첫 판이 이 가지 없이 돌았고 Bedrock · Athena 를 「손으로 만든 자원」 으로
    물었다 — 거짓 양성 둘**(DECISIONS §180). **자원을 세우고 쓰는 것과 불러서 쓰는 것은
    다르다.** Bedrock 에는 세울 자원이 없다."""
    것 = _선언(서비스={"Amazon Bedrock": {"월": 0.1582, "갈래": "과금", "자원": "부른다"}})
    assert cc.흠(것, set(), [], 오늘) == ([], [])


def test_세우는_서비스가_terraform_밖에서_과금되면_알린다():
    """★ 2026-10-10 에 `AWS Secrets Manager` 가 그랬다. `deploy_drift` 도 `check_infra` 도
    **IaC 안만** 보므로 **손으로 만든 과금 자원은 어느 자도 못 봤다.**"""
    것 = _선언(서비스={"AWS Secrets Manager": {"월": 0.0001, "갈래": "과금", "자원": "세운다"}})
    막, 알 = cc.흠(것, set(), [], 오늘)
    assert 막 == []
    assert len(알) == 1 and "Secrets Manager" in 알[0]


def test_과금이_0_이면_terraform_밖이어도_안_알린다():
    """★ 음성 대조. 쓰지 않는 서비스까지 짖으면 그 경고는 곧 안 읽힌다(§133)."""
    것 = _선언(서비스={"AWS Secrets Manager": {"월": 0.0, "갈래": "과금", "자원": "세운다"}})
    assert cc.흠(것, set(), [], 오늘) == ([], [])


# ── 임계 ────────────────────────────────────────────────────────────────

def test_경고선과_막음선이_다른_일을_한다():
    적음 = _선언(서비스={"A": {"월": 7.0, "갈래": "과금", "자원": "부른다"}})
    막, 알 = cc.흠(적음, set(), [], 오늘)
    assert 막 == [] and any("경고선" in x for x in 알)

    많음 = _선언(서비스={"A": {"월": 25.0, "갈래": "과금", "자원": "부른다"}})
    막, _ = cc.흠(많음, set(), [], 오늘)
    assert any("바닥" in x for x in 막)


def test_유예가_가까우면_알리고_지났으면_막는다():
    가까움 = _선언(유예={"크레딧만료": "2026-10-20"})
    막, 알 = cc.흠(가까움, {"Amazon DynamoDB"}, [], 오늘)
    assert 막 == [] and any("D-10" in x for x in 알)

    지남 = _선언(유예={"무료플랜끝": "2026-09-30"})
    막, _ = cc.흠(지남, {"Amazon DynamoDB"}, [], 오늘)
    assert any("지났다" in x for x in 막)


def test_먼_유예는_조용하다():
    먼것 = _선언(유예={"크레딧만료": "2027-08-27"})
    assert cc.흠(먼것, {"Amazon DynamoDB"}, [], 오늘) == ([], [])


# ── 낡음 : 「못 쟀다」 ≠ 「맞다」 (DECISIONS §59) ─────────────────────────

def test_잰날이_없으면_막는다():
    것 = _선언()
    del 것["잰날"]
    막, _ = cc.흠(것, {"Amazon DynamoDB"}, [], 오늘)
    assert any("`잰날` 이 없다" in x for x in 막)


def test_선언이_낡으면_알린다():
    것 = _선언(잰날="2026-08-01")
    막, 알 = cc.흠(것, {"Amazon DynamoDB"}, [], 오늘)
    assert 막 == [] and any("일 됐다" in x for x in 알)


def test_낡으면_종료코드가_0_이_아니다(monkeypatch, tmp_path):
    """★ **낡은 값으로 초록을 내면 그 관문은 꺼진 채 사는 것이다.**"""
    f = tmp_path / "cost.json"
    f.write_text(json.dumps(_선언(잰날="2026-01-01")), encoding="utf-8")
    monkeypatch.setattr(cc, "선언파일", f)
    # ★ **실물 인프라를 같이 보면 흠(1)이 나서 낡음(2)을 못 가른다.** 재려는 것 하나만
    #   남긴다 — 「무엇을 재는 중인가」 를 시험이 밝혀 적는다.
    monkeypatch.setattr(cc, "자원들", lambda *a, **k: [("aws_dynamodb_table", "t")])
    monkeypatch.setattr(sys, "argv", ["cost_check.py"])
    assert cc.main() == 2

    # 음성 대조 — 안 낡으면 0 이다. 아니면 이 검사는 **늘 2** 를 보고 통과한다.
    f.write_text(json.dumps(_선언(잰날=d.date.today().isoformat())), encoding="utf-8")
    assert cc.main() == 0


def test_선언을_못_읽으면_2_다(monkeypatch, tmp_path):
    monkeypatch.setattr(cc, "선언파일", tmp_path / "없다.json")
    monkeypatch.setattr(sys, "argv", ["cost_check.py"])
    assert cc.main() == 2


# ── 실물 ────────────────────────────────────────────────────────────────

def test_infra_의_자원_종류가_전부_이름을_가진다():
    """★ **족 가드다.** 새 자원 종류가 `infra/` 에 생기면 **자동으로 걸린다** — 손으로
    만든 목록이 아니라 실물에서 뽑아 맞댄다(§123)."""
    _, 모름 = cc.쓰는서비스(cc.자원들())
    assert 모름 == [], f"`cost_check.자원서비스` 에 없는 자원 종류 : {모름}"


def test_실물_선언이_실물_인프라와_맞는다():
    막, _ = cc.흠(cc.선언(), *cc.쓰는서비스(cc.자원들()), 오늘)
    assert 막 == []


def test_모든_서비스가_갈래와_상환을_든다():
    """★ **「나중에 생각한다」 는 적을 수 없다.** 과금 자원마다 **어떻게 0 으로 내려가는지**
    가 적혀 있어야 하고, 안 내려가는 것은 그 까닭이 적혀 있어야 한다."""
    for 이름, s in (cc.선언().get("서비스") or {}).items():
        assert s.get("갈래") in ("과금", "항상무료"), f"{이름} 의 갈래가 어휘 밖이다"
        assert s.get("자원") in ("세운다", "부른다"), f"{이름} 에 자원 칸이 없다"
        assert s.get("상환"), f"{이름} 에 상환이 안 적혀 있다"
        assert s.get("프리티어"), f"{이름} 에 프리티어가 안 적혀 있다"


# ── 배선 ────────────────────────────────────────────────────────────────

def test_doctor_가_이_관문을_본다():
    sh = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    assert "tools/cost_check.py" in sh, "doctor 가 과금을 안 본다"


def test_doctor_가_재다를_안_부른다():
    """★ **관문이 과금이면 안 된다.** Cost Explorer 는 **호출당 $0.01** 이고 `doctor` 는
    하루에 열 번도 돈다 — **재는 자가 재려는 것을 늘린다.** 그 줄이 돌아오면 여기서 문다."""
    # ★ **글자로 찾으면 안내문에 걸린다.** `skip "… --재다"` 는 **부르는 것이 아니라
    #   사람에게 알려 주는 말**이다 — 첫 판이 거기 걸렸다(§178 과 같은 모양 : 글을 코드로
    #   읽었다). **부름만 본다** — 명령 치환 안의 `cost_check.py` 를 센다.
    import re as _re
    sh = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    부름 = _re.findall(r"\$\([^)]*cost_check\.py[^)]*\)", sh)
    assert 부름, "doctor 가 cost_check.py 를 아예 안 부른다"
    for x in 부름:
        assert "--재다" not in x, f"doctor 가 `--재다` 를 부른다 — 관문 한 번에 $0.01 이다 : {x}"
    src = (ROOT / "tools/cost_check.py").read_text(encoding="utf-8")
    본 = "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("#"))
    머리, 꼬리 = 본.split("def 재다(", 1)
    assert "subprocess.run" not in 머리.split("def _aws(")[0], \
        "`재다` 밖에서 AWS 를 부른다 — 평소 경로에 네트워크가 들어왔다"


def test_재다가_크레딧을_뺀다():
    """★ **크레딧을 빼야 「크레딧이 없으면 얼마 나가나」 가 보인다**(DECISIONS §180).
    안 빼면 Bedrock $0.1582 + 크레딧 −$0.1582 = **$0.00** 이고, 크레딧이 끝나는 날
    갑자기 숫자가 뜬다. 그건 측정이 아니라 지뢰다."""
    src = (ROOT / "tools/cost_check.py").read_text(encoding="utf-8")
    assert "RECORD_TYPE" in src and '"Credit"' in src, "CE 질의가 크레딧을 안 뺀다"


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
