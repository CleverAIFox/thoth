"""기획서 본문이 제 자리를 지키나 (DECISIONS §155).

★ **0건이 목표인 검사는 깨끗해서 0 인지 죽어서 0 인지 못 가른다.** 그래서 **가짜 입력**으로
  묻는다 — 저장소가 지금 깨끗한 것은 따로 한 줄로 본다.
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("cp", ROOT / "tools/check_proposal.py")
CP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CP)


# ── 문 — 본문이 렌더러의 것을 가져가는가 ──────────────────────────────────

def _가짜(tmp_path, 줄: str) -> pathlib.Path:
    d = tmp_path / "docs/proposal"
    d.mkdir(parents=True, exist_ok=True)   # ★ 한 시험이 여러 번 부른다
    for f in CP.본문:
        (d / f).write_text(줄 if f == "part1.js" else 'const { P } = require("./lib");\n',
                           encoding="utf-8")
    return tmp_path


def test_lib_만_부르면_조용하다(tmp_path):
    assert CP.문(_가짜(tmp_path, 'const { P, TBL } = require("./lib");\n')) == []


def test_다른_것을_부르면_운다(tmp_path):
    난것 = CP.문(_가짜(tmp_path, 'const D = require("docx");\n'))
    assert any("docx" in x for x in 난것), 난것


def test_렌더러의_것을_가져가면_운다(tmp_path):
    for 이름 in ("D", "t", "runs", "W", "FONT"):
        난것 = CP.문(_가짜(tmp_path, f'const {{ P, {이름} }} = require("./lib");\n'))
        assert any(f"`{이름}`" in x for x in 난것), (이름, 난것)


def test_표_칸의_글자는_안_걸린다(tmp_path):
    # ★ 첫 판은 정규식 `\bD\b\.` 를 썼고 **표 칸의 `"D. 호스팅 LLM + 캐시"` 가 걸렸다.**
    #   글자는 뜻을 안 나른다 — `require` 와 구조분해만이 「무엇을 가져왔나」 를 말한다.
    글 = 'const { P, TBL } = require("./lib");\nconst x = [["D. 호스팅 LLM + 캐시", "5"]];\n'
    assert CP.문(_가짜(tmp_path, 글)) == []


# ── 블록 ──────────────────────────────────────────────────────────────────

def test_docx_직접은_운다():
    # ★ **말까지 본다.** 「선언 밖 블록」 으로만 울면 고치는 사람이 `lib.js` 에 `DOCX직접`
    #   블록을 여는 쪽으로 간다 — 정반대다.
    난것 = CP.블록({"블록이름": ["P"], "블록": [{"종류": "DOCX직접", "글": []}], "난것": []})
    assert any("직접 만진다" in x for x in 난것), 난것


def test_선언_밖_블록은_운다():
    assert CP.블록({"블록이름": ["P"], "블록": [{"종류": "몰라", "글": []}], "난것": []})


def test_끝까지_못_돌면_운다():
    assert CP.블록({"블록이름": ["P"], "블록": [], "난것": ["part2 못 읽는다"]})


def test_아는_블록만_있으면_조용하다():
    assert CP.블록({"블록이름": ["P", "TBL"], "블록": [{"종류": "P", "글": []},
                                                 {"종류": "TBL", "글": []}], "난것": []}) == []


# ── 수 ────────────────────────────────────────────────────────────────────

def test_산문의_수만_센다():
    t = {"블록": [{"종류": "P", "글": ["45유닛 · $0.59"]}, {"종류": "TBL", "글": ["99건"]},
                 {"종류": "FIGURE", "글": ["12개"]}]}
    assert CP.수들(t) == ["$0.59", "45유닛"], "표·그림은 안 본다"


def test_소수점_뒤_공백은_수가_아니다():
    # ★ 목차의 「12. 개발 환경」 이 `12. 개` 로 잡혔다 — 46 이 36 으로 줄었다.
    assert CP.수들({"블록": [{"종류": "P", "글": ["12. 개발 환경 및 배포 설계"]}]}) == []


def test_장부에_없으면_운다():
    새것, 안쓰는것 = CP.견준다(["45유닛", "99건"], {"45유닛"})
    assert 새것 == ["99건"] and 안쓰는것 == []


def test_안_쓰게_된_수를_찍는다():
    # ★ 안 찍으면 장부는 영원히 안 줄고, **줄지 않는 장부는 영구 면제**가 된다.
    새것, 안쓰는것 = CP.견준다([], {"45유닛"})
    assert 새것 == [] and 안쓰는것 == ["45유닛"]


# ── 장부와 카나리아 ───────────────────────────────────────────────────────

def test_장부가_주석_열쇠를_안_센다(tmp_path, monkeypatch):
    """★ **까닭이 장부로 새면 안 된다.** `_` 열쇠가 목록을 들 수도 있으므로 **꼴이 아니라
    이름**으로 거른다 — 「목록이면 장부다」 로 적으면 그날 조용히 샌다."""
    raw = json.loads(CP.장부파일.read_text(encoding="utf-8"))
    assert any(k.startswith("_") for k in raw), "까닭이 사라졌다"
    가짜 = tmp_path / "docs/proposal"
    가짜.mkdir(parents=True)
    (가짜 / "numbers.json").write_text(
        json.dumps({"_밖": ["이건 까닭이다"], "지금": ["45유닛"]}, ensure_ascii=False),
        encoding="utf-8")
    assert CP.장부(tmp_path) == {"45유닛"}, "`_` 열쇠가 목록을 들면 샌다"


def test_카나리아가_산다():
    CP._canary()


def test_selftest_가_0_으로_끝난다():
    assert CP.main(["--selftest"]) == 0


def test_지금_저장소가_조용하다():
    # ★ 위의 가짜 입력 시험들과 **다른 물음**이다 — 저쪽은 「자가 사나」, 이쪽은 「지금 깨끗한가」.
    if not (ROOT / "docs/proposal/node_modules").exists():
        pytest.skip("npm ci 를 안 돌려 extract 를 못 돌린다")
    assert CP.main([]) == 0


# ── extract.js — 실행으로 가르는 자리 ─────────────────────────────────────

def _가짜_생성기(tmp_path: pathlib.Path, part1: str) -> pathlib.Path:
    """`lib.js` 와 `extract.js` 를 그대로 두고 본문만 바꾼 작은 생성기."""
    import shutil
    d = tmp_path / "proposal"
    d.mkdir()
    for f in ("lib.js", "extract.js"):
        shutil.copy(ROOT / "docs/proposal" / f, d / f)
    (d / "part1.js").write_text(part1, encoding="utf-8")
    for f in ("part2.js", "part3.js"):
        (d / f).write_text(f'const {{ P }} = require("./lib");\n'
                           f'module.exports = {{ {f[:5]}: [P("ㄱ")] }};\n', encoding="utf-8")
    return d


def _돌린다(d: pathlib.Path) -> dict:
    import subprocess
    r = subprocess.run(["node", "extract.js"], cwd=d, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
    return json.loads(r.stdout)


def test_extract_가_docx_를_만지면_기록한다(tmp_path):
    """★ **저장소가 깨끗하면 이 자리를 아무도 안 밟는다.** 그래서 **가짜 본문**으로 민다 —
    프록시를 지워도 시험이 조용하면 그 프록시는 장식이다(DECISIONS §152 · §155)."""
    if not (ROOT / "docs/proposal/node_modules").exists():
        pytest.skip("npm ci 를 안 돌려 docx 를 못 읽는다")
    글 = ('const { P, D } = require("./lib");\n'
          'const { Paragraph } = D;\n'
          'module.exports = { cover: [new Paragraph({})], toc: [P("ㄱ")] };\n')
    t = _돌린다(_가짜_생성기(tmp_path, 글))
    assert any(b["종류"] == "DOCX직접" for b in t["블록"]), "docx 를 만졌는데 기록이 없다"
    assert CP.블록(t), "기록이 있는데 판정이 조용하다"


def test_extract_가_깨끗한_본문에서는_조용하다(tmp_path):
    if not (ROOT / "docs/proposal/node_modules").exists():
        pytest.skip("npm ci 를 안 돌려 docx 를 못 읽는다")
    글 = ('const { P, H1 } = require("./lib");\n'
          'module.exports = { cover: [H1("ㄱ")], toc: [P("ㄴ")] };\n')
    t = _돌린다(_가짜_생성기(tmp_path, 글))
    assert not any(b["종류"] == "DOCX직접" for b in t["블록"])
    assert t["난것"] == [] and CP.블록(t) == []


def test_본문이_함수를_내보내면_운다(tmp_path):
    """★ **본문은 데이터다.** 함수를 내보내면 부르는 쪽마다 다른 글이 나올 수 있고, 그러면
    이 자가 본 것과 렌더러가 굽는 것이 갈린다. 첫 판은 「함수면 불러 본다」 였는데 **부를
    함수가 하나도 없어 죽은 줄**이었다 — 돌연변이가 살려 보내서 알았다."""
    if not (ROOT / "docs/proposal/node_modules").exists():
        pytest.skip("npm ci 를 안 돌려 docx 를 못 읽는다")
    글 = ('const { P } = require("./lib");\n'
          'module.exports = { cover: () => [P("ㄱ")], toc: [P("ㄴ")] };\n')
    t = _돌린다(_가짜_생성기(tmp_path, 글))
    assert any("배열이 아니다" in x for x in t["난것"]), t["난것"]
    assert CP.블록(t), "배열이 아닌데 판정이 조용하다"
