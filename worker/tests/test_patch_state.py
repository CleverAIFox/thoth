"""받았는데 안 붙은 패치가 있나 (DECISIONS §156).

★ **2026-10-04 에 이것 때문에 거짓 제목이 밀렸다.** `apply_patch` 가 바탕 불일치로 막았는데
  뒤 명령들이 그 거절을 안 읽고 돌아, **기획서 재빌드만 든 커밋**에 `thoth-155: …` 제목이
  붙었다. 저장소는 멀쩡했으므로 `doctor` 는 초록이었다.

★ **「저장소가 맞나」 와 「하려던 일이 됐나」 는 다른 물음이다.** `doctor` 는 앞을 보고
  이 자는 뒤를 본다.
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("ps", ROOT / "tools/patch_state.py")
PS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PS)

def 없다(p, root=None) -> bool:   # 나무에 없다
    return False


def 있다(p, root=None) -> bool:    # 나무에 있다
    return True


def _함(tmp_path, **파일):
    for 이름, 글 in 파일.items():
        (tmp_path / 이름.replace("_", "-").replace("--", ".")).write_text(글, encoding="utf-8")
    return tmp_path


def test_안_붙은_것을_찾는다(tmp_path):
    (tmp_path / "thoth-1.patch").write_text("x\n", encoding="utf-8")
    assert PS.미적용(tmp_path, set(), 있나=없다) == ["thoth-1.patch"]


def test_영수증에_있으면_안_센다(tmp_path):
    p = tmp_path / "thoth-1.patch"
    p.write_text("x\n", encoding="utf-8")
    assert PS.미적용(tmp_path, {PS.씻은_해시(p)}, 있나=없다) == []


def test_나무에_있으면_안_센다(tmp_path):
    # ★ 영수증이 생기기 **전에** 붙은 옛 패치가 여기 걸린다. 역적용이 그것을 가른다.
    (tmp_path / "thoth-1.patch").write_text("x\n", encoding="utf-8")
    assert PS.미적용(tmp_path, set(), 있나=있다) == []


def test_수신함_밖_파일은_안_본다(tmp_path):
    (tmp_path / "그밖.txt").write_text("x\n", encoding="utf-8")
    (tmp_path / "seshat-9.patch").write_text("x\n", encoding="utf-8")
    assert PS.미적용(tmp_path, set(), 있나=없다) == [], "thoth-*.patch 만 본다"


def test_수신함이_없으면_조용하다(tmp_path):
    assert PS.미적용(tmp_path / "없다", set(), 있나=없다) == []


def test_줄끝을_벗기고_해시한다(tmp_path):
    """★ 브라우저를 거친 사본은 CRLF 가 된다. `apply_patch` 도 같은 정규화를 한 뒤 영수증을
    쓰므로 **두 곳이 다르게 씻으면 같은 패치가 달라 보이고**, 그러면 붙은 것이 미적용으로 뜬다."""
    a, b = tmp_path / "thoth-1.patch", tmp_path / "x"
    a.write_bytes(b"ab\r\ncd\r\n")
    b.write_bytes(b"ab\ncd\n")
    assert PS.씻은_해시(a) == PS.씻은_해시(b)


def test_영수증을_읽는다(tmp_path):
    r = tmp_path / "r.tsv"
    r.write_text("aaa\tthoth-1.patch\t2026-10-04\n\nbbb\tthoth-2.patch\t2026-10-04\n",
                 encoding="utf-8")
    assert PS.영수증(r) == {"aaa", "bbb"}, "빈 줄을 세거나 열을 안 가른다"


def test_영수증이_없으면_빈_집합이다(tmp_path):
    assert PS.영수증(tmp_path / "없다") == set()


def test_카나리아가_산다():
    PS._canary()


def test_selftest_가_0_으로_끝난다():
    assert PS.main(["--selftest"]) == 0


def test_수신함을_모르면_3_이다(monkeypatch):
    # ★ **못 잰 것을 통과로 세지 않는다**(§59). 3 은 「안 봤다」 고 `ship` 이 막지 않는다.
    monkeypatch.delenv("WIN_DOWNLOADS", raising=False)
    assert PS.main([]) == 3


def test_ship_이_0단계에서_묻는다():
    """★ **4분을 쓰고 알리면 늦다** — 실패는 그것이 일어난 자리에서 알린다(§37 · §52)."""
    몸 = (ROOT / "tools/ship.sh").read_text(encoding="utf-8")
    묻 = 몸.index("tools/patch_state.py")
    닥 = 몸.index('step "1/4  doctor"')
    assert 묻 < 닥, "doctor 를 다 돌리고 나서 묻는다"
    블록 = 몸[묻:닥]
    assert "\n  3)" in 블록, "`못 잼(3)` 을 따로 안 받는다 — 막아 버리면 수신함 없는 기계가 못 민다"
    # ★ **가지마다 따로 본다.** 첫 판은 `"die " in 블록` 으로 적었는데 `*)`(도구 고장)
    #   가지에도 `die` 가 있어 **미적용 가지를 통째로 지워도 통과했다** — 돌연변이가 잡았다.
    위반가지 = 블록[블록.index("\n  1)"):블록.index("\n  *)")]
    assert "die " in 위반가지, "미적용(1)을 찾고도 안 멈춘다"
    못잼가지 = 블록[블록.index("\n  3)"):블록.index("\n  1)")]
    assert "die " not in 못잼가지, "못 잰 것으로 막으면 수신함 없는 기계가 못 민다"
