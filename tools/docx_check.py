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
| STRUCTURE | 통합본의 뼈대(Part I · II · III · seshat · 3.0 의 절 넷)가 남아 있는가(DECISIONS §116 · §129) |
| FIGURES | 그림마다 선언한 사실(대체 텍스트)이 지금 산출물과 맞는가(DECISIONS §116) |
| RETIRED | 폐기된 옛 값 · 옛 서술이 남아 있는가 |
| PLAN 참조 | **생성기**가 못 세는 행 번호를 들었는가 — 닫힌 자기 행 · 남의 저장소의 행(DECISIONS §129) |

★ **마지막 줄만 docx 가 아니라 생성기를 읽는다.** 번호가 사는 자리가 거기이고,
  **docx 를 다시 안 구웠어도 고쳐야 할 글은 이미 틀려 있다.**

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
#
# ★ **3.0 의 줄 아홉이 한 사건에서 나왔다**(DECISIONS §129). 2.0 의 seshat 장은 설계였고
#   그 설계가 **재서 뒤집혔다.** 뒤집힌 문장은 「없어야 할 것」 으로 적어 둬야 한다 —
#   **있는지만 보면 옛 값과 새 값이 둘 다 있어도 통과한다.**
RETIRED = [
    ("2,478", "어미 코퍼스 생성기 1판의 줄 수(DECISIONS §108)"),
    ("틀림 218", "톱니 상한 옛 값"),
    ("Free 플랜", "2026-09-16 유료 전환(DECISIONS §98)"),
    ("형태소 분석기로 교체", "후처리는 땜질에서 멈췄다(DECISIONS §108)"),
    ("껍데기 완결 · 번역 엔진 교체 대기", "기획서 1.0 표지의 상태 줄 — 2.0 은 thoth · seshat 통합본이다(DECISIONS §116)"),
    # ── 3.0 에서 폐기한 2.0 의 문장들(DECISIONS §124 · §129) ──
    ("판 2.0", "표지의 판 번호 — 3.0 이다(DECISIONS §129)"),
    ("v0.1.8", "저장소에 정본이 없는 판 번호였다. 배포 판은 태그가 들고 문서는 수를 안 적는다"),
    ("0.0.2 기준", "seshat 판 번호를 기획서가 손으로 적던 자리 — 지금 선 팔의 정본은 seshat `data/scoreboard.toml` 이다"),
    ("모델은 아직 없다", "자체 가중치는 0 이지만 **팔 넷을 쟀고 재는 체계가 섰다**. 「없다」 로 적으면 8장의 수가 거짓이 된다"),
    ("설계이고 실측이 아니다", "2026-09-30 ~ 10-01 에 밖의 판정자 넷으로 쟀다(seshat §229 · §262)"),
    ("품질은 아직 누구도 이기지 못했다", "쟀고 순위가 났다 — 배포본이 뜻에서 가장 낫다(seshat §229)"),
    ("신경망 지표 — 검토 중", "검토가 끝났고 기각했다 — ollama LLM 판정이 ρ 로 0.22 앞선다(seshat §254)"),
    ("torch 는 별도 의존성 그룹", "`torch` · `transformers` 를 통째로 뺐다(seshat §254)"),
    ("워커 392", "테스트 건수를 기획서가 손으로 적던 자리 — 정본은 저장소 `README` 이고 `check_counts.py` 가 실측과 대조한다"),
    ("묻지 않는다. 결정적으로", "「모델에게 판정을 묻지 않는다」 는 **자리를 적어야 하는 문장**이었다 — "
                             "번역 경로에서는 참이고 평가 경로에서는 반대다(DECISIONS §66 · seshat §262)"),
]

# 통합본의 뼈대. 12장짜리 요약으로 돌아가면 걸린다(DECISIONS §116).
#
# ★ **3.0 의 뼈대 넷을 더했다.** 8장이 설계로 되돌아가거나 11장의 세 층이 한 표로
#   합쳐지면 **그것이 2.0 으로 돌아간 것**이고, 그 되돌림은 숫자 대조로는 안 걸린다
#   (DECISIONS §129).
STRUCTURE = ["Part I.", "Part II.", "Part III.", "seshat", "세부 기능 요구사항 정의서", "비기능 요구사항",
             "판 3.0", "바뀐 결론 넷", "자를 세 층으로 가른다", "전선이 셋이고 문턱이 둘이다"]


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


# ── 행 번호 참조 ──────────────────────────────────────────────────────────
#
# ★ **`check_docs` 는 문서 셋만 본다**(`DOCS` 상수). 기획서 생성기는 **어느 검사도 안
#   읽는다** — 그런데 이 저장소에서 **밖으로 나가는 문서가 그것뿐**이다. 이 파일 머리말이
#   「밖이 읽는 문서인데 시제 규칙 밖이라 강제자가 없기 쉽다」 로 적어 둔 그 자리에
#   **참조 검사가 빠져 있었다**(DECISIONS §129).
#
# ★ **물음은 「#5 가 있나」 가 아니라 「못 세는 번호를 들었나」 다**(족 가드). 전자로 적으면
#   새로 들인 참조가 검사를 비켜 간다.
#
#   | 꼴 | 판정 |
#   |---|---|
#   | `PLAN #N` · `thoth PLAN #N` | **센다** — `docs/PLAN.md` 에 그 행이 살아 있어야 한다 |
#   | `<남의 저장소> PLAN #N` | **금지한다** — 이 저장소에 그것을 아는 자가 없고, **닫힌 행은 사라진다** |
#
# ★ **남의 PLAN 행을 금지하고 DECISIONS 절은 허용하는 까닭.** PLAN 행은 닫히면 **지운다**
#   (양쪽 PLAN 의 규약). DECISIONS 는 **append-only** 라 절 번호가 안 사라진다. 그리고
#   기획서를 읽는 사람은 비공개 저장소의 PLAN 을 **열어 볼 수도 없다** — 못 따라가는 참조다.
#   2026-10-03 에 세어 보니 생성기가 **죽은 seshat 행 여섯과 닫힌 자기 행 하나**를 들고 있었다.
# ★ **임자를 「앞 낱말」 로 읽으면 한국어 부사가 저장소 이름이 된다.** 첫 판이
#   「넉 달 **동안** PLAN #59」 를 「`동안` 저장소의 행」 으로 읽었다. 그래서 임자는
#   **ASCII 소문자 식별자**(새 저장소 이름이 들어올 꼴) 아니면 **아래 적어 둔 한글 이름**
#   하나여야 한다. 둘 다 아니면 **임자가 없는 것**이고 이 저장소의 행으로 센다.
# ★ **그림 쪽 소스도 센다.** 첫 판은 `*.js` 만 봤는데, `f_seshat` 그림이 **닫힌 행
#   여섯을 번호로 그리고 있었다** — **그림은 글과 달리 검사가 글자를 못 읽어서 더 오래
#   산다.** 번호가 사는 자리는 `figures/*.py` 이고, 거기는 읽을 수 있다(DECISIONS §129).
생성기들 = ("part1.js", "part2.js", "part3.js", "build.js", "html.js", "lib.js", "facts.js",
          "figures/charts.py", "figures/diagrams.py", "figures/shots.py", "figures/figlib.py")
남의이름 = frozenset({"파이어레인", "하토르", "세샤트", "베스"})
_PLAN참조 = re.compile(r"(?:([가-힣]+|[a-z][a-z0-9_-]*)\s+)?PLAN\s+(#\d+(?:\s*[·–]\s*#?\d+)*)")
_번호 = re.compile(r"\d+")


def 임자(앞: str | None) -> str | None:
    """`PLAN` 앞의 낱말이 **저장소 이름인가.** 아니면 `None` — 이 저장소의 행이다."""
    if not 앞:
        return None
    if 앞 in 남의이름:
        return 앞
    if re.fullmatch(r"[a-z][a-z0-9_-]*", 앞):   # 새 ASCII 저장소 이름도 걸린다
        return 앞
    return None


def plan_rows(root: Path) -> set[int]:
    """`docs/PLAN.md` §1 표에 **살아 있는** 행 번호."""
    t = (root / "docs/PLAN.md").read_text(encoding="utf-8")
    return {int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", t, re.M)}


def plan_ref_fails(text: str, 산: set[int], 어디: str = "") -> list[str]:
    """빈 리스트가 통과다. 글 하나에서 행 번호 참조를 본다."""
    난것 = []
    머리 = f"{어디}: " if 어디 else ""
    for m in _PLAN참조.finditer(text):
        주인, 번호들 = 임자(m.group(1)), [int(x) for x in _번호.findall(m.group(2))]
        if 주인 and 주인 != "thoth":
            난것.append(f"{머리}`{주인} PLAN {m.group(2)}` — **남의 저장소의 PLAN 행은 적지 않는다.** "
                       f"닫히면 사라지고 이 저장소에 그것을 아는 자가 없다. "
                       f"`{주인} DECISIONS §N` 으로 적거나 할 일을 그대로 쓴다")
            continue
        죽은 = sorted(n for n in 번호들 if n not in 산)
        if 죽은:
            난것.append(f"{머리}`PLAN {m.group(2)}` 중 {죽은} 이 docs/PLAN.md 에 없다 — "
                       f"닫힌 행이면 DECISIONS 절을 가리킨다")
    return 난것


# ★ **「PLAN」 을 안 붙인 맨 `#N` 이 더 많았다.** 첫 판은 `PLAN #N` 만 봤는데, 세어 보니
#   생성기가 `약관 확인(#2)` · `PL + " #19"` · `추출(#6)` 꼴로 **서른 자리**를 더 들고
#   있었고 그중 아홉이 이미 닫힌 행이었다(DECISIONS §129). 문서명 없는 번호는
#   **이 저장소의 규약부터 어긴다** — 참조는 문서명을 앞에 적는다.
# ★ 16진 색(`#1F3864`) · 앵커(`#question-prompt`) · `quota#2026-09` 는 숫자 뒤에 글자가
#   붙거나 네 자리라 안 걸린다. **음성 대조를 카나리아에 둔다** — 전부 우는 규칙은 쓸모가 없다.
_맨번호 = re.compile(r"#(\d{1,3})\b(?![-\w])")
_이어적기 = re.compile(r"PLAN\s*(?:#\d+\s*[·–]\s*)*$")


def bare_ref_fails(text: str, 어디: str = "") -> list[str]:
    """`PLAN` 을 안 붙인 맨 `#N`. 빈 리스트가 통과다."""
    머리 = f"{어디}: " if 어디 else ""
    난것 = []
    for line in text.splitlines():
        for m in _맨번호.finditer(line):
            if _이어적기.search(line[max(0, m.start() - 12):m.start()]):
                continue
            난것.append(f"{머리}`{m.group(0)}` — **문서명 없는 행 번호다.** "
                       f"`<저장소> DECISIONS §N` 으로 적거나 할 일을 그대로 쓴다")
    return 난것


def check_plan_refs(root: Path) -> list[str]:
    산 = plan_rows(root)
    난것 = []
    for rel in 생성기들:
        p = root / "docs/proposal" / rel
        if p.exists():
            글 = p.read_text(encoding="utf-8")
            난것 += plan_ref_fails(글, 산, f"docs/proposal/{rel}")
            난것 += bare_ref_fails(글, f"docs/proposal/{rel}")
    return 난것


def _canary() -> None:
    # ★ 행 번호 참조 — 판별식 넷을 합성으로 물어 둔다. **「통과한다」 도 같이 묻는다**:
    #   전부 우는 규칙은 「운다」 만 보면 초록이다.
    # ★ **보기를 글자로 박지 않고 짜 맞춘다.** 첫 판이 합성 입력을 그냥 적었더니
    #   `check_docs` 의 `check_refs` 가 **그 보기를 진짜 참조로 읽고** 「없는 행을
    #   가리킨다」 로 울었다 — **검사가 보기와 주장을 안 가른다**(DECISIONS §129 가
    #   기획서에서 적은 그 자리가 한 층 아래서 또 났다). 고르는 길이 둘이었다:
    #   `check_refs` 에 「이건 보기다」 표시를 들이거나, 보기를 **런타임에 짜 맞추거나.**
    #   앞엣것은 **검사를 끄는 손잡이**가 되므로 뒤엣것을 골랐다 — 이 파일의 다른
    #   카나리아도 합성 docx 를 **코드로 만든다.** 번호는 세 자리를 넘겨 둔다.
    산것, 죽은행, ㅍ = {9001, 9002}, 9003, "PLAN #%d"
    def 글(앞: str, *ns: int) -> str:
        return (앞 + " " if 앞 else "") + " · ".join(
            (ㅍ % n) if i == 0 else f"#{n}" for i, n in enumerate(ns))
    probes = {
        "남의 PLAN 을 금지한다": plan_ref_fails(글("seshat", 9001), 산것),
        "남의 DECISIONS 는 통과한다": not plan_ref_fails("seshat DECISIONS §9001", set()),
        "한국어 부사를 임자로 읽지 않는다": not plan_ref_fails(글("넉 달 동안", 9001), 산것),
        "죽은 자기 행을 든다": plan_ref_fails(글("", 죽은행), 산것),
        "산 자기 행은 통과한다": not plan_ref_fails(글("thoth", 9001, 9002), 산것),
        "이어 적은 번호도 본다": plan_ref_fails(글("", 9001, 죽은행), 산것),
        "맨 번호를 든다": bare_ref_fails("약관 확인(" + "#%d" % 2 + ")을 앞에 둔다"),
        "이어 적기는 맨 번호가 아니다": not bare_ref_fails(글("thoth", 9001, 9002)),
        "16진 색은 안 든다": not bare_ref_fails('color: "' + "#1F3864" + '"'),
        "앵커는 안 든다": not bare_ref_fails("`" + "#question-prompt" + "`"),
        "네 자리는 안 든다": not bare_ref_fails("quota" + "#2026-09"),
    }
    죽은 = [k for k, ok in probes.items() if not ok]
    if 죽은:
        print(f"    ★ 카나리아가 죽었다 — {죽은}. 행 번호 검사가 아무것도 못 찾는 상태다")
        sys.exit(2)
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


# ── 생성기 지문 ────────────────────────────────────────────────────────────
#
# ★ **docx 를 생성기에 묶는 것이 없었다**(DECISIONS §126). 사슬은
#   `docs/proposal/*.js` → `node build.js` → `docs/proposal.docx` → Pages 인데
#   **가운데 화살표를 사람이 손으로 돌린다.** 위의 검사들은 **손으로 적어 둔 숫자
#   목록**만 대조하므로, 생성기를 고치고 다시 만들지 않으면 **docx 가 몇 달 뒤져도
#   초록**이다. 2026-10-03 에 배포본이 실제로 그렇게 낡아 있었다.
#
# ★ **바이트로 견주지 않는다.** docx 는 zip 이고 타임스탬프와 압축이 판마다 달라
#   같은 입력에서 같은 바이트가 안 나온다. 대신 **입력의 지문**을 산출물 옆에 적고
#   그것이 어긋나면 「다시 만들어야 한다」 로 읽는다 — 봉인과 같은 꼴이다.
#
# ★ **`doctor` 에서는 WARN 이고 배포에서는 실패다**(`--deploy`). 다시 쓰는 중에
#   커밋을 막을 일은 아니지만 **낡은 기획서를 내보내는 것은 막아야 한다.** 등급이
#   다른 두 자리에서 같은 사실을 쓴다.
# ★ **두 번째 렌더러도 생성기다**(DECISIONS §166). `html.js` 가 바뀌면 화면이 바뀌고,
#   `facts.js` 가 바뀌면 **둘 다** 바뀐다 — 자물쇠가 그것을 안 세면 배포본이 조용히 뒤진다.
생성기 = ("build.js", "html.js", "lib.js", "facts.js", "part1.js", "part2.js", "part3.js",
          "figures/figlib.py", "figures/charts.py", "figures/diagrams.py", "figures/shots.py")


def 생성기지문(root: Path) -> dict[str, str]:
    """생성기 파일마다 sha256 앞 16자. 없는 파일은 `없다` 로 적는다 — 빠진 것도 변화다."""
    import hashlib
    것 = {}
    for rel in 생성기:
        p = root / "docs/proposal" / rel
        것[rel] = (hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "없다")
    return 것


def check_build_lock(root: Path) -> list[str]:
    """빈 리스트가 통과다. 자물쇠가 없거나 어긋나면 **다시 만들어야 한다.**

    ★ 자리를 `root` 에서 구한다 — 모듈 상수를 쓰면 **시험이 제 나무를 못 세운다.**
    """
    자물쇠 = root / "docs/proposal/build.lock.json"
    if not 자물쇠.exists():
        return ["docs/proposal/build.lock.json 이 없다 — "
                "docx 가 생성기의 지금 출력인지 아무도 모른다\n"
                "        bash tools/build_proposal.sh   (그림 · docx · 자물쇠 · 대조)"]
    try:
        적힌 = json.loads(자물쇠.read_text(encoding="utf-8")).get("생성기", {})
    except ValueError as e:
        return [f"docs/proposal/build.lock.json 을 읽지 못했다 — {e}"]
    참 = 생성기지문(root)
    다른 = [k for k in 참 if 적힌.get(k) != 참[k]]
    if not 다른:
        return []
    return [f"docx 가 생성기보다 낡았다 — {' · '.join(다른)} 이 바뀌었는데 다시 만들지 않았다\n"
            f"        bash tools/build_proposal.sh"]


def main() -> int:
    """종료 코드 — **0 과 3 을 가른다**(DECISIONS §127).

      0  이상 없음
      1  기획서가 정본과 어긋난다
      2  도구가 죽었다
      3  **지금은 통과, 그러나 배포는 막힌다** — docx 가 생성기보다 낡았다

    ★ **3 을 따로 둔 까닭.** 처음에는 이것을 stdout 의 `WARN` 줄로만 냈는데,
      `doctor` 의 `0) ok` 가지가 출력을 통째로 버려서 **화면에 아예 안 떴다.**
      2026-10-03 에 `doctor` 초록 → 밀기 → **CI 빨강**이 났다. 「이 기계가 초록인
      것과 CI 가 초록인 것은 다른 말이다」(§170)를 **새로 만든 셈**이다.
      상태를 **문자열이 아니라 종료 코드로** 내면 부르는 쪽이 안 버린다.
    """
    _canary()
    배포 = "--deploy" in sys.argv[1:]
    if not DOCX.exists():
        print(f"    {DOCX.relative_to(ROOT)} 가 없다")
        return 1
    # ★ **행 번호 참조는 docx 가 아니라 생성기에서 본다.** 번호가 사는 자리가 거기다 —
    #   docx 를 다시 안 구웠어도 **고쳐야 할 글은 이미 틀려 있다**(DECISIONS §129).
    fails = (check(text_of(DOCX), ROOT) + check_figures(figures_of(DOCX), ROOT)
             + check_plan_refs(ROOT))
    낡음 = check_build_lock(ROOT)
    if 배포:
        fails += 낡음
    # ★ **까닭을 결과보다 먼저 적는다**(DECISIONS §129). 생성기가 docx 보다 새로우면
    #   아래의 `PRESENT` · `RETIRED` 어긋남은 **고칠 결함이 아니라 안 구운 자국**이다.
    #   까닭을 안 적으면 **다시 구우면 끝날 일을 글을 고쳐서 맞추게 된다** — 그러면
    #   생성기와 docx 가 더 벌어진다. 2026-10-03 에 3.0 패치를 받는 자리에서 실제로
    #   그렇게 보였다: 폐기 문장 열이 「남아 있다」 로 뜨는데 **원인은 안 구운 것 하나**다.
    if fails and 낡음:
        print("    ※ 먼저 : docx 가 생성기보다 낡았다 — 아래 어긋남은 대개 그 자국이다")
        print("      bash tools/build_proposal.sh   (굽고 나서 다시 본다)")
    for f in fails:
        print(f"    {f}")
    if fails:
        return 1
    if 낡음:
        for f in 낡음:
            print(f"    {f}")
        print("    이 상태로는 `기획서 배포` 가 멈춘다 — 커밋은 막지 않는다")
        return 3
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
