"""돌연변이 관문 자신을 본다 — `tools/mutate_gate.py` (DECISIONS §152).

★ **관문이 파일을 되돌리지 못하면 저장소를 망가뜨린다.** 가장 먼저 그것을 본다.

★ **선언이 썩는다.** 코드가 바뀌면 `전` 이 안 맞고, 그러면 관문은 「살아남음」 으로
  세면서 **실제로는 아무것도 안 재게 된다.** 정적으로 맞대 본다 — pytest 를 마흔 번
  돌리지 않고도 선언이 늙었는지 안다.

★ **관문 자체를 돌리는 것은 `doctor` 의 일이다.** 여기서 또 돌리면 17초를 두 번 쓴다.
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("mg", ROOT / "tools/mutate_gate.py")
mg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mg)

선언 = mg.읽기()
가드들 = mg.가드들(선언)   # ★ 관문이 쓰는 그 함수로 센다 — 두 곳이 정하지 않는다


# ── 파일을 되돌리는가 ───────────────────────────────────────────────────

def test_시험이_울어도_파일을_되돌린다(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1\n", encoding="utf-8")
    물었나, _ = mg.한건(f, "x = 1", "x = 2", ["false"])
    assert 물었나
    assert f.read_text(encoding="utf-8") == "x = 1\n", "되돌리지 않았다 — 저장소가 망가진다"


def test_시험이_안_울어도_파일을_되돌린다(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1\n", encoding="utf-8")
    물었나, _ = mg.한건(f, "x = 1", "x = 2", ["true"])
    assert not 물었나
    assert f.read_text(encoding="utf-8") == "x = 1\n"


# ── 겨냥이 흐리면 거절한다 ──────────────────────────────────────────────

def test_바꿀_자리가_없으면_거절한다(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("x = 1\n", encoding="utf-8")
    물었나, 까닭 = mg.한건(f, "없는 줄", "y", ["false"])
    assert not 물었나 and "못 찾았다" in 까닭


def test_바꿀_자리가_둘이면_거절한다(tmp_path):
    # ★ 두 곳이면 **가드가 아니라 아무 줄이나** 바꾸게 된다.
    f = tmp_path / "a.py"
    f.write_text("x = 1\nx = 1\n", encoding="utf-8")
    물었나, 까닭 = mg.한건(f, "x = 1", "y = 1", ["false"])
    assert not 물었나 and "두" in 까닭 or "2곳" in 까닭 or "흐리다" in 까닭


# ── 선언이 늙지 않았는가 ────────────────────────────────────────────────

def test_모든_선언의_겨냥이_파일에_꼭_한_번_있다():
    난것 = []
    for 이름, g in 가드들.items():
        글 = (ROOT / g["파일"]).read_text(encoding="utf-8")
        for m in g["돌연변이"]:
            n = 글.count(m["전"])
            if n != 1:
                난것.append(f'[{이름}] {m["이름"]} — {g["파일"]} 에 {n}번 나온다')
    assert 난것 == [], 난것


def test_바닥이_실제_선언_수와_맞다():
    # ★ 같은 수를 두 곳이 들면 갈린다(§132). 바닥이 실제보다 낮으면 톱니가 헐렁하다.
    전체 = sum(len(g["돌연변이"]) for g in 가드들.values())
    assert mg.MIN_돌연변이 == 전체, f"바닥 {mg.MIN_돌연변이} ≠ 선언 {전체}"
    assert mg.MIN_가드 == len(가드들), f"바닥 {mg.MIN_가드} ≠ 가드 {len(가드들)}"


def test_미선언_가드가_실제로_있는_파일이다():
    # ★ 못 보는 자리를 적되, **없는 파일을 적어 두면 그 칸이 쓰레기통이 된다.**
    for p in 선언.get("미선언", []):
        assert (ROOT / p).exists(), f"미선언에 적힌 {p} 가 없다"


def test_선언_파일이_까닭을_싣는다():
    raw = json.loads(mg.선언파일.read_text(encoding="utf-8"))
    assert any(k.startswith("_") for k in raw), "주석이 사라졌다"
    # ★ `읽기()` 를 직접 본다. 다시 거른 사전을 보면 **거르기가 꺼져도 조용하다.**
    assert not any(k.startswith("_") for k in 선언), "주석 열쇠가 가드로 샜다"
