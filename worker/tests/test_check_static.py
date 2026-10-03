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


# ---------- 액션 고정 (DECISIONS §125) ----------

핀 = "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1\n"


def test_맨_메이저_태그를_잡는다():
    assert cs.unpinned_uses("      - uses: actions/checkout@v7\n") == [(1, "actions/checkout@v7")]


def test_SHA_로_고정하면_통과한다():
    assert cs.unpinned_uses(핀) == []


def test_SHA_인데_판_주석이_없으면_잡는다():
    # ★ 주석은 장식이 아니다 — `node20_uses` 가 메이저를 거기서 읽는다.
    assert cs.unpinned_uses(핀.split("  #")[0] + "\n")


def test_짧은_해시는_고정이_아니다():
    assert cs.unpinned_uses("      - uses: actions/checkout@3d3c42e  # v7.0.1\n")


def test_같은_저장소_경로는_밖이다():
    assert cs.unpinned_uses("      - uses: ./.github/actions/setup\n") == []


def test_주석_안의_uses_는_보지_않는다_고정():
    assert cs.unpinned_uses("      # uses: actions/checkout@v7 을 쓰던 자리\n") == []


def test_워크플로가_지금_전부_고정됐다():
    assert cs.check_pinned() == []


def test_고정한_줄에서도_Node20_을_읽는다():
    """★ **이것이 이 묶음의 핵이다.**

    2026-10-03 에 `uses:` 를 전부 SHA 로 바꾸자 `node20_uses` 가 주석을 벗기는
    바람에 조용히 0건이 됐다. 꼴을 바꾸는 고침이 **그 꼴을 읽던 검사를 껐다.**
    옛 메이저를 SHA 로 고정해도 잡혀야 한다 — 고정은 판을 못 박는 것이고
    **옛 판을 허락하는 것이 아니다.**
    """
    옛 = "      - uses: actions/checkout@" + "a" * 40 + "  # v4.2.2\n"
    assert cs.node20_uses(옛) == [(1, "actions/checkout@v4")]


# ---------- 번역 캐시 삭제 지시 (DECISIONS §125) ----------

def test_캐시를_지우라는_줄을_잡는다():
    assert cs.cache_rm("rm -f worker/.cache/translations.json   # 캐시를 비운다\n") == [1]


def test_CACHE_FILE_로_가리키면_통과한다():
    assert cs.cache_rm("CACHE_FILE=/tmp/bench-cache.json bash tools/run_worker.sh &\n") == []


def test_다른_파일_삭제는_안_본다():
    assert cs.cache_rm("rm -f /tmp/golden.json\n") == []


def test_저장소에_캐시_삭제_지시가_없다():
    assert cs.check_cache_rm() == []


def test_잘못된_이스케이프를_잡는다():
    # ★ 2026-09-22 `pairs.py` docstring 의 모양이다. 지금은 경고, 나중에는 import 에서 죽는다.
    assert cs.py_warnings('def f():\n    """`:\\d+$` 로 벗긴다"""\n', "x.py")


def test_raw_문자열은_통과한다():
    assert cs.py_warnings('def f():\n    r"""`:\\d+$` 로 벗긴다"""\n', "x.py") == []


def test_저장소에_컴파일_경고가_없다():
    assert cs.check_python() == []


# ---------- 작업 시간 상한 (DECISIONS §126) ----------

_WF = """name: x
on: push
jobs:
  a:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    steps:
      - run: echo
  b:
    runs-on: ubuntu-24.04
    steps:
      - run: echo
  c:
    uses: ./.github/workflows/other.yml
"""


def test_상한_없는_작업을_잡는다():
    assert cs.timeout_faults(_WF) == ["b"]


def test_재사용_워크플로_작업은_밖이다():
    """★ GitHub 이 그 작업에 `timeout-minutes` 를 거부한다 — 넣으면 통째로 안 돈다."""
    assert "c" not in cs.timeout_faults(_WF)


def test_작업을_다_센다():
    assert sorted(cs.jobs(_WF)) == ["a", "b", "c"]


def test_저장소의_모든_작업에_상한이_있다():
    assert cs.check_timeouts() == []


# ---------- CI 밖의 선언 (파이어레인 gate_parity.py · DECISIONS §127) ----------

_DOC = '\n'.join([
    'if [ "$SCOPE" = "--repo" ]; then',
    '  skip "SSD 비밀 검사 (기계 설정이다)"',
    'else',
    '  ok "봤다"',
    'fi',
    '[ "${SCOPE}" != "--repo" ] && ok "저쪽"',
])


def test_가지를_센다():
    assert cs.scope_branches(_DOC) == [1, 6]


def test_주석의_SCOPE_는_안_센다():
    assert cs.scope_branches('# [ "$SCOPE" = "--repo" ] 를 쓰던 자리\n') == []


def test_저장소가_지금_선언을_다_한다():
    """★ **없는 병에 관문을 세우지 않았다.** 2026-10-03 실측 — 여섯 가지가 전부
    사유 딸린 `skip` 을 낸다. 그래서 파이어레인처럼 선언 표를 새로 만들지 않고
    **수만 못 박았다.**"""
    assert cs.check_scope_declared() == []


def test_선언_수가_실물과_맞다():
    """★ **양방향 래칫이다**(파이어레인 `ratchet.py`). 늘어도 줄어도 운다 —
    **느슨해진 래칫은 초록으로 위장한다.**"""
    몸 = (cs.ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    assert len(cs.scope_branches(몸)) == cs.SCOPE_BRANCHES
