"""bench_golden 의 불변식 검사를 검사한다.

★ 검사도 코드이고 결함이 있다. 하루에 네 번 검사가 틀렸다(DECISIONS §21).
  일부러 위반을 만들어 잡히는지, 정상을 넣어 안 잡히는지 양쪽을 본다.
"""
import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "bench", pathlib.Path(__file__).resolve().parents[2] / "tools/bench_golden.py")
bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bench)

BOOK = {"record": "레코드", "consumer": "컨슈머",
        "consumer application": "컨슈머 애플리케이션", "catalog": "카탈로그"}


def unit(text, **kw):
    return {"text": text, "ratio_max": 0.75, "ratio_min": 0.30, **kw}


def test_정상은_통과한다():
    u = unit("The stream retains records for 168 hours in total here.",
             keep=[], terms=["record"])
    assert bench.check(u, "스트림은 레코드를 168시간 보관합니다.", BOOK) == []


def test_의문형_합니다체를_위반으로_보지_않는다():
    # 후처리가 만들어 내는 형태다. 검사가 이것을 잡으면 스스로를 부정한다.
    u = unit("Which condition must be confirmed?", keep=[], terms=[])
    assert bench.check(u, "어떤 조건을 확인해야 합니까?", BOOK) == []


def test_해요체는_잡는다():
    u = unit("Confirm the checkpoint position now please.", keep=[], terms=[])
    assert any("합니다체" in b for b in bench.check(u, "체크포인트를 확인하세요.", BOOK))


def test_원문에_없는_용어는_보지_않는다():
    u = unit("The shard count matches throughput.", keep=[], terms=["record"])
    assert not any("term" in b for b in bench.check(u, "샤드 수가 처리량과 맞습니다.", BOOK))


def test_긴_용어에_포함된_짧은_용어는_빼고_본다():
    u = unit("Every consumer application has checkpointed past the record.",
             keep=[], terms=["consumer", "consumer application"])
    ko = "모든 컨슈머 애플리케이션이 레코드를 지나 체크포인트했습니다."
    assert not any("term" in b for b in bench.check(u, ko, BOOK))


def test_길이가_과하면_덧붙임으로_잡는다():
    u = unit("Short source here.", keep=[], terms=[])
    bad = bench.check(u, "원문보다 훨씬 길게 늘어난 번역문을 여기에 넣습니다.", BOOK)
    assert any("덧붙임" in b for b in bad)


def test_길이가_모자라면_누락으로_잡는다():
    u = unit("A" * 200 + " records are retained for a long period of time.",
             keep=[], terms=[])
    assert any("누락" in b for b in bench.check(u, "짧습니다.", BOOK))


def test_물음표가_사라지면_잡는다():
    u = unit("Which condition must be confirmed?", keep=[], terms=[])
    assert any("물음표" in b for b in bench.check(u, "조건을 확인해야 합니다.", BOOK))


def test_keep_토큰이_번역되면_잡는다():
    u = unit("A Glue crawler populates the Data Catalog nightly here now.",
             keep=["Data Catalog"], terms=[])
    ko = "Glue 크롤러가 매일 밤 데이터 카탈로그를 채웁니다."
    assert any("keep" in b for b in bench.check(u, ko, BOOK))


def test_한글이_없으면_잡는다():
    u = unit("The stream retains records.", keep=[], terms=[])
    assert any("한글" in b for b in bench.check(u, "[KO] The stream retains records.", BOOK))
