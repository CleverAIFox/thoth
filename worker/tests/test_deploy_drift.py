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


def test_응답에서_해시를_꺼낸다():
    assert dd.parse_remote(json.dumps({"Configuration": {"CodeSha256": "abc="}})) == "abc="


def test_응답_형식이_바뀌면_조용히_빈_값을_내지_않는다():
    # ★ 빈 문자열은 비교에서 '다르다' 가 된다. 파싱 실패는 실패로 드러나야 한다.
    for bad in ["{}", '{"Configuration":{}}', "그냥 글자"]:
        try:
            dd.parse_remote(bad)
        except (ValueError, KeyError):
            continue
        raise AssertionError(f"{bad!r} 을 통과시켰다")


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
