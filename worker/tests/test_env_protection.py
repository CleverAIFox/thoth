"""배포 게이트 판정(DECISIONS §110). **게이트가 빠진 설정이 초록이면 안 된다.**"""
import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "env_protection", pathlib.Path(__file__).resolve().parents[2] / "tools/env_protection.py")
ep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ep)

# 2026-09-16 에 건 설정의 모양이다. 값은 시험값이다.
GOOD_ENV = {
    "name": "production",
    "protection_rules": [
        {"type": "required_reviewers", "prevent_self_review": False,
         "reviewers": [{"type": "User", "reviewer": {"login": "CleverAIFox"}}]},
        {"type": "branch_policy"},
    ],
    "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True},
}
GOOD_POL = {"total_count": 1, "branch_policies": [{"name": "v*", "type": "tag"}]}


def test_걸려_있으면_통과다():
    assert ep.judge(GOOD_ENV, GOOD_POL) == []


def test_2026_09_16_이전_모양은_실패다():
    # ★ §98 — 규칙이 비어 있었다. 태그를 밀자 승인 없이 apply 가 돌았다.
    bad = ep.judge({"name": "production", "protection_rules": [],
                    "deployment_branch_policy": None}, {"branch_policies": []})
    assert len(bad) == 3


def test_승인자_목록이_비면_실패다():
    env = {**GOOD_ENV, "protection_rules": [{"type": "required_reviewers", "reviewers": []}]}
    assert any("reviewers" in b for b in ep.judge(env, GOOD_POL))


def test_태그가_아니라_브랜치_정책이면_실패다():
    pol = {"branch_policies": [{"name": "v*", "type": "branch"}]}
    assert any("태그" in b for b in ep.judge(GOOD_ENV, pol))


def test_읽어_둔_응답으로도_판정한다(tmp_path):
    import json
    e, p = tmp_path / "e.json", tmp_path / "p.json"
    e.write_text(json.dumps(GOOD_ENV), encoding="utf-8")
    p.write_text(json.dumps(GOOD_POL), encoding="utf-8")
    assert ep.main([str(e), str(p)]) == 0
