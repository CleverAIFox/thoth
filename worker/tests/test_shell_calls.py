"""셸이 **없는 이름을 부르면 조용히 초록이 된다**(DECISIONS §190).

★ **이것이 실제로 일어났다.** §186 이 `doctor.sh` 에 인프라 표류 눈 둘을 달면서
  `no` 대신 `fail` 이라고 적었다. `fail` 은 정의된 적이 없다. 배시는 `set -uo pipefail`
  아래에서 **없는 명령을 만나면 stderr 에 한 줄 적고 그대로 다음 줄로 간다** —
  `FAIL=1` 이 안 서고, 종료 코드가 0 이고, **CI 가 초록이다.**

      $ fail "안 올렸다"
      line 4: fail: command not found       ← stderr. 아무도 안 읽는다
      $ echo $?
      0                                     ← 초록

  즉 §186 이 「CI 의 눈이 하나 비어 있었다」 를 고치려고 단 눈 둘이 **달린 적이 없다.**

★ **왜 아무도 못 봤나.** 두 줄 다 **한 번도 안 밟히는 가지**다(§182). 하나는
  `tools/infra_applied.json` 이 **없을 때**만, 다른 하나는 **표류했을 때**만 돈다.
  내 기계에서도 CI 에서도 둘 다 참이 아니었으므로 그 줄은 영영 안 돌았다.
  `bash -n` 은 문법만 보고, `shellcheck` 은 「이 이름이 실재하나」 를 못 묻는다.

★ **이 검사가 묻는 것 — 그리고 안 묻는 것.**
  묻는다 : `낱말 "따옴표 인자"` 꼴로 **줄 머리에서** 부르는 이름이 실재하는가.
           `ok` · `no` · `skip` · `warn` 같은 보고 함수가 전부 이 꼴이고, `fail` 도 그랬다.
  **안 묻는다** : 인자 없이 부르는 것 · 변수로 부르는 것(`$CMD "x"`) · 파이프 뒤 ·
           `$( )` 안. 셸을 제대로 파싱해야 보이는 자리이고, 여기서는 **안 본다.**

★ **좁힌 까닭을 적어 둔다.** 처음에는 셸 전체를 파싱해 「줄 머리 이름이 전부 실재하나」
  를 물으려 했다. `shlex` 까지 써 봤지만 heredoc · `case` 꼴 · 여러 줄 작은따옴표에 담긴
  파이썬 때문에 `def` · `from` · `href` 같은 것이 **셸 호출로 읽혀 거짓 빨강**이 났다.
  **거짓 빨강은 사람이 검사를 끄게 만든다**(§126) — 넓고 틀린 것보다 **좁고 맞는 것**을
  택했다. 지금 꼴로 저장소의 셸 7개에서 거짓 빨강 0이고, 그 날의 버그는 잡는다.
"""
import pathlib
import re
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]

# ★ **기계에 없을 수 있는 바깥 도구.** 여기 적는 것은 「없어도 된다」 가 아니라
#   **「이 검사가 판단하지 않는다」** 다 — 그 자리를 지키는 것은 `doctor` 의 SKIP 이다.
바깥 = {"aws", "terraform", "gh", "uv", "uvx", "npm", "npx", "node", "ollama", "jq",
        "shellcheck", "ruff", "playwright", "zip", "unzip", "rsync"}

내장 = set("""echo printf export local read eval exec trap test source return exit cd set
unset declare command type alias case esac if then else elif fi for while until do done
shift true false let builtin getopts wait kill umask times hash readarray mapfile""".split())

_부름 = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s+["\']')
_정의 = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\)", re.M)


def 셸들() -> list[pathlib.Path]:
    out = subprocess.run(["git", "ls-files", "*.sh"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    return [ROOT / x for x in out]


def 정의된_함수(글: str) -> set[str]:
    return set(_정의.findall(글))


def 모든_정의() -> set[str]:
    """★ **들여오는 파일의 함수도 센다.** `tools/lib/*.sh` 를 `.` 로 읽어 쓰므로,
    한 파일만 보면 남이 정의한 이름을 「없다」 로 읽어 **거짓 빨강**이 난다."""
    것 = set()
    for p in 셸들():
        것 |= 정의된_함수(p.read_text(encoding="utf-8"))
    return 것


def 없는_이름(경로: pathlib.Path, 정의: set[str] | None = None) -> list[str]:
    정의 = 모든_정의() if 정의 is None else 정의
    부른 = set()
    for 줄 in 경로.read_text(encoding="utf-8").splitlines():
        s = 줄.strip()
        if not s or s.startswith("#"):
            continue
        m = _부름.match(s)
        if m:
            부른.add(m.group(1))
    return sorted(x for x in (부른 - 정의 - 내장 - 바깥) if shutil.which(x) is None)


def test_셸_파일을_찾았다():
    # ★ **0개를 통과로 세지 않는다**(§59). 못 찾으면 이 시험은 아무것도 안 묻는다.
    것 = 셸들()
    assert len(것) >= 5, 것


def test_보고_함수가_실제로_정의돼_있다():
    # ★ `doctor` 가 FAIL 을 적는 길은 `no` 하나다. 그 이름이 실재하는지부터 묻는다.
    것 = 정의된_함수((ROOT / "tools/doctor.sh").read_text(encoding="utf-8"))
    assert {"ok", "no", "skip", "warn"} <= 것, sorted(것)


def test_doctor_가_없는_이름을_안_부른다():
    # ★ **이 한 줄이 §186 의 눈 둘을 되살린다.** `fail` → `no`.
    assert 없는_이름(ROOT / "tools/doctor.sh") == []


def test_모든_셸이_없는_이름을_안_부른다():
    정의 = 모든_정의()
    흠 = {str(p.relative_to(ROOT)): 없는_이름(p, 정의) for p in 셸들()}
    assert {k: v for k, v in 흠.items() if v} == {}


def test_없는_이름을_넣으면_잡는다(tmp_path):
    # ★ **관문이 무는지를 본다**(§152). 「검사를 더했다」 와 「검사가 문다」 는 다른 말이다.
    p = tmp_path / "x.sh"
    p.write_text('fail "없는 이름"\n', encoding="utf-8")
    assert 없는_이름(p, {"no"}) == ["fail"]


def test_박힌_파이썬을_셸_호출로_안_읽는다(tmp_path):
    # ★ **거짓 빨강이 안 나야 한다**(§126). `doctor.sh` 는 파이썬을 여러 줄 따옴표에
    #   담는다 — `from app import x` · `def g(n):` · `except ValueError:` 가 전부
    #   그 안에 있다. 인자가 **따옴표로 시작할 때만** 호출로 읽어 그 셋을 피한다.
    p = tmp_path / "y.sh"
    p.write_text("python3 -c '\nfrom app import x\ndef g(n):\n    pass\nexcept ValueError:\n'\n",
                 encoding="utf-8")
    assert 없는_이름(p, set()) == []


def test_배시가_없는_이름에_안_멈춘다():
    # ★ **이 시험이 왜 있어야 하는지의 근거다.** 배시가 멈춰 준다면 이 관문은 없어도 된다.
    #   멈추지 않는다는 것을 **글이 아니라 실행으로** 적어 둔다.
    글 = 'set -uo pipefail\nFAIL=0\nno(){ FAIL=1; }\nfail "x"\nexit "$FAIL"\n'
    r = subprocess.run(["bash", "-c", 글], capture_output=True, text=True)
    assert r.returncode == 0, "배시가 멈춘다면 이 관문은 없어도 된다"
    assert "command not found" in r.stderr
