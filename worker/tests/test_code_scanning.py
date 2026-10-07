"""`tools/code_scanning.py` — **코드 스캐닝이 지금 무엇을 들고 있는가**(DECISIONS §171).

★ **이 검사가 생긴 까닭은 다른 검사가 참말을 했기 때문이다.** `ci_status.py` 는 물을
  목록을 `.github/workflows/*.yml` 에서 꺼낸다 — 옳은 설계다. 그런데 **CodeQL 은 GitHub
  기본 설정으로 돌아 파일이 없다.** 그래서 「CI 가 이 커밋을 초록으로 봤다 — 워크플로 3
  전부」 가 **참이면서** `docs/proposal/html.js` 의 경보 둘을 이틀 동안 안 보여 줬다.
  **참말인 초록이 가장 오래 숨긴다.**

★ **네트워크 없이 전부 먹인다.** 판정은 순수 함수라 합성 경보로 가른다(§132 와 같은 꼴).
"""
import pathlib
import subprocess
import sys

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents
            if (p / "tools/code_scanning.py").exists())
sys.path.insert(0, str(ROOT / "tools"))
import code_scanning as CS


def _경보(번호=1, 규칙="js/incomplete-sanitization", 길="docs/proposal/html.js",
          줄=87, 심각="medium", sha="deadbee"):
    return {"number": 번호,
            "rule": {"id": 규칙, "security_severity_level": 심각},
            "most_recent_instance": {"commit_sha": sha,
                                     "location": {"path": 길, "start_line": 줄}}}


# 기본값 — **이 나무에서 안 바뀌었다**(그러면 막는다)
def 그대로(*_):
    return False


def test_열린_경보를_센다():
    막, 바뀜 = CS.판정([_경보(5, 줄=89), _경보(6, 줄=87)], 바뀜=그대로)
    assert len(막) == 2 and 바뀜 == []
    assert "html.js:89" in 막[0] and "#5" in 막[0]


def test_빈_목록은_조용하다():
    assert CS.판정([], 바뀜=그대로) == ([], [])


def test_심각도로_안_거른다():
    """★ **「medium 은 나중에」 가 이틀을 만들었다.** 열려 있으면 막는다."""
    for 심각 in ("low", "medium", "high", "critical", "note", None):
        assert len(CS.판정([_경보(심각=심각)], 바뀜=그대로)[0]) == 1, f"{심각} 를 흘린다"


def test_칸이_비어도_안_터진다():
    """★ **남이 주는 JSON 이다.** 칸이 빠졌다고 재는 자가 죽으면 그날 아무도 못 본다."""
    막, _ = CS.판정([{}, {"rule": {}}, {"most_recent_instance": {}}], 바뀜=그대로)
    assert len(막) == 3
    assert all("?" in x for x in 막)


def test_면제는_이름으로만_걸린다():
    """★ **수로 면제하지 않는다**(§167 의 갈래와 같은 처방). 「스물둘 중 스물하나」 가
    통과가 되면 **어느 하나가 새 것인지 아무도 모른다.**"""
    원 = dict(CS.면제)
    try:
        CS.면제["js/incomplete-sanitization"] = "시험용"
        assert CS.판정([_경보()], 바뀜=그대로) == ([], [])
        assert len(CS.판정([_경보(규칙="js/다른규칙")], 바뀜=그대로)[0]) == 1, \
            "다른 규칙까지 면제된다"
    finally:
        CS.면제.clear()
        CS.면제.update(원)


def test_저장소_이름을_코드에_안_박는다():
    """★ 포크에서도 **제 것**을 묻는다. 이름을 박으면 남의 저장소 경보를 보고 초록을 낸다."""
    src = (ROOT / "tools/code_scanning.py").read_text(encoding="utf-8")
    assert "CleverAIFox" not in src and "thoth" not in src.split('"""', 2)[2], \
        "저장소 이름이 코드에 박혀 있다"
    assert CS.저장소(ROOT), "origin 에서 owner/repo 를 못 읽는다"


def test_못_물으면_둘이고_초록이_아니다():
    """★ **「못 쟀다」 ≠ 「없다」**(DECISIONS §59). 404 도 0 이 아니다 — 코드 스캐닝이
    꺼져 있다는 뜻이고 그것은 **이 검사가 지켜 주지 않는다**는 말이다."""
    class _R:
        returncode, stdout, stderr = 1, "", "HTTP 404"
    것 = CS.묻는다("a/b", 부른다=lambda _: _R())
    assert isinstance(것, str) and "못 읽었다" in 것
    class _J:
        returncode, stdout, stderr = 0, "{}", ""
    assert isinstance(CS.묻는다("a/b", 부른다=lambda _: _J()), str), "목록이 아닌 것을 받았다"


def test_doctor_가_이_검사를_본다():
    """★ **사슬 밖에 둔 도구는 사람이 기억해야 돌고, 사람은 안 돌린다**(§152)."""
    sh = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    assert "tools/code_scanning.py" in sh, "doctor 가 코드 스캐닝을 안 본다"
    # ★ **CI 절 안에 둔다** — `--repo` 에서는 제 판정을 제가 묻지 않는다.
    머리 = sh.index("== CI ==")
    assert sh.index("tools/code_scanning.py") > 머리


def test_정말_도는가():
    """★ **글자로 본 것과 돌려 본 것은 다르다**(§152). 임포트만 되고 `main` 이 죽는
    꼴을 막는다. 여기서는 종료 코드가 0 · 1 · 2 중 하나이기만 하면 된다 —
    **무엇이 나오는가는 네트워크에 달렸고 그것은 이 시험의 일이 아니다.**"""
    r = subprocess.run([sys.executable, "tools/code_scanning.py"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode in (0, 1, 2), f"{r.returncode} / {r.stderr[-300:]}"
    assert r.stdout.strip(), "아무 말도 안 한다"


# ── 고치는 커밋을 제가 막지 않는다 (DECISIONS §172) ─────────────────────────


def test_스캔_뒤_그_파일이_바뀌면_안_막는다():
    """★ **`ship.sh` 는 `doctor` 가 FAIL 이면 죽는다.** 열려 있다는 이유만으로 막으면
    **경보를 고친 커밋이 영영 못 나간다** — 2026-10-07 에 실제로 그 교착에 빠졌다.
    ★ **코드 스캐닝은 「스캔된 커밋」 에 대해 답한다.** 아직 안 민 고침이 있으면
      그 답은 **과거의 나무**에 관한 것이다."""
    막, 바뀜 = CS.판정([_경보()], 바뀜=lambda *_: True)
    assert 막 == [] and len(바뀜) == 1
    assert "바뀌었다" in 바뀜[0]


def test_못_쟀으면_막는_쪽이다():
    """★ **「모르겠으니 넘어간다」 가 §171 을 만들었다**(§59)."""
    막, 바뀜 = CS.판정([_경보()], 바뀜=lambda *_: None)
    assert len(막) == 1 and 바뀜 == []


def test_나무가_더럽다는_이유로_안_꺼진다():
    """★ **묻는 것은 그 경보가 가리킨 파일 하나다.** 「작업 트리가 더러운가」 로 물으면
    **패치를 붙인 모든 판에서 관문이 통째로 꺼진다** — 관문을 끄는 가장 쉬운 길이
    거기 생긴다. 딴 파일이 바뀐 것은 이 경보와 상관이 없다."""
    바뀐파일 = {"docs/proposal/html.js"}

    def 섞어(_sha, 길):
        return 길 in 바뀐파일

    막, 바뀜 = CS.판정([_경보(5, 길="docs/proposal/html.js"),
                        _경보(6, 길="extension/src/broker.js")], 바뀜=섞어)
    assert len(바뀜) == 1 and "html.js" in 바뀜[0]
    assert len(막) == 1 and "broker.js" in 막[0], "딴 파일 경보까지 꺼졌다"


def test_바뀌었나가_git_종료코드를_가른다():
    """★ **0 · 1 · 그 밖**이 각각 다른 말이다. 그 밖은 **못 잼**이고 `None` 이다 —
    없는 커밋을 「안 바뀌었다」 로 읽으면 막고, 「바뀌었다」 로 읽으면 꺼진다."""
    class _R:
        def __init__(self, rc): self.returncode = rc
    assert CS.바뀌었나("abc", "x.js", 부른다=lambda _: _R(0)) is False
    assert CS.바뀌었나("abc", "x.js", 부른다=lambda _: _R(1)) is True
    assert CS.바뀌었나("abc", "x.js", 부른다=lambda _: _R(128)) is None
    assert CS.바뀌었나("", "x.js") is None, "sha 가 없는데 재려 든다"
    assert CS.바뀌었나("abc", "") is None, "경로가 없는데 재려 든다"


def test_실물_나무에서_돈다():
    """★ **합성만으로는 git 호출의 모양을 못 본다**(§152). HEAD 로 물으면 **안 바뀐
    파일**은 False 가 나와야 한다."""
    assert CS.바뀌었나("HEAD", "tools/code_scanning.py") in (False, True)
    assert CS.바뀌었나("HEAD", "없는파일.xyz") is False
