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


def test_정본_값이_모두_있으면_통과한다(tmp_path):
    want = [w for w, _ in dc.truths(ROOT)]
    assert dc.check(dc.text_of(_docx(tmp_path, want)), ROOT) == []


def test_값이_빠지면_걸린다(tmp_path):
    want = [w for w, _ in dc.truths(ROOT)]
    fails = dc.check(dc.text_of(_docx(tmp_path, want[1:])), ROOT)
    assert len(fails) == 1 and want[0] in fails[0]


def test_옛_값이_함께_있으면_걸린다(tmp_path):
    # ★ 있는지만 보면 옛 값과 새 값이 둘 다 있어도 통과한다.
    want = [w for w, _ in dc.truths(ROOT)] + ["코퍼스 2,478줄"]
    fails = dc.check(dc.text_of(_docx(tmp_path, want)), ROOT)
    assert any("2,478" in f for f in fails)
