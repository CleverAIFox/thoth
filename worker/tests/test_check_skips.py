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


def test_빚이_죽은_행을_가리키면_문다():
    # ★ **행이 닫혔는데 skip 이 남아 있으면 그 skip 은 근거가 없다.**
    글 = 'skip "기준선이 stale 이다 ($STALE) — 재측정 후 값을 채우고 플래그를 지운다"\n'
    for arg in list(cs.선언):
        if arg != 글.split('"')[1]:
            pass
    난것 = cs.fails(글, {63, 68})        # #59 가 닫힌 세상
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
          'skip "기준선이 stale 이다 (local) — 재측정 후 값을 채우고 플래그를 지운다"\n')
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
