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


def as_prompt(terms: dict[str, str]) -> str:
    if not terms:
        return ""
    lines = "\n".join(f"  {en} -> {ko}" for en, ko in terms.items())
    return (
        "\nUse these term translations consistently "
        "(apply to every occurrence, including inflected forms):\n" + lines
    )
