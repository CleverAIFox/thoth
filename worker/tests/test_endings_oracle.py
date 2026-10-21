"""어미 표를 **두 엔진으로** 좁히는 자(DECISIONS §196 · §206).

★ **순환을 피하는 것이 설계 전부다.** `review.tsv` 의 `정답` 칸은 `tools/gen_endings.py`
  가 **Kiwi 의 `join`** 으로 만든 것이고, 그 머리말이 「순환이다. 그래서 사람이 본다」 고
  이미 적어 뒤었다. **Kiwi 로 채점하면 아무것도 안 잰다** — 제 출력을 제가 읽을 뿐이다.
  그래서 표를 만드는 데 관여하지 않은 **mecab-ko** 를 증인으로 세우고, **둘이 같은
  말을 할 때만** 걷어 낸다.

★ **시험은 엔진 없이 돈다.** 판정식은 `(종결어미, 선어말 집합)` 만 보므로 **가짜 엔진**
  으로 묻는다. 그 꼴은 2026-10-19 에 **실물 kiwi 0.24.0 · mecab 1.3.7 을 찍어 재서** 쓴
  것이다 — 추측한 꼴로 가드를 세우면 가드가 제 상상을 지킨다(§194).
★ **이 눈 밖** : CI 는 「실물 표 × 실물 엔진」 을 안 본다(엔진 둘이 50MB 넘는다).
  그 자리는 `doctor` 가 기계 범위에서 본다.
"""
import importlib.util
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import strip_prose

ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("oracle", ROOT / "tools/endings_oracle.py")
OR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(OR)

# ★ **실물을 찍어 재서 쓴 꼴이다.** 값은 `(종결어미, 선어말 집합)` — 두 엔진이 **같은
#   문장을 다른 자모 꼴로** 낸다는 것이 이 표의 요점이다.
#   `봅니다` : kiwi 는 종성 `ᆸ니다`(U+11B8) · mecab 은 초성 `ᄇ니다`(U+1107)
#   `봐요`   : kiwi 는 `어요` · mecab 은 **호환 자모** `ㅏ요`(U+314F)
찍은것 = {
    "kiwi": {
        "그것을 봐요.": ("어요", set()),
        "그것을 봅니다.": ("ᆸ니다", set()),
        "봅니다.": ("ᆸ니다", set()),
        "봐요.": ("어요", set()),
        "봐요!": ("어요", set()),
        "봤어요.": ("어요", {"았"}),
        "그것을 들으세요.": ("으세요", set()),
        "그것을 들으십시오.": ("ᆸ시오", {"으시"}),
        "하얘요.": ("어요", set()),           # 둘 다 읽는다
        "하얗습니다.": ("습니다", set()),
        "그럴까요?": ("ᆯ까요", set()),        # mecab 이 모르는 자리
        "그렇습니까?": ("습니까", set()),
    },
    "mecab": {
        "그것을 봐요.": ("ㅏ요", set()),
        "그것을 봅니다.": ("ᄇ니다", set()),
        "봅니다.": ("ᄇ니다", set()),
        "봐요.": ("ㅏ요", set()),
        "봐요!": ("ㅏ요", set()),
        "봤어요.": ("어요", {"았"}),
        "그것을 들으세요.": ("으세요", set()),
        "그것을 들으십시오.": ("ᄇ시오", {"으시", "시"}),
        "하얘요.": ("어요", set()),
        "하얗습니다.": ("ᄇ니다", set()),      # 체는 같고 꼴만 다르다
        "그럴까요?": ("ㄹ걸", set()),          # 어미 목록 밖 — 모른다
        "그렇습니까?": ("습니까", set()),
    },
}


def _읽기(이름):
    def 읽는다(s):
        표 = 찍은것[이름]
        if s not in 표:
            raise AssertionError(f"찍어 두지 않은 입력이다 : {이름} / {s}")
        return 표[s]
    return 읽는다


@pytest.fixture
def 엔진():
    return {이름: _읽기(이름) for 이름 in 찍은것}


@pytest.fixture
def 한쪽():
    """증인이 하나뿐인 판 — **그것이 순환이다.** 이 꼴로 돌면 안 된다는 것을 묻는다."""
    return {"kiwi": _읽기("kiwi")}


def test_둘이_같이_읽으면_맞다(엔진):
    assert OR.본다(엔진, "그것을 봐요.", "그것을 봅니다.") == ("맞다", "")


def test_자모_꼴이_달라도_같게_읽는다(엔진):
    """★ kiwi 의 `ᆸ니다`(종성) · mecab 의 `ᄇ니다`(초성) · `ㅏ요`(호환 자모)는 **표기
    차이**이지 판정 차이가 아니다. 앞에 붙은 자모를 떼어 맞춘다 — 재서 안 구멍이고
    카나리아가 바로 물었다."""
    assert OR.표준("ᆸ니다") == OR.표준("ᄇ니다") == "니다"
    assert OR.표준("ㅏ요") == "요"
    assert OR.본다(엔진, "하얘요.", "하얗습니다.") == ("맞다", "")


def test_원문과_정답이_같으면_그대로다(엔진):
    # ★ **손대면 안 되는 자리다** — 입력이 이미 합쇼체면 답은 「안 바꾼다」 이고
    #   그 줄이 283 중 87 이다. 틀렸다고 읽으면 검사가 통째로 거짓 빨강이 된다.
    assert OR.본다(엔진, "봅니다.", "봅니다.") == ("그대로", "")


def test_정답이_합쇼체가_아니면_운다(엔진):
    갈래, 까닭 = OR.본다(엔진, "그것을 봐요.", "봐요!")
    assert 갈래 == "다르다" and "체가" in 까닭, 까닭


def test_시제가_갈리면_운다(엔진):
    갈래, 까닭 = OR.본다(엔진, "봤어요.", "봅니다.")
    assert 갈래 == "다르다", (갈래, 까닭)


def test_한_엔진이_못_읽으면_모른다다(엔진):
    # ★ **못 읽은 것은 통과가 아니다**(§59). 그리고 한 엔진만 읽은 줄을 「맞다」 로
    #   세면 **증인이 하나인 판정**이 된다 — 그것이 피하려던 바로 그 꼴이다.
    갈래, 까닭 = OR.본다(엔진, "그럴까요?", "그렇습니까?")
    assert 갈래 == "모른다" and "mecab" in 까닭, 까닭


def test_높임은_켜짐_꺼짐이지_세는_것이_아니다(엔진):
    """★ **2026-10-19 의 거짓 빨강이다.** `들으십시오` 는 선어말 `으시` **와** 높임을
    품은 어미 `ᆸ시오` 를 **둘 다** 들고, `들으세요` 는 어미 하나만 든다. 높임을
    **더하면** 2 ≠ 1 이 되어 **맞는 줄 스물셋이 틀렸다고 났다.**"""
    assert OR.본다(엔진, "그것을 들으세요.", "그것을 들으십시오.") == ("맞다", "")


def test_엔진이_갈리면_사람에게_간다():
    """★ **증인 둘이 말이 다르면 그 줄이 사람 자리다.** 실물 표에서 셋이 그랬다."""
    엔진 = {"a": lambda s: ("어요", set()) if "봐" in s else ("습니다", set()),
            "b": lambda s: ("어요", set()) if "봐" in s else ("어요", set())}
    갈래, 까닭 = OR.본다(엔진, "봐요.", "봅니다.")
    assert 갈래 == "엔진이갈린다" and "a" in 까닭 and "b" in 까닭, 까닭


def test_증인이_하나면_그것은_순환이다(한쪽):
    # ★ **한 엔진만으로도 「맞다」 가 나온다 — 그래서 위험하다.** 이 시험은 그 꼴이
    #   가능하다는 것을 **드러내 놓고** 적는다. 막는 것은 `엔진들()` 이 둘을 다
    #   들이지 못하면 `None` 을 내는 자리다(아래 시험).
    assert OR.본다(한쪽, "그것을 봐요.", "그것을 봅니다.") == ("맞다", "")


def test_엔진이_하나라도_없으면_2_로_끝난다(monkeypatch):
    monkeypatch.setattr(OR, "엔진들", lambda 만든다=None: None)
    assert OR.main([]) == 2


def test_카나리아가_산다(엔진):
    OR._카나리아검사(엔진)          # 죽으면 SystemExit(2)


def test_카나리아가_판정식이_죽은_것을_잡는다(monkeypatch, 엔진):
    # ★ **0 건을 통과로 세지 않는다.** `본다` 가 늘 「맞다」 면 이 검사는 **꺼진 채
    #   초록**이다 — §171 이 만들어진 모양 그대로다.
    monkeypatch.setattr(OR, "본다", lambda *a: ("맞다", ""))
    with pytest.raises(SystemExit) as e:
        OR._카나리아검사(엔진)
    assert e.value.code == 2


def test_목록을_자료에_맞춰_깎지_않는다():
    # ★ **통과율이 올라갈 때까지 목록을 늘리면 오라클이 아니라 거울이 된다.** 그
    #   위험을 글로 적어 두는 것이 이 검사의 전부다 — 지우면 다음 사람이 모른다.
    글 = (ROOT / "tools/endings_oracle.py").read_text(encoding="utf-8")
    assert "거울" in 글, "자료에 맞춰 깎는 위험이 안 적혀 있다"


def test_판정_칸에_아무것도_안_쓴다():
    # ★ **이 도구는 좁히고 사람이 정한다.** 기계가 `판정` 을 채우면 `MASTER §7-3` 이
    #   기대는 고리가 **도로 닫힌다.**
    코드 = strip_prose.본문(ROOT / "tools/endings_oracle.py")
    for 쓰기 in ("write_text", "writer(", ".write("):
        assert 쓰기 not in 코드, f"표에 쓰는 길이 있다 : {쓰기}"
    assert 'open(encoding="utf-8")' in 코드, "읽기가 읽기 전용이 아니다"


def test_표가_실재하고_칸이_맞다():
    import csv
    p = ROOT / "worker/tests/endings/review.tsv"
    assert p.is_file(), "어미 표가 없다"
    with p.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    assert len(rows) >= 200, f"{len(rows)}줄뿐이다 — 표가 좁아졌다"
    for 칸 in ("id", "부류", "문형", "원문", "정답", "판정"):
        assert 칸 in rows[0], f"{칸} 칸이 없다"


# ── 판 고정 (§194 의 `pw.sh` 와 같은 결) ───────────────────────────────────

맨들 = ["--with " + "kiwipiepy", "--with " + "python-mecab-ko"]
맨목록 = "ls-" + "files"


def test_정본이_둘을_다_든다():
    import re
    글 = (ROOT / "tools/lib/morph.sh").read_text(encoding="utf-8")
    for 이름, 꼴 in (("KIWI_PIN", r"kiwipiepy==\d+\.\d+\.\d+"),
                     ("MECAB_PIN", r"python-mecab-ko==\d+\.\d+\.\d+")):
        m = re.search(이름 + r'="([^"]+)"', 글)
        assert m and re.fullmatch(꼴, m.group(1)), (이름, 글[:60])
    assert "이 눈 밖" in 글, "엔진이 못 보는 것을 안 적는다"


def test_아무도_맨_엔진을_안_부른다():
    # ★ **핀 없이 부르면 어느 날 `정답` 칸이 조용히 달라진다.** 2026-10-19 까지
    #   `tools/gen_endings.py` 가 그렇게 돌고 있었다 — §194 의 playwright 와 같은 병.
    import re
    흠 = {}
    for p in strip_prose.추적파일("*.sh", "*.py", "*.yml"):
        rel = str(p.relative_to(ROOT))
        if rel in ("tools/lib/morph.sh", "worker/tests/test_endings_oracle.py"):
            continue
        난것 = [x.strip() for x in strip_prose.본문(p).splitlines()
               if re.search(r"--with\s+(kiwipiepy|python-mecab-ko)(?![=\w])", x)]
        if 난것:
            흠[rel] = 난것
    assert 흠 == {}, 흠


def test_doctor_와_생성기가_정본을_들여온다():
    for rel, 핀 in (("tools/doctor.sh", '"$KIWI_PIN"'),
                    ("tools/gen_endings.py", '"$KIWI_PIN"')):
        글 = (ROOT / rel).read_text(encoding="utf-8")
        assert "tools/lib/morph.sh" in 글, f"{rel} 이 핀 정본을 안 들여온다"
        assert 핀 in 글, f"{rel} 이 핀을 안 쓴다"
    # ★ 증인 쪽 핀은 doctor 만 쓴다 — 생성기는 Kiwi 만 쓴다(그것이 순환의 출처다).
    assert '"$MECAB_PIN"' in (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")


def test_목록_뽑는_자리가_하나다():
    """★ **§195 가 「추적 경로가 전부 ASCII 인 것을 관문으로 들었다」 고 적었는데 그
    관문은 없었고 주장도 거짓이었다** — `docs/proposal/수.js` 와 `extension/src/지문.js`
    가 이미 있었다. `.js` 라 어느 목록에도 안 걸렸을 뿐이고, §196 이 `.py` 하나를
    한글로 두자마자 검사 셋이 **없는 파일**로 터졌다.

    ★ **고칠 자리는 이름이 아니라 구분자다.** `-z` 면 git 이 안 싼다. 이름을 ASCII 로
      묶는 관문은 **이미 못 지키는 약속**이다 — 목록 뽑는 자리를 **하나로 모은다.**
    ★ 저장소 전체에 `-z` 를 강요하지는 않는다. `doctor.sh` 의 `ls-files | grep` 처럼
      **경로를 열지 않는 자리**는 싸여도 상관없다 — **거짓 빨강을 만들지 않는다**(§126).
    """
    쓰는것 = (ROOT / "worker/tests/test_endings_oracle.py",
              ROOT / "worker/tests/test_pw_pin.py")
    for p in 쓰는것:
        코드 = strip_prose.본문(p)
        assert "strip_prose.추적파일" in 코드, f"{p.name} 이 목록 정본을 안 쓴다"
        # ★ **금지하는 글자를 제 소스에 적지 않는다** — 런타임에 짜 맞춘다(§131 의
        #   `"7" * 12` · §195 의 `맨`). 그대로 적으면 **이 줄이 제 검사에 걸린다.**
        assert 맨목록 not in 코드, f"{p.name} 이 제 손으로 목록을 뽑는다"
    # ★ **정본이 실제로 읽히는지 잰다** — 글만 재면 배선을 안 잰다(§173).
    것 = strip_prose.추적파일("*.py")
    assert len(것) >= 50 and all(p.is_file() for p in 것), len(것)


def test_파이썬_판도_핀이다():
    """★ **안 박으면 엔진이 아예 안 깔린다** — 2026-10-19 에 그의 기계에서 터졌다.
    `python-mecab-ko` 는 **cp313 휠이 하나도 없고** 워커가 3.13 이라 `uv` 가 소스
    빌드로 떨어져 `mecab-config not found` 로 죽었다. cp312 에는 manylinux 휠이 있다.
    ★ **워커 판과 엮지 않는다.** 엮으면 워커를 올릴 때 이 검사가 **조용히 꺼진다.**"""
    import re
    글 = (ROOT / "tools/lib/morph.sh").read_text(encoding="utf-8")
    m = re.search(r'MORPH_PY="(\d+\.\d+)"', 글)
    assert m, "파이썬 판을 안 박는다"
    assert "cp313" in 글, "왜 그 판인지(휠 표)를 안 적는다"
    doc = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    assert '--python "$MORPH_PY"' in doc, "doctor 가 그 판으로 안 부른다"
    assert "--no-project" in doc, "워커 판에 묶이면 휠 없는 쪽으로 끌려간다"


def test_못_들인_것을_흠으로_안_읽는다():
    """★ **종료 코드만으로는 못 가른다** — `uv` 가 빌드에 실패해도 **1** 로 끝나서
    2026-10-19 에 「엔진이 없다」 가 **WARN** 으로 찍혔다. 읽는 사람은 「표에 흠이
    있다」 로 읽는다. 그 자가 **실제로 입을 열었는지**를 같이 본다(§59)."""
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    코드 = strip_prose.본문(ROOT / "tools/doctor.sh")
    절 = 코드[코드.index('echo "== 어미 표 =="'):]
    절 = 절[:절.index('echo "== 돌연변이 =="')]
    assert 'case "$EN_OUT" in' in 절, "출력을 안 보고 종료 코드만 믿는다"
    assert "EN_RC=9" in 절, "못 들인 것을 다른 갈래로 안 옮긴다"
    assert "grep -m1" in 절, "요약 줄을 이름으로 안 집는다"


# ── 이미 판정된 줄은 다시 안 묻는다 (DECISIONS §206) ──────────────────────
# ★ **종전에는 `판정` 칸을 아예 안 읽었다.** 그래서 밖에서 채워 넣어도 이 자가 같은
#   줄을 계속 찍었고, 「볼 줄 22」 가 영영 22 였다. **좁히는 자가 채운 것을 모르면
#   좁히기가 끝나지 않는다** — 일한 것이 도구에 안 보이면 안 한 것과 같다.

def _줄(판정, 원문="봤어요.", 정답="봅니다."):
    """기본값은 **엔진이 「다르다」 로 보는 줄**이다 — 건너뜀이 갈래 때문이 아니라
    판정 때문임을 묻는다."""
    return {"id": "x1", "부류": "ㅅ", "문형": "평서", "원문": 원문, "정답": 정답, "판정": 판정}


def test_미정인_줄은_볼_줄로_남는다(엔진):
    셈, 남은것 = OR.훑는다(엔진, [_줄("미정")])
    assert [r["id"] for _, _, r in 남은것] == ["x1"]
    assert 셈["판정됨"] == 0


def test_판정된_줄은_볼_줄에서_빠진다(엔진):
    for 값 in ("O", "X"):
        셈, 남은것 = OR.훑는다(엔진, [_줄(값)])
        assert 남은것 == [], f"{값} 인데 다시 묻는다"
        assert 셈["판정됨"] == 1


def test_판정_칸이_없어도_미정으로_본다(엔진):
    """★ **없는 것을 「봤다」 로 읽지 않는다**(§59). 칸이 비면 안 본 것이다."""
    줄 = _줄("미정"); 줄.pop("판정")
    assert len(OR.훑는다(엔진, [줄])[1]) == 1
    빈줄 = _줄("   ")
    assert len(OR.훑는다(엔진, [빈줄])[1]) == 1


def test_실물_표에_미정이_아닌_줄이_있다():
    """★ **채운 것이 실제로 거기 있나.** 합성으로만 물으면 표가 비어도 초록이다."""
    import csv
    with (OR.표).open(encoding="utf-8") as f:
        값 = [r["판정"] for r in csv.DictReader(f, delimiter="\t")]
    assert 값.count("O") + 값.count("X") >= 22, f"판정된 줄 {len(값) - 값.count('미정')}"
