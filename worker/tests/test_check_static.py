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


# ── 워크플로가 드는 저장소 경로(DECISIONS §164) ──────────────────────────────

def test_워크플로가_드는_경로가_실재한다():
    """★ **세샤트가 이것으로 엿새를 날렸다**(§164 · 세샤트 §291). 예약 작업이 옮긴 파일을
    계속 가리켰고, 주 1회라 아무도 몰랐고, 그 빨강이 관계없는 밀기를 막았다."""
    assert cs.check_workflow_paths() == []


def test_워크플로_경로_카나리아():
    """★ **이 저장소는 0 건이다** — 그래서 정규식이 죽어도 **초록**이다. 합성으로 묻는다."""
    assert cs.워크플로경로("  run: python3 tools/x.py\n") == [(1, "tools/x.py")]
    assert cs.워크플로경로("  run: bash tools/doctor.sh --repo\n") == [(1, "tools/doctor.sh")]
    assert cs.워크플로경로("  run: cat docs/*.md\n") == []
    assert cs.워크플로경로("  run: ls $HOME/tools/x.py\n") == []
    assert cs.워크플로경로("  # 세샤트 tools/ci_status.py 와 같다\n") == []
    assert cs.워크플로경로("  run: git add docs/papers.md\n") == [(1, "docs/papers.md")]
    # ★ **ASCII 만 든다**(세샤트와 같은 꼴). 한글 파일 이름은 이 자가 **못 본다** —
    #   이 저장소의 워크플로에는 하나도 없고, 생기면 여기가 조용히 안 본다는 뜻이다
    assert cs.워크플로경로("  run: python3 tools/없는것.py\n") == []
    # ★ **글롭은 「안에」 가 아니라 「뒤에」 남는다**(§164). 글자 집합이 `*` 를 안 받으므로
    #   `"*" in q` 는 영영 거짓이었다 — 돌연변이가 그 줄을 **아무것도 안 붙든다**고 물었다.
    #   진짜 꼴은 이것이다 : 정규식이 `docs/a` 까지만 집고 그 잘린 것이 없는 파일이다
    assert cs.워크플로경로("  path: docs/a*b.md\n") == []
    assert cs.워크플로경로("  run: python3 tools/${NAME}.py\n") == []


def test_없는_경로를_들면_걸린다(tmp_path, monkeypatch):
    """★ **양성만 보면 아무것도 못 잡는 검사가 초록이다.** 0 건인 저장소에서는 더 그렇다."""
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/x.yml").write_text(
        "name: x\non:\n  push:\njobs:\n  a:\n    steps:\n"
        "      - run: python3 tools/no_such.py\n", encoding="utf-8")
    monkeypatch.setattr(cs, "ROOT", tmp_path)
    난것 = cs.check_workflow_paths()
    assert any("tools/no_such.py" in x for x in 난것), 난것


def test_무시되는_자리는_안_든다(tmp_path, monkeypatch):
    """★ **거짓 빨강이 쌓이면 사람이 검사를 끈다**(§158). `dist/` 는 만들어지는 것이다.

    ★ 이 저장소에 무시되는 자리를 드는 워크플로가 **지금 하나도 없다** — 그래서 실물로는
      이 가지가 **안 돌고**, 돌연변이가 그것을 물었다. 합성 저장소에서 묻는다.
    """
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("dist/\n", encoding="utf-8")
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/x.yml").write_text(
        "name: x\non:\n  push:\njobs:\n  a:\n    steps:\n"
        "      - run: ls tools/dist/pkg.zip\n", encoding="utf-8")
    (tmp_path / "tools").mkdir(exist_ok=True)
    monkeypatch.setattr(cs, "ROOT", tmp_path)
    assert cs._무시된다("tools/dist/pkg.zip"), "git 이 무시한다고 하는데 못 읽었다"
    assert cs.check_workflow_paths() == [], "무시되는 자리를 흠으로 세면 거짓 빨강이다"


def test_무시_안_되는_없는_자리는_든다(tmp_path, monkeypatch):
    """★ **음성만 있으면 무엇이든 통과시키는 검사가 초록이다.** 위 시험의 짝이다."""
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("dist/\n", encoding="utf-8")
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/x.yml").write_text(
        "name: x\non:\n  push:\njobs:\n  a:\n    steps:\n"
        "      - run: ls tools/build/pkg.zip\n", encoding="utf-8")
    monkeypatch.setattr(cs, "ROOT", tmp_path)
    assert not cs._무시된다("tools/build/pkg.zip")
    assert any("tools/build/pkg.zip" in x for x in cs.check_workflow_paths())


# ── 인터프리터 고정 (DECISIONS §179) ───────────────────────────────────────
#
# ★ **고정 목록에 파이썬만 빠져 있었다.** 러너도 액션도 SHA 로 못 박으면서
#   인터프리터는 `uv` 가 그날 가장 새것을 집게 뒀다. 2026-10-10 **CPython 3.15.0 이
#   나오자** `smoke` 가 그것을 받아 갔고 3.15 휠이 없어 `pydantic-core` · `uvloop` ·
#   `httptools` 를 **소스에서 빌드**하다 30초 기동 창을 넘겼다. **이쪽은 한 줄도 안
#   바뀌었는데 초록이 빨개졌다** — 그것이 고정이 막는 사고다.

_UV작업 = ("name: x\non:\n  push:\njobs:\n  smoke:\n    steps:\n"
           "      - run: uv run uvicorn app.main:app\n")


def test_핀이_없으면_문다():
    난것 = cs.python_pin_faults(_UV작업, None)
    assert len(난것) == 1 and "python-version" in 난것[0]


def test_핀이_있으면_조용하다():
    assert cs.python_pin_faults(_UV작업, "3.13") == []


def test_uv_를_안_부르는_작업은_안_본다():
    글 = "name: x\non:\n  push:\njobs:\n  lint:\n    steps:\n      - run: ls\n"
    assert cs.python_pin_faults(글, None) == []


def test_setup_python_이_핀과_다르면_문다():
    """★ **작업 안에서 묻지 않는다.** `verify` 는 `setup-python` 으로 깔면서 `uv` 를
    `doctor.sh` **안에서** 부른다 — 작업 몸에 `uv` 글자가 없다. 둘이 한 작업에서
    만나야만 묻는 규칙은 **한 번도 안 문다**(DECISIONS §21)."""
    글 = ("name: x\non:\n  push:\njobs:\n"
          "  verify:\n    steps:\n      - uses: a/b\n        with: { python-version: \"3.14\" }\n"
          "  smoke:\n    steps:\n      - run: uv run x\n")
    난것 = cs.python_pin_faults(글, "3.13")
    assert len(난것) == 1 and "두 파이썬이 돈다" in 난것[0]


def test_지금_저장소가_고정돼_있다():
    assert cs.적힌파이썬() == "3.13", "worker/.python-version 이 없거나 값이 다르다"
    assert cs.check_python_pin() == []


def test_핀_파일이_커밋된다():
    """★ `.` 으로 시작하는 파일이라 **무시되면 CI 에만 없다** — 그러면 고친 것이
    아니라 고친 척이다."""
    import subprocess
    r = subprocess.run(["git", "check-ignore", "worker/.python-version"],
                       cwd=cs.ROOT, capture_output=True, text=True)
    assert r.returncode != 0, "worker/.python-version 이 gitignore 에 걸린다"


def test_핀_파일이_없으면_없다고_한다(tmp_path, monkeypatch):
    """★ **「못 읽었다」 를 「3.13 이다」 로 읽으면 안 된다**(DECISIONS §59). 기본값을
    돌려주면 핀 파일을 지운 날 **검사가 제 손으로 통과를 만든다.**"""
    monkeypatch.setattr(cs, "ROOT", tmp_path)
    assert cs.적힌파이썬() is None
    (tmp_path / "worker").mkdir()
    (tmp_path / "worker/.python-version").write_text("  \n", encoding="utf-8")
    assert cs.적힌파이썬() is None, "빈 파일을 값으로 읽는다"
    (tmp_path / "worker/.python-version").write_text("3.13\n", encoding="utf-8")
    assert cs.적힌파이썬() == "3.13"


def test_main_이_핀_검사를_부른다():
    """★ **함수가 있어도 `main` 이 안 부르면 `doctor` 는 아무것도 못 본다**(§21).
    `test_fails_가_갈래_검사를_부른다` 와 같은 자리다."""
    src = (cs.ROOT / "tools/check_static.py").read_text(encoding="utf-8")
    몸 = src[src.index("def main() -> int:"):]
    본문 = "\n".join(l for l in 몸.split("\n") if not l.lstrip().startswith("#"))
    assert "check_python_pin()" in 본문, "main 이 인터프리터 고정을 안 본다"
