"""usage_report 의 집계를 검사한다.

★ 이 도구가 내는 수가 #45 의 교환비가 된다. 집계가 틀리면 비용과 품질을
  맞바꾸는 판단이 틀린 수 위에 선다 — 검사도 코드이고 결함이 있다(§21).
"""
import importlib.util
import json
import pathlib

_spec = importlib.util.spec_from_file_location(
    "usage_report", pathlib.Path(__file__).resolve().parents[2] / "tools/usage_report.py")
ur = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ur)


def line(**kw):
    d = {"engine": "bedrock", "model": "m", "n": 3, "in_chars": 100,
         "sys_chars": 1149, "in_tok": 400, "out_tok": 200, "latency_ms": 900}
    d.update(kw)
    return f"INFO:thoth:usage {json.dumps(d, ensure_ascii=False)}"


def test_usage_줄만_뽑는다():
    text = "\n".join(["관계없는 줄", line(), "배치 파싱 실패 — 개별 호출로 되돌린다", line(n=1)])
    assert len(ur.parse(text)) == 2


def test_깨진_줄_하나가_판을_버리지_않는다():
    # 로그 형식이 바뀌어도 나머지는 읽힌다.
    text = "\n".join([line(), "usage {깨진 json", line()])
    assert len(ur.parse(text)) == 2


def test_배치_크기별로_가른다():
    rows = ur.parse("\n".join([line(n=3), line(n=3), line(n=1, in_chars=40)]))
    g = ur.group(rows)
    assert g[3]["calls"] == 2 and g[3]["units"] == 6
    assert g[1]["calls"] == 1 and g[1]["units"] == 1
    assert g[3]["body"] == 200 and g[1]["body"] == 40


def test_못_잰_토큰을_0_으로_더하지_않는다():
    # ★ 없는 것과 0 은 다르다(DECISIONS §59). 채워 넣으면 합계가 조용히 낮아진다.
    rows = ur.parse("\n".join([line(in_tok=400), line(in_tok=None, out_tok=None)]))
    g = ur.group(rows)
    assert g[3]["in_tok"] == 400           # 800 도 400.0 도 아니다
    assert g[3]["unmeasured"] == 1


def test_못_잰_건이_있으면_합계에_표시한다():
    out = "\n".join(ur.render("w.log", ur.parse(line(in_tok=None, out_tok=None))))
    assert "부분" in out


def test_개별_폴백을_따로_알린다():
    # 배치가 깨지면 호출 수가 n 배가 되고 과금 엔진에서는 그대로 돈이다.
    out = "\n".join(ur.render("w.log", ur.parse("\n".join([line(n=3), line(n=1)]))))
    assert "개별 폴백" in out


def test_한_건도_못_잰_칸은_0_이_아니라_대시다():
    # 0 으로 찍으면 "토큰을 쓰지 않았다" 로 읽힌다.
    out = "\n".join(ur.render("w.log", ur.parse(line(in_tok=None, out_tok=None))))
    assert "—" in out and " 0 " not in out


def test_못_잰_호출의_문자는_분모에_넣지_않는다():
    # 섞으면 문자당 토큰이 실제보다 낮게 나온다.
    rows = ur.parse("\n".join([line(in_tok=400, in_chars=100, sys_chars=100),
                               line(in_tok=None, out_tok=None, in_chars=900, sys_chars=900)]))
    assert ur.group(rows)[3]["m_chars"] == 200


def test_분모가_0_이면_비를_내지_않는다():
    assert ur._ratio(5, 0) == "—"


def test_usage_가_없으면_통과가_아니다(tmp_path, capsys):
    p = tmp_path / "w.log"
    p.write_text("아무 usage 줄도 없다\n", encoding="utf-8")
    assert ur.main([str(p)]) == 3


def test_웜업은_첫_줄이고_뺀_사실을_적는다(tmp_path, capsys):
    # ★ 말없이 빠진 수는 다음에 읽는 사람에게 없던 수가 된다.
    f = tmp_path / "w.log"
    f.write_text("\n".join([line(n=1), line(n=3), line(n=3)]), encoding="utf-8")
    assert ur.main(["--drop-warmup", str(f)]) == 0
    out = capsys.readouterr().out
    assert "웜업 1건을 뺐다" in out
    assert "요청 2회" in out              # 웜업이 빠진 수다


def test_웜업을_자동으로_빼지_않는다(tmp_path, capsys):
    # 프로덕션 로그에는 웜업이 없다. 말없이 한 줄을 버리면 그쪽이 틀린다.
    f = tmp_path / "w.log"
    f.write_text("\n".join([line(n=1), line(n=3)]), encoding="utf-8")
    assert ur.main([str(f)]) == 0
    out = capsys.readouterr().out
    assert "요청 2회" in out
    assert "웜업을 빼지 않았다면" in out


def test_읽지_못하면_1_이다(tmp_path):
    assert ur.main([str(tmp_path / "없다.log")]) == 1


def test_두_판을_나란히_낸다(tmp_path, capsys):
    a = tmp_path / "w3.log"
    b = tmp_path / "w9.log"
    a.write_text(line(n=3), encoding="utf-8")
    b.write_text(line(n=9), encoding="utf-8")
    assert ur.main([str(a), str(b)]) == 0
    out = capsys.readouterr().out
    assert "w3.log" in out and "w9.log" in out
