"""시험이 부른 쉘을 보지 않는가 (DECISIONS §147).

★ **2026-10-04 실측 — `WORKER_TOKEN` 하나로 41개가 깨졌다.** 코드는 멀쩡했고
  저장소도 멀쩡했다. **배포 뒤 `smoke.sh` 를 돌리려고 저장소가 시킨 대로 `export`
  한 쉘**에서 `doctor` 를 돌린 것이 전부다.

★ **묻는 것은 「`WORKER_TOKEN` 이 비었나」 가 아니라 「선언된 설정 중 새 들어온 것이
  있나」** 다(족 가드). 새 키가 `.env.example` 에 생기면 **고칠 것 없이** 덮인다.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conftest as C


# ── 기전이 실제로 도는가 ────────────────────────────────────────────────
#
# ★ **세션의 `os.environ` 으로는 못 잰다.** `tests/test_sweep_cache.py` 가 `.env` 를
#   통째로 프로세스에 싣고 `tests/test_pairs.py` 는 `ENGINE`·`CACHE` 를 박는다 —
#   **여럿이 쓰는 공유 상태라 거기서 읽은 값은 아무것도 증명하지 않는다.** 그렇게
#   쓴 시험을 한 번 썼다가 지웠다. **예외 목록을 손으로 기르는 것이 답이 아니다.**
# ★ **그래서 더러운 환경을 만들어 하위 프로세스에서 묻는다.**

def test_모듈을_들이는_것만으로_비워진다():
    """★ **위 둘은 깨끗한 환경에서 공허하게 통과한다.** 더러운 환경이 없으면 잴 것도
    없기 때문이다 — 그래서 **더러운 환경을 만들어서** 묻는다. 돌연변이 시험이
    「아예 안 비운다」 를 살려 보낸 자리가 바로 여기였다.
    """
    import subprocess
    here = str(Path(__file__).resolve().parent)
    코드 = ("import sys, os; sys.path.insert(0, %r); import conftest; "
          "print('WORKER_TOKEN' in os.environ)" % here)
    r = subprocess.run([sys.executable, "-c", 코드],
                       env={**os.environ, "WORKER_TOKEN": "zzz"},
                       capture_output=True, text=True)
    assert r.stdout.strip() == "False", f"conftest 를 들여도 안 비워졌다\n{r.stdout}{r.stderr}"


def test_더러운_환경을_실제로_만든다():
    """★ 음성 대조 — 위 시험이 **conftest 없이도 참**이면 아무것도 안 재는 것이다."""
    import subprocess
    r = subprocess.run([sys.executable, "-c", "import os; print('WORKER_TOKEN' in os.environ)"],
                       env={**os.environ, "WORKER_TOKEN": "zzz"},
                       capture_output=True, text=True)
    assert r.stdout.strip() == "True", "더러운 환경이 안 만들어졌다 — 위 시험이 공허하다"


# ── 비우는 일 자체 ──────────────────────────────────────────────────────

def test_선언된_키를_파일에서_읽는다(tmp_path):
    # ★ **목록을 손으로 들면 `.env.example` 과 갈린다.** 파일에서 읽는지 본다.
    p = tmp_path / ".env.example"
    p.write_text("NEW_KEY=1\n# 주석\nANOTHER_ONE=2\nnot_a_key=3\n", encoding="utf-8")
    assert C.선언된_키(p) == ["ANOTHER_ONE", "NEW_KEY"]


def test_선언된_것만_지운다(tmp_path):
    p = tmp_path / ".env.example"
    p.write_text("ZZZ_ONE=1\n", encoding="utf-8")
    가짜 = {"ZZZ_ONE": "x", "PATH": "/usr/bin", "HOME": "/home/x"}
    지운것 = C.환경을_비운다(가짜, p)
    assert 지운것 == ["ZZZ_ONE"]
    assert 가짜 == {"PATH": "/usr/bin", "HOME": "/home/x"}, "남의 변수를 건드렸다"


def test_없는_키는_안_센다(tmp_path):
    # ★ 음성 대조 — 전부 지웠다고 세는 자는 아무것도 안 재는 것이다.
    p = tmp_path / ".env.example"
    p.write_text("ZZZ_ONE=1\nZZZ_TWO=2\n", encoding="utf-8")
    assert C.환경을_비운다({"ZZZ_TWO": "x"}, p) == ["ZZZ_TWO"]
    assert C.환경을_비운다({}, p) == []


def test_파일이_없으면_조용히_넘어간다(tmp_path):
    # ★ 시험이 저장소 밖에서 돌 수도 있다. 거기서 터지면 **시험이 못 돈다.**
    assert C.선언된_키(tmp_path / "없다") == []
    assert C.환경을_비운다({"WORKER_TOKEN": "x"}, tmp_path / "없다") == []


# ── 정본이 하나인가 ─────────────────────────────────────────────────────

def test_env_example_이_실제로_키를_싣고_있다():
    # ★ `.env.example` 이 비면 **비우는 일이 조용히 아무것도 안 하게 된다.**
    #   그러면 이 가드 전체가 꺼지면서 화면은 초록이다.
    키 = C.선언된_키()
    assert len(키) >= 20, f"선언된 키가 {len(키)}개뿐이다 — 정본이 맞나"
    assert "WORKER_TOKEN" in 키
