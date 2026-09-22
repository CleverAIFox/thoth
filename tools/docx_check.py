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
| RETIRED | 폐기된 옛 값 · 옛 서술이 남아 있는가 |

★ 있는지만 보면 옛 값과 새 값이 **둘 다** 있어도 통과한다. 없어야 할 것을 따로 본다
  (파이어레인 `docnum_check.py` 2026-08-18 확장과 같은 이유).

★ docx 는 표준 라이브러리로 연다(zip + XML). 의존성이 없다.
"""
from __future__ import annotations

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
]


def text_of(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
    return "\n".join("".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", p)) for p in paras)


def truths(root: Path) -> list[tuple[str, str]]:
    """(기획서에 있어야 할 문자열, 출처)."""
    base = json.loads((root / "docs/bench/baseline.json").read_text(encoding="utf-8"))
    bed = base["engines"]["bedrock"]
    rows = [json.loads(x) for x in (root / "worker/tests/endings/corpus.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
    corpus = sum(1 for r in rows if not r.get("meta"))
    test = (root / "worker/tests/test_endings_corpus.py").read_text(encoding="utf-8")
    ceiling = re.search(r"^WRONG_CEILING = (\d+)", test, re.M).group(1)
    engines = re.findall(r'ENGINE == "(\w+)"', (root / "worker/app/engine.py").read_text(encoding="utf-8"))
    out = [
        (f"{base['golden']['units']}유닛", "baseline.json golden.units"),
        (f"{bed['speed']['sec_per_question']}초", "baseline.json bedrock.speed.sec_per_question"),
        (f"${bed['cost']['golden_run_usd']['3']}", "baseline.json bedrock.cost.golden_run_usd[3]"),
        (f"{corpus:,}", "corpus.jsonl 줄 수"),
        (f"틀림 {ceiling}", "test_endings_corpus.WRONG_CEILING"),
    ]
    out += [(e, "engine.py 엔진 분기") for e in engines]
    return out


def check(text: str, root: Path) -> list[str]:
    fails = [f"기획서에 '{want}' 가 없다 — 정본 {src}" for want, src in truths(root) if want not in text]
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


def main() -> int:
    _canary()
    if not DOCX.exists():
        print(f"    {DOCX.relative_to(ROOT)} 가 없다")
        return 1
    fails = check(text_of(DOCX), ROOT)
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
