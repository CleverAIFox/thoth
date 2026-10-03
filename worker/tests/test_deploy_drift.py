"""배포본 드리프트 판정.

★ AWS 에 닿는 `remote_hash` 하나만 여기서 재지 못한다. 나머지 — 해시 형식 ·
  응답 파싱 · 판정 · 종료 코드 — 는 전부 덮는다. **못 재는 자리를 좁히고 그
  자리를 적어 두는 것**이 지금 할 수 있는 전부다(§73).
"""
import base64
import hashlib
import importlib.util
import json
import pathlib

_spec = importlib.util.spec_from_file_location(
    "deploy_drift", pathlib.Path(__file__).resolve().parents[2] / "tools/deploy_drift.py")
dd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dd)


def test_해시가_base64_다_16진수가_아니다(tmp_path):
    # ★ Lambda 의 CodeSha256 은 base64 다. sha256sum 출력과 비교하면 영원히 다르다.
    f = tmp_path / "w.zip"
    f.write_bytes(b"thoth")
    got = dd.local_hash(str(f))
    assert got == base64.b64encode(hashlib.sha256(b"thoth").digest()).decode()
    assert got != hashlib.sha256(b"thoth").hexdigest()


def test_태그에서_해시를_꺼낸다():
    assert dd.parse_remote(json.dumps({"Tags": {dd.TAG: "abc="}})) == "abc="


def test_응답_형식이_바뀌면_조용히_빈_값을_내지_않는다():
    # ★ 빈 문자열은 비교에서 '다르다' 가 된다. 파싱 실패는 실패로 드러나야 한다.
    # ★ 셋째는 **첫 apply 전**의 꼴이다 — 태그가 아직 없다. 그때도 「못 쟀다」(1)여야지
    #   「다르다」(2)면 안 된다. 둘은 고치는 일이 다르다.
    for bad in ["{}", '{"Tags":{}}', '{"Configuration":{"CodeSha256":"abc="}}', "그냥 글자"]:
        try:
            dd.parse_remote(bad)
        except (ValueError, KeyError):
            continue
        raise AssertionError(f"{bad!r} 을 통과시켰다")


def test_계정을_꺼낸다():
    assert dd.parse_account(json.dumps({"Account": "123456789012"})) == "123456789012"
    for bad in ["{}", "그냥 글자"]:
        try:
            dd.parse_account(bad)
        except (ValueError, KeyError):
            continue
        raise AssertionError(f"{bad!r} 을 통과시켰다")


def test_ARN_을_계정과_리전과_이름으로_짓는다():
    """★ **ARN 을 저장소에 적어 두지 않는다.** 이 저장소는 공개이고 계정 번호가
    거기 박히면 지울 수가 없다. 계정은 `sts` 가 주고 나머지 둘은 인자다."""
    got = dd.ARN.format(region="ap-northeast-2", account="123456789012", function="thoth-worker")
    assert got == "arn:aws:lambda:ap-northeast-2:123456789012:function:thoth-worker"


def test_태그_이름이_인프라와_같다():
    """★ **두 곳에 사는 글자다**(DECISIONS §131). `compute.tf` 가 붙이고 여기가 읽는다 —
    한쪽만 고치면 드리프트가 「못 쟀다」 로 영영 멈춘다. 검사가 그 둘을 묶는다."""
    tf = (pathlib.Path(__file__).resolve().parents[2] / "infra/compute.tf").read_text(encoding="utf-8")
    assert f"{dd.TAG} = filebase64sha256(" in tf, f"compute.tf 가 태그 `{dd.TAG}` 를 안 붙인다"


def test_CI_역할이_함수를_통째로_못_읽는다():
    """★ **0 건이 목표인 검사다**(DECISIONS §131). `lambda:GetFunction` 은 응답에
    환경변수를 싣는다 — 그 액션이 CI 역할로 돌아오면 비밀이 다시 읽힌다."""
    tf = (pathlib.Path(__file__).resolve().parents[2] / "infra/oidc.tf").read_text(encoding="utf-8")
    import re
    몸 = re.search(r'data "aws_iam_policy_document" "ci" \{(.*?)\n\}', tf, re.S)
    assert 몸, "oidc.tf 에서 ci 정책을 못 찾았다 — 검사가 아무것도 안 보고 있다"
    본문 = 몸.group(1)
    assert "lambda:ListTags" in 본문
    for 금지 in ("lambda:GetFunction", "lambda:GetFunctionConfiguration"):
        assert 금지 not in 본문, f"CI 역할이 {금지} 를 든다 — 응답에 환경변수가 실린다"


def test_같으면_0():
    code, text = dd.report("A=", "A=")
    assert code == 0 and "이 코드다" in text


def test_다르면_2_이고_양쪽을_다_적는다():
    code, text = dd.report("A=", "B=")
    assert code == 2
    assert "A=" in text and "B=" in text      # 어느 쪽이 무엇인지 없으면 못 고친다
    assert "package_lambda" in text           # 고치는 명령을 함께 적는다


def test_zip_이_없으면_못_쟀다_1_이다(tmp_path):
    # ★ 0 이 아니다. 못 잰 것을 통과로 세면 검사가 없는 것과 같다(§59).
    assert dd.main(["--zip", str(tmp_path / "없다.zip"), "--remote", "A="]) == 1


def test_remote_를_주면_aws_를_부르지_않는다(tmp_path, monkeypatch):
    f = tmp_path / "w.zip"
    f.write_bytes(b"thoth")
    monkeypatch.setattr(dd, "remote_hash", lambda *a: (_ for _ in ()).throw(AssertionError("불렀다")))
    assert dd.main(["--zip", str(f), "--remote", dd.local_hash(str(f))]) == 0


def test_aws_가_실패하면_못_쟀다_1_이다(tmp_path, monkeypatch):
    f = tmp_path / "w.zip"
    f.write_bytes(b"thoth")
    monkeypatch.setattr(dd, "remote_hash", lambda *a: (None, "자격증명 만료"))
    assert dd.main(["--zip", str(f)]) == 1


def test_계정을_못_물으면_태그를_안_묻는다(monkeypatch):
    """★ 앞이 실패했는데 뒤를 부르면 **두 번째 오류가 첫 번째를 덮는다.**"""
    부른것 = []

    def 가짜(cmd, profile):
        부른것.append(cmd[1])
        return (None, "거절당했다") if cmd[1] == "sts" else ("{}", None)

    monkeypatch.setattr(dd, "_aws", 가짜)
    got, why = dd.remote_hash("thoth-worker", "ap-northeast-2", None)
    assert got is None and "계정" in why
    assert 부른것 == ["sts"], f"계정이 없는데 더 불렀다 — {부른것}"


def test_태그가_없으면_고치는_명령을_함께_적는다(monkeypatch):
    """★ 첫 `apply` 전이면 **맞는 상태**다. 「못 쟀다」 에 다음 수를 안 적으면
    읽는 사람이 배포가 깨진 줄 안다."""
    monkeypatch.setattr(dd, "_aws", lambda cmd, profile:
                        (json.dumps({"Account": "1"}), None) if cmd[1] == "sts" else ("{}", None))
    got, why = dd.remote_hash("thoth-worker", "ap-northeast-2", None)
    assert got is None
    assert dd.TAG in why and "apply" in why


def test_태그를_읽으면_ARN_으로_물었다(monkeypatch):
    본 = {}

    def 가짜(cmd, profile):
        if cmd[1] == "sts":
            return json.dumps({"Account": "123456789012"}), None
        본["cmd"] = cmd
        return json.dumps({"Tags": {dd.TAG: "A="}}), None

    monkeypatch.setattr(dd, "_aws", 가짜)
    got, why = dd.remote_hash("thoth-worker", "ap-northeast-2", None)
    assert (got, why) == ("A=", None)
    assert 본["cmd"][1:3] == ["lambda", "list-tags"]
    assert "arn:aws:lambda:ap-northeast-2:123456789012:function:thoth-worker" in 본["cmd"]
