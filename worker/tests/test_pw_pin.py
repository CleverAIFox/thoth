"""playwright 판을 **한 곳에서** 못 박았는가(DECISIONS §194).

★ **안 박으면 매번 최신이 온다.** `uv run --with playwright` 는 부를 때마다 **그 순간의
  최신**을 푸는데, 브라우저는 `~/.cache/ms-playwright/` 에 **빌드 번호로** 깔려 있다.
  판이 올라가는 날 둘이 어긋나고 빌드가 죽는다 — 2026-10-15 에 기획서 굽기가 멈췄고
  191MB 를 다시 받았다. 같은 날 CI 의 캐스케이드 검사도 그 까닭으로 건너뛰어졌다.

★ **재서 골랐다.** 판↔크로미움 빌드를 직접 재 봤다 :
  1.56.0→1194 · 1.57.0→1200 · 1.58.0→1208 · 1.59.0→1217 · 1.60.0→1223 ·
  1.63.0→1243 · **1.64.0→1248** · 1.65.0 없음. `1248` 이 깔려 있으므로 다시 안 받는다.

★ **늙는 것이 설계다.** 판을 올리는 일은 **한 줄을 고치는 일**이어야 하지, 어느 날
  아침 빌드가 죽는 일이면 안 된다 — 액션을 SHA 로 박고 `npm ci` 를 쓰는 것과 같은 결.
"""
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
PW = ROOT / "tools/lib/pw.sh"


def 핀() -> str:
    m = re.search(r'PW_PIN="([^"]+)"', PW.read_text(encoding="utf-8"))
    assert m, "tools/lib/pw.sh 가 PW_PIN 을 안 든다"
    return m.group(1)


def _본문(p: pathlib.Path) -> str:
    """주석 **과 글귀**를 걷어낸 코드.

    ★ **글을 코드로 읽는 검사는 글부터 지운다 — 열여섯 번째.** 앞판은 `#` 줄만
      지웠는데, **이 파일의 모듈 글귀에 `uv run --with playwright` 가 적혀 있었다.**
      그래서 194 를 커밋하는 순간 이 시험이 **제 글에 걸려 터졌다**(2026-10-16).
      앞의 열다섯은 전부 `#` 만 지우고도 통과했는데, 그건 설계가 아니라 **운**이었다 —
      찾는 글자가 제 산문에 안 들어 있었을 뿐이다. `#` 이 아닌 글도 글이다.
    ★ **지우는 것은 줄 머리에서 열리는 세겹 따옴표뿐이다.** 값으로 쓰이는 세겹
      문자열(`MOCK = \"\"\"...`)은 머리가 이름이라 안 지워진다 — 그것은 글이 아니라
      **데이터**이고, 거기 든 명령은 실제로 돈다.
    """
    줄, 안 = [], ""
    for x in p.read_text(encoding="utf-8").splitlines():
        s = x.strip()
        if 안:                                  # 글귀 안이다
            if 안 in s:
                안 = ""
            continue
        if s.startswith("#") or s.startswith("//"):
            continue
        m = re.match(r"""[rbuRBU]{0,2}("{3}|'{3})""", s)
        if m:
            if m.group(1) not in s[m.end():]:   # 한 줄로 닫히지 않는다
                안 = m.group(1)
            continue
        줄.append(x)
    return "\n".join(줄)


def _부르는것() -> list[pathlib.Path]:
    out = subprocess.run(["git", "ls-files", "*.sh", "*.py", "*.yml"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    것 = []
    for rel in out:
        if rel in ("tools/lib/pw.sh", "tools/lib/pw.py"):
            continue
        p = ROOT / rel
        if "playwright" in _본문(p):
            것.append(p)
    return 것


def test_정본이_하나_있다():
    assert PW.is_file()
    assert re.fullmatch(r"playwright==\d+\.\d+\.\d+", 핀()), 핀()


def test_정본이_무엇을_안_보는지_적는다():
    # ★ **못 보는 것을 적는다**(§59). CI 러너에는 브라우저가 아예 없어 이 핀으로는
    #   캐스케이드 건너뜀이 안 풀린다 — 그 사실이 적혀 있어야 다음 사람이 오해 안 한다.
    assert "이 눈 밖" in PW.read_text(encoding="utf-8")


def test_부르는_자리를_찾았다():
    # ★ **0곳을 통과로 세지 않는다**(§59). 못 찾으면 이 시험은 아무것도 안 묻는다.
    것 = _부르는것()
    assert len(것) >= 3, [str(x) for x in 것]


def test_아무도_맨_playwright_를_안_부른다():
    # ★ 이것이 이 판의 요점이다 — `--with playwright` 가 코드에 남아 있으면 그 자리가
    #   다음 사고의 입구다.
    흠 = {}
    for p in _부르는것():
        맨 = [x.strip() for x in _본문(p).splitlines()
              if re.search(r"--with\s+playwright(?![=\w])", x)]
        if 맨:
            흠[str(p.relative_to(ROOT))] = 맨
    assert 흠 == {}, 흠


# ★ **금지하는 글자를 제 소스에 적지 않는다** — 런타임에 짜 맞춘다(§131 의 `"7" * 12`
#   와 같은 결). 아래 둘은 **맨 `--with playwright` 가 어떻게 생겼는지**를 알아야 하는데,
#   그 글자를 그대로 적으면 바로 위 `test_아무도_맨_playwright_를_안_부른다` 가 **이
#   시험에 걸린다.** 실제로 처음 판이 그렇게 터졌다(2026-10-16).
맨 = "--with " + "playwright"


def test_글귀도_지운다(tmp_path):
    # ★ **이 지움이 되돌려지면 194 의 커밋이 다시 터진다**(2026-10-16). 그러므로 지움을
    #   글로 묻지 않고 **합성 파일로 재서** 묻는다 — 「글만 재면 배선을 안 잰다」(§173).
    p = tmp_path / "x.py"
    p.write_text(f'"""머리글\n    uv run {맨}\n"""\n코드 = 1\n# uv run {맨}\n',
                 encoding="utf-8")
    본 = _본문(p)
    assert "playwright" not in 본, 본
    assert "코드 = 1" in 본, 본


def test_값으로_쓰는_세겹문자열은_남긴다(tmp_path):
    # ★ **글만 지운다 — 데이터는 코드다.** `shots.py` 의 `MOCK = """…"""` 처럼 값으로
    #   쓰이는 세겹 문자열까지 지우면 **거기 든 명령을 아무도 안 본다.** 글을 지우는
    #   것과 코드를 지우는 것은 한 글자 차이로 갈린다.
    p = tmp_path / "y.py"
    p.write_text(f'M = """uv run {맨}"""\n', encoding="utf-8")
    assert "playwright" in _본문(p)


def test_맨_꼴을_실제로_잡는다(tmp_path):
    # ★ **0곳을 통과로 세지 않는다**(§59). 위 두 시험은 **지움**을 재는데, 지움이
    #   너무 세져서 **아무것도 안 남으면** 그것도 통과로 보인다. 그래서 **잡아야 하는
    #   것을 잡는지**를 따로 묻는다 — 카나리아다.
    p = tmp_path / "z.sh"
    p.write_text(f'uv run {맨} python -c x\n', encoding="utf-8")
    맞은것 = [x for x in _본문(p).splitlines()
             if re.search(r"--with\s+playwright(?![=\w])", x)]
    assert len(맞은것) == 1, _본문(p)
    # ★ 핀이 붙은 꼴은 잡지 않는다 — 그것이 **옳은 상태**다.
    q = tmp_path / "w.sh"
    q.write_text('uv run --with "$PW_PIN" python -c x\n', encoding="utf-8")
    assert not [x for x in _본문(q).splitlines()
                if re.search(r"--with\s+playwright(?![=\w])", x)]


def test_셸과_파이썬이_같은_수를_든다():
    # ★ **두 곳에 적으면 한쪽만 늙는다**(§91). 파이썬은 셸 파일을 **읽어** 쓴다.
    import importlib.util
    s = importlib.util.spec_from_file_location("pw", ROOT / "tools/lib/pw.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    assert m.핀(ROOT) == 핀()


def test_정본을_못_읽으면_핀_없는_명령이_드러난다(tmp_path):
    # ★ **조용히 최신을 쓰는 것보다, 핀이 없다는 것이 보이는 편이 낫다**(§59).
    import importlib.util
    s = importlib.util.spec_from_file_location("pw", ROOT / "tools/lib/pw.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    assert m.핀(tmp_path) == "playwright"


def test_파이썬_도구가_핀을_실제로_싣는다():
    # ★ **글만 재면 배선을 안 잰다**(§173). 모듈을 올려 상수를 본다.
    import importlib.util
    for rel in ("tools/shot_stale.py", "tools/cascade_check.py"):
        s = importlib.util.spec_from_file_location(rel, ROOT / rel)
        mod = importlib.util.module_from_spec(s)
        s.loader.exec_module(mod)
        assert getattr(mod, "핀", None) == 핀(), rel


def test_셸이_정본을_들여온다():
    for rel in ("tools/build_proposal.sh", "tools/doctor.sh"):
        글 = (ROOT / rel).read_text(encoding="utf-8")
        assert "tools/lib/pw.sh" in 글, rel
        assert '"$PW_PIN"' in 글, rel


# ── CI 가 브라우저를 깐다 ───────────────────────────────────────────────────


def _CI() -> str:
    return (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")


def _단계(이름: str) -> str:
    글 = _CI()
    i = 글.index(이름)
    j = 글.find("\n      - ", i)
    return 글[i:j if j != -1 else len(글)]


def test_CI_가_브라우저를_깐다():
    # ★ **가진 것과 도는 것은 다른 말이다**(§186). 러너에 브라우저가 없으면 캐스케이드
    #   검사가 「재다 터졌다」 로 **조용히 건너뛰어진다** — 2026-10-15 까지 그랬다.
    assert "브라우저 — 캐스케이드 검사가 쓴다" in _CI()


def test_CI_가_전체_크로미움을_안_받는다():
    # ★ **재서 좁혔다.** 캐스케이드는 헤드리스 셸만으로 돈다 — `playwright==1.63.0`
    #   (빌드 1243) 으로 실제로 돌려 확인했다. 191MiB 대신 120MiB 다.
    단 = _단계("브라우저 — 캐스케이드 검사가 쓴다")
    assert "chromium-headless-shell" in 단, 단
    assert "install chromium\n" not in 단 and "install chromium " not in 단, 단


def test_CI_도_같은_핀을_쓴다():
    # ★ **수를 또 적으면 한쪽만 늙는다**(§91). 워크플로도 `pw.sh` 를 들여온다.
    단 = _단계("브라우저 — 캐스케이드 검사가 쓴다")
    assert "tools/lib/pw.sh" in 단, 단
    assert '"$PW_PIN"' in 단, 단
    assert 핀() not in _CI(), "워크플로가 판을 직접 적는다"


def test_브라우저를_doctor_보다_먼저_깐다():
    # ★ 순서가 뒤집히면 그 판은 또 건너뛴다 — 그리고 **건너뜀은 초록으로 보인다**.
    글 = _CI()
    assert 글.index("브라우저 — 캐스케이드") < 글.index("bash tools/doctor.sh --repo")
