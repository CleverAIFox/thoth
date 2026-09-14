"""용어집. 도메인 판정을 코드가 아니라 데이터가 한다.

★ 용어집을 코드에 박으면 그 도메인 전용 도구가 된다. 대신 glossary/*.json 을
  전부 훑어 원문에 실제로 나타난 용어가 가장 많은 것을 고른다. 새 도메인은
  JSON 파일 하나 추가로 끝나고 코드는 건드리지 않는다.

★ 맞은 개수로 판정하면 오탐이 난다. object · policy · role · node 같은 평범한
  영어 단어가 등재어이므로 AWS 와 무관한 산문도 두어 개는 쉽게 맞는다. 단어
  수로 가중치를 준다 — 여러 낱말로 된 용어(partition key)는 우연히 맞을 수
  없으므로 도메인 신호가 강하다(DECISIONS §10).

★ 용어집이 없거나 맞는 것이 없어도 번역은 정상 동작한다. 보편 규칙(고유명사
  유지 · 조사 부착 · 내용 추가 금지)이 프롬프트에 따로 있기 때문이다.
  용어집은 외부 관행과 표기를 맞추는 정련이지 번역의 전제가 아니다.

★ 맞은 용어만 프롬프트에 싣는다. 전부 실으면 프롬프트가 길어져 느려지고,
  쓰이지도 않을 항목이 모델의 주의를 나눠 가진다.
"""
import json
import pathlib
import re

DIR = pathlib.Path(__file__).parent / "glossary"
MIN_HITS = 2          # 맞은 용어 수의 하한
MIN_SCORE = 5         # 가중 점수의 하한. 한 낱말 용어 넷으로는 못 넘는다
MULTIWORD_W = 4       # 여러 낱말 용어의 가중치
MAX_TERMS = 25        # 프롬프트에 실을 상한

# ★ **절 표지를 상수로 둔다.** 검사가 프롬프트 문구를 리터럴로 들고 있으면
#   문구를 고칠 때마다 관계없는 이유로 깨진다. 같은 문자열이 두 곳에 살면
#   언젠가 갈린다(DECISIONS §14 · §66).
TRANS_HEADER = ("Use these term translations consistently "
                "(apply to every occurrence, including inflected forms):")
KEEP_HEADER = (
    "The following appear in the source and must be copied into the translation "
    "character for character, in English. Never translate them into Korean, "
    "even when the words look like ordinary nouns. "
    "Attach Korean particles after them:"
)

_books: dict[str, dict[str, str]] | None = None


def _load() -> dict[str, dict[str, str]]:
    global _books
    if _books is None:
        _books = {}
        if DIR.is_dir():
            for f in sorted(DIR.glob("*.json")):
                _books[f.stem] = json.loads(f.read_text(encoding="utf-8"))
    return _books


def _weight(term: str) -> int:
    """여러 낱말로 된 용어는 우연히 맞지 않는다. 'partition key' 한 건이
    'object' · 'policy' 같은 평범한 낱말 넷보다 강한 신호다."""
    return MULTIWORD_W if " " in term else 1


def _hits(book: dict[str, str], blob: str) -> dict[str, str]:
    found = {}
    for en, ko in book.items():
        # 어미 변화를 표제어 하나로 흡수한다. records · recording 이 record 에
        # 걸리게 해서, 용어집에 단복수를 따로 넣는 취약한 방식을 피한다.
        if re.search(rf"\b{re.escape(en)}(s|es|ing|ed)?\b", blob):
            found[en] = ko
    return found


def score(terms: dict[str, str]) -> int:
    return sum(_weight(en) for en in terms)


def match(texts: list[str]) -> tuple[str | None, dict[str, str]]:
    """원문에 가장 잘 맞은 용어집과 그중 실제로 등장한 항목만 돌려준다."""
    blob = " ".join(texts).lower()
    best_name, best, best_score = None, {}, -1
    for name, book in _load().items():
        found = _hits(book, blob)
        s = score(found)
        if s > best_score:
            best_name, best, best_score = name, found, s
    if len(best) < MIN_HITS or best_score < MIN_SCORE:
        return None, {}
    trimmed = dict(sorted(best.items(), key=lambda kv: -len(kv[0]))[:MAX_TERMS])
    return best_name, trimmed


def is_keep(en: str, ko: str) -> bool:
    """항등 항목인가. 표기가 같으면 '번역하지 말라' 는 뜻이다."""
    return en.strip().lower() == ko.strip().lower()


def as_prompt(terms: dict[str, str]) -> str:
    """★ 항등 항목을 번역 목록에 섞지 않는다. `Data Catalog -> Data Catalog`
    는 사람에게는 자명하나 모델에게는 번역 지시 형식 그대로라, 나머지 항목과
    같은 자리에 놓이면 무엇을 하라는 것인지 흐려진다. 지시가 다르면 줄을
    나눈다(DECISIONS §20).
    """
    keep = {en: ko for en, ko in terms.items() if is_keep(en, ko)}
    trans = {en: ko for en, ko in terms.items() if not is_keep(en, ko)}

    # ★ 항등 항목 안에 들어 있는 짧은 용어는 번역 목록에서 뺀다.
    #   `catalog -> 카탈로그` 와 `Data Catalog 유지` 를 나란히 실으면 프롬프트
    #   자체가 모순이고, 모델은 둘 중 하나를 고른다. 2026-09-13 실측에서
    #   `DynamoDB Streams` 는 이겼고 `Data Catalog` 는 졌다 — 같은 모순인데
    #   결과가 갈렸으므로 모순을 남겨 두면 어느 쪽이 나올지 정할 수 없다.
    #
    # ★ `check()` 는 이미 같은 일을 한다("긴 용어에 포함된 짧은 용어는 빼고
    #   본다"). 검사만 그렇게 하고 프롬프트는 그러지 않았다. 같은 질문에 두
    #   답이 있으면 하나는 틀렸다(DECISIONS §28 · §30 의 재발).
    if keep:
        blob = " ".join(keep).lower()
        trans = {en: ko for en, ko in trans.items()
                 if not re.search(rf"\b{re.escape(en.lower())}(s|es)?\b", blob)}
    out = ""
    if trans:
        lines = "\n".join(f"  {en} -> {ko}" for en, ko in trans.items())
        out += "\n" + TRANS_HEADER + "\n" + lines
    if keep:
        # ★ 규칙 1 의 예시가 아니라 데이터다. 예시는 모델이 목록으로 취급해
        #   거기 없는 이름을 놓치는데(DECISIONS §30), 이 목록은 원문에 실제로
        #   나타난 것만 배치마다 새로 실린다. 늘어도 프롬프트가 자라지 않는다.
        names = ", ".join(sorted(keep.values()))
        # ★ **"proper names" 라고만 하면 모델이 그 판정을 스스로 한다.**
        #   `DynamoDB Streams` 는 지켜지는데 `Data Catalog` 는 3판 연속
        #   "데이터 카탈로그" 로 나왔다(Nova Lite). 차이는 브랜드 토큰이고,
        #   원문에 `the Data Catalog` 로 나오면 보통명사구처럼 읽힌다.
        #   **판정을 모델에게 맡기지 않고 목록 자체를 근거로 준다**
        #   (DECISIONS §66).
        out += "\n" + KEEP_HEADER + "\n  " + names
    return out
