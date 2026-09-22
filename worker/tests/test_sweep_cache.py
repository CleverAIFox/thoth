"""sweep 의 uv 캐시 판정(DECISIONS §118). **세는 것과 지울 수 있는 것이 같아야 한다.**"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("sweep", ROOT / "tools/sweep.py")
sw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sw)


def test_캐시에_있는_것만_센다(tmp_path):
    (tmp_path / "wheels-v5/pypi/boto3").mkdir(parents=True)
    (tmp_path / "simple-v17/pypi").mkdir(parents=True)
    (tmp_path / "simple-v17/pypi/s3transfer.rkyv").write_text("", encoding="utf-8")
    assert sw.in_cache("boto3", tmp_path)
    assert sw.in_cache("s3transfer", tmp_path)
    # ★ lock 에는 있으나 이미 지운 것 — 전에는 이것을 세고 `--fix` 가 빈손이었다
    assert not sw.in_cache("awscrt", tmp_path)


def test_이름을_정규화한다(tmp_path):
    (tmp_path / "wheels-v5/pypi/typing-extensions").mkdir(parents=True)
    assert sw.in_cache("typing_extensions", tmp_path)
    assert sw.in_cache("Typing.Extensions", tmp_path)


def test_캐시_자리는_환경이_이긴다(tmp_path, monkeypatch):
    monkeypatch.setenv("UV_CACHE_DIR", str(tmp_path))
    assert sw.cache_dir() == tmp_path
