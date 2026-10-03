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


# ---------- 종료 코드 0 과 3 을 가른다 (DECISIONS §127) ----------

def _돌린다(*인자):
    import subprocess
    import sys
    return subprocess.run([sys.executable, str(ROOT / "tools/docx_check.py"), *인자],
                          cwd=ROOT, capture_output=True, text=True)


def test_낡으면_3_이고_배포에서는_1_이다():
    """★ **상태를 문자열이 아니라 종료 코드로 낸다**(DECISIONS §127).

    처음에는 이것을 stdout 의 `WARN` 줄로만 냈는데 `doctor` 의 `0) ok` 가지가
    출력을 통째로 버려서 **화면에 아예 안 떴다.** 2026-10-03 에 `doctor` 초록 →
    밀기 → **CI 빨강**이 났다 — 「이 기계가 초록인 것과 CI 가 초록인 것은 다른
    말이다」(§170)를 그 자리에서 **새로 만든 셈**이다.

    ★ 이 시험은 저장소가 **어느 상태든** 참이다 — 낡았으면 3/1, 안 낡았으면 0/0.
      「지금 낡았나」 를 묻지 않고 **「두 자리가 같은 답을 내지 않는가」** 를 묻는다.
    """
    보통, 배포 = _돌린다(), _돌린다("--deploy")
    assert (보통.returncode, 배포.returncode) in {(0, 0), (3, 1)}, (보통.returncode, 배포.returncode)
    if 보통.returncode == 3:
        assert "기획서 배포" in 보통.stdout, "3 인데 무엇이 막히는지 안 적었다"


def test_doctor_가_3_을_받는다():
    """★ **부르는 쪽이 그 코드를 안 버리는가.** 코드를 만들어 놓고 `*)` 로 흘리면
    「도구가 죽었다」 로 읽힌다 — 그것이 이 자리의 원래 결함이다."""
    몸 = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    블록 = 몸[몸.index("DOCX_OUT="):]
    블록 = 블록[:블록.index("esac")]
    assert "\n  3)" in 블록, "doctor 가 3 을 따로 안 받는다"
    assert 'CI:-' in 블록, "CI 와 이 기계를 안 가른다"


# ── 행 번호 참조(DECISIONS §129) ────────────────────────────────────────────
#
# ★ **합성 번호를 글자로 박지 않는다.** `PLAN #N` 을 그냥 적으면 `check_docs` 의
#   `check_refs` 가 **이 시험 파일을 읽고** 「없는 행을 가리킨다」 로 운다 —
#   도구 쪽 카나리아와 같은 이유다. 번호는 세 자리를 넘겨 짜 맞춘다.
_산 = {9001, 9002}


def _글(앞, *ns):
    꼴 = "PLAN #%d"
    return (앞 + " " if 앞 else "") + " · ".join(
        (꼴 % n) if i == 0 else f"#{n}" for i, n in enumerate(ns))


def test_남의_저장소_PLAN_행을_금지한다():
    """★ **닫힌 행은 지워진다**(양쪽 PLAN 의 규약). 이 저장소에는 seshat 의 PLAN 을
    세는 자가 없고, 기획서를 읽는 사람은 비공개 저장소를 **열어 볼 수도 없다.**"""
    난 = dc.plan_ref_fails(_글("seshat", 9001), _산)
    assert 난 and "남의 저장소" in 난[0]


def test_남의_저장소_DECISIONS_절은_통과한다():
    """★ **음성 대조다.** 「남의 저장소 이름이 보이면 운다」 로 적으면 **append-only 라
    안 사라지는 참조까지 막는다** — 그러면 적을 자리가 없어지고 번호가 사라진다."""
    assert dc.plan_ref_fails("seshat DECISIONS §9001", set()) == []


def test_한국어_부사를_저장소_이름으로_읽지_않는다():
    """★ 첫 판이 「넉 달 **동안** PLAN #59」 를 「`동안` 저장소의 행」 으로 읽었다.
    임자는 ASCII 소문자 식별자나 적어 둔 한글 이름 하나여야 한다."""
    assert dc.plan_ref_fails(_글("넉 달 동안", 9001), _산) == []


def test_닫힌_자기_행을_든다():
    난 = dc.plan_ref_fails(_글("", 9003), _산)
    assert 난 and "9003" in 난[0]


def test_산_자기_행은_조용하다():
    assert dc.plan_ref_fails(_글("thoth", 9001, 9002), _산) == []


def test_이어_적은_번호도_본다():
    """★ `PLAN #59 · #61` 꼴에서 **뒤엣것만 죽어도** 잡아야 한다."""
    난 = dc.plan_ref_fails(_글("", 9001, 9003), _산)
    assert 난 and "9003" in 난[0]


def test_살아_있는_행을_PLAN_에서_읽는다():
    산 = dc.plan_rows(ROOT)
    assert 산, "docs/PLAN.md §1 표에서 행을 하나도 못 읽었다"
    assert all(isinstance(n, int) for n in 산)


def test_실제_생성기가_통과한다():
    """★ 검사를 넣는 날 이미 깨져 있으면 아무도 고치지 않고 꺼 버린다(DECISIONS §46).
    넣은 날 **죽은 참조 일곱을 먼저 고쳤다**(§129)."""
    assert dc.check_plan_refs(ROOT) == []


def test_낡았으면_어긋남보다_먼저_굽기를_말한다(tmp_path, monkeypatch, capsys):
    """★ **까닭을 결과보다 먼저 적는다**(DECISIONS §129).

    생성기가 docx 보다 새로우면 `RETIRED` 어긋남은 **고칠 결함이 아니라 안 구운 자국**이다.
    까닭을 안 적으면 **다시 구우면 끝날 일을 글을 고쳐서 맞추게 되고**, 그러면
    생성기와 docx 가 더 벌어진다.
    """
    docx = _docx(tmp_path, ["옛 말"])
    monkeypatch.setattr(dc, "DOCX", docx)
    monkeypatch.setattr(dc, "truths", lambda root: [("없는값", "합성")])
    monkeypatch.setattr(dc, "STRUCTURE", [])
    monkeypatch.setattr(dc, "RETIRED", [("옛 말", "합성")])
    monkeypatch.setattr(dc, "figures_of", lambda p: [])
    monkeypatch.setattr(dc, "check_plan_refs", lambda root: [])
    monkeypatch.setattr(dc, "check_build_lock", lambda root: ["docx 가 생성기보다 낡았다 — 합성"])
    monkeypatch.setattr(dc.sys, "argv", ["docx_check.py"])
    assert dc.main() == 1
    줄 = capsys.readouterr().out.splitlines()
    먼저 = next(i for i, x in enumerate(줄) if "먼저" in x)
    어긋남 = next(i for i, x in enumerate(줄) if "폐기된" in x)
    assert 먼저 < 어긋남, "까닭이 결과 뒤에 적혔다 — 읽는 사람이 글부터 고친다"


def test_안_낡았으면_굽기를_말하지_않는다(tmp_path, monkeypatch, capsys):
    """★ **음성 대조다.** 「언제나 굽으라고 한다」 면 그 말은 아무것도 안 가리킨다."""
    docx = _docx(tmp_path, ["옛 말"])
    monkeypatch.setattr(dc, "DOCX", docx)
    monkeypatch.setattr(dc, "truths", lambda root: [])
    monkeypatch.setattr(dc, "STRUCTURE", [])
    monkeypatch.setattr(dc, "RETIRED", [("옛 말", "합성")])
    monkeypatch.setattr(dc, "figures_of", lambda p: [])
    monkeypatch.setattr(dc, "check_plan_refs", lambda root: [])
    monkeypatch.setattr(dc, "check_build_lock", lambda root: [])
    monkeypatch.setattr(dc.sys, "argv", ["docx_check.py"])
    assert dc.main() == 1
    assert "먼저" not in capsys.readouterr().out


# ── 문서명 없는 맨 `#N`(DECISIONS §129) ────────────────────────────────────
#
# ★ 첫 판은 `PLAN #N` 만 봤고, 세어 보니 생성기가 `약관 확인(#2)` 꼴로 서른 자리를 더
#   들고 있었으며 그중 아홉이 이미 닫힌 행이었다. **좁게 물으면 좁게 답한다.**
def test_맨_번호를_든다():
    난 = dc.bare_ref_fails("약관 확인(" + "#%d" % 2 + ")을 앞에 둔다")
    assert 난 and "문서명 없는" in 난[0]


def test_이어_적기는_맨_번호가_아니다():
    """★ 이어 적은 번호(`PLAN` 뒤에 붙은 둘째)는 `plan_ref_fails` 가 이미 본다 — 두 번 울지 않는다."""
    assert dc.bare_ref_fails(_글("thoth", 9001, 9002)) == []


def test_16진_색과_앵커와_네자리는_안_든다():
    """★ **음성 대조다.** 전부 우는 규칙은 「운다」 만 보면 초록이고, 그러면 켤 수가 없다."""
    assert dc.bare_ref_fails('color: "' + "#1F3864" + '"') == []
    assert dc.bare_ref_fails("`" + "#question-prompt" + "`") == []
    assert dc.bare_ref_fails("quota" + "#2026-09") == []
