"""전검사 — 판정과 레지스트리.

★ 네트워크도 AWS 도 만지지 않는다. 바깥을 만지는 것은 `check_*` 이고 판정은
  순수 함수로 떼어 두었으므로 그쪽만 본다(DECISIONS §47 · §48).

★ **재인증 명령을 고르는 자리가 이 파일의 핵심이다.** 여기를 눈으로만 보다가
  `login_session` 프로파일에 `aws sso login` 을 찍은 적이 있다. 둘은 대체
  관계가 아니라 다른 자격증명 출처다.
"""
import re
from pathlib import Path

import pytest

from app import engine, preflight

SSO = """
[profile work]
sso_session = corp
region = ap-northeast-2
"""

LOGIN = """
[profile fox]
login_session = arn:aws:iam::111122223333:user/fox-admin
region = ap-northeast-2
"""

STATIC = """
[profile keys]
region = ap-northeast-2
"""

LEGACY_SSO = """
[profile old]
sso_start_url = https://example.awsapps.com/start
"""


# ── aws_login_command ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,profile,expected",
    [
        (SSO, "work", "aws sso login --profile work"),
        (LEGACY_SSO, "old", "aws sso login --profile old"),
        (LOGIN, "fox", "aws login --profile fox"),
        (STATIC, "keys", None),
        (LOGIN, "없는프로파일", None),
        ("", "fox", None),
    ],
)
def test_login_command(text, profile, expected):
    assert preflight.aws_login_command(profile, text) == expected


def test_default_profile_has_no_flag():
    assert preflight.aws_login_command("", "[default]\nlogin_session = x\n") == "aws login"


def test_broken_config_does_not_raise():
    # ★ 손상된 config 로 전검사가 죽으면 원인이 바뀐다 — 자격증명 문제를
    #   보러 왔는데 파서 예외를 보게 된다.
    assert preflight.aws_login_command("fox", "이건 ini 가 아니다 [[[") is None


# ── classify_aws_error ───────────────────────────────────────────────────


def test_throttle_passes():
    # 쓰로틀은 접근이 된다는 증거다. 막으면 승인 후에도 기동이 막힌다.
    f = preflight.classify_aws_error("ThrottlingException", "slow down")
    assert f.ok and f.code == "throttled"


@pytest.mark.parametrize("code", sorted(preflight.CREDENTIAL_CODES))
def test_credential_codes_fail_as_credentials(code):
    f = preflight.classify_aws_error(code, "x")
    assert not f.ok and f.code == "credentials"


def test_access_denied_names_both_causes():
    f = preflight.classify_aws_error("AccessDeniedException", "denied")
    assert not f.ok
    # 콘솔 승인과 IAM 둘 다 가리킨다. 하나로 못 박지 않는다(§37).
    joined = " ".join(f.hints)
    assert "Model access" in joined and "IAM" in joined


def test_unknown_code_keeps_the_message_and_invents_nothing():
    f = preflight.classify_aws_error("무슨Exception", "원문 그대로")
    assert not f.ok and f.code == "unknown_error"
    assert "원문 그대로" in f.fact and f.hints == ()


# ── 레지스트리 ───────────────────────────────────────────────────────────


def test_registry_covers_every_engine():
    """★ `engine._raw_batch` 가 아는 엔진과 `CHECKS` 의 키가 같아야 한다.

    엔진을 추가하면서 전검사를 빠뜨리면 조용히 통과한다 — `run` 이 모르는
    엔진을 통과시키기 때문이다. 그 판단은 사용자가 아니라 여기서 막는다.
    """
    src = Path(engine.__file__).read_text(encoding="utf-8")
    known = set(re.findall(r'ENGINE == "(\w+)"', src))
    assert known, "engine.py 에서 엔진 분기를 찾지 못했다"
    assert known == set(preflight.CHECKS), (
        f"engine 에만 있는 것 {known - set(preflight.CHECKS)} / "
        f"CHECKS 에만 있는 것 {set(preflight.CHECKS) - known}"
    )


def test_unregistered_engine_passes():
    f = preflight.run("아직없는엔진")
    assert f.ok and f.code == "unregistered"


def test_echo_needs_nothing():
    assert preflight.run("echo").ok


def test_local_failure_does_not_touch_the_network(monkeypatch):
    # ollama 가 없을 때의 판정만 본다. 실제 기동 여부는 이 테스트의 관심이 아니다.
    monkeypatch.setattr(engine, "OLLAMA_URL", "http://127.0.0.1:1")
    f = preflight.run("local")
    assert not f.ok and f.code == "ollama_down"


# ── 표현 ─────────────────────────────────────────────────────────────────


def test_describe_carries_fact_and_hints():
    f = preflight.Finding(False, "credentials", "만료됐다", ("aws login --profile fox",))
    out = "\n".join(preflight.describe("bedrock", f))
    assert "실패" in out and "만료됐다" in out and "aws login --profile fox" in out


def test_describe_omits_empty_hints():
    out = preflight.describe("echo", preflight.Finding(True, "ok", "외부 의존이 없다"))
    assert len(out) == 2


# ── 원격 게이팅 ──────────────────────────────────────────────────────────


def test_remote_is_a_subset_of_the_registry():
    # REMOTE 에 오타가 나면 게이팅이 조용히 아무것도 하지 않는다.
    assert preflight.REMOTE <= set(preflight.CHECKS)


@pytest.mark.parametrize("name", sorted(preflight.REMOTE))
def test_cheap_mode_does_not_go_out(name, monkeypatch):
    # 호출됐다면 테스트가 죽는다. 안 나간다는 것을 이렇게 확인한다.
    monkeypatch.setitem(
        preflight.CHECKS, name, lambda: pytest.fail("cheap 인데 바깥에 나갔다")
    )
    f = preflight.run(name, remote=False)
    assert f.ok and f.code == "not_measured"


def test_cheap_mode_still_checks_local(monkeypatch):
    # ollama 는 127.0.0.1 이라 공짜다. 게이팅에서 빠져야 한다.
    assert "local" not in preflight.REMOTE
    monkeypatch.setattr(engine, "OLLAMA_URL", "http://127.0.0.1:1")
    assert preflight.run("local", remote=False).code == "ollama_down"


def test_not_measured_is_not_ok_code():
    # ★ 못 잰 것과 깨끗한 것을 같은 코드로 내보내면 doctor 가 둘을 섞는다.
    assert preflight.run("bedrock", remote=False).code != "ok"


# ── brief ────────────────────────────────────────────────────────────────


def test_brief_has_three_fields():
    line = preflight.brief(preflight.Finding(False, "credentials", "만료됐다"))
    assert line.split("|") == ["0", "credentials", "만료됐다"]


def test_brief_survives_a_pipe_in_the_fact():
    line = preflight.brief(preflight.Finding(True, "ok", "a|b|c"))
    assert len(line.split("|")) == 3


def test_main_brief_prints_one_line(capsys, monkeypatch):
    monkeypatch.setenv("ENGINE", "echo")
    assert preflight.main(["--cheap", "--brief"]) == 0
    out = capsys.readouterr().out.strip().split("\n")
    assert len(out) == 1 and out[0].startswith("1|ok|")
