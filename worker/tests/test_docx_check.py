"""기획서 대조(DECISIONS §112). **있는지와 없는지를 둘 다 본다.**"""
import importlib.util
import io
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("docx_check", ROOT / "tools/docx_check.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)


def _docx(tmp_path, paragraphs):
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", f"<w:document><w:body>{body}</w:body></w:document>")
    p = tmp_path / "p.docx"
    p.write_bytes(buf.getvalue())
    return p


def test_카나리아가_산다():
    dc._canary()


def test_실제_기획서가_정본과_맞다():
    assert dc.check(dc.text_of(dc.DOCX), ROOT) == []


def test_실제_기획서의_그림이_산출물과_맞다():
    descrs = dc.figures_of(dc.DOCX)
    assert descrs, "그림이 하나도 없다"
    assert dc.check_figures(descrs, ROOT) == []


def test_정본_값이_모두_있으면_통과한다(tmp_path):
    want = [w for w, _ in dc.truths(ROOT)] + dc.STRUCTURE
    assert dc.check(dc.text_of(_docx(tmp_path, want)), ROOT) == []


def test_값이_빠지면_걸린다(tmp_path):
    want = [w for w, _ in dc.truths(ROOT)]
    fails = dc.check(dc.text_of(_docx(tmp_path, want[1:] + dc.STRUCTURE)), ROOT)
    assert len(fails) == 1 and want[0] in fails[0]


def test_옛_값이_함께_있으면_걸린다(tmp_path):
    # ★ 있는지만 보면 옛 값과 새 값이 둘 다 있어도 통과한다.
    want = [w for w, _ in dc.truths(ROOT)] + dc.STRUCTURE + ["코퍼스 2,478줄"]
    fails = dc.check(dc.text_of(_docx(tmp_path, want)), ROOT)
    assert any("2,478" in f for f in fails)


def test_요약판으로_돌아가면_걸린다(tmp_path):
    # ★ 숫자가 다 있어도 뼈대가 빠지면 통합본이 아니다(DECISIONS §116).
    want = [w for w, _ in dc.truths(ROOT)] + [x for x in dc.STRUCTURE if x != "Part III."]
    fails = dc.check(dc.text_of(_docx(tmp_path, want)), ROOT)
    assert len(fails) == 1 and "Part III." in fails[0]


def test_그림_사실이_늙으면_걸린다():
    # ★ 기준선이 바뀌었는데 그림을 다시 그리지 않은 상태를 흉내낸다(DECISIONS §116).
    ok = "json:docs/bench/baseline.json#golden.units=45"
    assert dc.check_figures(["src: " + ok], ROOT) == []
    fails = dc.check_figures(["src: none ¦ json:docs/bench/baseline.json#golden.units=44"], ROOT)
    assert len(fails) == 1 and "44" in fails[0]


def test_선언_없는_그림이_걸린다():
    assert any("사실 선언이 없다" in f for f in dc.check_figures([None, "그냥 그림"], ROOT))


def test_사실_문법마다_대조한다():
    assert dc.fact_fails("file:docs/MASTER.md~없는문자열zz", ROOT)
    assert dc.fact_fails("len:worker/app/glossary/aws.json=0", ROOT)
    assert dc.fact_fails("decisions:2026-09-12=§1–§2", ROOT)
    assert dc.fact_fails("모르는:x", ROOT)
    assert dc.fact_fails("external:seshat — 비공개", ROOT) == []


# ---------- 생성기 지문 (DECISIONS §126) ----------

def _생성기(tmp_path, 내용="x"):
    """최소한의 생성기 나무. `생성기지문` 은 없는 파일을 `없다` 로 적는다."""
    d = tmp_path / "docs/proposal/figures"
    d.mkdir(parents=True)
    (tmp_path / "docs/proposal/build.js").write_text(내용, encoding="utf-8")
    return tmp_path


def test_지문은_없는_파일도_적는다():
    """★ **빠진 것도 변화다.** 없는 파일을 건너뛰면 지우는 고침이 검사 밖으로 빠진다."""
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        것 = dc.생성기지문(_생성기(pathlib.Path(t)))
    assert 것["build.js"] != "없다"
    assert 것["lib.js"] == "없다"


def test_생성기가_바뀌면_지문도_바뀐다():
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        하나 = dc.생성기지문(_생성기(pathlib.Path(t), "a"))
    with tempfile.TemporaryDirectory() as t:
        둘 = dc.생성기지문(_생성기(pathlib.Path(t), "b"))
    assert 하나["build.js"] != 둘["build.js"]


def test_자물쇠가_없으면_낡은_것으로_읽는다():
    """★ **「모른다」 는 통과가 아니다**(DECISIONS §54). 자물쇠가 없으면 docx 가 생성기의
    지금 출력인지 **아무도 모르는** 상태이고, 그 상태로 밖에 내보내지 않는다."""
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        난 = dc.check_build_lock(_생성기(pathlib.Path(t)))
    assert 난 and "모른다" in 난[0]


def test_지문이_어긋나면_걸린다():
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        root = _생성기(pathlib.Path(t))
        (root / "docs/proposal/build.lock.json").write_text(
            json.dumps({"생성기": {k: "낡은지문000000" for k in dc.생성기}}), encoding="utf-8")
        난 = dc.check_build_lock(root)
    assert 난 and "낡았다" in 난[0] and "build.js" in 난[0]


def test_지문이_맞으면_통과한다():
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        root = _생성기(pathlib.Path(t))
        (root / "docs/proposal/build.lock.json").write_text(
            json.dumps({"생성기": dc.생성기지문(root)}, ensure_ascii=False), encoding="utf-8")
        난 = dc.check_build_lock(root)
    assert 난 == []


def test_빌드가_쓰는_지문과_검사가_읽는_지문이_같은_목록이다():
    """★ **두 곳에 적힌 같은 목록이다**(DECISIONS §14). `build.js` 가 쓰고 이 파일이 읽으므로
    한쪽만 늘면 **지문이 영원히 어긋나거나 영원히 맞는다.** 목록을 글자로 견준다."""
    import re
    js = (ROOT / "docs/proposal/build.js").read_text(encoding="utf-8")
    블록 = js[js.index("const 것 = ["):]
    블록 = 블록[:블록.index("];")]
    적힌 = re.findall(r'"([^"]+)"', 블록)
    이쪽 = list(dc.생성기)
    assert 이쪽, "검사 쪽 목록이 비었다"
    assert 적힌 == 이쪽, f"build.js {적힌}\ndocx_check {이쪽}"


def test_저장소의_자물쇠가_채워져_있다():
    """★ **씨앗 시험이 제 할 일을 하고 죽었다**(DECISIONS §126).

    기전을 세운 날(2026-10-03 01:00) docx 는 이미 낡아 있었고, 그 자리에서 참 지문을 적으면
    **낡은 것을 「최신」 이라고 적는 일**이었다. 그래서 자물쇠를 빈 채로 넣고
    `test_저장소의_자물쇠가_씨앗_상태다` 로 그 빈 상태를 못 박았다 — 「채워지는 날 스스로
    빨개져 지워야 할 시험임을 알린다」 고 적어 두고. **같은 날 01:04 에 실제로 빨개졌다.**

    그 자리를 뒤집은 것이 이 시험이다. 이제 무는 것은 반대쪽이다 — **한 번도 안 만든 상태로
    되돌아가지 않는가.** 지문이 지금 생성기와 맞는지는 `docx_check` 가 보고(배포에서 실패),
    여기가 보는 것은 **자물쇠가 비어 있지 않은가** 하나다.
    """
    import json
    것 = json.loads((ROOT / "docs/proposal/build.lock.json").read_text(encoding="utf-8"))
    assert 것.get("생성기"), "자물쇠가 비었다 — bash tools/build_proposal.sh 를 한 번 돌린다"
    assert set(것["생성기"]) == set(dc.생성기), "자물쇠가 든 파일 목록이 검사와 다르다"
