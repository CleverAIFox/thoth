"""푸시·apply 뒤에야 드러나던 것을 앞으로 당기는 검사.

★ 이 검사가 잡는 둘은 2026-09-15 에 실제로 났다 — IAM `description` 의 한글이
  `apply` 에서, 깨진 워크플로가 `gh workflow run` 에서. **둘 다 원격에 나간
  뒤였다**(DECISIONS §87).
"""
import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "check_static", pathlib.Path(__file__).resolve().parents[2] / "tools/check_static.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)

RESOURCE = '''resource "aws_iam_role" "ci" {
  name        = "thoth-ci"
  description = "%s"
}
'''


def test_resource_안의_한글을_잡는다():
    assert cs.tf_bad_strings(RESOURCE % "읽기 전용")


def test_resource_안이_ASCII_면_통과한다():
    assert cs.tf_bad_strings(RESOURCE % "read-only") == []


def test_variable_설명의_한글은_잡지_않는다():
    # ★ terraform 안에서 끝나고 API 로 나가지 않는다. 여기까지 막으면 한글
    #   문서를 쓰지 말라는 말이 된다.
    assert cs.tf_bad_strings('variable "region" {\n  description = "리소스를 세울 리전"\n}\n') == []


def test_output_설명의_한글도_잡지_않는다():
    assert cs.tf_bad_strings('output "url" {\n  description = "확장에 넣는 값"\n}\n') == []


def test_주석의_한글은_잡지_않는다():
    assert cs.tf_bad_strings('resource "aws_iam_role" "ci" {\n  # 읽기 전용이다 "따옴표" 포함\n  name = "ci"\n}\n') == []


def test_히어독의_한글은_잡지_않는다():
    src = 'resource "aws_x" "y" {\n  policy = <<-EOT\n    한글 "인용" 이 들어 있다\n  EOT\n  name = "y"\n}\n'
    assert cs.tf_bad_strings(src) == []


def test_블록이_끝나면_다시_보지_않는다():
    src = RESOURCE % "read-only" + '\nvariable "v" {\n  description = "한글"\n}\n'
    assert cs.tf_bad_strings(src) == []


def test_중첩_블록_안도_본다():
    src = 'resource "aws_x" "y" {\n  tags = {\n    Note = "한글"\n  }\n}\n'
    assert cs.tf_bad_strings(src)


def test_저장소가_지금_통과한다():
    # ★ 검사를 넣는 날 이미 깨져 있으면 아무도 고치지 않고 꺼 버린다(§46).
    assert cs.check_tf() == []


# ---------- Node 20 액션 (DECISIONS §100) ----------

def test_Node20_메이저를_잡는다():
    assert cs.node20_uses("      - uses: actions/checkout@v4\n") == [(1, "actions/checkout@v4")]


def test_올린_메이저는_통과한다():
    assert cs.node20_uses("      - uses: hashicorp/setup-terraform@v4\n") == []


def test_모르는_액션은_판정하지_않는다():
    assert cs.node20_uses("      - uses: someone/some-action@v1\n") == []


def test_gitleaks_v2_도_잡는다():
    # 경고가 두 번째 run 에서야 이름을 댔다(DECISIONS §101).
    assert cs.node20_uses("      - uses: gitleaks/gitleaks-action@v2\n") == [(1, "gitleaks/gitleaks-action@v2")]


def test_주석_안의_uses_는_보지_않는다():
    assert cs.node20_uses("      # uses: actions/checkout@v4 를 쓰던 자리\n") == []


def test_워크플로가_지금_Node20_을_쓰지_않는다():
    assert cs.check_node20() == []


# ---------- 러너 고정 (DECISIONS §105) ----------

def test_ubuntu_latest_를_잡는다():
    assert cs.latest_runners("    runs-on: ubuntu-latest\n") == [1]


def test_고정한_판은_통과한다():
    assert cs.latest_runners("    runs-on: ubuntu-24.04\n") == []


def test_주석의_latest_는_보지_않는다():
    assert cs.latest_runners("    runs-on: ubuntu-24.04  # ubuntu-latest 를 쓰던 자리\n") == []


def test_워크플로가_지금_러너를_고정했다():
    assert cs.check_runner() == []
