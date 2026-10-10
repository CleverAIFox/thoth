#!/usr/bin/env python3
"""**과금을 재는 자가 없었다**(DECISIONS §180).

    python3 tools/cost_check.py          선언과 실물을 맞댄다 — **네트워크 0 · 과금 0**
    python3 tools/cost_check.py --재다    AWS 에 물어 선언을 갱신한다 (**Cost Explorer $0.01**)
    python3 tools/cost_check.py --selftest 판별식이 살아 있나

★ **이 저장소는 코드·문서·인프라·CI·CSS·주석까지 다 재면서 돈만 안 쟀다.** 그리고 그
  사각이 이미 한 번 물었다 — §177 전까지 **꺼 둔 줄 알고 Bedrock 요청이 계속 나갔고 아무도
  안 울었다.** 목표가 「무과금 개인용 확장」 이므로 **과금 의존 자체가 빚**이고, 크레딧은
  그 빚을 갚는 동안의 유예다.

★ **관문이 과금이면 안 된다.** Cost Explorer API 는 **호출당 $0.01** 이라 `doctor` 가
  부를 수 없다 — 하루 열 번이면 월 $3 이고, **재는 자가 재려는 것을 늘린다.** 그래서
  평소에는 **선언만** 보고, 재는 것은 사람이 `--재다` 로 한다(기준선 지문과 같은 꼴).

★ **값은 잰 것만 적는다.** 2026-10-10 에 AWS 문서만 읽고 「Firehose 가 제일 나쁘다」 고
  단정했다가 재니까 **$0.0000** 이었다. 「없는 병에 관문을 세우지 않는다」(§133).

★ 밖 — **이 관문은 「지금 얼마 나가나」 를 안 본다.** 선언이 마지막으로 잰 값을 볼 뿐이고,
  그래서 선언이 낡으면 **「맞다」 가 아니라 「모른다」** 로 끝난다(종료 코드 2, DECISIONS §59).
★ 밖 — **「그 값이 옳은가」 는 안 묻는다.** AWS 가 준 수를 그대로 든다.
★ 밖 — **IAM·VPC 같은 과금 없는 자원은 안 센다.** 서비스 이름을 못 붙이는 자원도 안 본다 —
  그 목록이 `_모름` 이고, 거기 든 것은 **이 관문의 사각**이다.

★ **종료 코드가 상태를 든다**(DECISIONS §127).
    0  선언과 실물이 맞고 임계 아래다
    1  흠이 있다
    2  **못 쟀다** — 선언이 낡았거나 읽을 수 없다. 통과로 세지 않는다
"""
from __future__ import annotations

import datetime as _d
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
선언파일 = ROOT / "tools" / "cost.json"

# ★ **terraform 자원 → AWS 가 청구서에 쓰는 서비스 이름.** 청구서 쪽 이름을 쓴다 —
#   선언의 열쇠가 Cost Explorer 가 돌려주는 글자와 같아야 `--재다` 가 덮어쓸 수 있다.
# ★ **값이 `None` 이면 「과금 없음」 이다** — IAM 처럼 세지 않는 자원이다.
자원서비스 = {
    "aws_dynamodb_table": "Amazon DynamoDB",
    "aws_lambda_function": "AWS Lambda",
    "aws_lambda_function_url": "AWS Lambda",
    "aws_s3_bucket": "Amazon Simple Storage Service",
    "aws_s3_bucket_versioning": "Amazon Simple Storage Service",
    "aws_s3_bucket_lifecycle_configuration": "Amazon Simple Storage Service",
    "aws_kinesis_firehose_delivery_stream": "Amazon Kinesis Firehose",
    "aws_glue_catalog_database": "AWS Glue",
    "aws_glue_catalog_table": "AWS Glue",
    "aws_cloudwatch_log_group": "AmazonCloudWatch",
    "aws_cloudwatch_log_stream": "AmazonCloudWatch",
    "aws_cloudwatch_log_subscription_filter": "AmazonCloudWatch",
    "aws_secretsmanager_secret": "AWS Secrets Manager",
    "aws_secretsmanager_secret_version": "AWS Secrets Manager",
    "aws_athena_workgroup": "Amazon Athena",
    # ── 과금 없음 ──────────────────────────────────────────────
    "aws_iam_role": None,
    "aws_iam_role_policy": None,
    "aws_iam_policy": None,
    "aws_iam_openid_connect_provider": None,
}

_자원 = re.compile(r'^resource\s+"([a-z0-9_]+)"\s+"([^"]+)"', re.M)


def _보일(p: pathlib.Path) -> str:
    """저장소 안이면 상대 경로로. **밖이면 그냥 그대로** — 시험이 tmp 로 갈아 끼운다."""
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def 선언(파일: pathlib.Path | None = None) -> dict:
    """`tools/cost.json`. 못 읽으면 빈 dict — **그러면 아래가 「못 쟀다」 로 끝난다.**"""
    try:
        return json.loads((파일 or 선언파일).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def 자원들(root: pathlib.Path | None = None) -> list[tuple[str, str]]:
    """`infra/*.tf` 의 (자원종류, 이름). **손 목록을 안 만든다** — 실물에서 뽑는다."""
    d = (root or ROOT) / "infra"
    out: list[tuple[str, str]] = []
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.tf")):
        out += _자원.findall(f.read_text(encoding="utf-8"))
    return out


def 쓰는서비스(자원: list[tuple[str, str]]) -> tuple[set[str], list[str]]:
    """(terraform 이 세우는 과금 서비스, 이름을 못 붙인 자원 종류).

    ★ **모르는 자원 종류를 조용히 넘기지 않는다.** 넘기면 새 과금 자원이 생겨도
      이 관문이 **아무 말 없이 초록**이다 — 그것이 §21 의 모양이다.
    """
    본것: set[str] = set()
    모름: list[str] = []
    for 종류, _이름 in 자원:
        if 종류 not in 자원서비스:
            if 종류 not in 모름:
                모름.append(종류)
            continue
        svc = 자원서비스[종류]
        if svc:
            본것.add(svc)
    return 본것, sorted(모름)


def 날(s: str) -> _d.date:
    return _d.date.fromisoformat(s)


def 흠(선언값: dict, 세우는것: set[str], 모름: list[str],
       오늘: _d.date | None = None) -> tuple[list[str], list[str]]:
    """`(막을 것, 알릴 것)`. **순수 함수다** — 네트워크도 파일도 안 읽는다."""
    오늘 = 오늘 or _d.date.today()
    막 : list[str] = []
    알 : list[str] = []

    서비스 = 선언값.get("서비스") or {}
    if not 서비스:
        return ["선언에 서비스가 하나도 없다"], []

    # ── 선언이 낡았나 ──────────────────────────────────────────
    잰날 = 선언값.get("잰날")
    낡음 = int(선언값.get("낡음일수") or 30)
    if not 잰날:
        막.append("선언에 `잰날` 이 없다 — 언제 잰 값인지 모르면 그 값은 못 쓴다")
    else:
        지남 = (오늘 - 날(잰날)).days
        if 지남 > 낡음:
            알.append(f"선언이 {지남}일 됐다(바닥 {낡음}) — `--재다` 로 다시 잰다. "
                      "**낡은 값은 「맞다」 가 아니라 「모른다」 다**")

    # ── 선언 밖의 자원 ────────────────────────────────────────
    for svc in sorted(세우는것 - set(서비스)):
        막.append(f"`{svc}` 가 terraform 에 서 있는데 `tools/cost.json` 에 없다 — "
                  "선언하지 않은 자원은 과금이 나도 아무도 안 본다")
    for 종류 in 모름:
        막.append(f"자원 종류 `{종류}` 에 서비스 이름이 안 붙어 있다 — "
                  "`cost_check.자원서비스` 에 더한다(과금이 없으면 `None`)")

    # ── terraform 밖에서 과금되는 것 ──────────────────────────
    # ★ 2026-10-10 에 `AWS Secrets Manager` 가 그랬다. `deploy_drift` 도 `check_infra` 도
    #   **IaC 안만** 보므로 손으로 만든 과금 자원은 어느 자도 못 본다(DECISIONS §180).
    for 이름, s in sorted(서비스.items()):
        갈 = s.get("자원")
        if 갈 not in ("세운다", "부른다"):
            막.append(f"`{이름}` 에 `자원` 칸이 없다 — "
                      "자원을 **세우는** 서비스인지 **부르는** 서비스인지 적는다")
            continue
        # ★ **부르는 서비스는 terraform 에 없는 것이 정상이다.** 첫 판이 이 가지 없이
        #   돌았고 Bedrock · Athena 를 「손으로 만든 자원」 으로 물었다 — **거짓 양성 둘**.
        if 갈 == "세운다" and float(s.get("월") or 0) > 0 and 이름 not in 세우는것:
            알.append(f"`{이름}` 이 과금되는데 terraform 에 자원이 없다 — "
                      "손으로 만든 자원이다. 지우거나 IaC 로 들인다")

    # ── 임계 ─────────────────────────────────────────────────
    임계 = 선언값.get("임계") or {}
    합 = sum(float(s.get("월") or 0) for s in 서비스.values())
    경고 = float(임계.get("월경고") or 0)
    막음 = float(임계.get("월막음") or 0)
    if 막음 and 합 > 막음:
        막.append(f"월 ${합:.4f} 가 바닥 ${막음:.2f} 를 넘었다")
    elif 경고 and 합 > 경고:
        알.append(f"월 ${합:.4f} 가 경고선 ${경고:.2f} 를 넘었다")

    # ── 유예 ─────────────────────────────────────────────────
    유예 = 선언값.get("유예") or {}
    경고일 = int(임계.get("유예경고일") or 30)
    for 열쇠, 말 in (("무료플랜끝", "무료 플랜이 끝난다 — 유료로 올리지 않으면 계정이 어떻게 되는지 AWS 가 안 적는다"),
                     ("크레딧만료", "크레딧이 만료된다 — 그 뒤는 전부 네 돈이다")):
        v = 유예.get(열쇠)
        if not v:
            continue
        남 = (날(v) - 오늘).days
        if 남 < 0:
            막.append(f"{열쇠} {v} 가 지났다 — {말}")
        elif 남 <= 경고일:
            알.append(f"{열쇠} D-{남} ({v}) — {말}")
    return 막, 알


def _canary() -> None:
    """★ **판별식이 사나.** `흠` 이 아무것도 못 꺼내면 **과금 자원이 몇 개든 0건**이 되고,
    그러면 이 관문은 **꺼진 채 초록**이다 — §177 을 만든 모양 그대로다."""
    오늘 = _d.date(2026, 10, 10)
    합성 = {"잰날": "2026-10-10", "낡음일수": 30,
            "임계": {"월경고": 5.0, "월막음": 20.0, "유예경고일": 30},
            "유예": {"크레딧만료": "2027-08-27"},
            "서비스": {"Amazon DynamoDB": {"월": 0.001, "갈래": "과금", "자원": "세운다"}}}
    if 흠(합성, {"Amazon DynamoDB"}, [], 오늘) != ([], []):
        print("    ★ 카나리아가 죽었다 — 맞는 선언을 흠으로 본다")
        sys.exit(2)
    막, _ = 흠(합성, {"Amazon DynamoDB", "새서비스"}, [], 오늘)
    if not any("새서비스" in x for x in 막):
        print("    ★ 카나리아가 죽었다 — 선언 밖 자원을 못 잡는다")
        sys.exit(2)


# ── 재다 (사람이 손으로. Cost Explorer 를 부르므로 $0.01) ──────────────────

def _aws(args: list[str]) -> dict | None:
    r = subprocess.run(["aws", *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    aws {' '.join(args[:3])} … 실패 — {(r.stderr or '').strip().splitlines()[-1:]}" )
        return None
    try:
        return json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return None


def 재다() -> int:
    """★ **이 자리만 네트워크를 쓴다.** `doctor` 는 절대 여기 안 들어온다."""
    오늘 = _d.date.today()
    맨앞 = (오늘.replace(day=1) - _d.timedelta(days=1)).replace(day=1)
    것 = _aws(["ce", "get-cost-and-usage", "--region", "us-east-1",
               "--time-period", f"Start={맨앞},End={오늘}", "--granularity", "MONTHLY",
               "--metrics", "UnblendedCost",
               "--group-by", "Type=DIMENSION,Key=SERVICE",
               # ★ **크레딧을 빼야 「크레딧이 없으면 얼마 나가나」 가 보인다**(DECISIONS §180).
               #   안 빼면 크레딧이 끝날 때까지 0원으로 보이다가 그날 갑자기 뜬다.
               "--filter", '{"Not":{"Dimensions":{"Key":"RECORD_TYPE",'
                           '"Values":["Credit","Refund"]}}}',
               "--output", "json"])
    if not 것:
        print("Cost Explorer 를 못 읽었다 — `aws login` 과 `ce:GetCostAndUsage` 권한을 본다")
        return 2
    달들 = 것.get("ResultsByTime") or []
    최근 = 달들[-1] if 달들 else {}
    잰것 = {g["Keys"][0]: round(float(g["Metrics"]["UnblendedCost"]["Amount"]), 4)
            for g in (최근.get("Groups") or [])}

    d = 선언()
    서비스 = d.setdefault("서비스", {})
    for 이름, 값 in sorted(잰것.items()):
        칸 = 서비스.setdefault(이름, {"갈래": "과금", "프리티어": "모름", "상환": "미정",
                                      "_note": "`--재다` 가 새로 보았다. 갈래와 상환을 손으로 적는다"})
        칸["월"] = 값
    d["잰날"] = 오늘.isoformat()
    선언파일.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{최근.get('TimePeriod', {}).get('Start', '?')} 기준으로 {len(잰것)}개 서비스를 적었다 "
          f"— {_보일(선언파일)}")
    for 이름, 값 in sorted(잰것.items(), key=lambda x: -x[1]):
        print(f"    {이름:<40} ${값:.4f}")
    return 0


def main() -> int:
    _canary()
    if "--selftest" in sys.argv[1:]:
        print("  프로브 살아 있다 — 맞는 선언 · 선언 밖 자원을 합성으로 묻는다")
        return 0
    if "--재다" in sys.argv[1:]:
        return 재다()

    d = 선언()
    if not d:
        print(f"{_보일(선언파일)} 를 못 읽었다 — **못 쟀다는 뜻이지 통과가 아니다**")
        return 2
    세우는것, 모름 = 쓰는서비스(자원들())
    막, 알 = 흠(d, 세우는것, 모름)
    합 = sum(float(s.get("월") or 0) for s in (d.get("서비스") or {}).values())
    for x in 알:
        print(f"    · {x}")
    if 막:
        print(f"과금 선언에 흠 {len(막)}건 — 월 ${합:.4f} (잰날 {d.get('잰날', '?')})")
        for x in 막:
            print(f"    {x}")
        return 1
    낡음 = any("일 됐다" in x for x in 알)
    print(f"과금 선언이 실물과 맞는다 — 월 ${합:.4f} · 서비스 {len(d.get('서비스') or {})}개 "
          f"(잰날 {d.get('잰날', '?')})")
    return 2 if 낡음 else 0


if __name__ == "__main__":
    sys.exit(main())
