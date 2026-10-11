#!/usr/bin/env python3
"""**과금을 재는 자가 없었다**(DECISIONS §180).

    python3 tools/cost_check.py            선언과 실물을 맞댄다 — **네트워크 0 · 과금 0**
    python3 tools/cost_check.py --재다      AWS 에 묻는다 — **공짜 경로만**(§181)
    python3 tools/cost_check.py --서비스별  서비스별 달러. **Cost Explorer 호출당 $0.01**
    python3 tools/cost_check.py --selftest  판별식이 살아 있나

★ **이 저장소는 코드·문서·인프라·CI·CSS·주석까지 다 재면서 돈만 안 쟀다.** 그리고 그
  사각이 이미 한 번 물었다 — §177 전까지 **꺼 둔 줄 알고 Bedrock 요청이 계속 나갔고 아무도
  안 울었다.** 목표가 「무과금 개인용 확장」 이므로 **과금 의존 자체가 빚**이고, 크레딧은
  그 빚을 갚는 동안의 유예다.

★ **관문이 과금이면 안 된다.** Cost Explorer API 는 **호출당 $0.01** 이라 `doctor` 가
  부를 수 없다 — 하루 열 번이면 월 $3 이고, **재는 자가 재려는 것을 늘린다.** 그래서
  평소에는 **선언만** 보고, 재는 것은 사람이 `--재다` 로 한다(기준선 지문과 같은 꼴).

★ **그런데 `--재다` 자체가 과금이었다**(DECISIONS §181). 「재는 것은 사람이 한다」 로
  막아 둔 것은 **빈도**일 뿐이고, 목표가 「무과금」 인 저장소에 **$0.01 짜리 측정자**가
  서 있는 것은 그대로 빚이다. 2026-10-11 에 공짜 경로를 재서 갈라 두었다 —

    `cloudwatch list-metrics --namespace AWS/Billing`  어느 서비스가 **돈이 걸렸나**
                                                       (실측 13개. CE 의 group-by 보다 넓다)
    `cloudwatch get-metric-statistics  EstimatedCharges`  **크레딧 적용 후** 총액
    `billing get-credits`                                 남은 크레딧과 만료일

  셋 다 CloudWatch 무료 API 요청 100만 안이고 `billing` 은 과금이 없다. 달러의
  **서비스별 쪼개기만** 유료라, 그것을 `--서비스별` 로 떼어 냈다.

★ **`EstimatedCharges` 는 달러로 못 쓴다 — 신호로 쓴다.** 2026-10-11 02:31·08:31 두
  데이터포인트가 **둘 다 0.0** 인데 콘솔은 같은 달을 **$0.05** 로 적었다. 갈렸고, 갈린
  쪽이 이 지표다 — **크레딧 적용 후**를 준다. 그래서 **`0 이다` = 「크레딧이 아직 덮고
  있다」** 이고, **0 이 아니게 되는 날이 내 돈이 나가기 시작한 날**이다. 공짜 조기경보다.

★ **계정 번호는 이 모듈이 유일하게 손에 쥔다.** `billing get-credits` 가 `--account-id`
  를 **요구한다**(botocore `billing/2023-09-07` 서비스 모델). 쥐는 손 옆에 관문을 둔다 —
  `계정흠` 이 추적 파일 전체에서 12자리를 찾아 문다(§131).

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

★ **「못 쟀다」 를 글자로 찾지 않는다.** 179 판은 `main` 에서 `any("일 됐다" in x for x
  in 알)` 로 알림 문구를 되읽어 종료 코드를 정했다 — **글을 코드로 읽는 자**가 하나 더
  있었던 것이고(§168 집안), 문구를 다듬으면 조용히 0 이 된다. `흠` 이 이제
  `(막, 알, 못쟀다)` 세 묶음을 돌려주고 종료 코드는 묶음을 센다.
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

# ★ **CloudWatch `AWS/Billing` 쪽 짧은 이름 → 청구서(= Cost Explorer) 쪽 이름.**
#   공짜 경로가 돌려주는 글자와 선언의 열쇠가 다르다. 그 사이를 여기서 잇는다.
# ★ **모르는 이름은 넘기지 않는다.** 넘기면 **새 과금 서비스가 붙어도 초록**이다(§21).
# ★ 2026-10-11 실측 13개. `list-metrics` 는 **지난 2주 안에 지표를 낸 것**만 돌려주므로
#   이 목록이 곧 「지금 돈이 걸린 표면」 이다 — terraform 에도 CE 에도 안 보이는 것이 섞여
#   있었다(KMS · 데이터 전송 · SQS · SNS · Marketplace).
청구별칭 = {
    "AmazonBedrock": "Amazon Bedrock",
    "AmazonS3": "Amazon Simple Storage Service",
    "AmazonDynamoDB": "Amazon DynamoDB",
    "AWSLambda": "AWS Lambda",
    "AWSGlue": "AWS Glue",
    "AmazonCloudWatch": "AmazonCloudWatch",
    "AmazonKinesisFirehose": "Amazon Kinesis Firehose",
    "AWSSecretsManager": "AWS Secrets Manager",
    "AmazonAthena": "Amazon Athena",
    "AWSDataTransfer": "AWS Data Transfer",
    "awskms": "AWS Key Management Service",
    "AWSQueueService": "Amazon Simple Queue Service",
    "AmazonSNS": "Amazon Simple Notification Service",
    "AWSMarketplace": "AWS Marketplace",
}

# ── DynamoDB 무료 용량 ────────────────────────────────────────────────────
# ★ **요청 프리티어는 `PROVISIONED` 에만 붙는다.** 온디맨드(`PAY_PER_REQUEST`)에는
#   요청 무료분이 아예 없어서 **월 $0.001 이 영구히 깔린다** — 「거의 0」 은 0 이 아니다.
#   25 WCU · 25 RCU 는 **계정·리전마다** 주는 몫이고 테이블들이 나눠 쓴다. 그래서 합을 센다.
# ★ **넘치면 조르는 것이 답이다.** 자동 확장을 붙이면 25 를 넘겨 과금되므로 금지한다 —
#   조름은 재번역(시간)이고 과금은 돈이다(DECISIONS §181).
무료용량 = 25
금지자원 = {
    "aws_appautoscaling_target":
        "자동 확장 대상이 붙으면 25 를 **넘겨서** 과금된다 — 넘치면 조르는 쪽으로 진다",
    "aws_appautoscaling_policy":
        "자동 확장 정책이 붙으면 25 를 **넘겨서** 과금된다 — 넘치면 조르는 쪽으로 진다",
    "aws_dynamodb_table_replica":
        "글로벌 테이블은 리전마다 쓰기를 다시 센다 — 무료 25 는 리전 하나 몫이다",
}

_자원 = re.compile(r'^resource\s+"([a-z0-9_]+)"\s+"([^"]+)"', re.M)
_자원줄 = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"([^"]+)"')
_머리 = re.compile(
    r"^(resource|data|module|variable|output|locals|provider|terraform)\b.*$", re.M)
_용량 = re.compile(r"\b(read|write)_capacity\s*=\s*([0-9]+)")
_모드 = re.compile(r'\bbilling_mode\s*=\s*"([A-Z_]+)"')
# ★ **12자리 계정 번호.** 양쪽을 **숫자·글자가 아닌 것**으로 묶는다 — 묶지 않으면
#   sha256 지문과 잠금 파일 속 16진수에 전부 걸린다(2026-10-11 에 재서 갈랐다 : 느슨한
#   식은 20줄 넘게 물었고 묶은 식은 **문서 예시 둘만** 남았다).
_계정 = re.compile(r"(?<![0-9A-Za-z])[0-9]{12}(?![0-9A-Za-z])")
# ★ AWS 문서가 예시로 쓰는 번호만 허용한다. **손 목록이지만 짧고, 늘리는 것이 곧 심사다.**
문서계정 = {"123456789012", "111122223333"}


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


def 자원블록들(root: pathlib.Path | None = None) -> list[tuple[str, str, str]]:
    """`infra/*.tf` 의 (자원종류, 이름, 블록 본문). **손 목록을 안 만든다.**

    ★ **중괄호를 세지 않는다.** 주석도 문자열도 중괄호를 들 수 있고, 그것을 가리려면
      HCL 파서가 필요하다. 대신 **다음 최상위 선언까지**를 한 블록으로 자른다 —
      `resource` · `data` · `module` 같은 머리말은 **반드시 0열에서 시작**하기 때문이다.
      넉넉하게 자르므로 **놓치는 쪽이 아니라 더 보는 쪽으로 틀린다**.
    """
    d = (root or ROOT) / "infra"
    out: list[tuple[str, str, str]] = []
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.tf")):
        글 = f.read_text(encoding="utf-8")
        머리들 = list(_머리.finditer(글))
        for i, m in enumerate(머리들):
            r = _자원줄.match(m.group(0))
            if not r:
                continue
            끝 = 머리들[i + 1].start() if i + 1 < len(머리들) else len(글)
            out.append((r.group(1), r.group(2), 글[m.start():끝]))
    return out


def 자원들(root: pathlib.Path | None = None) -> list[tuple[str, str]]:
    """`infra/*.tf` 의 (자원종류, 이름). `자원블록들` 에서 본문만 떼어 낸다."""
    return [(종류, 이름) for 종류, 이름, _본문 in 자원블록들(root)]


def 용량흠(블록들: list[tuple[str, str, str]]) -> list[str]:
    """DynamoDB 가 **구조적으로** 0원인가. **순수 함수다.**

    ★ **「거의 0」 은 0 이 아니다.** `PAY_PER_REQUEST` 는 요청 무료분이 없어 월 $0.001 이
      영구히 깔린다 — 측정 아래라서 안 보이는 것이지 없는 것이 아니다(DECISIONS §181).
    ★ **25 는 계정·리전 몫이라 테이블이 나눠 쓴다.** 그래서 테이블 하나씩이 아니라
      **합**을 센다 — 수집 적재지로 두 번째 테이블이 붙는 것이 다음 패치다(PLAN #70).
    """
    fails: list[str] = []
    표 = [(이름, 본문) for 종류, 이름, 본문 in 블록들 if 종류 == "aws_dynamodb_table"]
    for 종류, 이름, _본문 in 블록들:
        if 종류 in 금지자원:
            fails.append(f"`{종류}` `{이름}` 이 서 있다 — {금지자원[종류]}")
    if not 표:
        return fails
    합 = {"read": 0, "write": 0}
    for 이름, 본문 in 표:
        m = _모드.search(본문)
        if not m:
            fails.append(f"테이블 `{이름}` 에 `billing_mode` 가 안 적혀 있다 — "
                         "terraform 의 기정값에 맡기면 무엇이 무료인지 글로 안 남는다")
            continue
        if m.group(1) != "PROVISIONED":
            fails.append(
                f"테이블 `{이름}` 이 `{m.group(1)}` 이다 — **요청 프리티어는 "
                "`PROVISIONED` 에만 붙는다**(실측 월 $0.001). 온디맨드는 영구히 0 이 아니다")
            continue
        것 = _용량.findall(본문)
        if not 것:
            fails.append(f"테이블 `{이름}` 이 `PROVISIONED` 인데 용량이 안 적혀 있다")
            continue
        for 갈, 값 in 것:
            합[갈] += int(값)
    for 갈, 말 in (("read", "읽기 RCU"), ("write", "쓰기 WCU")):
        if 합[갈] > 무료용량:
            fails.append(f"{말} 합이 {합[갈]} 이다 — 무료 몫 {무료용량} 를 넘는다. "
                         "25 는 **계정·리전마다** 주는 몫이고 테이블들이 나눠 쓴다")
    return fails


def 계정흠(파일글: dict[str, str]) -> list[str]:
    """추적 파일에서 **12자리 계정 번호**를 찾는다(§131). **순수 함수다.**

    ★ **이 모듈이 계정 번호를 손에 쥔다.** `billing get-credits` 가 `--account-id` 를
      요구하므로(botocore 서비스 모델) `--재다` 가 `sts get-caller-identity` 로 그것을
      읽는다. 쥔 것을 **어디에도 적지 않는다**는 약속을 사람의 기억에 맡기지 않는다.
    ★ 밖 — **커밋 메시지와 이슈는 여기서 못 본다.** 파일만 본다.
    """
    fails: list[str] = []
    for 경로 in sorted(파일글):
        for 번호 in sorted(set(_계정.findall(파일글[경로]))):
            if 번호 in 문서계정:
                continue
            fails.append(f"{경로} 에 12자리 번호가 있다 — 계정 번호는 저장소에 안 들어온다"
                         f"(§131). 문서 예시라면 {' · '.join(sorted(문서계정))} 를 쓴다")
    return fails


def 추적파일글(root: pathlib.Path | None = None) -> dict[str, str]:
    """`git ls-files` 가 든 텍스트 파일만. 못 읽으면 **빈 dict** — 그러면 「못 쟀다」 다."""
    d = root or ROOT
    try:
        r = subprocess.run(["git", "ls-files", "-z"], cwd=d,
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if r.returncode != 0:
        return {}
    out: dict[str, str] = {}
    for 이름 in r.stdout.split("\0"):
        if not 이름:
            continue
        p = d / 이름
        try:
            out[이름] = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue          # 바이너리와 사라진 파일은 글이 아니다
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
       오늘: _d.date | None = None) -> tuple[list[str], list[str], list[str]]:
    """`(막을 것, 알릴 것, 못 쟀다)`. **순수 함수다** — 네트워크도 파일도 안 읽는다.

    ★ **세 묶음인 까닭**(DECISIONS §181) : 179 판은 두 묶음이었고 `main` 이
      `any("일 됐다" in x for x in 알)` 로 **알림 문구를 되읽어** 종료 코드를 정했다.
      문구를 다듬으면 조용히 0 이 되는 자리였다 — 「글을 코드로 읽는 검사」 집안(§168).
    """
    오늘 = 오늘 or _d.date.today()
    막 : list[str] = []
    알 : list[str] = []
    못 : list[str] = []

    서비스 = 선언값.get("서비스") or {}
    if not 서비스:
        return ["선언에 서비스가 하나도 없다"], [], []

    # ── 선언이 낡았나 ──────────────────────────────────────────
    잰날 = 선언값.get("잰날")
    낡음 = int(선언값.get("낡음일수") or 30)
    if not 잰날:
        막.append("선언에 `잰날` 이 없다 — 언제 잰 값인지 모르면 그 값은 못 쓴다")
    else:
        지남 = (오늘 - 날(잰날)).days
        if 지남 > 낡음:
            못.append(f"선언이 {지남}일 됐다(바닥 {낡음}) — `--재다` 로 다시 잰다. "
                      "**낡은 값은 「맞다」 가 아니라 「모른다」 다**")

    # ── 청구 지표 — **공짜로 재는 「돈이 걸린 표면」** ──────────
    # ★ terraform 에도 CE 에도 안 보이는 서비스가 여기 뜬다. 2026-10-11 에 다섯 개가
    #   그랬다 — KMS · 데이터 전송 · SQS · SNS · Marketplace(DECISIONS §181).
    지표 = 선언값.get("청구지표") or {}
    # ★ **빈 목록은 「하나도 안 걸렸다」 이고 없는 칸은 「안 재 봤다」 다** — 다른 말이다(§59).
    if "서비스" not in 지표:
        못.append("`청구지표` 가 선언에 없다 — `--재다` 가 공짜로 채운다")
    else:
        for 짧은 in sorted(지표["서비스"]):
            if 짧은 not in 청구별칭:
                막.append(f"청구 지표의 `{짧은}` 에 청구서 이름이 안 붙어 있다 — "
                          "`cost_check.청구별칭` 에 더한다")
                continue
            긴 = 청구별칭[짧은]
            if 긴 and 긴 not in 서비스:
                막.append(f"`{긴}` 이 청구 지표에 뜨는데 `tools/cost.json` 에 없다 — "
                          "terraform 밖에서 돈이 걸린 서비스다")

    # ── 덮임 — `EstimatedCharges` 는 **크레딧 적용 후**다 ──────
    덮임 = 선언값.get("덮임") or {}
    if "값" not in 덮임:
        못.append("`덮임` 이 선언에 없다 — `EstimatedCharges` 를 공짜로 재서 적는다")
    elif float(덮임.get("값") or 0) > 0:
        막.append(f"`EstimatedCharges` 가 ${float(덮임['값']):.4f} 다 — "
                  "**크레딧이 더는 덮지 않는다. 지금부터 나가는 것은 네 돈이다**")

    # ── 크레딧 ────────────────────────────────────────────────
    크레딧 = 선언값.get("크레딧") or {}
    if 크레딧.get("남은것") is None:
        못.append("`크레딧` 이 선언에 없다 — `billing get-credits` 는 **공짜**다")
    elif float(크레딧["남은것"]) <= 0:
        막.append("크레딧이 바닥났다 — 지금부터 나가는 것은 전부 네 돈이다")

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
        # ★ **「아직 안 쟀다」 는 0 이 아니다**(§59). 179 판은 `월` 이 없으면 0 으로 읽어
        #   합에 보태지 않았다 — **안 잰 것이 싼 것으로 보이는** 자리였다.
        # ★ **그런데 181 은 그 둘을 다시 한 말로 뭉갰다**(DECISIONS §182). 「달러를 못
        #   쟀다」 와 「갈래를 안 정했다」 는 **다른 상태이고 할 일이 다르다** — 앞은 재는
        #   일(기계)이고 뒤는 정하는 일(사람)이다. `AWS Cost Explorer` 가 **$0.02 로
        #   멀쩡히 재져 있는데** 관문이 「달러를 못 쟀다」 고 말하고 있었다.
        if s.get("월") is None:
            못.append(f"`{이름}` 의 달러를 못 쟀다 — `--서비스별` 이 채운다($0.01)")
            continue
        if s.get("갈래") == "모름":
            못.append(f"`{이름}` 의 갈래를 안 정했다 — 달러는 ${float(s['월']):.4f} 로 재져 "
                      "있다. `tools/cost.json` 에 **사람이** 적는다(과금|항상무료)")
            continue
        # ★ **잰 달이 안 적힌 수는 읽을 수 없다.** 179 의 선언에는 9월 값과 10월 값이
        #   섞여 있었고 어느 것이 어느 달인지 적힌 곳이 없었다(DECISIONS §181).
        if float(s.get("월") or 0) > 0 and not s.get("잰달"):
            막.append(f"`{이름}` 에 `잰달` 이 없다 — 어느 달 값인지 모르면 못 읽는 수다")
        # ★ **부르는 서비스는 terraform 에 없는 것이 정상이다.** 첫 판이 이 가지 없이
        #   돌았고 Bedrock · Athena 를 「손으로 만든 자원」 으로 물었다 — **거짓 양성 둘**.
        if 갈 == "세운다" and float(s.get("월") or 0) > 0 and 이름 not in 세우는것:
            알.append(f"`{이름}` 이 과금되는데 terraform 에 자원이 없다 — "
                      "손으로 만든 자원이다. 지우거나 IaC 로 들인다")

    # ── 달이 섞인 합은 거짓이다 ───────────────────────────────
    # ★ **181 은 「잰달」 로 섞임을 *보이게* 만들었고 섞임 자체는 안 고쳤다**(§182).
    #   `--서비스별` 이 **CE 가 돌려준 것만** 갱신했으므로, CE 가 생략한 서비스는
    #   **옛 달 값을 그대로 든 채 합계에 들어갔다.** 2026-10-11 에 그것이 났다 —
    #   열다섯은 10월이고 `Amazon Athena` 만 9월이었고, 합 $0.0737 의 꼬리 $0.0003 이
    #   그것이다. **달이 다른 수를 더하면 임계 판정 자체가 뜻을 잃는다.**
    달들 = {s.get("잰달") for s in 서비스.values() if s.get("잰달")}
    if len(달들) > 1:
        어느 = {}
        for 이름, s in 서비스.items():
            if s.get("잰달"):
                어느.setdefault(s["잰달"], []).append(이름)
        적은쪽 = min(어느, key=lambda m: len(어느[m]))
        막.append(f"잰 달이 섞였다 — {' · '.join(sorted(달들))}. "
                  f"합계가 달이 다른 수를 더하고 있다. 적은 쪽은 {적은쪽} "
                  f"({' · '.join(sorted(어느[적은쪽]))})")

    # ── 임계 ─────────────────────────────────────────────────
    임계 = 선언값.get("임계") or {}
    합 = sum(float(s.get("월") or 0) for s in 서비스.values())
    # ★ **진행 중인 달의 합은 월 합이 아니다**(DECISIONS §182). 2026-10-11 의 $0.0737 은
    #   달의 1/3 이고, 그것을 월 임계와 맞대면 **과소 평가**다. 달 끝까지 늘려서 묻는다.
    # ★ **그래도 늘 짖지는 않는다.** 「진행 중이다」 는 그 달 내내 참이라, 알림으로 내면
    #   **한 달 중 서른 날이 `·` 한 줄**이다 — 그러면 `·` 를 안 읽게 된다(§46 · §133).
    #   임계를 **넘길 때만** 말하고, 그때 늘려 쟀다는 것을 같이 적는다.
    진행중 = 달들 == {오늘.strftime("%Y-%m")} and 오늘.day > 0
    끝까지 = 합 / 오늘.day * 30 if 진행중 else 합
    꼬리 = (f" (잰 달이 진행 중이라 {오늘.day}일째 ${합:.4f} 를 달 끝까지 늘렸다)"
            if 진행중 else "")
    경고 = float(임계.get("월경고") or 0)
    막음 = float(임계.get("월막음") or 0)
    if 막음 and 끝까지 > 막음:
        막.append(f"월 ${끝까지:.4f} 가 바닥 ${막음:.2f} 를 넘었다{꼬리}")
    elif 경고 and 끝까지 > 경고:
        알.append(f"월 ${끝까지:.4f} 가 경고선 ${경고:.2f} 를 넘었다{꼬리}")

    # ── 유예 ─────────────────────────────────────────────────
    # ★ **크레딧 만료일을 두 곳에 안 적는다**(§91). 179 의 선언은 `유예.크레딧만료` 와
    #   측정값을 따로 들고 있었고, 그러면 **사람이 둘을 맞춰야** 한다. 만료일은
    #   `크레딧` 블록이 정본이고 여기서 읽어 쓴다 — `--재다` 가 그 한 곳만 갱신한다.
    유예 = dict(선언값.get("유예") or {})
    if 크레딧.get("만료"):
        유예["크레딧만료"] = 크레딧["만료"]
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
    return 막, 알, 못


def _canary() -> None:
    """★ **판별식이 사나.** `흠` 이 아무것도 못 꺼내면 **과금 자원이 몇 개든 0건**이 되고,
    그러면 이 관문은 **꺼진 채 초록**이다 — §177 을 만든 모양 그대로다."""
    오늘 = _d.date(2026, 10, 10)
    합성 = {"잰날": "2026-10-10", "낡음일수": 30,
            "임계": {"월경고": 5.0, "월막음": 20.0, "유예경고일": 30},
            "유예": {}, "덮임": {"값": 0.0},
            "크레딧": {"남은것": 139.84, "만료": "2027-08-27"},
            "청구지표": {"서비스": ["AmazonDynamoDB"]},
            "서비스": {"Amazon DynamoDB": {"월": 0.001, "잰달": "2026-10",
                                            "갈래": "과금", "자원": "세운다"}}}
    if 흠(합성, {"Amazon DynamoDB"}, [], 오늘) != ([], [], []):
        print("    ★ 카나리아가 죽었다 — 맞는 선언을 흠으로 본다")
        sys.exit(2)
    막, _, _ = 흠(합성, {"Amazon DynamoDB", "새서비스"}, [], 오늘)
    if not any("새서비스" in x for x in 막):
        print("    ★ 카나리아가 죽었다 — 선언 밖 자원을 못 잡는다")
        sys.exit(2)
    # ★ **카나리아가 새 판별식까지 든다.** 들지 않으면 갈래가 늘어도 꺼진 줄 모른다.
    덮임 = dict(합성, 덮임={"값": 0.01})
    if not any("네 돈" in x for x in 흠(덮임, {"Amazon DynamoDB"}, [], 오늘)[0]):
        print("    ★ 카나리아가 죽었다 — 크레딧이 걷힌 것을 못 잡는다")
        sys.exit(2)
    if not 용량흠([("aws_dynamodb_table", "t", 'billing_mode = "PAY_PER_REQUEST"')]):
        print("    ★ 카나리아가 죽었다 — 온디맨드 테이블을 못 잡는다")
        sys.exit(2)
    # ★ **12자리를 글자로 적으면 이 파일이 제 관문에 걸린다** — 「글을 코드로 읽는
    #   검사는 글부터 지운다」 집안의 아홉 번째다(§168 · §180). **지어서** 먹인다.
    if not 계정흠({"x": "arn:aws:iam::" + "7" * 12 + ":root"}):
        print("    ★ 카나리아가 죽었다 — 계정 번호를 못 잡는다")
        sys.exit(2)
    # ★ 182 가 더한 두 판별식도 카나리아가 든다 — 들지 않으면 꺼진 줄 모른다.
    섞임 = dict(합성, 서비스=dict(
        합성["서비스"], **{"Amazon Athena": {"월": 0.0003, "잰달": "2026-09",
                                             "갈래": "과금", "자원": "부른다"}}))
    if not any("섞였다" in x for x in 흠(섞임, {"Amazon DynamoDB"}, [], 오늘)[0]):
        print("    ★ 카나리아가 죽었다 — 잰 달이 섞인 것을 못 잡는다")
        sys.exit(2)
    모름 = dict(합성, 서비스={"X": {"월": 0.02, "잰달": "2026-10",
                                    "갈래": "모름", "자원": "부른다"}})
    if not any("갈래를 안 정했다" in x for x in 흠(모름, set(), [], 오늘)[2]):
        print("    ★ 카나리아가 죽었다 — 안 정한 갈래를 못 잡는다")
        sys.exit(2)
    if 계정흠({"x": f"arn:aws:iam::{sorted(문서계정)[0]}:root"}):
        print("    ★ 카나리아가 죽었다 — 문서 예시 계정까지 문다")
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


def _날짜(v) -> _d.date | None:
    """AWS 가 주는 시각을 날짜로. **CLI 는 ISO 로, SDK 는 epoch 으로 준다.**"""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return _d.datetime.fromtimestamp(v, _d.timezone.utc).date()
    if isinstance(v, str):
        s = v.strip().replace("Z", "+00:00")
        try:
            return _d.datetime.fromisoformat(s).date()
        except ValueError:
            pass
        try:
            return _d.date.fromisoformat(s[:10])
        except ValueError:
            return None
    return None


def 크레딧파싱(것: dict | None) -> tuple[dict | None, str]:
    """`billing get-credits` → `{남은것, 만료, 센것}`. 꼴을 못 알아보면 `(None, 까닭)`.

    ★ **필드 이름을 짐작하지 않았다.** botocore 의 `billing/2023-09-07` 서비스 모델을
      읽어서 적었다 — `credits[].remainingAmount.currencyAmount`(**문자열**) ·
      `endDate`(timestamp) · `creditStatus`(`ENABLED`|`DISABLED`).
    ★ **못 알아본 꼴을 0 으로 쓰지 않는다.** 0 은 「크레딧이 없다」 라는 뜻이고 그러면
      이 관문이 막아 버린다 — 「못 쟀다」 와 「없다」 는 다른 말이다(§59).
    """
    목록 = (것 or {}).get("credits")
    if not isinstance(목록, list):
        return None, "`credits` 배열이 없다 — API 꼴이 바뀌었거나 권한이 없다"
    남, 끝, 센것 = 0.0, None, 0
    for c in 목록:
        if not isinstance(c, dict):
            continue
        if (c.get("creditStatus") or "ENABLED").upper() == "DISABLED":
            continue
        몫 = (c.get("remainingAmount") or {}).get("currencyAmount")
        if 몫 is None:
            return None, "`remainingAmount.currencyAmount` 가 없다 — API 꼴이 바뀌었다"
        try:
            남 += float(몫)
        except (TypeError, ValueError):
            return None, f"남은 금액을 수로 못 읽었다 — {몫!r}"
        d = _날짜(c.get("endDate"))
        if d and (끝 is None or d < 끝):
            끝 = d                      # **가장 먼저 만료되는 것**이 다음 절벽이다
        센것 += 1
    if not 센것:
        return None, "살아 있는 크레딧이 하나도 없다 — 0 인지 못 읽은 것인지 가른다"
    return {"남은것": round(남, 2), "만료": 끝.isoformat() if 끝 else None,
            "센것": 센것}, ""


def 계정번호() -> str | None:
    """`sts get-caller-identity` 의 `Account`. **어디에도 적지 않는다**(§131)."""
    것 = _aws(["sts", "get-caller-identity", "--output", "json"])
    번호 = (것 or {}).get("Account")
    return 번호 if isinstance(번호, str) and _계정.fullmatch(번호) else None


def 재다() -> int:
    """**공짜 경로만**(DECISIONS §181). 서비스별 달러는 `--서비스별` 이 한다.

    ★ 세 부름 다 무료다 — CloudWatch 는 월 100만 API 요청 안이고(무료에서 빠지는 것은
      `GetMetricData` 와 `GetMetricWidgetImage` 다) `billing` 은 과금 자체가 없다.
    """
    오늘 = _d.date.today()
    d = 선언()
    적음: list[str] = []

    # ① 어느 서비스가 **돈이 걸렸나**. terraform 도 CE 도 못 보는 것이 여기 뜬다.
    것 = _aws(["cloudwatch", "list-metrics", "--namespace", "AWS/Billing",
               "--metric-name", "EstimatedCharges", "--region", "us-east-1",
               "--output", "json"])
    if 것 is None:
        print("청구 지표를 못 읽었다 — `aws sso login` 과 `cloudwatch:ListMetrics` 를 본다")
        return 2
    이름들 = sorted({v.get("Value") for m in (것.get("Metrics") or [])
                     for v in (m.get("Dimensions") or [])
                     if v.get("Name") == "ServiceName" and v.get("Value")})
    d["청구지표"] = {
        "잰날": 오늘.isoformat(), "서비스": 이름들,
        "_note": "`cloudwatch list-metrics --namespace AWS/Billing`. **공짜다.** "
                 "지난 2주 안에 지표를 낸 서비스만 뜨므로 **「지금 돈이 걸린 표면」** 이고, "
                 "Cost Explorer 의 group-by 보다 넓다(2026-10-11 : 여기 13 · CE 9).",
    }
    적음.append(f"청구 지표 {len(이름들)}개")

    # ② **크레딧 적용 후** 총액. 달러로는 못 쓰고 **덮임 신호**로 쓴다.
    끝시각 = _d.datetime.now(_d.timezone.utc)
    것 = _aws(["cloudwatch", "get-metric-statistics", "--namespace", "AWS/Billing",
               "--metric-name", "EstimatedCharges",
               "--dimensions", "Name=Currency,Value=USD",
               "--statistics", "Maximum", "--period", "21600",
               "--start-time", (끝시각 - _d.timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "--end-time", 끝시각.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "--region", "us-east-1", "--output", "json"])
    점들 = sorted((것 or {}).get("Datapoints") or [], key=lambda p: str(p.get("Timestamp")))
    if not 점들:
        print("`EstimatedCharges` 에 데이터포인트가 없다 — 결제 기본 설정에서 "
              "**「CloudWatch 결제 알림 수신」** 을 켠다. 그 스위치가 이 지표를 켠다")
        return 2
    d["덮임"] = {
        "잰날": 오늘.isoformat(), "값": round(float(점들[-1].get("Maximum") or 0), 4),
        "잰시각": str(점들[-1].get("Timestamp")), "점": len(점들),
        "_note": "★ **크레딧 적용 *후* 다.** 2026-10-11 의 두 데이터포인트가 둘 다 0.0 인데 "
                 "콘솔은 같은 달을 $0.05 로 적었다 — 갈렸고, 갈린 쪽이 이 지표다. 그래서 "
                 "**달러로는 못 쓰고 「0 이다」 = 「크레딧이 아직 덮고 있다」 로 쓴다**. "
                 "0 이 아니게 되는 날이 **내 돈이 나가기 시작한 날**이다(DECISIONS §181).",
    }
    적음.append(f"덮임 ${d['덮임']['값']:.4f}")

    # ③ 크레딧. **계정 번호가 필요한 유일한 부름**이고, 그 번호는 아무 데도 안 적는다.
    번호 = 계정번호()
    if not 번호:
        print("계정 번호를 못 읽었다 — `sts get-caller-identity` 가 먼저다")
        return 2
    한해전 = (오늘 - _d.timedelta(days=364)).isoformat()
    블록, 까닭 = 크레딧파싱(_aws(["billing", "get-credits", "--region", "us-east-1",
                                  "--account-id", 번호, "--start-date", 한해전,
                                  "--output", "json"]))
    if not 블록:
        print(f"크레딧을 못 읽었다 — {까닭}")
        return 2
    블록["잰날"] = 오늘.isoformat()
    블록["_note"] = ("`aws billing get-credits`. **공짜 부름이다.** 남은 금액은 소진이 아니라 "
                    "**만료로 날아간다** — 그래서 목표는 「크레딧을 다 쓰자」 가 아니라 "
                    "**「덮고 있는 동안에 과금 의존을 끊자」** 다. `만료` 는 여기가 정본이고 "
                    "`유예.크레딧만료` 를 따로 안 적는다(§91).")
    d["크레딧"] = 블록
    적음.append(f"크레딧 ${블록['남은것']:.2f} (만료 {블록['만료']})")

    d["잰날"] = 오늘.isoformat()
    선언파일.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"공짜 경로로 {' · '.join(적음)} 를 적었다 — {_보일(선언파일)}")
    for 짧은 in 이름들:
        print(f"    {짧은:<28} {'' if 짧은 in 청구별칭 else '★ 청구별칭에 없다'}")
    return 0


def 서비스별() -> int:
    """★ **이 자리만 과금이다** — Cost Explorer 호출당 $0.01. `doctor` 는 안 들어온다."""
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
    잰달 = str(최근.get("TimePeriod", {}).get("Start", ""))[:7]
    for 이름, 값 in sorted(잰것.items()):
        칸 = 서비스.setdefault(이름, {"갈래": "모름", "프리티어": "모름", "상환": "미정",
                                      "자원": "부른다",
                                      "_note": "`--서비스별` 이 새로 보았다. 갈래와 상환을 손으로 적는다"})
        칸["월"] = 값
        # ★ **수와 잰 달을 같이 적는다.** 179 의 선언에는 9월 값과 10월 값이 섞여 있었고
        #   어느 것이 어느 달인지 적힌 곳이 없었다 — 읽을 수 없는 수였다(§181).
        칸["잰달"] = 잰달
    # ★ **CE 가 안 돌려준 것도 적는다 — 0 으로.**(DECISIONS §182)
    #   181 판은 **돌려준 것만** 갱신했고, 그래서 CE 가 생략한 서비스는 **옛 달 값을
    #   그대로 든 채 합계에 남았다** — 2026-10-11 에 `Amazon Athena` 가 9월 $0.0003 을
    #   들고 10월 합계에 섞였다.
    # ★ **「안 온다」 가 「모른다」 가 아닌 근거** : CE 는 그 달에 **쓴 적이 있으면**
    #   $0.0000 이라도 레코드를 준다(실측 : Glue · Lambda · KMS · SNS · SQS · Tax ·
    #   Firehose · CloudWatch 여덟이 0.0000 으로 **왔다**). 아예 안 오는 것은 **그 달에
    #   쓴 적이 없다**는 뜻이고, 쓴 적이 없으면 과금도 없다.
    빠진것 = [이름 for 이름 in 서비스 if 이름 not in 잰것]
    for 이름 in 빠진것:
        서비스[이름]["월"] = 0.0
        서비스[이름]["잰달"] = 잰달
        서비스[이름]["_빠짐"] = (f"{잰달} CE 응답에 레코드가 없다 — 그 달에 쓴 적이 "
                                 "없다는 뜻이고, 그래서 0 이다(§182)")
    d["잰날"] = 오늘.isoformat()
    선언파일.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{최근.get('TimePeriod', {}).get('Start', '?')} 기준으로 {len(잰것)}개 서비스를 적었다 "
          f"— {_보일(선언파일)}")
    for 이름, 값 in sorted(잰것.items(), key=lambda x: -x[1]):
        print(f"    {이름:<40} ${값:.4f}")
    for 이름 in sorted(빠진것):
        print(f"    {이름:<40} $0.0000  (CE 응답에 없다 — 그 달에 안 썼다)")
    return 0


def main() -> int:
    _canary()
    if "--selftest" in sys.argv[1:]:
        print("  프로브 살아 있다 — 맞는 선언 · 선언 밖 자원 · 걷힌 크레딧 · "
              "온디맨드 테이블 · 계정 번호 · 섞인 잰달 · 안 정한 갈래를 합성으로 묻는다")
        return 0
    if "--재다" in sys.argv[1:]:
        return 재다()
    if "--서비스별" in sys.argv[1:]:
        return 서비스별()

    d = 선언()
    if not d:
        print(f"{_보일(선언파일)} 를 못 읽었다 — **못 쟀다는 뜻이지 통과가 아니다**")
        return 2
    블록들 = 자원블록들()
    세우는것, 모름 = 쓰는서비스([(종류, 이름) for 종류, 이름, _ in 블록들])
    막, 알, 못 = 흠(d, 세우는것, 모름)
    막 += 용량흠(블록들)
    글들 = 추적파일글()
    if 글들:
        막 += 계정흠(글들)
    else:
        못.append("`git ls-files` 를 못 읽어 계정 번호를 못 훑었다(§131)")
    것들 = (d.get("서비스") or {}).values()
    합 = sum(float(s.get("월") or 0) for s in 것들)
    달들 = sorted({s.get("잰달") for s in 것들 if s.get("잰달")})
    꼬리 = (f"월 ${합:.4f} ({' · '.join(달들) or '잰 달 없음'}) · "
            f"서비스 {len(d.get('서비스') or {})}개 (잰날 {d.get('잰날', '?')})")
    for x in 알:
        print(f"    · {x}")
    if 막:
        print(f"과금 선언에 흠 {len(막)}건 — {꼬리}")
        for x in 막:
            print(f"    {x}")
        return 1
    if 못:
        print(f"과금을 다 못 쟀다 {len(못)}건 — {꼬리}")
        for x in 못:
            print(f"    {x}")
        return 2
    print(f"과금 선언이 실물과 맞는다 — {꼬리}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
