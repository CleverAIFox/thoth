"""건너뛰는 자리가 전부 선언됐는가 — `tools/check_skips.py`.

★ **SKIP 은 「통과」 가 아니라 「안 봤다」 다.** 검사를 끄는 가장 쉬운 길이 `skip`
  한 줄을 더하는 것이고, 그러면 그 자리는 영원히 안 보이면서 화면에는 「이상 없음」
  이 뜬다(DECISIONS §135 · §136).

★ **합성 글만 재면 진짜 `doctor.sh` 가 어긋나도 초록이다.** 실물도 함께 본다.
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("check_skips", ROOT / "tools/check_skips.py")
cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cs)

산행 = {59, 63, 68}


def test_지금_저장소가_조용하다():
    assert cs.fails(cs.DOCTOR.read_text(encoding="utf-8"), cs._plan_rows()) == []


def test_모든_갈래가_어휘_안이다():
    for arg, (갈래, _) in cs.선언.items():
        assert 갈래 in ("범위", "도구", "조건", "빚"), f"{arg} → {갈래}"


def test_빚은_전부_행이나_절을_든다():
    # ★ **빚은 가리킬 곳이 있어야 한다.** 안 들면 영원히 노란 채로 남는다.
    for arg, (갈래, 근거) in cs.선언.items():
        if 갈래 == "빚":
            assert cs._근거참조.search(근거), f"{arg} 의 근거에 행도 절도 없다"


def test_선언_안_된_skip_을_문다():
    글 = 'skip "이건 아무 데도 선언 안 된 말이다"\n'
    난것 = cs.fails(글, 산행)
    assert any("선언 안 된 skip" in x for x in 난것)


def test_죽은_선언을_문다():
    # ★ **표가 썩는 것도 잡는다.** 양방향이다 — 늘어도 줄어도 운다.
    글 = 'skip "infra 가 없다"\n'
    난것 = cs.fails(글, 산행)
    assert any("죽은 선언" in x for x in 난것)
    assert not any('"infra 가 없다"' in x and "선언 안 된" in x for x in 난것)


def test_주석_속_skip_은_안_센다():
    # ★ 음성 대조. 주석의 예시를 호출로 읽으면 **고칠 수 없는 FAIL** 이 생긴다.
    글 = '# 이렇게 적는다 : skip "예시다"\n   #  skip "들여쓴 주석"\n'
    assert cs.호출들(글) == []


def test_비슷한_이름의_함수를_안_센다():
    # ★ 음성 대조. `noskip` · `skipped` 같은 이름이 걸리면 안 된다.
    글 = 'noskip "x"\nskipper "y"\n'
    assert cs.호출들(글) == []


def test_빚이_죽은_행을_가리키면_문다(monkeypatch):
    # ★ **행이 닫혔는데 skip 이 남아 있으면 그 skip 은 근거가 없다.**
    # ★ **합성으로 묻는다**(DECISIONS §179). 종전에는 실물 선언(기준선 자리)을 예로
    #   들었는데, 2026-10-10 에 그 자리가 **빚에서 조건으로** 옮겨 가자 이 검사의
    #   전제가 통째로 죽었다 — **예로 든 실물이 바뀌면 검사가 같이 죽는다.**
    monkeypatch.setitem(cs.선언, "합성 빚", ("빚", "PLAN #59 가 연다"))
    난것 = cs.fails('skip "합성 빚"\n', {63, 68})        # #59 가 닫힌 세상
    assert any("죽은 행을 가리킨다" in x for x in 난것)


def test_근거_없는_빚을_문다(monkeypatch):
    monkeypatch.setitem(cs.선언, "합성 빚", ("빚", "그냥 나중에 한다"))
    난것 = cs.fails('skip "합성 빚"\n', 산행)
    assert any("빚인데 근거가 없다" in x for x in 난것)


# ── 갈래가 참말인가 (DECISIONS §150) ─────────────────────────────────────
#
# ★ **§136 은 「선언이 있나」 만 봤다.** `도구` 라고 적고 아무 조건 없이 늘 건너뛰어도
#   통과한다 — 그러면 검사는 영원히 꺼진 채로 **「이 기계에 도구가 없을 뿐」** 이라고
#   말한다. 검사를 끄는 가장 싼 길이 한 칸 더 안쪽으로 옮겨 간 것뿐이다.
#
# ★ **`조건`(15곳)은 안 본다.** 자리 모양이 여섯 가지라 하나를 고르면 **맞는 코드를
#   검사 만족시키려고 비틀게** 된다. 못 보는 자리를 좁히고 그 자리를 적는다(§73).

_도구글 = '''echo "== 파이썬 =="
if command -v ruff >/dev/null 2>&1; then
  RUFF=(ruff)
fi
if [ "${#RUFF[@]}" = 0 ]; then
  skip "ruff 를 부르지 못해 파이썬을 보지 못한다"
fi
'''


def test_도구인데_그_칸에_도구를_안_묻으면_문다():
    글 = _도구글.replace("command -v ruff >/dev/null 2>&1", "false")
    난것 = cs.갈래가_거짓말인가(글)
    assert any("command -v ruff" in x for x in 난것), 난것


def test_도구를_묻는_칸이면_안_문다():
    # ★ 음성 대조 — 모든 `도구` 에 우는 자는 아무것도 안 재는 것이다.
    assert cs.갈래가_거짓말인가(_도구글) == []


def test_한_다리_건너_물어도_받는다():
    # ★ **모양으로 안 본다.** `ruff` 는 `command -v` 가 변수를 세우고 skip 은 그
    #   변수로 갈린다 — 「감싸는 if 의 조건문」 으로 보면 이 정직한 자리가 걸린다.
    assert "command -v ruff" in _도구글 and "RUFF" in _도구글
    assert cs.갈래가_거짓말인가(_도구글) == []


def test_다른_칸의_도구_검사는_안_쳐준다():
    # ★ **칸 경계를 안 찾으면 파일 전체가 둘레가 되어 아무거나 걸린다.**
    글 = ('echo "== 다른 칸 =="\n'
          'if command -v ruff >/dev/null 2>&1; then :; fi\n'
          'echo "== 파이썬 =="\n'
          'skip "ruff 를 부르지 못해 파이썬을 보지 못한다"\n')
    난것 = cs.갈래가_거짓말인가(글)
    assert any("command -v ruff" in x for x in 난것), f"남의 칸 검사를 쳐줬다 {난것}"


def test_범위인데_SCOPE_로_안_갈리면_문다():
    글 = 'echo "== 비밀값 =="\ntrue && skip ".env 존재 (기계 설정이다)"\n'
    assert any("SCOPE" in x for x in cs.갈래가_거짓말인가(글))


def test_범위가_SCOPE_로_갈리면_안_문다():
    글 = ('echo "== 비밀값 =="\n'
          '[ "$SCOPE" = "--repo" ] && skip ".env 존재 (기계 설정이다)"\n')
    assert cs.갈래가_거짓말인가(글) == []


def test_조건과_빚은_모양을_안_본다():
    # ★ **안 보는 것이 설계다.** 모양이 하나로 안 모이므로 관문을 세우지 않는다.
    글 = ('echo "== 아무 칸 =="\n'
          'skip "ollama 에 묻지 못해 미채택 모델을 재지 못했다"\n'
          'skip "기준선이 지금 코드의 것이 아니다 — 재측정은 PLAN #59 가 연다"\n')
    assert cs.갈래가_거짓말인가(글) == []


def test_fails_가_갈래_검사를_부른다():
    # ★ 함수가 있어도 `fails` 가 안 부르면 `doctor` 는 아무것도 못 본다.
    글 = _도구글.replace("command -v ruff >/dev/null 2>&1", "false")
    assert any("command -v ruff" in x for x in cs.fails(글, 산행))


def test_지금_저장소는_갈래도_참말이다():
    assert cs.갈래가_거짓말인가(cs.DOCTOR.read_text(encoding="utf-8")) == []


def test_주석_처리된_skip_은_안_본다():
    # ★ 주석 속 `skip` 을 세면 **없는 자리에 대고 운다.** `호출들` 과 같은 규칙이다.
    글 = ('echo "== 파이썬 =="\n'
          '# skip "ruff 를 부르지 못해 파이썬을 보지 못한다"\n')
    assert cs.갈래가_거짓말인가(글) == []


# ── 갈래별 자리 수 (DECISIONS §152) ─────────────────────────────────────────
#
# ★ MASTER 0-8 이 「도구 9곳 · 16곳만 본다」 를 **글자로** 박고 있었고 skip 하나를
#   더하자 **세 수가 한꺼번에 늙었다.** 이제 이 함수가 정본이고 `<!--count:-->` 가
#   문서를 묶는다 — 그러니 **이 함수가 틀리면 문서도 함께 틀린다.**

_가짜 = '''
echo "== 가 =="
command -v uv >/dev/null && skip "ㄱ"
if [ "$SCOPE" = "--repo" ]; then skip "ㄴ"; fi
skip "ㄷ"
skip "ㄹ"
'''
# ★ **합성 번호를 글자로 박지 않는다**(DECISIONS §129). 그냥 적으면 `check_docs` 가
#   이 파일을 읽고 「없는 행을 가리킨다」 로 운다 — 도구 쪽 카나리아와 같은 자리다.
_빚 = "PLAN " + "#" + "9001"
_선언 = {"ㄱ": ("도구", "uv"), "ㄴ": ("범위", "x"), "ㄷ": ("조건", "y"), "ㄹ": ("빚", _빚)}


def _센다(글=_가짜, 선언=None):
    원 = cs.선언
    cs.선언 = 선언 if 선언 is not None else _선언
    try:
        return cs.세기(글)
    finally:
        cs.선언 = 원


def test_갈래별로_센다():
    assert _센다() == {"skip_tool": 1, "skip_scope": 1, "skip_cond": 1,
                      "skip_debt": 1, "skip_all": 4, "skip_seen": 2}


def test_보는_것은_도구와_범위뿐이다():
    # ★ **「다 본다」 로 읽히면 안 본 자리를 본 것으로 믿는다.** 조건·빚은 안 본다.
    셈 = _센다()
    assert 셈["skip_seen"] < 셈["skip_all"], "본 수와 전체가 같아졌다 — 둘을 가르는 뜻이 사라진다"
    assert 셈["skip_seen"] == 셈["skip_tool"] + 셈["skip_scope"]


def test_선언_안_된_자리도_전체에는_든다():
    # ★ 안 선언된 것을 전체에서 빼면 **빠뜨린 것이 수에서도 사라진다.**
    셈 = _센다(선언={"ㄱ": ("도구", "uv")})
    assert 셈["skip_all"] == 4 and 셈["skip_tool"] == 1
    assert 셈["skip_seen"] == 1


def test_지금_저장소의_수가_문서와_묶여_있다():
    # ★ 수를 내는 것으로 끝나면 아무도 안 본다. `check_counts` 가 아는 이름이어야 한다.
    import importlib.util
    s = importlib.util.spec_from_file_location("cc", cs.ROOT / "tools/check_counts.py")
    cc = importlib.util.module_from_spec(s)
    s.loader.exec_module(cc)
    for 이름 in cs.세기(cs.DOCTOR.read_text(encoding="utf-8")):
        assert 이름 in cc.KNOWN, f"{이름} 을 check_counts 가 모른다 — 문서에 쓸 수 없다"


# ── 문자열 안의 ` #` 을 주석으로 읽었다 (DECISIONS §179) ──────────────────
#
# ★ 종전 `호출들` 은 `줄.split(" #", 1)[0]` 로 인라인 주석을 벗겼다. 그러면
#   `skip "… PLAN #59 가 연다"` 가 **문자열 한가운데서 잘리고** `_호출` 이 안 맞아
#   **선언이 멀쩡히 있는데 「죽은 선언」** 이 울었다. §178 의 `"/*"` 와 같은 모양이다.
# ★ **잠복해 있었다** — 선언 서른아홉 중 ` #` 을 품은 것이 없어서 안 터졌다.

def test_문자열_안의_우물정은_주석이_아니다():
    줄 = '  skip "기준선이 지금 코드의 것이 아니다 — 재측정은 PLAN #59 가 연다"'
    assert cs.호출들(줄) == ["기준선이 지금 코드의 것이 아니다 — 재측정은 PLAN #59 가 연다"]


def test_따옴표_밖의_우물정부터는_주석이다():
    assert cs.주석벗긴다('ok "가" # 뒤는 주석 "나"').rstrip() == 'ok "가"'
    assert cs.호출들('skip "가"   # skip "나"') == ["가"]


def test_우물정이_줄머리면_통째로_주석이다():
    assert cs.주석벗긴다('# skip "가"') == ""


def test_낱말_안의_우물정은_안_자른다():
    # ★ `a#b` 는 주석이 아니다. 앞이 공백일 때만 자른다 — 셸의 꼴 그대로다.
    assert cs.주석벗긴다('echo a#b') == 'echo a#b'


def test_벗긴_뒤에도_이스케이프된_따옴표를_안_센다():
    # ★ `\"` 를 따옴표로 세면 안팎이 뒤집히고, 그 뒤의 ` #` 판정이 전부 틀린다.
    assert cs.주석벗긴다(r'skip "가\"나" # 주석').rstrip() == r'skip "가\"나"'
