"""도장의 **입자** — `uses:` 는 메이저까지, 잠금 파일은 봉인 밖(seshat DECISIONS §330).

★ **세샤트의 `tests/test_docseal_grain.py` 에서 왔다. 정본은 세샤트다.** 갈린 자리는 하나다 —
  `ROOT` 를 `tools/docseal.py` 가 있는 조상에서 찾는다(이 저장소는 시험이 `worker/tests/` 에 산다).
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents
            if (p / "tools/docseal.py").exists())
_spec = importlib.util.spec_from_file_location("docseal", ROOT / "tools/docseal.py")
DS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(DS)
DG = DS.낟알          # 표는 가진 쪽 하나만 본다(세샤트 §57 · §325) — 시험은 `DG.잠금이름` 을 고친다


# ───────── 도장 입자 — `uses:` 는 메이저까지, 잠금 파일은 봉인 밖(seshat DECISIONS §330) ─────────

_해시 = "3d3c42e5aac5ba805825da76410c181273ba90b1"
_다른해시 = "0123456789abcdef0123456789abcdef01234567"
_워크플로 = (f"jobs:\n  a:\n    steps:\n"
          f"      - uses: actions/checkout@{_해시}  # v7.0.1\n"
          f"      - run: echo hi\n")


def _yml(tmp_path, 글):
    p = tmp_path / "w.yml"
    p.write_text(글, encoding="utf-8")
    return DS.로직_지문(p)


def test_도장입자_1_소유자가_바뀌면_깨진다(tmp_path):
    assert _yml(tmp_path, _워크플로) != _yml(tmp_path, _워크플로.replace("actions/", "evil/"))


def test_도장입자_2_메이저가_바뀌면_깨진다(tmp_path):
    assert _yml(tmp_path, _워크플로) != _yml(tmp_path, _워크플로.replace("# v7.0.1", "# v8.0.0"))


def test_도장입자_3_uses_줄을_지우면_깨진다(tmp_path):
    줄 = f"      - uses: actions/checkout@{_해시}  # v7.0.1\n"
    assert _yml(tmp_path, _워크플로) != _yml(tmp_path, _워크플로.replace(줄, ""))


def test_도장입자_4_해시만_바뀌면_안_깨진다(tmp_path):
    """★ 이번 판의 목적. 해시를 바꾸고 판본 주석은 그대로."""
    assert _yml(tmp_path, _워크플로) == _yml(tmp_path, _워크플로.replace(_해시, _다른해시))


def test_도장입자_마이너_패치도_안_깨진다(tmp_path):
    assert _yml(tmp_path, _워크플로) == _yml(
        tmp_path, _워크플로.replace(_해시, _다른해시).replace("v7.0.1", "v7.3.9"))


def test_도장입자_태그_꼴도_메이저로_접는다():
    assert DG._uses_입자("- uses: a/b@v4.1.2\n") == DG._uses_입자("- uses: a/b@v4\n") == "- uses: a/b@v4"


def test_도장입자_밖은_그대로다():
    """로컬 액션 · 도커 · 브랜치 · 판본 주석 없는 해시는 건드리지 않는다(넓은 쪽이 안전하다)."""
    for 줄 in ("- uses: ./.github/actions/x", "- uses: docker://alpine@sha256:ab12",
              "- uses: a/b@main", f"- uses: a/b@{_해시}"):
        assert DG._uses_입자(줄) == 줄


def test_도장입자_다른_줄은_그대로_문다(tmp_path):
    """과잉 제거를 못 잡는 부정 단언 대신 — 딴 줄이 바뀌면 깨져야 한다."""
    assert _yml(tmp_path, _워크플로) != _yml(tmp_path, _워크플로.replace("echo hi", "echo bye"))


def test_잠금_파일을_강제자로_들면_도구가_죽는다(capsys):
    import pytest
    글 = "## §9. 가\n\n**2026-10-01**\n\n강제자 — `extension/package-lock.json`\n"
    with pytest.raises(SystemExit) as e:
        DS.절들(글)
    assert e.value.code == 2
    assert "package-lock.json" in capsys.readouterr().err


def test_잠금_목록을_비우면_카나리아가_운다(monkeypatch, capsys):
    import pytest
    monkeypatch.setattr(DG, "잠금이름", frozenset())
    with pytest.raises(SystemExit) as e:
        DS._canary()
    assert e.value.code == 2
    assert "잠금" in capsys.readouterr().out


def test_매니페스트는_강제자로_든다():
    글 = "## §9. 가\n\n**2026-10-01**\n\n강제자 — `tools/docseal.py`\n"
    assert DS.절들(글)[0]["파일"] == ["tools/docseal.py"]


def test_저장소_봉인에_잠금_파일이_하나도_없다():
    """★ 이 저장소는 §194 가 `package-lock.json` 을 강제자로 든 적이 있다. 가드가 도구 고장(2)으로
    죽이므로 실제 절 전수가 SystemExit 없이 끝나고, 어느 절도 잠금 파일을 안 든다."""
    잠금 = [f"{절['표시']} {f}" for 절 in DS.절들() for f in 절["파일"]
          if f.split("::")[0].rsplit("/", 1)[-1] in DG.잠금이름]
    assert 잠금 == []


def test_도장입자_5_매니페스트_키를_지우면_깨진다(tmp_path):
    p = tmp_path / "package.json"
    p.write_text('{"devDependencies": {"jsdom": "^30.1.1", "x": "^1"}}\n', encoding="utf-8")
    앞 = DS.로직_지문(p)
    p.write_text('{"devDependencies": {"jsdom": "^30.1.1"}}\n', encoding="utf-8")
    assert DS.로직_지문(p) != 앞


def test_도장입자_6_잠금_판본만_바뀌어도_봉인은_안_깨진다():
    """잠금 파일이 봉인 밖이라 어느 절의 지문에도 안 든다 — 판본 숫자는 지문의 재료가 아니다."""
    for 절 in DS.절들():
        assert not any("lock" in f.split("::")[0].rsplit("/", 1)[-1] for f in 절["파일"])


# ───────── package.json 은 이름은 문다 · 범위는 접는다(seshat DECISIONS §335) ─────────

_PJ = '{"name": "t", "scripts": {"test": "node --test"}, "devDependencies": {"jsdom": "^30.1.1"}}\n'


def _pj(tmp_path, 글):
    p = tmp_path / "package.json"
    p.write_text(글, encoding="utf-8")
    return DS.로직_지문(p)


def test_package_json_범위만_바뀌면_안_깨진다(tmp_path):
    """★ Dependabot PR 은 잠금뿐 아니라 `package.json` 의 범위(`^30.1.1` → `^30.1.3`)도 올린다."""
    assert _pj(tmp_path, _PJ) == _pj(tmp_path, _PJ.replace("^30.1.1", "^30.1.3"))


def test_package_json_의존성_키를_지우거나_더하면_깨진다(tmp_path):
    assert _pj(tmp_path, _PJ) != _pj(tmp_path, _PJ.replace('"jsdom": "^30.1.1"', '"zz": "^1"'))
    assert _pj(tmp_path, _PJ) != _pj(tmp_path, _PJ.replace(', "devDependencies": {"jsdom": "^30.1.1"}', ""))


def test_package_json_의존성_밖이_바뀌면_깨진다(tmp_path):
    """과잉 제거를 못 잡는 부정 단언 대신 — 스크립트가 바뀌면 깨져야 한다."""
    assert _pj(tmp_path, _PJ) != _pj(tmp_path, _PJ.replace("node --test", "node --check"))


def test_package_json_이_아닌_json_은_글자_그대로_문다(tmp_path):
    p = tmp_path / "other.json"
    p.write_text('{"devDependencies": {"a": "^1"}}\n', encoding="utf-8")
    앞 = DS.로직_지문(p)
    p.write_text('{"devDependencies": {"a": "^2"}}\n', encoding="utf-8")
    assert DS.로직_지문(p) != 앞


def test_깨진_package_json_은_글자_그대로_문다(tmp_path):
    assert _pj(tmp_path, "{깨진") != _pj(tmp_path, "{깨진2")
