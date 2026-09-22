"""기획서가 정본과 어긋나지 않는가(DECISIONS §112).

  python3 tools/docx_check.py          검사한다. 위반이면 1, 도구 고장이면 2

★ **기획서는 네 문서 중 유일하게 밖이 읽는 것인데 시제 규칙 밖이라 강제자가 없기 쉽다.**
  파이어레인이 그렇게 낡았다(파이어레인 `docx_check.py` 머리말) — 갱신 대상 표까지
  같이 낡았다. 그래서 첫 판부터 검사를 붙인다.

★ **정본은 docx 가 아니다.** 숫자의 정본은 산출물이다 — `docs/bench/baseline.json` ·
  어미 코퍼스 · 톱니 상한 · 엔진 목록. 기획서가 그것과 다르면 산출물이 옳다.

| 검사 | 무엇 |
|---|---|
| PRESENT | 정본에서 읽은 값이 기획서에 문자열로 있는가 |
| STRUCTURE | 통합본의 뼈대(Part I · II · III · seshat)가 남아 있는가(DECISIONS §116) |
| FIGURES | 그림마다 선언한 사실(대체 텍스트)이 지금 산출물과 맞는가(DECISIONS §116) |
| RETIRED | 폐기된 옛 값 · 옛 서술이 남아 있는가 |

★ 있는지만 보면 옛 값과 새 값이 **둘 다** 있어도 통과한다. 없어야 할 것을 따로 본다
  (파이어레인 `docnum_check.py` 2026-08-18 확장과 같은 이유).

★ docx 는 표준 라이브러리로 연다(zip + XML). 의존성이 없다.

★ **그림 속 숫자는 PNG 라 읽지 못한다. 대신 선언을 읽는다.** 생성기(`docs/proposal/`)가 그림마다
  숫자의 출처를 사실로 적어 대체 텍스트(`wp:docPr descr`)에 싣고, 여기서 그 사실을 산출물과 다시
  대조한다. 기준선이 바뀌면 그 수를 그린 그림이 빨개진다. 문법은 `docs/proposal/figures/figlib.py`.
"""
from __future__ import annotations

import html
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCX = ROOT / "docs/proposal.docx"

# 폐기된 값. 값이 바뀌면 옛 값을 여기로 옮긴다.
RETIRED = [
    ("2,478", "어미 코퍼스 생성기 1판의 줄 수(DECISIONS §108)"),
    ("틀림 218", "톱니 상한 옛 값"),
    ("Free 플랜", "2026-09-16 유료 전환(DECISIONS §98)"),
    ("형태소 분석기로 교체", "후처리는 땜질에서 멈췄다(DECISIONS §108)"),
    ("껍데기 완결 · 번역 엔진 교체 대기", "기획서 1.0 표지의 상태 줄 — 2.0 은 thoth · seshat 통합본이다(DECISIONS §116)"),
]

# 통합본의 뼈대. 12장짜리 요약으로 돌아가면 걸린다(DECISIONS §116).
STRUCTURE = ["Part I.", "Part II.", "Part III.", "seshat", "세부 기능 요구사항 정의서", "비기능 요구사항"]


def text_of(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
    return "\n".join("".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", p)) for p in paras)


SEP = " ¦ "  # 사실 구분자. docs/proposal/lib.js 와 같다
DOCPR = re.compile(r"<wp:docPr\b[^>]*>")
DESCR = re.compile(r'\bdescr="([^"]*)"')


def figures_of(path: Path) -> list[str | None]:
    """그림마다 대체 텍스트(없으면 None)."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    out = []
    for tag in DOCPR.findall(xml):
        m = DESCR.search(tag)
        out.append(html.unescape(m.group(1)) if m else None)
    return out


def decisions_ranges(root: Path) -> dict[str, str]:
    """DECISIONS 의 날짜 → '§a–§b'. docs/proposal/figures/figlib.py 와 같은 규칙."""
    rng: dict[str, tuple[int, int]] = {}
    cur = None
    for line in (root / "docs/DECISIONS.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^## §(\d+)\.", line)
        if m:
            cur = int(m.group(1))
            continue
        m = re.match(r"^\*\*(\d{4}-\d{2}-\d{2})\*\*$", line)
        if m and cur is not None:
            a, b = rng.get(m.group(1), (cur, cur))
            rng[m.group(1)] = (min(a, cur), max(b, cur))
            cur = None
    return {d: (f"§{a}–§{b}" if a != b else f"§{a}") for d, (a, b) in rng.items()}


def _same(got, want: str) -> bool:
    if str(got) == want or json.dumps(got, ensure_ascii=False) == want:
        return True
    if isinstance(got, (int, float)) and not isinstance(got, bool):
        try:
            return float(want) == float(got)
        except ValueError:
            return False
    return False


def fact_fails(fact: str, root: Path) -> list[str]:
    """사실 하나를 산출물과 대조한다. 맞으면 []. external 은 대조 밖이라 [] 다."""
    if fact == "none" or fact.startswith("external:"):
        return []
    try:
        if fact.startswith("json:"):
            ref, want = fact[5:].split("=", 1)
            rel, dotted = ref.split("#", 1)
            got = json.loads((root / rel).read_text(encoding="utf-8"))
            for part in dotted.split("."):
                got = got[int(part)] if isinstance(got, list) else got[part]
            return [] if _same(got, want) else [f"{ref} 는 지금 {got!r} 인데 그림은 {want} 를 그렸다"]
        if fact.startswith("file:"):
            rel, want = fact[5:].split("~", 1)
            return [] if want in (root / rel).read_text(encoding="utf-8") else [f"{rel} 에 '{want}' 가 없다"]
        if fact.startswith("len:"):
            rel, want = fact[4:].split("=", 1)
            n = len(json.loads((root / rel).read_text(encoding="utf-8")))
            return [] if str(n) == want else [f"{rel} 는 지금 {n} 항목인데 그림은 {want} 를 그렸다"]
        if fact.startswith("decisions:"):
            day, want = fact[10:].split("=", 1)
            got = decisions_ranges(root).get(day)
            return [] if got == want else [f"DECISIONS {day} 는 지금 {got} 인데 그림은 {want} 를 그렸다"]
    except (OSError, KeyError, IndexError, ValueError) as e:
        return [f"'{fact}' 를 읽지 못했다 ({type(e).__name__}: {e})"]
    return [f"문법 밖의 사실 '{fact}'"]


def check_figures(descrs: list[str | None], root: Path) -> list[str]:
    fails = []
    for i, d in enumerate(descrs, 1):
        if not d or not d.startswith("src: "):
            fails.append(f"그림 {i} 에 사실 선언이 없다 — 생성기(docs/proposal/)로 다시 만든다")
            continue
        for fact in d[5:].split(SEP):
            fails += [f"그림 {i}: {x} — 그림을 다시 그린다" for x in fact_fails(fact.strip(), root)]
    return fails


def truths(root: Path) -> list[tuple[str, str]]:
    """(기획서에 있어야 할 문자열, 출처)."""
    base = json.loads((root / "docs/bench/baseline.json").read_text(encoding="utf-8"))
    bed = base["engines"]["bedrock"]
    rows = [json.loads(x) for x in (root / "worker/tests/endings/corpus.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    corpus = sum(1 for r in rows if not r.get("meta"))
    test = (root / "worker/tests/test_endings_corpus.py").read_text(encoding="utf-8")
    ceiling = re.search(r"^WRONG_CEILING = (\d+)", test, re.M).group(1)
    book = json.loads((root / "worker/app/glossary/aws.json").read_text(encoding="utf-8"))
    engines = re.findall(r'ENGINE == "(\w+)"', (root / "worker/app/engine.py").read_text(encoding="utf-8"))
    out = [
        (f"{base['golden']['units']}유닛", "baseline.json golden.units"),
        (f"{bed['speed']['sec_per_question']}초", "baseline.json bedrock.speed.sec_per_question"),
        (f"${bed['cost']['golden_run_usd']['3']}", "baseline.json bedrock.cost.golden_run_usd[3]"),
        (f"{corpus:,}", "corpus.jsonl 줄 수"),
        (f"틀림 {ceiling}", "test_endings_corpus.WRONG_CEILING"),
        (f"{base['golden']['chars']:,}자", "baseline.json golden.chars"),
        (f"${bed['cost']['usd_per_1m_input']}", "baseline.json bedrock.cost.usd_per_1m_input"),
        (f"{len(book)}항목", "glossary/aws.json 항목 수"),
    ]
    out += [(e, "engine.py 엔진 분기") for e in engines]
    return out


def check(text: str, root: Path) -> list[str]:
    fails = [f"기획서에 '{want}' 가 없다 — 정본 {src}" for want, src in truths(root) if want not in text]
    fails += [f"기획서에 뼈대 '{want}' 가 없다 — 통합본 구조(DECISIONS §116)" for want in STRUCTURE if want not in text]
    fails += [f"기획서에 폐기된 '{old}' 가 남아 있다 — {why}" for old, why in RETIRED if old in text]
    return fails


def _canary() -> None:
    xml = ('<w:document><w:body><w:p><w:r><w:t>가</w:t></w:r><w:r><w:t xml:space="preserve">나 </w:t></w:r></w:p>'
           '<w:p><w:r><w:t>다</w:t></w:r></w:p></w:body></w:document>')
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    buf.seek(0)
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d) / "c.docx"
        tmp.write_bytes(buf.getvalue())
        got = text_of(tmp)
    if got != "가나 \n다":
        print(f"    ★ 카나리아가 죽었다 — docx 본문을 {got!r} 로 읽었다")
        sys.exit(2)
    tag = '<wp:docPr id="1" name="f" descr="src: none &#166; x"/>'
    found = [html.unescape(DESCR.search(t).group(1)) for t in DOCPR.findall(tag)]
    if found != ["src: none ¦ x"]:
        print(f"    ★ 카나리아가 죽었다 — 그림 선언을 {found!r} 로 읽었다")
        sys.exit(2)


def main() -> int:
    _canary()
    if not DOCX.exists():
        print(f"    {DOCX.relative_to(ROOT)} 가 없다")
        return 1
    fails = check(text_of(DOCX), ROOT) + check_figures(figures_of(DOCX), ROOT)
    for f in fails:
        print(f"    {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
