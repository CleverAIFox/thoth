"""기획서 본문이 제 자리를 지키나 (DECISIONS §155).

★ **0건이 목표인 검사는 깨끗해서 0 인지 죽어서 0 인지 못 가른다.** 그래서 **가짜 입력**으로
  묻는다 — 저장소가 지금 깨끗한 것은 따로 한 줄로 본다.
"""
import importlib.util
import json
import pathlib
import re

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


# ── 날짜 이름표 (DECISIONS §158) ──────────────────────────────────────────

def test_빠진_이름표를_찾는다():
    assert CP.날짜흠("**2026-01-02**\n", '    "2026-01-03": "ㄱ",\n') == ["2026-01-02"]


def test_있는_이름표는_안_센다():
    assert CP.날짜흠("**2026-01-02**\n", '    "2026-01-02": "ㄱ",\n') == []


def test_날짜가_여럿이면_빠진_것만_낸다():
    dec = "**2026-01-02**\n글\n**2026-01-03**\n"
    assert CP.날짜흠(dec, '    "2026-01-02": "ㄱ",\n') == ["2026-01-03"]


def test_굵게가_아닌_날짜는_안_센다():
    # ★ DECISIONS 의 날짜 줄은 `**YYYY-MM-DD**` 다. 본문에 적힌 날짜까지 세면
    #   **이름표를 영원히 다 못 채운다** — 거짓 빨강이 쌓이면 검사를 끈다.
    assert CP.날짜흠("2026-01-02 에 그랬다\n", "") == []


def test_지금_저장소에_빠진_이름표가_없다():
    assert CP.날짜흠(CP.DEC.read_text(encoding="utf-8"),
                    CP.CHARTS.read_text(encoding="utf-8")) == []


# ── 두 번째 렌더러(DECISIONS §166) ──────────────────────────────────────────

def test_html_렌더러가_블록_이름을_전부_안다():
    """★ **족 가드다**(DECISIONS §166). 손 목록을 만들면 `lib.js` 에 블록이 하나 늘 때
    그 목록이 늙고, 늙은 목록은 **빠진 것을 조용히 안 굽는다.** `extract.js` 가 드는
    이름에서 꺼내 맞댄다 — 둘 다 같은 자리에서 나온다."""
    t = CP.나무()
    src = (ROOT / "docs/proposal/html.js").read_text(encoding="utf-8")
    빠진 = [n for n in t["블록이름"] if not re.search(rf"^\s+{re.escape(n)}:", src, re.M)]
    assert 빠진 == [], f"HTML 렌더러가 모르는 블록 — {빠진}"


def test_두_렌더러가_같은_글을_받는다():
    """★ **이것이 「본문이 포맷 중립이다」 의 증명이다**(DECISIONS §155 · §166).
    §155 는 「본문이 docx 를 안 만진다」 까지였고 그것은 **기록만 하는 가짜**로 보인다.
    실제 산출물이 하나 더 나와야 주장이 사실이 된다."""
    t = CP.나무()
    assert CP.두렌더러(t, CP.html_글()) == []


def test_안_보이는_인자를_선언으로_뺀다():
    """★ **`FIGURE(name, …)` 의 `name` 은 파일 이름이라 화면에 안 나온다.** 선언 없이
    빼면 다음 사람이 「왜 이것만 안 보나」 를 다시 판다(§73)."""
    assert ("FIGURE", 0) in CP.안보이는인자


def test_facts_는_포맷을_모른다():
    """★ **정본이 하나여야 한다**(§91). 날짜→절 범위는 `docx` 와도 태그와도 상관이 없다 —
    두 렌더러가 **같은 자리**에서 읽어야 한쪽만 안 늙는다."""
    src = (ROOT / "docs/proposal/facts.js").read_text(encoding="utf-8")
    assert 'require("docx")' not in src, "포맷이 공통 사실 안으로 들어왔다"
    assert "<" not in src.split("module.exports")[0].replace("<<", ""), "태그가 들어왔다"
    for 쪽 in ("lib.js", "html.js"):
        assert 'require("./facts")' in (ROOT / "docs/proposal" / 쪽).read_text(encoding="utf-8"), 쪽


def test_html_이_그물에_안_기댄다():
    """★ **받은 사람이 파일 하나를 열면 그걸로 끝이다.** 종전 화면은 `jsdelivr` 에서
    `docx-preview` 를 받아 와 브라우저에서 docx 를 풀었다 — **그물이 끊기면 빈 쪽**이다."""
    글 = (ROOT / "site/proposal.html").read_text(encoding="utf-8")
    assert "cdn." not in 글 and "https://unpkg" not in 글, "바깥에서 받아 오는 것이 있다"
    assert "<script" not in 글, "스크립트가 없어야 한다 — 글은 글로 선다"
    실린그림 = 글.count('src="data:image/png;base64,')
    assert 실린그림 >= 5, f"그림이 실려 있지 않다 — {실린그림}"


def _나무(글들):
    return {"블록": [{"n": i + 1, "종류": "P", "글": [g]} for i, g in enumerate(글들)],
            "난것": [], "블록이름": ["P"]}


def test_빠진_글을_잡는다():
    """★ **음성만 있으면 아무것도 안 잡는 검사가 초록이다.** 저장소가 지금 깨끗한 것은
    「자가 산다」 는 뜻이 아니다 — 합성으로 **빨개지는지**를 따로 묻는다."""
    난것 = CP.두렌더러(_나무(["이 문장은 HTML 에 없는 긴 문장이다"]), "<html><body><p>딴 글</p></body></html>")
    assert len(난것) == 1 and "두 렌더러가 다른 것을 받았다" in 난것[0]
    assert CP.두렌더러(_나무(["이 문장은 HTML 에 있는 긴 문장이다"]),
                      "<html><body><p>이 문장은 HTML 에 있는 긴 문장이다</p></body></html>") == []


def test_짧은_토막은_안_본다():
    """★ **여섯 자 미만은 표의 `-` 나 `○` 같은 기호가 섞여 우연히 들어 있는지를 못 가른다.**
    보기 시작하면 멀쩡한 산출물이 빨개지고, **거짓 빨강이 쌓이면 사람이 검사를 끈다**(§158)."""
    assert CP.두렌더러(_나무(["없다"]), "<html><body><p>딴 글</p></body></html>") == []
    assert CP.두렌더러(_나무(["다섯자이다"]), "<html><body><p>딴 글</p></body></html>") == []
    assert len(CP.두렌더러(_나무(["여섯자입니다"]), "<html><body><p>딴 글</p></body></html>")) == 1


# ── 박은 수와 갈래(DECISIONS §167) ──────────────────────────────────────────

def test_박은_수와_치환된_수를_가른다():
    """★ **기계가 가르는 것과 사람이 가르는 것을 나눈다**(§167). 「소스에 글자 그대로
    있나」 는 기계가 센다 — 실측으로 36 중 **여덟이 이미 치환돼 있었고**(`${rows.length}건`)
    장부가 36 을 한 뭉치로 들던 동안 **그 사실이 안 보였다**(세샤트 §302 와 같은 꼴)."""
    박, 치환됨 = CP.박은수(["5초", "없는수9건"], 'P(`앞 5초 뒤`)\n')
    assert 박 == ["5초"] and 치환됨 == ["없는수9건"]


def test_온_줄_주석은_소스가_아니다(tmp_path, monkeypatch):
    """★ **치환하고 나서 왜 치환했는지를 주석에 적으면 그 수가 「아직 박혀 있다」 로
    세어진다**(§167). 실제로 `35%` 를 치환한 판에서 그랬다 — 주석은 안 그려진다."""
    (tmp_path / "docs/proposal").mkdir(parents=True)
    for f in CP.본문파일:
        (tmp_path / "docs/proposal" / f).write_text(
            "  // 종전에는 35% 가 박혀 있었다\nP(`지금 12건`);\n", encoding="utf-8")
    monkeypatch.setattr(CP, "ROOT", tmp_path)
    소스 = CP.본문소스()
    assert "35%" not in 소스 and "12건" in 소스


def test_줄_끝_주석은_안_지운다(tmp_path, monkeypatch):
    """★ **`https://` 가 문자열 안에 있다**(§167). `//` 를 찾아 자르면 **멀쩡한 글이
    사라지고 수가 조용히 줄어든다** — 줄어든 수는 톱니를 느슨하게 만든다."""
    (tmp_path / "docs/proposal").mkdir(parents=True)
    for f in CP.본문파일:
        (tmp_path / "docs/proposal" / f).write_text(
            'P(`https://example.com 에서 40개를 센다`);\n', encoding="utf-8")
    monkeypatch.setattr(CP, "ROOT", tmp_path)
    assert "40개" in CP.본문소스()


def test_박은_수마다_갈래가_꼭_하나다():
    raw = CP._장부raw()
    박, _ = CP.박은수(CP.수들(CP.나무()), CP.본문소스())
    assert CP.갈래흠(박, raw) == []


def test_갈래가_없거나_둘이면_걸린다():
    """★ **양성과 음성을 함께 본다.** 지금 저장소가 깨끗한 것은 「자가 산다」 가 아니다."""
    raw = {"밖": {"5초": "까닭"}, "면제": {"5초": "까닭"}, "치환예정": []}
    assert any("갈래 둘" in x for x in CP.갈래흠(["5초"], raw))
    assert any("갈래가 없다" in x for x in CP.갈래흠(["9건"], {"밖": {}, "면제": {}, "치환예정": []}))
    assert any("장부에서 지운다" in x for x in CP.갈래흠([], {"밖": {"5초": "까닭"}}))


def test_치환예정이_줄기만_한다():
    """★ **양방향 톱니다**(§167). 치환하지 않고 `밖` 으로 옮겨 적으면 **갚은 것이 아니다.**"""
    raw = CP._장부raw()
    assert len(raw["치환예정"]) <= CP.MAX_치환예정
    박, _ = CP.박은수(CP.수들(CP.나무()), CP.본문소스())
    assert len(박) <= CP.MAX_박은수


def test_다섯_단계의_합을_산문이_안_든다():
    """★ **칸 하나를 고치면 제목과 산문의 수가 같이 움직인다**(§167). 종전에는 `35%` 가
    **세 자리**에 박혀 있었고 그 셋이 갈릴 수 있었다."""
    src = (ROOT / "docs/proposal/part3.js").read_text(encoding="utf-8")
    본문 = "\n".join(l for l in src.split("\n") if not l.lstrip().startswith("//"))
    assert "35%" not in 본문, "합이 아직 박혀 있다"
    assert "Math.floor(참값)" in 본문, "내림이 아니면 진행률이 과장되는 쪽으로 틀린다"


def test_톱니가_실제로_막는다(monkeypatch, capsys):
    """★ **「바닥이 있다」 와 「바닥이 문다」 는 다른 말이다**(§153). 저장소가 지금 그 안에
    있는 것은 **톱니가 산다**는 뜻이 아니다 — 바닥을 낮춰 **울리는지**를 묻는다."""
    박, _ = CP.박은수(CP.수들(CP.나무()), CP.본문소스())
    monkeypatch.setattr(CP, "MAX_박은수", len(박) - 1)
    assert CP.main([]) == 1
    assert "바닥" in capsys.readouterr().out


def test_치환예정_천장이_실제로_막는다(monkeypatch, capsys):
    예정 = len(CP._장부raw()["치환예정"])
    monkeypatch.setattr(CP, "MAX_치환예정", 예정 - 1)
    assert CP.main([]) == 1
    assert "빚은 늘지 않는다" in capsys.readouterr().out
