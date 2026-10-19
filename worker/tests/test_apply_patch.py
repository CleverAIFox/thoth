"""`apply_patch.sh` 가 **세 갈래를 가르나**(DECISIONS §195 · §59).

★ **이 스크립트에 시험이 하나도 없었다.** 패치를 받는 모든 판이 이것을 지나가는데,
  묻는 자리가 없어서 2026-10-16 에 같은 밤에 **둘** 터졌다 :

  ㉠ `error: … already exists in working directory` 를 git 이 **정확히** 찍었는데,
     그 바로 아래에 「패치를 만든 시점과 다른 상태이거나」 를 붙였다. 바탕은 바로
     위에서 **맞다고 찍었는데도** 읽는 사람은 바탕을 의심한다.
  ㉡ 앞판이 만든 새 파일 여섯을 지우고 같은 패치를 다시 돌리니 **「이미 적용되어
     있다」 를 찍고 0 으로 끝났다.** 저장소는 **반쯤 붙은** 상태였다 — 영수증은
     「언젠가 붙였다」 를 알고 역방향 검사는 「되돌릴 수 있나」 를 아는데,
     **둘 다 「지금 다 있나」 를 모른다.** 이건 메시지 흠이 아니라 **틀린 초록**이다.

★ **글로 묻지 않는다 — 실제로 돌린다.** 임시 저장소를 만들고 진짜 패치를 지어
  `apply_patch.sh` 를 **부른다**. 「`already exists` 라는 글자가 소스에 있나」 를
  묻는 검사는 ㉠ 을 못 잡는다(그 글자는 틀린 판에도 있었다).
"""
import os
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/apply_patch.sh"


def _git(터: pathlib.Path, *a: str) -> str:
    r = subprocess.run(["git", *a], cwd=터, capture_output=True, text=True)
    assert r.returncode == 0, f"git {' '.join(a)} : {r.stderr}"
    return r.stdout


@pytest.fixture
def 터(tmp_path: pathlib.Path) -> pathlib.Path:
    """`apply_patch.sh` 가 혼자 설 수 있는 **최소 저장소**."""
    d = tmp_path / "repo"
    (d / "tools/lib").mkdir(parents=True)
    shutil.copy(SCRIPT, d / "tools/apply_patch.sh")
    shutil.copy(ROOT / "tools/lib/env.sh", d / "tools/lib/env.sh")
    (d / ".env.example").write_text("WIN_DOWNLOADS=\n", encoding="utf-8")
    (d / ".env").write_text(f"WIN_DOWNLOADS={tmp_path / 'dl'}\n", encoding="utf-8")
    (tmp_path / "dl").mkdir()
    (d / "base.txt").write_text("한 줄\n", encoding="utf-8")
    _git(d, "init", "-q", "-b", "main")
    _git(d, "add", "-A")
    _git(d, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "-m", "바탕")
    return d


def _패치를_짓는다(터: pathlib.Path) -> pathlib.Path:
    """`base.txt` 를 고치고 `new.txt` 를 **만드는** 패치. 바탕 선언을 붙인다."""
    나무 = _git(터, "rev-parse", "HEAD^{tree}").strip()
    (터 / "base.txt").write_text("한 줄\n두 줄\n", encoding="utf-8")
    (터 / "new.txt").write_text("새 파일\n", encoding="utf-8")
    _git(터, "add", "-A")
    본문 = _git(터, "diff", "--cached")
    _git(터, "reset", "-q")
    _git(터, "checkout", "--", "base.txt")
    (터 / "new.txt").unlink()
    p = pathlib.Path(_git(터, "rev-parse", "--show-toplevel").strip())
    받은곳 = p.parent / "dl" / "t.patch"
    받은곳.write_text(f"머리글\n\n----\n\n바탕 : {나무}\n\n{본문}", encoding="utf-8")
    return 받은곳


def _돌린다(터: pathlib.Path, *a: str):
    환경 = dict(os.environ)
    환경.pop("WIN_DOWNLOADS", None)        # .env 가 정본이다
    return subprocess.run(["bash", "tools/apply_patch.sh", *a], cwd=터,
                          capture_output=True, text=True, env=환경)


def test_붙는다(터):
    _패치를_짓는다(터)
    r = _돌린다(터, "t.patch")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "적용 완료" in r.stdout
    assert (터 / "new.txt").is_file()


def test_두_번_돌리면_이미_적용되어_있다(터):
    _패치를_짓는다(터)
    assert _돌린다(터, "t.patch").returncode == 0
    r = _돌린다(터, "t.patch")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "이미 적용되어 있다" in r.stdout


def test_새_파일이_사라지면_반쯤이라고_운다(터):
    # ★ **㉡ 그 자리다.** 영수증이 「붙였다」 고 하는데 패치가 만든 파일이 없다.
    #   앞판은 여기서 **「이미 적용되어 있다」 를 찍고 0 으로 끝났다.**
    _패치를_짓는다(터)
    assert _돌린다(터, "t.patch").returncode == 0
    (터 / "new.txt").unlink()
    r = _돌린다(터, "t.patch")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "반쯤 붙어 있다" in r.stderr, r.stderr
    assert "new.txt" in r.stderr, r.stderr
    assert "이미 적용되어 있다" not in r.stdout, r.stdout


def test_앞판_찌꺼기가_남으면_그렇게_말한다(터):
    # ★ **㉠ 그 자리다.** `git reset --hard` 는 추적 안 되는 파일을 안 지운다 —
    #   앞판이 만든 새 파일이 남은 채 정방향이 거절된다. 바탕은 **맞는데도**
    #   앞판은 「패치를 만든 시점과 다른 상태이거나」 를 찍었다.
    _패치를_짓는다(터)
    (터 / "new.txt").write_text("딴 손이 쓴 것\n", encoding="utf-8")
    r = _돌린다(터, "t.patch")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "앞판이 만든 파일이 남아 있다" in r.stderr, r.stderr
    assert "new.txt" in r.stderr, r.stderr
    # ★ **바탕을 의심하게 만들지 않는다.** 바탕은 맞다고 바로 위에서 찍었다.
    assert "바탕 맞다" in r.stdout, r.stdout
    assert "패치를 만든 시점과 다른 상태" not in r.stderr, r.stderr


def test_찌꺼기_안내가_쓸어담는_빗자루를_권하지_않는다(터):
    # ★ **지울 것을 정확히 아는 자리에서 `git clean` 을 권하지 않는다.** gitignore 된
    #   `node_modules` · `.build` 는 안 지워지지만, **틀렸을 때 알아차릴 자리가 없다.**
    _패치를_짓는다(터)
    (터 / "new.txt").write_text("x\n", encoding="utf-8")
    말 = _돌린다(터, "t.patch").stderr
    assert "이름으로 지운 뒤" in 말, 말
    assert "git clean -fd" not in 말, 말


def test_새_파일을_안_만드는_패치는_조용하다(터):
    # ★ **없는 병에 관문을 세우지 않는다**(§133). 고치기만 하는 패치는 목록이 비고
    #   이 자리는 아무 일도 안 한다.
    나무 = _git(터, "rev-parse", "HEAD^{tree}").strip()
    (터 / "base.txt").write_text("한 줄\n두 줄\n", encoding="utf-8")
    본문 = _git(터, "diff")
    _git(터, "checkout", "--", "base.txt")
    (터.parent / "dl" / "m.patch").write_text(
        f"머리글\n\n----\n\n바탕 : {나무}\n\n{본문}", encoding="utf-8")
    assert _돌린다(터, "m.patch").returncode == 0
    r = _돌린다(터, "m.patch")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "이미 적용되어 있다" in r.stdout
    assert "반쯤" not in r.stderr


def _함수(이름: str) -> str:
    """`apply_patch.sh` 에서 함수 하나를 **소스째** 떼어 온다 — 베끼면 한쪽만 늙는다(§91)."""
    글 = SCRIPT.read_text(encoding="utf-8")
    i = 글.index(f"{이름}(){{")
    j = 글.index("\n}\n", i) + 3
    return 글[i:j]


def test_새_파일_목록을_패치에서_읽는다(터):
    # ★ **배선을 잰다**(§173). `new_files` 를 **스크립트에서 떼어** 불러, 패치가 적은
    #   그대로 드는지 본다.
    받은곳 = _패치를_짓는다(터)
    r = subprocess.run(["bash", "-c", f'TMP="$1"\n{_함수("new_files")}\nnew_files',
                        "_", str(받은곳)], capture_output=True, text=True)
    assert r.stdout.split() == ["new.txt"], r.stdout + r.stderr


def test_비_ASCII_경로는_못_본다고_말한다(터):
    """★ **따옴표 경로는 이 눈 밖이다 — 그리고 그렇게 말한다**(§59).

    git 이 비 ASCII 경로를 `"b/\\354…"` 로 escape 하므로 `[ -e ]` 가 **있는 파일을
    없다고 읽는다.** 조용히 건너뛰면 다음 사람이 「다 봤다」 고 믿는다.
    """
    나무 = _git(터, "rev-parse", "HEAD^{tree}").strip()
    (터 / "한글.txt").write_text("x\n", encoding="utf-8")
    _git(터, "add", "-A")
    본문 = _git(터, "diff", "--cached")
    assert '"b/' in 본문, "git 이 경로를 안 쌌다 — 이 시험의 전제가 깨졌다"
    _git(터, "reset", "-q")
    (터.parent / "dl" / "q.patch").write_text(
        f"머리글\n\n----\n\n바탕 : {나무}\n\n{본문}", encoding="utf-8")
    r = _돌린다(터, "q.patch")
    # ★ 파일이 이미 있으니 역방향이 붙어 「이미 적용되어 있다」 가 맞다. 묻는 것은
    #   그 판정이 아니라 **못 본 것을 말했나** 다.
    assert r.returncode == 0, r.stdout + r.stderr
    assert "이 눈 밖 : 따옴표로 싸인 경로 1개" in r.stderr, r.stderr
    셋 = subprocess.run(["bash", "-c",
                        f'TMP="$1"\n{_함수("quoted_new")}\nquoted_new', "_",
                        str(터.parent / "dl" / "q.patch")], capture_output=True, text=True)
    assert 셋.stdout.strip() == "1", 셋.stdout + 셋.stderr


def test_셸에_한글_함수_이름이_없다():
    # ★ **§186 · §188 이 「함수 이름에는 한글을 받는다」 고 적었는데 모자랐다**(§195).
    #   배시는 받지만 **shellcheck 가 파싱을 못 하고 거기서 멈춘다** — 멈춘 뒤의
    #   셸 코드는 **조용히 검사 밖**이 된다. 이 저장소의 셸 함수는 전부 ASCII 였다 :
    #   규약이었는데 적혀 있지 않았고, 그래서 내가 한 번 어겼다.
    난것 = subprocess.run(["git", "ls-files", "-z", "*.sh"], cwd=ROOT,
                         capture_output=True, text=True)
    assert 난것.returncode == 0, "`git ls-files` 를 못 읽었다 — 못 쟀다는 뜻이다"
    쉘 = [x for x in 난것.stdout.split("\0") if x]
    assert len(쉘) >= 20, f"셸 파일이 {len(쉘)}개뿐이다 — 훑는 범위가 좁아졌다"
    흠 = {}
    for rel in 쉘:
        나쁜 = [l for l in (ROOT / rel).read_text(encoding="utf-8").splitlines()
               if not l.lstrip().startswith("#")
               and __import__("re").match(r"^\s*[^\x00-\x7f][^\s()]*\s*\(\)", l)]
        if 나쁜:
            흠[rel] = 나쁜[:2]
    assert 흠 == {}, 흠


# ── 색인이 더러우면 멈춘다 (§195) ─────────────────────────────────────────


def test_색인이_더러우면_멈춘다(터):
    """★ **2026-10-19 이 자리다.** `ship.sh` 가 `git add -A` 한 뒤 훅에 막혀 판 전체가
    **색인에 올라간 채** 남았는데, 앞판은 경고 한 줄만 찍고 **그냥 붙이려 들었다.**
    `git apply` 는 색인을 안 보므로 작업 트리의 앞판 내용과 겹쳐 **18 개가 전부
    거절**됐고, 그 열여덟 줄은 「바탕이 틀렸나」 로 읽혔다. 바탕은 맞았다."""
    _패치를_짓는다(터)
    # ★ **패치와 안 겹치는 것을 올린다.** 겹치는 것을 올리면 `git apply` 가 어차피
    #   거절해서 **멈춤이 일을 했는지 안 했는지 못 가른다** — 그 시험은 `exit 1` 을
    #   지워도 통과한다(돌연변이로 재서 알았다). 안 겹치면 **멈추지 않는 판은 붙는다.**
    (터 / "딴것.txt").write_text("안 겹친다\n", encoding="utf-8")
    _git(터, "add", "딴것.txt")
    r = _돌린다(터, "t.patch")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "색인에 올라간 변경이 있다" in r.stderr, r.stderr
    assert "적용 완료" not in r.stdout, r.stdout
    assert not (터 / "new.txt").exists(), "멈춘다고 해 놓고 붙였다"


def test_색인_안내가_restore_로_되는_척하지_않는다(터):
    # ★ **틀린 명령을 주는 것이 아무 명령도 안 주는 것보다 나쁘다.** `git restore .` 는
    #   색인을 안 건드린다 — 작업 트리를 **색인에서** 되돌리므로 같은 것이 돌아온다.
    _패치를_짓는다(터)
    (터 / "base.txt").write_text("x\n", encoding="utf-8")
    _git(터, "add", "base.txt")
    말 = _돌린다(터, "t.patch").stderr
    assert "git reset --hard HEAD" in 말, 말
    assert "안 지운다" in 말, 말


def test_작업트리만_더러우면_경고로_끝난다(터):
    # ★ **없는 병에 관문을 세우지 않는다**(§133). 작업 트리만 더러운 것은 `git apply`
    #   가 겹치면 거기서 운다 — 멈출 일이 아니다.
    _패치를_짓는다(터)
    (터 / "딴것.txt").write_text("안 겹친다\n", encoding="utf-8")
    r = _돌린다(터, "t.patch")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "색인에 올라간" not in r.stderr, r.stderr
    assert "적용 완료" in r.stdout


def test_add_N_은_색인이_더럽다고_안_센다(터):
    # ★ **이 저장소가 권하는 명령이 제 관문에 걸리면 안 된다**(§194 ㉢ 의 `git add -N`).
    #   의도만 올린 항목은 색인↔HEAD 차이에 **안 뜬다** — 재서 확인했다.
    _패치를_짓는다(터)
    (터 / "새눈.txt").write_text("x\n", encoding="utf-8")
    _git(터, "add", "-N", "새눈.txt")
    r = _돌린다(터, "t.patch")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "색인에 올라간" not in r.stderr, r.stderr
