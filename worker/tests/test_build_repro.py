"""기획서를 **같은 소스에서 다시 구우면 같은 바이트가 나오는가**(DECISIONS §189).

★ **까닭은 미관이 아니다.** `docs/proposal.docx` · `site/proposal.html` ·
  `docs/proposal/build.lock.json` 셋은 **추적된다.** 안에 벽시계나 애니메이션 한 프레임이
  박히면 소스를 한 글자도 안 고치고 다시 구워도 **나무 해시가 달라진다.**
  `apply_patch.sh` 의 바탕 선언(§129 · §130)은 나무 해시로 「같은 내용 위에 서 있나」 를
  묻는 자다 — 그 자가 **세 번 어긋났고 그때마다 패치를 의심했다.** 까닭은 패치가 아니었다.

★ **재서 알았다.** §126 은 「docx 는 zip 이라 같은 입력에서 같은 바이트가 안 나온다」 고
  적어 뒀다 — 안 재고 적은 말이다. 재니 zip 항목 시각은 이미 고정이고 **다른 것은
  `docProps/core.xml` 의 두 줄뿐**이었고, 그림 22장 중 **한 장**(`f_preview_a`)뿐이었다.

★ **여기서 두 번 굽지 않는다.** 한 판에 1분이 넘고 크로미움과 npm 이 든다 — 시험이
  그것을 들면 사람이 시험을 끈다. 대신 **구운 물건에 남은 자국**을 본다 : docx 속성의
  시각 · 자물쇠의 칸 · 그림 지문. 벽시계가 돌아오면 이 셋 중 하나가 운다.
"""
import importlib.util
import json
import pathlib
import re
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("docx_check", ROOT / "tools/docx_check.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)

자물쇠 = ROOT / "docs/proposal/build.lock.json"
BUILD = ROOT / "docs/proposal/build.js"
SHOTS = ROOT / "docs/proposal/figures/shots.py"


def test_판_날짜를_읽는다():
    날 = dc.판날짜(ROOT)
    assert 날 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", 날), 날


def test_실제_docx_에_벽시계가_없다():
    assert dc.check_wall_clock(ROOT) == []


def test_docx_속성이_판_날짜다():
    with zipfile.ZipFile(ROOT / "docs/proposal.docx") as z:
        core = z.read("docProps/core.xml").decode("utf-8")
    박힌 = re.findall(r"<dcterms:(?:created|modified)[^>]*>([^<]+)<", core)
    assert len(박힌) == 2, 박힌
    assert all(x.startswith(dc.판날짜(ROOT)) for x in 박힌), 박힌


def test_판_날짜가_다르면_운다():
    # ★ **관문이 무는지를 본다**(§152). 「검사를 더했다」 와 「검사가 문다」 는 다른 말이다.
    원래 = dc.판날짜
    try:
        dc.판날짜 = lambda root: "1999-01-01"
        흠 = dc.check_wall_clock(ROOT)
    finally:
        dc.판날짜 = 원래
    assert 흠 and "벽시계" in 흠[0]


def _가짜나무(tmp_path, core: str | None):
    """`build.js` 와 `proposal.docx` 만 있는 나무. **한 번도 안 돌아 본 가지**를 밟게 한다."""
    (tmp_path / "docs/proposal").mkdir(parents=True)
    (tmp_path / "docs/proposal/build.js").write_text(
        'const 판 = { 이름: "3.0", 날짜: new Date("2026-10-14T00:00:00Z") };\n', encoding="utf-8")
    with zipfile.ZipFile(tmp_path / "docs/proposal.docx", "w") as z:
        z.writestr("docProps/core.xml", core if core is not None else "<cp:coreProperties/>")
    return tmp_path


def test_시각_칸이_사라지면_통과가_아니다(tmp_path):
    # ★ **「없다」 를 「괜찮다」 로 읽지 않는다**(§59). 꼴이 바뀌어 `dcterms` 가 통째로
    #   빠지면 `startswith` 검사는 **볼 것이 없어 조용히 통과**한다 — 그 가지를 따로 운다.
    #   이 가지는 실물 docx 로는 영영 안 밟힌다(§182).
    흠 = dc.check_wall_clock(_가짜나무(tmp_path, None))
    assert 흠 and "dcterms 시각이 없다" in 흠[0]


def test_가짜_나무에서도_판_날짜면_통과다(tmp_path):
    좋은 = ('<dcterms:created xsi:type="dcterms:W3CDTF">2026-10-14T00:00:00.000Z</dcterms:created>'
            '<dcterms:modified xsi:type="dcterms:W3CDTF">2026-10-14T00:00:00.000Z</dcterms:modified>')
    assert dc.check_wall_clock(_가짜나무(tmp_path, 좋은)) == []


def test_판_날짜를_못_읽으면_통과가_아니다(tmp_path):
    # ★ **못 쟀다 ≠ 없다**(§59). 꼴이 바뀌어 날짜를 못 읽으면 조용히 지나가면 안 된다.
    (tmp_path / "docs/proposal").mkdir(parents=True)
    (tmp_path / "docs/proposal/build.js").write_text("// 날짜 선언이 없다\n", encoding="utf-8")
    흠 = dc.check_wall_clock(tmp_path)
    assert 흠 and "판 날짜를 못 읽었다" in 흠[0]


def test_자물쇠에_벽시계_칸이_없다():
    # ★ `만든때` 는 아무도 안 읽는데 **매번 달라졌다** — §129 가 이미 그 소음을 적어 뒀다.
    것 = json.loads(자물쇠.read_text(encoding="utf-8"))
    assert "만든때" not in 것, "자물쇠에 벽시계가 돌아왔다"
    assert 것.get("판"), "자물쇠가 판 이름을 안 적는다"


def test_자물쇠가_그림_지문을_든다():
    # ★ **추적되는 파일을 증인으로 세운다.** 그림이 다시 비결정적이 되면 소스를 안 고쳐도
    #   이 파일이 매번 달라지고, 추적되므로 `git status` 가 그 자리에서 운다.
    것 = json.loads(자물쇠.read_text(encoding="utf-8"))
    그림 = 것.get("그림")
    assert 그림 != "없다", "자물쇠가 그림을 못 쟀다 — .build/fig 없이 구웠다"
    assert isinstance(그림, dict) and len(그림) >= 19, 그림
    assert all(k.endswith(".png") for k in 그림), list(그림)[:3]
    assert all(re.fullmatch(r"[0-9a-f]{16}", v) for v in 그림.values())


def test_자물쇠가_중간_산출물을_안_센다():
    # ★ **증인은 산출물에 도달하는 것이어야 한다**(DECISIONS §191). `shot_preview.png` ·
    #   `shot_popup_on.png` · `shot_popup_off.png` 셋은 **기획서에 안 들어간다** —
    #   `crop` 과 `trim` 으로 잘려 나가는 중간 산출물이다. 그 잘린 영역이 브라우저 판에
    #   따라 달라지면, 산출물이 한 바이트도 안 변했는데 자물쇠만 갈린다.
    # ★ **2026-10-14 에 실제로 그렇게 됐다.** 크로미움 1243 과 1248 에서 docx · html 이
    #   바이트까지 같은데 자물쇠만 달랐고, 다른 것은 저 셋뿐이었다.
    그림 = json.loads(자물쇠.read_text(encoding="utf-8")).get("그림")
    assert isinstance(그림, dict), 그림
    섞인것 = sorted(k for k in 그림 if not k.startswith("f_"))
    assert 섞인것 == [], f"산출물에 안 실리는 그림을 센다 : {섞인것}"


def _docx_그림지문() -> set[str]:
    """`proposal.docx` 가 **실제로 품고 있는** 그림의 지문. 추적되는 파일만 읽는다.

    ★ **`.build/fig` 를 보면 CI 에서 건너뛴다**(DECISIONS §192). 그 칸은 gitignore 라
      clone 에 없고, 건너뛴 시험은 `doctor` 가 세는 `passed` 를 줄여 **문서 건수를
      어긋나게** 한다 — `ci.yml` 이 §158 로 적어 둔 바로 그 함정이다.
    ★ **그리고 docx 를 보는 쪽이 더 센 말이다.** 묻는 것은 「자물쇠가 **실린 것**을
      적었나」 이고, 실린 것의 정본은 `.build/` 가 아니라 **산출물**이다. 재서 확인했다 —
      `word/media/*` 가 `.build/fig/f_*.png` 와 **바이트까지 같다**(19/19).
    """
    import hashlib
    import zipfile
    with zipfile.ZipFile(ROOT / "docs/proposal.docx") as z:
        return {hashlib.sha256(z.read(n)).hexdigest()[:16]
                for n in z.namelist() if n.startswith("word/media/")}


def test_실린_그림이_빠짐없이_세어진다():
    # ★ **좁히다가 빠뜨리면 관문이 조용해진다**(§59). `f_` 로 좁힌 것이 **실제로 기획서가
    #   드는 그림 전부**인지 산출물과 맞춰 본다 — 한쪽만 늙으면 못 본다(§91).
    적힌것 = json.loads(자물쇠.read_text(encoding="utf-8")).get("그림", {})
    assert isinstance(적힌것, dict) and 적힌것, 적힌것
    품은것 = _docx_그림지문()
    빠진것 = sorted(k for k, v in 적힌것.items() if v not in 품은것)
    assert 빠진것 == [], f"자물쇠가 적었는데 docx 에 없는 그림 : {빠진것}"
    assert len(품은것) >= len(적힌것), (len(품은것), len(적힌것))


def test_자물쇠의_그림_지문이_실물과_같다():
    # ★ **적힌 것과 실린 것을 견준다.** 둘이 갈라지면 적힌 쪽이 늙은 것이다(§91).
    # ★ **건너뛰지 않는다**(DECISIONS §192). 전에는 `.build/fig` 가 없으면 `skip` 했는데,
    #   그 칸은 gitignore 라 **CI 에는 언제나 없다** — 즉 이 시험은 CI 에서 한 번도 안 돌았고
    #   `passed` 만 하나 줄여 **문서 건수를 빨갛게** 했다. 산출물을 보면 둘 다 없어진다.
    것 = json.loads(자물쇠.read_text(encoding="utf-8")).get("그림")
    assert isinstance(것, dict) and 것, 것
    품은것 = _docx_그림지문()
    다른 = sorted(k for k, v in 것.items() if v not in 품은것)
    assert 다른 == [], f"자물쇠와 산출물이 다르다 : {다른[:3]}"


def test_화면을_애니메이션_없이_찍는다():
    # ★ **`content.css` 의 `st-pulse 1.5s infinite` 이 `preview.html` 에서 돈다.** 800ms 뒤에
    #   찍은 한 장은 **아무 프레임**이었고, 그 그림이 base64 로 docx · html 에 박혔다.
    글 = SHOTS.read_text(encoding="utf-8")
    assert '"animations": "disabled"' in 글, "찍기 설정에 animations 가 없다"
    # 모든 screenshot 호출이 같은 설정을 쓴다 — 한 곳만 고치면 다른 곳이 늙는다(§91)
    호출 = [x for x in 글.splitlines() if ".screenshot(" in x]
    assert len(호출) >= 2, 호출
    assert all("**찍기" in x for x in 호출), 호출


def test_생성기가_인자_없는_벽시계를_안_부른다():
    # ★ **글을 코드로 읽는 검사는 글부터 지운다.** 주석을 떼고 본다 — 주석에 적힌
    #   `new Date()` 를 코드로 읽으면 이 검사는 **제 글을 읽고 통과한다**(열두 번 겪었다).
    # ★ 이것은 `check_wall_clock` 과 겹치지 않는다. 저쪽은 **구운 docx** 를 보고, 이쪽은
    #   아직 안 구운 생성기를 본다 — 고치고 안 구운 사이가 바로 §129 가 터진 자리다.
    줄 = [x for x in BUILD.read_text(encoding="utf-8").splitlines()
          if not x.lstrip().startswith("//")]
    맨 = [x for x in 줄 if re.search(r"new Date\(\s*\)", x)]
    assert 맨 == [], f"build.js 에 인자 없는 new Date() 가 있다 : {맨}"
