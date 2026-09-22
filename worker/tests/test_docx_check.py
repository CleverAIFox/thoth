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
