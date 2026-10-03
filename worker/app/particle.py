"""조사 — 받침 한 비트로 결정적으로 갈린다.

★ **마스킹의 치명적 단점은 「모델이 그 자리를 못 봐서 조사가 어색해진다」 였다**
  (DECISIONS §143). 그 단점을 안고 현업 방식을 그대로 쓰는 것은 답이 아니다.
  **조사는 모델이 고를 일이 아니다** — 앞말의 끝 받침으로 닫힌 규칙이 정한다.
  규칙을 코드가 들면 모델이 그 자리를 보든 안 보든 조사는 맞는다.

★ **그래서 이 파일이 먼저다.** 조사를 결정적으로 고치면 자리표시 치환의 첫째
  대가가 사라진다. 그 전에 치환부터 넣으면 **대가를 그대로 받아 안는다.**

★ **이미 두 군데서 틀리고 있었다.** 2026-10-03 실측:
    모델    : `...Data Catalog이 버킷의...`   → 카탈로그는 받침이 없다. `가` 다
    되돌리기 : `DynamoDB 스트림을` → `DynamoDB Streams을`
              스트림(ㅁ)에 맞춰 고른 `을` 을 스트림스(받침 없음)에 그대로 붙였다
  둘째는 §139 가 만든 결함이다 — **되돌리기가 모델이 고른 조사를 들고 갔다.**

★ **음차표를 만들지 않는다**(§139 가 거부한 그것). 필요한 것은 표가 아니라
  **끝 받침 한 비트**이고, 그것은 영어 표기에서 **도출된다** — 외래어 표기법에서
  받침이 되는 끝소리는 `n`·`m`·`l`·`ng` 뿐이고 나머지 자음은 모두 `으`/`이` 를
  달고 열린다(`Catalog`→카탈로그, `Streams`→스트림스, `Bedrock`→베드록... 열림).
  **끝 `r` 은 받침이 아니다**(`Inspector`→인스펙터).

★ **도출이 위험한 자리는 선언하고, 선언을 가드가 덮는다**(§136 · §139 · §142 와
  같은 답). 숫자로 끝나는 이름은 읽기가 갈린다(`S3`→에스쓰리 / Route `53`→오십삼).
  **갈리는 자리에서는 추정하지 않고 손을 뗀다** — 세고, `particle.json` 이 선언하면
  그때 건다. 선언이 규칙과 같은 답이면 **죽은 선언**이므로 가드가 운다(양방향).
"""
import json
import pathlib
import re

# 한글 끝 자모 번호. 0 = 받침 없음.
_ㄱ, _ㄴ, _ㄹ, _ㅁ, _ㅂ, _ㅅ, _ㅇ = 1, 4, 8, 16, 17, 19, 21

# ★ 영어 표기의 끝 글자 → 한국어 음차의 끝 받침. 여기 없는 자음은 전부 열린다
#   (`g`→그 · `s`→스 · `f`→프 · `r`→터 ... 모두 `으` 를 달고 열린다).
_끝받침 = {"n": _ㄴ, "m": _ㅁ, "l": _ㄹ}

# ★ **무성파열음만 갈린다**(외래어 표기법 제3장 제1항). 짧은 모음 하나 뒤에서는
#   받침으로 적고(book→북 · rock→록 · cat→캣 · cup→컵), 겹모음·장모음·자음 뒤에서는
#   `으` 를 달아 열린다(lake→레이크 · mask→마스크 · beat→비트 · connect→커넥트).
#   **이 갈림이 이 규칙에서 가장 안 미더운 자리다** — 실제 모음 길이는 철자로
#   완전히 안 갈린다(summit→서밋 · bit→비트). 틀리면 `particle.json` 이 덮는다.
_파열받침 = {"p": _ㅂ, "t": _ㅅ, "k": _ㄱ}
_모음 = set("aeiouy")

# ★ 조사 쌍 — (받침 뒤, 받침 없는 뒤). **긴 것부터 본다.**
#   `이`/`가` 는 뒤가 경계일 때만 조사다. `Catalog이다` 의 `이` 는 서술격이고
#   `Lambda로그` 의 `로` 는 낱말의 첫 글자다 — 경계 규칙이 둘 다 걸러낸다.
쌍들: tuple[tuple[str, str], ...] = (
    ("으로서", "로서"), ("으로써", "로써"), ("으로", "로"),
    ("이라고", "라고"), ("이라는", "라는"), ("이라서", "라서"),
    ("이란", "란"), ("이라", "라"), ("이며", "며"), ("이나", "나"),
    ("은", "는"), ("이", "가"), ("을", "를"), ("과", "와"),
)

DECL_FILE = pathlib.Path(__file__).resolve().parent / "particle.json"
_선언: dict[str, str] | None = None
_값 = {"있음": _ㄴ, "ㄹ": _ㄹ, "없음": 0}


def _load_decl() -> dict[str, str]:
    """선언된 받침. 주석 열쇠(`_` 로 시작)는 버린다."""
    global _선언
    if _선언 is None:
        raw = json.loads(DECL_FILE.read_text(encoding="utf-8"))
        _선언 = {k: v for k, v in raw.items() if not k.startswith("_")}
    return _선언


def 한글받침(글자: str) -> int | None:
    """한글 한 글자의 끝 자모 번호. 한글이 아니면 None."""
    if not 글자 or not ("가" <= 글자 <= "힣"):
        return None
    return (ord(글자) - 0xAC00) % 28


def 영어받침(말: str) -> int | None:
    """영어 표기에서 한국어 음차의 끝 받침을 도출한다.

    None 은 **「모른다」** 다 — 추정하지 않고 손을 뗀다는 뜻이다.
    """
    선언 = _load_decl()
    if 말 in 선언:
        return _값[선언[말]]
    꼬리 = re.split(r"[\s_\-./]+", 말.strip())[-1]
    꼬리 = re.sub(r"[^A-Za-z0-9]", "", 꼬리)
    if not 꼬리:
        return None
    # ★ 끝소리가 조사를 정하므로 **선언도 꼬리로 찾는다.** `S3` 하나를 적으면
    #   `Amazon S3`·`AWS S3` 가 함께 덮인다 — 같은 말을 두 번 적게 하지 않는다.
    if 꼬리 in 선언:
        return _값[선언[꼬리]]
    # ★ 숫자로 끝나면 읽기가 갈린다(에스쓰리 / 오십삼). 선언 없이는 안 건다.
    if 꼬리[-1].isdigit():
        return None
    low = 꼬리.lower()
    # ★ 묵음 `e` 를 떼고 본다 — 단, 앞이 모음이면 그 모음이 끝소리다(Glue→글루).
    #   **묵음 `e` 는 앞 모음을 길게 만든다**(lake→레이크 · route→루트). 그래서
    #   뗐다는 사실 자체가 「장모음」 신호이고, 파열음은 그때 열린다.
    묵음e = len(low) > 2 and low.endswith("e") and low[-2] not in _모음
    if 묵음e:
        low = low[:-1]
    if low.endswith("ng"):
        return _ㅇ
    끝 = low[-1]
    if 끝 in _모음:
        return 0
    if 끝 in _끝받침:
        return _끝받침[끝]
    if 끝 in _파열받침:
        if 묵음e:
            return 0
        # `ck` 는 한 소리다 — 앞 모음은 `c` 를 건너뛰고 본다(rock→록).
        앞자리 = -3 if low.endswith("ck") else -2
        앞 = low[앞자리] if len(low) >= -앞자리 else ""
        앞앞 = low[앞자리 - 1] if len(low) >= -앞자리 + 1 else ""
        if 앞 in _모음 and 앞앞 not in _모음:
            return _파열받침[끝]
        return 0
    return 0


def 고르기(쌍: tuple[str, str], 받침: int) -> str:
    """받침 비트로 조사를 고른다."""
    받침꼴, 열린꼴 = 쌍
    # ★ `ㄹ` 받침은 `으로` 가 아니라 `로` 다 (서울로). 나머지 쌍은 받침 규칙대로다.
    if 받침꼴.startswith("으") and 받침 == _ㄹ:
        return 열린꼴
    return 받침꼴 if 받침 else 열린꼴


# 영어 덩이 + 조사. 조사 뒤는 **경계**여야 한다.
_조사알 = "|".join(sorted({a for 쌍 in 쌍들 for a in 쌍}, key=len, reverse=True))
_꼴 = re.compile(
    rf"(?<![A-Za-z])([A-Za-z][A-Za-z0-9]*(?:[ _\-./][A-Za-z0-9]+)*)({_조사알})"
    r"(?=$|[\s.,!?;:)\]’\"'」』·])"
)

UNSURE: dict[str, int] = {}


def fix(ko: str) -> tuple[str, list[str]]:
    """영어 낱말 뒤 조사를 받침에 맞춘다. 고친 자리를 함께 돌려준다."""
    고친것: list[str] = []

    def 바꾸기(m: re.Match[str]) -> str:
        말, 조사 = m.group(1), m.group(2)
        받침 = 영어받침(말)
        if 받침 is None:
            UNSURE[말] = UNSURE.get(말, 0) + 1
            return m.group(0)
        for 쌍 in 쌍들:
            if 조사 not in 쌍:
                continue
            맞는것 = 고르기(쌍, 받침)
            if 맞는것 != 조사:
                고친것.append(f"{말}{조사}→{맞는것}")
                return f"{말}{맞는것}"
            return m.group(0)
        return m.group(0)

    return _꼴.sub(바꾸기, ko), 고친것


# ── 족 가드 ─────────────────────────────────────────────────────────────────
#
# ★ 묻는 것은 「이 값이 맞나」 가 아니라 **「규칙과 선언이 어긋난 자리가 있나」** 다.
#   선언이 규칙과 같은 답이면 그 선언은 **아무 일도 하지 않으면서 썩는다.**


def decl_fails() -> list[str]:
    난것: list[str] = []
    raw = json.loads(DECL_FILE.read_text(encoding="utf-8"))
    if not any(k.startswith("_") for k in raw):
        난것.append("particle.json 에 까닭 주석이 없다")
    for 말, 값 in _load_decl().items():
        if 값 not in _값:
            난것.append(f"{말}: 받침 값 {값!r} 은 {sorted(_값)} 중 하나여야 한다")
            continue
        # ★ 선언을 끄고 규칙만 돌려 본다. 같은 답이면 죽은 선언이다.
        옛 = _선언
        try:
            globals()["_선언"] = {k: v for k, v in (옛 or {}).items() if k != 말}
            규칙 = 영어받침(말)
        finally:
            globals()["_선언"] = 옛
        if 규칙 is not None and 규칙 == _값[값]:
            난것.append(f"{말}: 규칙이 이미 같은 답을 낸다 — 죽은 선언이다")
    return 난것


def unsure_in(texts: list[str]) -> list[str]:
    """이 글뭉치 안에서 **규칙이 손을 떼는** 영어+조사 자리를 모은다.

    여기 걸린 것은 선언으로 덮어야 한다 — 안 덮으면 조사가 틀린 채 나간다.
    """
    난것: list[str] = []
    for t in texts:
        for m in _꼴.finditer(t):
            if 영어받침(m.group(1)) is None:
                난것.append(f"{m.group(1)}{m.group(2)}: 받침을 모른다 — particle.json 이 선언해야 한다")
    return sorted(set(난것))
