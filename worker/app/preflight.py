"""엔진별 기동 전제 확인.

  bash tools/preflight.sh                  현재 엔진
  ENGINE=bedrock bash tools/preflight.sh   이번 한 번만 다른 엔진
  bash tools/preflight.sh --cheap          바깥에 나가는 확인은 건너뛴다
  bash tools/preflight.sh --cheap --brief  한 줄로. doctor 가 쓴다

★ **실패는 그것이 일어난 자리에서 알린다**(DECISIONS §37). 전제가 깨져 있으면
  첫 번역 요청에서 502 로 나타나고, 띄운 뒤에 알면 원인을 찾는 데 시간이 든다.

★ **판정과 표현을 나눈다.** 확인은 `Finding` 을 돌려주고 문구는 `__main__` 이
  만든다. 그래야 판정을 테스트할 수 있다 — `state.js` 를 순수 함수로 떼어
  `node:test` 로 검증한 것과 같은 이유다(DECISIONS §47 · §48).

★ **레지스트리로 분기한다.** `run_worker.sh` 는 엔진 이름을 모르고 "해당하는
  전검사가 있으면 돌린다" 만 안다. 엔진을 추가할 때 셸 스크립트를 고치지
  않는다. 대신 `CHECKS` 에 등록하지 않으면 테스트가 잡는다.

★ **상수를 다시 선언하지 않는다.** `engine` 에서 가져온다. 같은 기본값을 두
  곳에 적으면 언젠가 갈린다(`tools/lib/env.sh` 가 여섯 스크립트의 중복 판단을
  모은 것과 같은 이유).

★ **원인을 단정하지 않는다.** 아는 코드만 갈라 적고 관측한 사실을 항상 함께
  싣는다. 재인증 명령은 프로파일 설정이 정하므로 `~/.aws/config` 를 읽어
  고르고, 읽어서 모르면 **아무 명령도 제시하지 않는다.** 틀린 원인을 단정하는
  메시지는 침묵보다 나쁘다(§37).
"""
from __future__ import annotations

import configparser
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from . import engine

AWS_CONFIG = os.path.expanduser(
    os.environ.get("AWS_CONFIG_FILE", "~/.aws/config")
)


@dataclass(frozen=True)
class Finding:
    """전검사 한 건의 결과.

    ok    기동해도 되는가
    code  판정 코드. 테스트와 호출부가 문구가 아니라 이것을 본다
    fact  관측한 사실. 예외 원문처럼 우리가 지어내지 않은 것만 담는다
    hints 다음에 할 일. **확실한 것만 담는다.** 모르면 비운다
    """

    ok: bool
    code: str
    fact: str = ""
    hints: tuple[str, ...] = field(default=())


# ─── 순수 판정 ────────────────────────────────────────────────────────────
# 네트워크도 파일도 만지지 않는다. 전부 테스트된다.


def parse_profile(config_text: str, profile: str) -> dict[str, str]:
    """`~/.aws/config` 에서 한 프로파일의 키를 뽑는다.

    ★ 절 이름이 `default` 와 `profile <이름>` 으로 갈린다. 이것을 호출부마다
      처리하면 갈리므로 여기 하나에 둔다.
    """
    cp = configparser.RawConfigParser()
    try:
        cp.read_string(config_text)
    except configparser.Error:
        return {}
    section = f"profile {profile}" if profile else "default"
    if not cp.has_section(section):
        return {}
    return dict(cp.items(section))


def aws_login_command(profile: str, config_text: str) -> str | None:
    """이 프로파일을 재인증하는 명령.

    ★ **`aws login` 과 `aws sso login` 은 대체 관계가 아니다.** 전자는 콘솔
      로그인을 재사용하는 IAM 사용자용이고 후자는 IAM Identity Center 용이다.
      프로파일 키가 어느 쪽인지 정한다 — `sso_session`/`sso_start_url` 이면
      Identity Center 이고 `login_session` 이면 콘솔 자격증명이다.

    ★ **모르면 None 이다.** 둘 중 어느 것도 아닌 프로파일(정적 키 · 역할 위임)
      에 로그인 명령을 들이미는 것은 틀린 원인을 단정하는 일이다.
    """
    keys = parse_profile(config_text, profile)
    suffix = f" --profile {profile}" if profile else ""
    if "sso_session" in keys or "sso_start_url" in keys:
        return f"aws sso login{suffix}"
    if "login_session" in keys:
        return f"aws login{suffix}"
    return None


# ★ 코드마다 '무엇을 봐야 하는가' 가 다르다. 표를 함수 밖에 두어 테스트가
#   목록 자체를 볼 수 있게 한다.
CREDENTIAL_CODES = frozenset({
    "ExpiredToken",
    "ExpiredTokenException",
    "InvalidClientTokenId",
    "UnrecognizedClientException",
    "TokenRetrievalError",
    "UnauthorizedSSOTokenError",
})

BEDROCK_HINTS: dict[str, tuple[str, ...]] = {
    "AccessDeniedException": (
        "Bedrock 콘솔 > Model access 에서 이 모델의 승인 여부를 본다",
        "승인돼 있다면 IAM 쪽이다 — bedrock:InvokeModel 권한을 본다",
    ),
    "ValidationException": (
        "모델 ID 가 이 리전에서 제공되는지 본다",
        "apac.* 는 크로스리전 추론 프로파일이라 일반 모델 ID 와 조건이 다르다",
        "BEDROCK_REGION 은 AWS_REGION 과 따로 둔다",
    ),
    "ResourceNotFoundException": (
        "모델 ID 가 이 리전에서 제공되는지 본다",
    ),
}


def classify_aws_error(code: str, message: str) -> Finding:
    """botocore 예외 코드를 판정으로 옮긴다.

    ★ **쓰로틀은 접근이 된다는 증거다.** 막을 이유가 없으므로 통과시키고
      사실만 싣는다. 실패로 세면 승인이 끝난 뒤에도 기동을 막는다.
    """
    if code == "ThrottlingException":
        return Finding(True, "throttled", f"쓰로틀됐다 ({code}) — {message}")
    if code in CREDENTIAL_CODES:
        return Finding(False, "credentials", f"자격증명이 유효하지 않다 ({code}) — {message}")
    if code in BEDROCK_HINTS:
        return Finding(False, code, f"{code} — {message}", BEDROCK_HINTS[code])
    return Finding(False, "unknown_error", f"{code} — {message}")


# ─── 확인 ────────────────────────────────────────────────────────────────
# 여기부터 바깥을 만진다. 판정은 위의 순수 함수가 한다.


def _login_hints() -> tuple[str, ...]:
    profile = os.environ.get("AWS_PROFILE", "")
    try:
        with open(AWS_CONFIG, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return ()
    cmd = aws_login_command(profile, text)
    return (cmd,) if cmd else ()


def _aws_credentials() -> Finding:
    """자격증명이 해결되고 살아 있는지. bedrock 과 translate 가 함께 쓴다."""
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as e:
        # ★ 의존성 누락을 트레이스백으로 알리면 원인이 바뀐다 — 자격증명을
        #   보러 왔는데 스택을 읽게 된다.
        return Finding(False, "missing_dependency", str(e), ("cd worker && uv sync",))

    session = boto3.Session()
    if session.get_credentials() is None:
        return Finding(False, "credentials", "자격증명이 해결되지 않는다", _login_hints())
    try:
        who = session.client("sts", region_name=engine.REGION).get_caller_identity()
    except ClientError as e:
        err = e.response.get("Error", {})
        f = classify_aws_error(err.get("Code", "?"), str(e))
        return Finding(f.ok, f.code, f.fact, f.hints or _login_hints())
    except BotoCoreError as e:
        # ★ SSO · login 캐시가 없거나 만료되면 ClientError 가 아니라 이쪽으로 온다.
        return Finding(False, "credentials", str(e), _login_hints())
    return Finding(True, "ok", f"호출자 {who['Arn']}")


def check_echo() -> Finding:
    return Finding(True, "ok", "외부 의존이 없다")


def check_local() -> Finding:
    url = f"{engine.OLLAMA_URL}/api/version"
    try:
        urllib.request.urlopen(url, timeout=3).read()
    except (urllib.error.URLError, OSError) as e:
        return Finding(
            False,
            "ollama_down",
            f"ollama 가 응답하지 않는다 ({engine.OLLAMA_URL}) — {e}",
            (
                "bash tools/run_ollama.sh > /tmp/ollama.log 2>&1 &",
                "이번 한 번만 엔진 없이 : ENGINE=echo bash tools/run_worker.sh",
            ),
        )
    return Finding(True, "ok", f"ollama 응답 ({engine.OLLAMA_MODEL})")


def check_translate() -> Finding:
    return _aws_credentials()


def check_bedrock() -> Finding:
    """★ 목록 API 로 대신하지 않는다. 권한이 갈려 '조회는 되는데 호출은 안 되는'
    상태를 통과시킨다. **실제로 탈 경로를 탄다** — `converse` 를 출력 1토큰으로
    한 번 때린다. 비용은 잰다는 말이 무의미한 수준이다.
    """
    cred = _aws_credentials()
    if not cred.ok:
        return cred

    from botocore.exceptions import BotoCoreError, ClientError

    try:
        engine._bedrock_client().converse(
            modelId=engine.BEDROCK_MODEL,
            messages=[{"role": "user", "content": [{"text": "ping"}]}],
            inferenceConfig={"temperature": 0, "maxTokens": 1},
        )
    except ClientError as e:
        return classify_aws_error(e.response.get("Error", {}).get("Code", "?"), str(e))
    except BotoCoreError as e:
        return Finding(False, "unknown_error", str(e))
    return Finding(True, "ok", f"{engine.BEDROCK_MODEL} 호출됨")


def judge_http_health(status: int, body: object, declared: str) -> Finding:
    """번역 서버 `/health` 응답의 판정. 순수 함수다.

    ★ **선언한 모델과 서버가 말하는 모델을 대조한다.** 어긋나면 쌍 로그의
      `model` 열이 거짓말을 하고, 그 쌍으로 다음 모델을 학습하면 어느 모델의
      출력을 배웠는지 모른다. 번역은 돌아도 기동을 막는다.

    ★ 선언이 비어 있으면 막지 않고 알린다. 로컬에서 서버를 막 띄워 보는 자리까지
      막으면 선언부터 채우라는 말이 되고, 쌍은 로컬에서 쌓이지 않는다(§104).
    """
    if status != 200 or not isinstance(body, dict):
        return Finding(False, "http_unhealthy", f"/health 가 {status} 를 냈다")
    served = body.get("model")
    if not isinstance(served, str) or not served:
        return Finding(False, "http_no_model", "/health 에 model 이 없다 — 계약 위반이다")
    if not declared:
        return Finding(True, "undeclared",
                       f"서버 모델 {served} · HTTP_MODEL 이 비어 쌍의 model 열이 http:undeclared 다",
                       (f"HTTP_MODEL={served}",))
    if served != declared:
        return Finding(False, "model_mismatch", f"선언 {declared} ≠ 서버 {served}")
    return Finding(True, "ok", f"{served} 응답")


def check_http() -> Finding:
    import json

    url = f"{engine.HTTP_URL.rstrip('/')}/health"
    req = urllib.request.Request(url, headers=engine._http_headers())
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        return judge_http_health(e.code, None, engine.HTTP_MODEL)
    except (urllib.error.URLError, OSError) as e:
        return Finding(False, "http_down", f"번역 서버가 응답하지 않는다 ({engine.HTTP_URL}) — {e}",
                       ("이번 한 번만 엔진 없이 : ENGINE=echo bash tools/run_worker.sh",))
    try:
        body = json.loads(raw)
    except ValueError:
        body = None
    return judge_http_health(status, body, engine.HTTP_MODEL)


# ★ 키는 `engine._raw_batch` 가 아는 엔진 이름과 같아야 한다. 테스트가 본다.
CHECKS = {
    "echo": check_echo,
    "local": check_local,
    "translate": check_translate,
    "bedrock": check_bedrock,
    "http": check_http,
}

# ★ **바깥에 나가는 확인과 그렇지 않은 확인을 가른다.** ollama 는 127.0.0.1 이라
#   공짜지만 bedrock 은 실제 호출이고 translate 는 AWS 왕복이다. `doctor` 는
#   커밋마다 도는 자리이므로 이쪽을 재지 않는다 — 검사가 돈을 쓰거나 네트워크에
#   기대면 비행기에서 커밋이 막힌다.
#
# ★ `http` 는 바깥으로 센다. 로컬 서버일 때도 있지만 URL 로 가르면 판정이 설정에
#   따라 흔들리고, 커밋 검사가 번역 서버 기동에 기대게 된다.
REMOTE = frozenset({"bedrock", "translate", "http"})


def run(name: str, remote: bool = True) -> Finding:
    """★ 모르는 엔진은 통과시킨다. 전검사가 없다는 것과 전제가 깨졌다는 것은
    다르고, 전자를 실패로 세면 등록을 잊었다는 이유로 기동이 막힌다. 등록
    누락은 테스트가 볼 자리이지 사용자가 볼 자리가 아니다.

    ★ `remote=False` 는 **통과가 아니라 못 쟀다는 뜻이다.** 코드를 따로 두어
      호출부가 둘을 섞지 못하게 한다 — 못 잰 것과 깨끗한 것은 다르다
      (DECISIONS §41 ㉢ · §47).
    """
    check = CHECKS.get(name)
    if check is None:
        return Finding(True, "unregistered", f"engine={name} 에 전검사가 없다")
    if not remote and name in REMOTE:
        return Finding(True, "not_measured", f"engine={name} 은 바깥에 나가야 잰다")
    return check()


def describe(name: str, f: Finding) -> list[str]:
    """표현. 판정을 문구로 옮기는 것만 한다."""
    head = "전검사 통과" if f.ok else "전검사 실패"
    lines = [f"{head} : engine={name}"]
    if f.fact:
        lines.append(f"  {f.fact}")
    lines += [f"  {h}" for h in f.hints]
    return lines


def brief(f: Finding) -> str:
    """한 줄 요약. 셸이 파싱한다 — `sweep.py --brief` 와 같은 자리다.

    ★ 사실에 `|` 가 섞이면 필드가 밀린다. 여기서 지운다.
    """
    return f"{int(f.ok)}|{f.code}|{f.fact.replace('|', '/')}"


def main(argv: list[str] | None = None) -> int:
    import sys

    args = sys.argv[1:] if argv is None else argv
    remote = "--cheap" not in args
    name = os.environ.get("ENGINE", "echo")
    f = run(name, remote=remote)

    if "--brief" in args:
        print(brief(f))
        return 0 if f.ok else 1

    profile = os.environ.get("AWS_PROFILE", "")
    # ★ 어느 프로파일이 잡혔는지 먼저 찍는다. `.env` 와 셸에 앞세운 지정이
    #   갈리면 여기서 눈에 보인다(DECISIONS §40).
    print(f"engine={name} profile={profile or '(기본 자격증명 체인)'}")
    out = sys.stdout if f.ok else sys.stderr
    for line in describe(name, f):
        print(line, file=out)
    return 0 if f.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
