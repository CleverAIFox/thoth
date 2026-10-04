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


# ── 종료코드 — 도구 고장을 「물었다」 로 세지 않는다 (DECISIONS §153) ──────

def _코드(monkeypatch, 코드: int) -> None:
    import subprocess
    monkeypatch.setattr(mg.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess([], 코드, "", ""))


def test_시험이_울면_물었다고_한다(tmp_path, monkeypatch):
    f = tmp_path / "a.py"; f.write_text("x = 1\n", encoding="utf-8")
    _코드(monkeypatch, 1)
    assert mg.한건(f, "x = 1", "x = 2", ["x"])[0] is True


def test_전부_통과하면_안_물었다고_한다(tmp_path, monkeypatch):
    f = tmp_path / "a.py"; f.write_text("x = 1\n", encoding="utf-8")
    _코드(monkeypatch, 0)
    물었나, 까닭 = mg.한건(f, "x = 1", "x = 2", ["x"])
    assert 물었나 is False and "안 붙들고" in 까닭


def test_도구가_깨지면_물었다고_안_한다(tmp_path, monkeypatch):
    """★ **`!= 0` 으로 보면 거짓 초록이다**(DECISIONS §153).

    선언한 시험 이름이 하나 틀리면 pytest 는 **4** 로 죽는다. 실물로 확인했다 — 가드를
    완전히 망가뜨리고 없는 시험 파일을 겨냥했더니 **「물었다」 로 찍혔다.**
    **5(모은 시험이 0)** 도 같은 자리다.
    """
    import pytest
    f = tmp_path / "a.py"
    for 코드 in (2, 3, 4, 5):
        f.write_text("x = 1\n", encoding="utf-8")
        _코드(monkeypatch, 코드)
        with pytest.raises(SystemExit) as e:
            mg.한건(f, "x = 1", "x = 2", ["x"])
        assert e.value.code == 2, f"{코드} 를 도구 고장으로 안 본다"
        assert f.read_text(encoding="utf-8") == "x = 1\n", "도구 고장으로 멈추면서 안 되돌렸다"


# ── 되돌리기 ──────────────────────────────────────────────────────────────

def test_못_되돌리면_멈춘다(tmp_path, monkeypatch):
    """★ **`finally` 는 조용히 실패한다.** 되돌리기가 실패해도 아무도 안 보면 뚫린 소스가
    남고 **그 뒤의 모든 판정이 거짓**이 된다."""
    import pytest
    f = tmp_path / "a.py"; f.write_text("x = 1\n", encoding="utf-8")
    _코드(monkeypatch, 1)
    원래쓰기 = type(f).write_text
    쓴횟수 = {"n": 0}

    def 두번째쓰기는_딴것(self, data, **kw):
        쓴횟수["n"] += 1
        return 원래쓰기(self, "망가진 것\n" if 쓴횟수["n"] == 2 else data, **kw)

    monkeypatch.setattr(type(f), "write_text", 두번째쓰기는_딴것)
    with pytest.raises(SystemExit) as e:
        mg.한건(f, "x = 1", "x = 2", ["x"])
    assert e.value.code == 2


def test_신호를_받으면_되돌리고_죽는다(tmp_path, monkeypatch):
    """★ **`try/finally` 는 신호에 안 돈다**(DECISIONS §153). seshat 이 같은 도구를
    `timeout` 으로 끊었다가 검사기 한 파일이 **주석 269줄을 잃은 채** 남았고, 그 망가진
    도구가 **조용히 틀린 일을 했다.**"""
    import pytest
    f = tmp_path / "a.py"
    f.write_text("뚫린 것\n", encoding="utf-8")
    monkeypatch.setitem(mg._뚫린것, f, "원본\n")
    with pytest.raises(SystemExit) as e:
        mg._되돌리고_죽는다(15, None)
    assert f.read_text(encoding="utf-8") == "원본\n" and e.value.code == 130


def test_되돌리는_길에서_이름_때문에_안_죽는다(tmp_path):
    # ★ `relative_to` 는 ROOT 밖 경로에 `ValueError` 를 던진다 — 그러면 **남은 파일을
    #   못 되돌린다.** 되돌리는 핸들러가 되돌리다 죽는 꼴이다.
    assert mg._이름(tmp_path / "밖.py") == str(tmp_path / "밖.py")
    assert mg._이름(mg.ROOT / "tools/mutate_gate.py") == "tools/mutate_gate.py"


def test_신호를_main_머리에서_받는다():
    몸 = (mg.ROOT / "tools/mutate_gate.py").read_text(encoding="utf-8")
    머리 = 몸.split("def main()")[1].split("ap = argparse")[0]
    assert "signal.signal(_sig, _되돌리고_죽는다)" in 머리, (
        "`main` 머리에서 안 받으면 **잊을 자리**가 생긴다")


# ── 바이트코드 — 길이가 같은 돌연변이의 덫 (DECISIONS §157) ────────────────

def test_되돌린_뒤_바이트코드를_버린다(tmp_path):
    """★ **`return 3` → `return 0` 은 글자 수가 같다.** 파이썬은 소스의 크기와 mtime 으로
    캐시를 쓰므로 둘 다 같으면 **복원한 뒤에도 뚫린 바이트코드를 다시 쓴다.** 해시로
    소스를 확인해도 안 잡힌다 — 소스는 멀쩡하기 때문이다.

    2026-10-05 에 실제로 났다. 시험 하나가 **설명 없이** 틀렸고 원인을 엉뚱한 데서 찾았다.
    """
    f = tmp_path / "a.py"
    f.write_text("def main():\n    return 3\n", encoding="utf-8")
    캐시 = tmp_path / "__pycache__"
    캐시.mkdir()
    썩은 = 캐시 / "a.cpython-313.pyc"
    썩은.write_bytes(b"stale bytecode")
    mg.한건(f, "return 3", "return 0", ["false"])
    assert not 썩은.exists(), "복원했는데 옛 바이트코드가 남았다"
    assert f.read_text(encoding="utf-8") == "def main():\n    return 3\n"


def test_뚫린_동안_바이트코드를_안_만든다():
    몸 = (mg.ROOT / "tools/mutate_gate.py").read_text(encoding="utf-8")
    assert 'PYTHONDONTWRITEBYTECODE' in 몸, "뚫린 동안 캐시가 쌓인다 — 막는 것이 치우는 것보다 싸다"
    블록 = 몸[몸.index("def 한건("):몸.index("def main(")]
    assert "_바이트코드를_버린다(파일)" in 블록, "되돌린 뒤 캐시를 안 버린다"


def test_신호로_죽을_때도_바이트코드를_버린다():
    몸 = (mg.ROOT / "tools/mutate_gate.py").read_text(encoding="utf-8")
    블록 = 몸[몸.index("def _되돌리고_죽는다("):몸.index("def 읽기(")]
    assert "_바이트코드를_버린다(p)" in 블록, "끊겨 죽을 때 캐시가 남는다"


def test_전부_건너뛰면_까닭을_가른다(tmp_path, monkeypatch):
    """★ **건너뛴 시험은 안 문다**(DECISIONS §158). 의존성 없는 기계에서 `skip` 된 시험은
    **통과로 끝나므로** 「약해서 안 물었다」 와 구별이 안 된다 — 2026-10-05 에 CI 가 그렇게
    빨개졌고 진단에 시간을 썼다."""
    import subprocess
    f = tmp_path / "a.py"
    f.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(mg.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess([], 0, "4 skipped in 0.1s", ""))
    물었나, 까닭 = mg.한건(f, "x = 1", "x = 2", ["x"])
    assert not 물었나 and "건너뛰어졌다" in 까닭, 까닭


def test_통과와_건너뜀을_안_섞는다(tmp_path, monkeypatch):
    import subprocess
    f = tmp_path / "a.py"
    f.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(mg.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess([], 0, "3 passed, 1 skipped", ""))
    물었나, 까닭 = mg.한건(f, "x = 1", "x = 2", ["x"])
    assert not 물었나 and "안 붙들고" in 까닭, "하나라도 돌았으면 건너뜀이 아니다"
