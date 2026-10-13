"""`tools/shot_stale.py` — **옛 그림이 지금 화면인가**(DECISIONS §185).

★ **「있다」 와 「지금 것이다」 는 다른 말이다.** `build_proposal.sh` 의 건너뛰기는
  옛 그림이 **있나**만 봤다. 2026-10-12 에 183 이 `popup.html` 에 내보내기 버튼을
  달았는데, 크로미움 없는 기계에서 구우면 **버튼 없는 옛 그림**이 그대로 실리고
  `doctor` 는 「기획서가 정본과 맞다」 로 **초록**이었다 — 참말인 초록이다(§171).

★ **사실 선언으로는 못 잡는다.** `*.facts.json` 은 「이 글자가 그 파일에 있나」 라서
  **더해진 것을 못 본다.** 선언은 빠진 것을 잡고, 지문은 더한 것을 잡는다.

★ **셋을 가른다**(§59) — 0 건너뛴다 · 1 다르다 · **2 못 쟀다**. 곁파일이 없는 것은
  통과가 아니다.
"""
import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("shot_stale", ROOT / "tools/shot_stale.py")
ss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ss)


def _둘(a="1", b="2"):
    return {"f_popup": {"extension/popup.html": a},
            "f_preview_a": {"extension/preview.html": b}}


def test_같으면_건너뛴다():
    막, 못 = ss.흠(_둘(), _둘())
    assert (막, 못) == ([], [])


def test_원본이_바뀌면_막는다():
    막, 못 = ss.흠(_둘(a="1"), _둘(a="바뀜"))
    assert 못 == []
    assert len(막) == 1 and "popup.html" in 막[0]


def test_안_적힌_그림은_막는_것이_아니라_못_잰_것이다():
    # ★ **이 가름이 요점이다.** 「다르다」 로 적으면 사람이 **그림을 다시 찍어** 지나갈
    #   수 있다고 읽는다 — 그런데 **무엇과 다른지를 모르는 상태**다(§59).
    적힌 = {"f_popup": {"extension/popup.html": "1"}}
    막, 못 = ss.흠(적힌, _둘(a="1"))
    assert 막 == []
    assert any("f_preview_a" in x for x in 못)


def test_원본_목록이_늘어도_못_잰_것이다():
    적힌 = _둘()
    이제 = _둘()
    이제["f_popup"]["extension/popup.css"] = "새것"
    막, 못 = ss.흠(적힌, 이제)
    assert 막 == []
    assert any("popup.css" in x for x in 못)


def test_원본_목록이_줄어도_못_잰_것이다():
    적힌 = _둘()
    적힌["f_popup"]["extension/popup.css"] = "옛것"
    막, 못 = ss.흠(적힌, _둘())
    assert 막 == []
    assert any("popup.css" in x for x in 못)


def test_찍은것이_실재하는_파일을_가리킨다():
    # ★ **목록이 실물을 가리키는지 묻는다.** 틀리면 `지금()` 이 터지는데, 그 터짐은
    #   건너뛰는 가지에서만 나므로 **크로미움 있는 기계에서는 영영 안 밟힌다**.
    for 이름, 것들 in ss.찍은것.items():
        assert 것들, f"{이름} 이 아무것도 안 찍었다고 적혀 있다"
        for f in 것들:
            assert (ROOT / f).is_file(), f"{이름} 이 없는 파일 {f} 를 찍었다고 한다"


def test_팝업_그림이_팝업의_글과_꼴을_둘_다_든다():
    # ★ **버튼은 `popup.html` 에 있고 그 모양은 `popup.css` 에 있다.** 하나만 들면
    #   스타일만 바뀐 판을 **옛 그림으로 통과**시킨다 — 183 이 연 바로 그 구멍이다.
    것 = ss.찍은것["f_popup"]
    assert "extension/popup.html" in 것 and "extension/popup.css" in 것
    assert "extension/src/popup.js" in 것


def test_shots_가_같은_목록을_쓴다():
    # ★ **두 곳에 적으면 한쪽만 늙는다**(§91). `shots.py` 는 목록을 제 손으로 들지
    #   않고 `shot_stale` 에서 읽어 써야 한다.
    글 = (ROOT / "docs/proposal/figures/shots.py").read_text(encoding="utf-8")
    assert "shot_stale" in 글, "shots.py 가 정본 목록을 안 읽는다"
    assert "원본.json" in 글, "shots.py 가 원본 지문을 안 남긴다"
    for 이름 in ss.찍은것:
        assert f'원본지문("{이름}")' in 글, f"{이름} 의 지문을 안 남긴다"


def test_빌드가_건너뛰기_전에_물어본다():
    # ★ **가지가 한 번도 안 밟힐 수 있다**(§182 · §305 와 같은 결). 크로미움이 있는
    #   기계에서는 이 줄이 영영 안 돈다 — 그래서 **글로 묻는다**.
    글 = (ROOT / "tools/build_proposal.sh").read_text(encoding="utf-8")
    건너뛰기 = 글.split("화면 — 실제")[1]
    assert "shot_stale.py" in 건너뛰기, "건너뛰는 가지가 원본을 안 본다"
    자리 = 건너뛰기.index("shot_stale.py")
    끝 = 건너뛰기.index("건너뛴다 — 크로미움이 없다")
    assert 자리 < 끝, "원본을 보기 전에 건너뛴다고 적는다"


def test_실물로_돌려도_세_갈래가_선다(tmp_path):
    # ★ **순수 함수만 재면 배선을 안 잰다**(§173). 실제로 불러 본다.
    r = subprocess.run([sys.executable, str(ROOT / "tools/shot_stale.py")],
                       capture_output=True, text=True)
    assert r.returncode in (0, 1, 2), r.stdout + r.stderr
    # 곁파일이 없으면 2, 있으면 0 이나 1 — 어느 쪽이든 **종료 코드로 말한다**
    if r.returncode == 2:
        assert "못 쟀다" in r.stdout
    elif r.returncode == 1:
        assert "건너뛸 수 없다" in r.stdout
    else:
        assert "건너뛴다" in r.stdout


def _돌린다(곁: pathlib.Path):
    import os
    환경 = dict(os.environ, THOTH_SHOT_FIG=str(곁))
    return subprocess.run([sys.executable, str(ROOT / "tools/shot_stale.py")],
                          capture_output=True, text=True, env=환경)


def test_곁파일이_없으면_2_다_통과가_아니다(tmp_path):
    r = _돌린다(tmp_path)
    assert r.returncode == 2, r.stdout
    assert "못 쟀다" in r.stdout


def test_원본이_바뀌면_1_이다(tmp_path):
    for 이름, 것들 in ss.찍은것.items():
        (tmp_path / f"{이름}.원본.json").write_text(
            json.dumps({f: "옛지문123456" for f in 것들}, ensure_ascii=False), encoding="utf-8")
    r = _돌린다(tmp_path)
    assert r.returncode == 1, r.stdout
    assert "건너뛸 수 없다" in r.stdout


def test_목록이_어긋나면_1_이_아니라_2_다(tmp_path):
    # ★ **「다르다」 로 뭉개면 사람이 「다시 찍으면 된다」 로 읽는다** — 그런데 무엇과
    #   다른지를 모르는 상태다(§59). 둘을 가른 채로 둔다.
    for 이름, 것들 in ss.찍은것.items():
        칸 = {f: ss.지문(ROOT / f) for f in 것들}
        칸.pop(next(iter(칸)))                     # 한 칸을 빼서 목록을 어긋나게 둔다
        (tmp_path / f"{이름}.원본.json").write_text(
            json.dumps(칸, ensure_ascii=False), encoding="utf-8")
    r = _돌린다(tmp_path)
    assert r.returncode == 2, r.stdout
    assert "못 쟀다" in r.stdout


def test_지금_것이면_0_이다(tmp_path):
    for 이름, 것들 in ss.찍은것.items():
        (tmp_path / f"{이름}.원본.json").write_text(
            json.dumps({f: ss.지문(ROOT / f) for f in 것들}, ensure_ascii=False), encoding="utf-8")
    r = _돌린다(tmp_path)
    assert r.returncode == 0, r.stdout
    assert "건너뛴다" in r.stdout
