r"""관문이 제 밖과 생사를 선언하나 (DECISIONS §157).

★ **가짜 도구 이름은 ASCII 다.** `doctor.sh` 에서 뽑는 정규식이 `[a-z_][a-z0-9_]*\.py` 라
  한글 이름은 애초에 안 걸린다 — 저장소 규약이기도 하다(셸이 받아도 shellcheck 가 못 읽는다).
  첫 판은 가짜를 한글로 지었고 **다섯이 터졌다. 자가 아니라 입력이 틀렸다.**

★ **0건이 목표인 검사는 깨끗해서 0 인지 죽어서 0 인지 못 가른다.** 그래서 **가짜 도구**로
  묻는다 — 저장소가 지금 조용한 것은 따로 한 줄로 본다.
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("cs", ROOT / "tools/check_scope.py")
CS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CS)


def _집(tmp_path, doctor: str, **도구) -> pathlib.Path:
    (tmp_path / "tools").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tools/doctor.sh").write_text(doctor, encoding="utf-8")
    for 이름, 글 in 도구.items():
        (tmp_path / "tools" / f"{이름}.py").write_text(글, encoding="utf-8")
    return tmp_path


밖있 = '"""이 자는 뜻은 안 본다."""\n'
생사있 = '"""글."""\ndef _canary(): pass\n'
둘다 = '"""이 자는 뜻은 안 본다."""\ndef _canary(): pass\n'


# ── 관문 고르기 — 목록을 안 만든다 ────────────────────────────────────────

def test_doctor_가_부르는_것만_본다(tmp_path):
    r = _집(tmp_path, "python3 tools/aa.py\n", aa=둘다, bb=둘다)
    assert CS.관문들(r) == ["aa.py"], "doctor 가 안 부르는 것까지 본다"


def test_없는_파일은_안_센다(tmp_path):
    # ★ 이름은 ASCII 여야 정규식에 걸린다 — 한글로 쓰면 **없어서 0 인지 이름 때문에 0 인지**
    #   못 가른다. 첫 판이 그랬고 돌연변이가 살아 돌아왔다.
    r = _집(tmp_path, "python3 tools/missing.py\npython3 tools/aa.py\n", aa=둘다)
    assert CS.관문들(r) == ["aa.py"], "없는 파일을 관문으로 센다"


def test_새_관문이_자동으로_걸린다(tmp_path):
    # ★ **목록을 안 만든다**(족 가드). 손 목록이면 새 관문이 조용히 샌다.
    r = _집(tmp_path, "python3 tools/aa.py\npython3 tools/bb.py\n", aa=둘다, bb='"""글."""\n')
    assert CS.흠(r) == ["bb.py:밖", "bb.py:생사"]


# ── 밖과 생사 ─────────────────────────────────────────────────────────────

def test_둘_다_있으면_조용하다(tmp_path):
    assert CS.흠(_집(tmp_path, "python3 tools/aa.py\n", aa=둘다)) == []


def test_밖이_없으면_운다(tmp_path):
    assert CS.흠(_집(tmp_path, "python3 tools/aa.py\n", aa=생사있)) == ["aa.py:밖"]


def test_생사가_없으면_운다(tmp_path):
    assert CS.흠(_집(tmp_path, "python3 tools/aa.py\n", aa=밖있)) == ["aa.py:생사"]


def test_selftest_도_생사로_친다(tmp_path):
    글 = '"""이 자는 뜻은 안 본다."""\nif "--selftest" in []: pass\n'
    assert CS.흠(_집(tmp_path, "python3 tools/aa.py\n", aa=글)) == []


def test_아무_글이나_밖으로_안_읽는다(tmp_path):
    # ★ **넓히면 거짓 초록이다.** 「본다」 가 들어 있다고 한계를 적은 것이 아니다.
    글 = '"""이 자는 전부를 본다."""\ndef _canary(): pass\n'
    assert CS.흠(_집(tmp_path, "python3 tools/aa.py\n", aa=글)) == ["aa.py:밖"]


# ── 장부 ──────────────────────────────────────────────────────────────────

def test_장부에_없는_것만_운다():
    새것, 갚음 = CS.견준다(["aa.py:밖", "bb.py:생사"], {"aa.py:밖"})
    assert 새것 == ["bb.py:생사"] and 갚음 == []


def test_갚은_것을_찍는다():
    # ★ 안 찍으면 장부는 영원히 안 줄고, **줄지 않는 장부는 영구 면제**가 된다.
    새것, 갚음 = CS.견준다([], {"aa.py:밖"})
    assert 새것 == [] and 갚음 == ["aa.py:밖"]


def test_장부의_자리가_실재한다():
    # ★ 없는 파일이 장부에 남으면 그 칸이 **쓰레기통**이 된다 — 영원히 「갚았다」 로 뜬다.
    문 = set(CS.관문들())
    for x in CS.장부():
        파일, _, 갈래 = x.partition(":")
        assert (ROOT / "tools" / 파일).exists(), f"장부의 {파일} 이 없다"
        assert 파일 in 문, f"{파일} 은 doctor 가 안 부른다 — 장부에서 지운다"
        assert 갈래 in ("밖", "생사"), 갈래


def test_장부가_주석_열쇠를_안_센다(tmp_path):
    """★ **까닭이 장부로 새면 안 된다.** `_` 열쇠가 목록을 들 수도 있으므로 **꼴이 아니라
    이름**으로 거른다 — 「목록이면 장부다」 로 적으면 그날 조용히 샌다."""
    raw = json.loads(CS.장부파일.read_text(encoding="utf-8"))
    assert any(k.startswith("_") for k in raw), "까닭이 사라졌다"
    assert all(":" in x for x in CS.장부())
    가짜 = tmp_path / "d.json"
    가짜.write_text(json.dumps({"_갚는_법": ["이건 까닭이다"], "지금": ["aa.py:밖"]},
                              ensure_ascii=False), encoding="utf-8")
    assert CS.장부(가짜) == {"aa.py:밖"}, "`_` 열쇠가 목록을 들면 샌다"


def test_카나리아가_산다():
    CS._canary()


def test_selftest_가_0_으로_끝난다():
    assert CS.main(["--selftest"]) == 0


def test_지금_저장소가_조용하다():
    assert CS.main([]) == 0
