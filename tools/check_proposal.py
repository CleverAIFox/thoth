r"""**기획서 본문이 제 자리를 지키나** — 틀린 모양이 **존재할 수 없게** 한다(DECISIONS §155).

  python3 tools/check_proposal.py            본다. 위반이면 1, 도구 고장이면 2
  python3 tools/check_proposal.py --list     지금 블록과 수를 찍는다
  python3 tools/check_proposal.py --selftest 판별식이 살아 있나

★ **「틀린 걸 잡는다」 와 「틀린 모양이 존재할 수 없다」 는 다른 말이다.** 본문(`part*.js`)이
  `docx` 를 직접 만질 수 있으면 **렌더러를 하나 더 붙일 수 없다** — 두 번째 렌더러가 그
  줄을 못 읽는다. 셋을 본다.

| | 묻는 것 |
|---|---|
| **문** | `part*.js` 가 `./lib` 말고 다른 것을 부르는가 · 렌더러의 것(`D` · `t` · `W` …)을 가져가는가 |
| **블록** | 가짜 `lib` 으로 끝까지 도는가 · 선언 밖 블록을 쓰는가 · `docx` 를 만지는가 |
| **수** | 산문에 든 **단위를 가진 수**가 장부에 있는가 — **늘면 막는다** |
| **날짜** | `DECISIONS` 의 날짜마다 `charts.py` 의 이름표가 있는가 |

★ **「문」 은 글자가 아니라 `require` 와 구조분해로 본다.** 첫 판은 정규식으로 `\bD\b\.` 를
  찾았는데 **표 칸의 `"D. 호스팅 LLM …"` 이 걸렸다** — 글자로는 뜻이 안 갈린다.

★ **「블록」 은 실행으로 본다.** `docs/proposal/extract.js` 가 `lib` 자리에 **기록만 하는
  가짜**를 끼워 `part*.js` 를 그대로 읽는다. 본문이 `docx` 를 만지면 그 프록시가 **기록을
  남긴다** — 주장이 아니라 실행이 가른다.

★ **「수」 는 장부다.** 지금 든 수를 이름으로 적고 **늘면 막는다.** 갈래(치환 · 밖 · 면제)로
  가르는 것은 **분류기를 만드는 일**이고 그것은 PLAN 이다 — 분류기를 합성 입력에 안 물리고
  세우면 그 비율이 자의 잡음이다(thoth §152 가 네 번 당한 자리).

★ **날짜 이름표는 사람이 기억하는 자리였다**(DECISIONS §158). `charts.py` 는 이름표 없는
  날짜를 만나면 `SystemExit` 으로 죽는데 — **맞는 설계인데 그 죽음이 `build_proposal` 안에서
  난다.** 즉 절을 더한 사람은 **기획서를 다시 구울 때까지 모른다.** 2026-10-05 에 실제로
  그렇게 막혔고, `charts.py` 주석이 「절을 더하는 사람이 여기도 더해야 한다」 고 적어 둔
  자리였다 — **적어 두는 것으로는 안 된다**(§152).

★ **밖 — 뜻은 안 본다.** 산문이 맞는 말인지, 표가 옳은지는 **사람이 읽는다.** 이 자는
  **모양**만 본다.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROP = ROOT / "docs/proposal"
장부파일 = PROP / "numbers.json"

# 본문이 가져가도 되는 것 — **블록과 색뿐이다.** `D` · `t` · `runs` · `W` · `FONT` 는 렌더러의 것이다
허용 = {"P", "GAP", "BR", "PART", "H1", "H2", "H3", "B", "NOTE", "CODE", "TBL", "KV",
       "FIGURE", "COVER", "TOC", "NAVY", "RED", "GRAY", "secs", "ROOT", "RNG"}
본문 = ("part1.js", "part2.js", "part3.js")
_구조분해 = re.compile(r"const\s*\{([^}]*)\}\s*=\s*require\(\"([^\"]+)\"\)")
_require = re.compile(r"require\(\"([^\"]+)\"\)")
산문갈래 = {"P", "NOTE", "B", "H1", "H2", "H3", "PART", "COVER"}
DEC = ROOT / "docs/DECISIONS.md"
CHARTS = ROOT / "docs/proposal/figures/charts.py"
_날짜 = re.compile(r"^\*\*(20\d\d-\d\d-\d\d)\*\*", re.M)
_이름표 = re.compile(r'^\s*"(20\d\d-\d\d-\d\d)":', re.M)
단위 = r"(?:유닛|초|자|항목|개|건|%|MB|ms|배|쪽|줄|점|회|종|구간|시간|분|문항)"
# ★ **소수점 뒤에 공백이 오면 수가 아니다.** 첫 판은 `\d+\.?\d*\s*단위` 로 적었고 목차의
#   「12. 개발 환경」 이 **`12. 개`** 로 잡혔다 — 자를 먼저 의심한다.
수 = re.compile(r"(?:\$\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?" + 단위 + r")")


def 문(root: Path | None = None) -> list[str]:
    """본문이 `./lib` 만 부르고 **블록만** 가져가는가."""
    root = root or ROOT
    난것 = []
    for f in 본문:
        글 = (root / "docs/proposal" / f).read_text(encoding="utf-8")
        for 자리 in set(_require.findall(글)):
            if 자리 != "./lib":
                난것.append(f"{f} 가 `{자리}` 를 부른다 — 본문은 `./lib` 만 부른다")
        for 이름들, 자리 in _구조분해.findall(글):
            if 자리 != "./lib":
                continue
            for n in (x.strip() for x in 이름들.split(",")):
                if n and n not in 허용:
                    난것.append(f"{f} 가 `{n}` 을 가져간다 — 렌더러의 것이다. "
                                f"블록이 모자라면 `lib.js` 에 블록을 연다")
    return 난것


def 날짜흠(dec: str, charts: str) -> list[str]:
    """DECISIONS 의 날짜 중 `charts.py` 이름표가 없는 것. **순수 함수다** — 저장소가
    깨끗해도 가짜 글로 물어 볼 수 있다."""
    적힌 = set(_이름표.findall(charts))
    return [d for d in sorted(set(_날짜.findall(dec))) if d not in 적힌]


def 나무(root: Path | None = None) -> dict:
    """가짜 `lib` 으로 읽은 블록 나무. **도구가 깨지면 2 로 끝낸다.**"""
    root = root or ROOT
    r = subprocess.run(["node", "extract.js"], cwd=root / "docs/proposal",
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    ★ extract.js 가 {r.returncode} 로 죽었다\n{r.stderr[-600:]}", file=sys.stderr)
        raise SystemExit(2)
    return json.loads(r.stdout)


def 블록(t: dict) -> list[str]:
    난것 = [f"본문이 끝까지 안 돈다 — {x}" for x in t["난것"]]
    안다 = set(t["블록이름"])
    for b in t["블록"]:
        if b["종류"] == "DOCX직접":
            난것.append("본문이 `docx` 를 직접 만진다 — 렌더러를 하나 더 붙일 수 없게 된다")
        elif b["종류"] not in 안다:
            난것.append(f"선언 밖 블록 `{b['종류']}` — `lib.js` 가 내보내는 것만 쓴다")
    return 난것


def 수들(t: dict) -> list[str]:
    """산문 블록에 든 **단위를 가진 수**. 자리마다 한 번씩."""
    out = []
    for b in t["블록"]:
        if b["종류"] not in 산문갈래:
            continue
        for 글 in b["글"]:
            out += [m.strip() for m in 수.findall(글)]
    return sorted(set(out))


# ── 두 번째 렌더러(DECISIONS §166) ──────────────────────────────────────────
#
# ★ **§155 는 「본문이 docx 를 안 만진다」 까지였다.** 그것은 `extract.js` 가 **기록만 하는
#   가짜**로 증명한다. 거기서 멈추면 「포맷 중립」 은 **아직 주장**이다 — 블록 어휘로
#   **실제 산출물이 하나 더** 나와야 증명이 끝난다. `html.js` 가 그 둘째다.
# ★ **묻는 것은 「HTML 이 예쁜가」 가 아니라 「두 렌더러가 같은 블록을 받았나」 다.**
#   블록의 **보이는 글**이 HTML 에 전부 있어야 한다 — 하나라도 빠지면 한쪽 산출물이
#   조용히 짧아진 것이다.
# ★ **밖 — 안 보이는 인자는 안 본다.** `FIGURE(name, caption)` 의 `name` 은 파일 이름이고
#   화면에 안 나온다(대체 텍스트로만 간다). **선언으로 뺀다** — 안 적으면 다음 사람이
#   「왜 이것만 빠지나」 를 다시 판다.
# ★ **밖 — 짧은 토막은 안 본다.** 여섯 자 미만은 표의 `-` 나 `○` 같은 기호가 섞여
#   **우연히 들어 있는지**를 가를 수 없다.
안보이는인자 = {("FIGURE", 0)}
# ★ **줄 안 태그는 지우고 덩이 태그는 빈칸으로 바꾼다**(DECISIONS §166). 둘을 같이 다루면
#   `<b>thoth</b>(공개` 가 `thoth (공개` 가 되어 **멀쩡한 산출물이 빨개진다** — 첫 판이
#   그랬고, 빨강 스물이 전부 그 한 줄 탓이었다. **자가 틀렸지 산출물이 아니었다.**
_줄안태그 = re.compile(r"</?(?:b|i|em|strong|code|span)>")
_태그 = re.compile(r"<[^>]+>")
_꾸밈 = re.compile(r"<style>.*?</style>", re.S)
_실린것 = re.compile(r'src="data:[^"]*"')


def html_글(root: Path | None = None) -> str:
    """`html.js` 가 구운 글. **굽는 것이 곧 검사다** — 터지면 2 로 끝난다."""
    root = root or ROOT
    out = root / "docs/proposal/.build/proposal.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["node", "html.js", str(out)], cwd=root / "docs/proposal",
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"    ★ html.js 가 {r.returncode} 로 죽었다\n{r.stderr[-600:]}", file=sys.stderr)
        raise SystemExit(2)
    return out.read_text(encoding="utf-8")


def 납작(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def 보이는글(t: dict) -> list[tuple[str, str]]:
    """(블록 종류, 화면에 나와야 하는 글). `**` 와 백틱은 **표시**라 뺀다."""
    out = []
    for b in t["블록"]:
        for i, 글 in enumerate(b["글"]):
            if (b["종류"], i) in 안보이는인자:
                continue
            조각 = 납작(re.sub(r"[*`]", "", 글))
            if len(조각) >= 6:
                out.append((b["종류"], 조각))
    return out


def 두렌더러(t: dict, html: str) -> list[str]:
    본문 = 납작(unescape(_태그.sub(" ", _줄안태그.sub("", _실린것.sub("", _꾸밈.sub("", html))))))
    난것 = []
    for 종류, 글 in 보이는글(t):
        if 글 not in 본문:
            난것.append(f"`{종류}` 의 글이 HTML 에 없다 — 두 렌더러가 다른 것을 받았다 : {글[:48]}")
    return 난것[:20]


# ── 박은 수와 치환된 수(DECISIONS §167) ─────────────────────────────────────
#
# ★ **기계가 가르는 것과 사람이 가르는 것을 나눈다.** 「소스에 글자 그대로 있나」 는 기계가
#   센다 — 있으면 **박은 수**, 없으면 **산출물에서 읽고 있는 수**다. 실측으로 36 중 **일곱이
#   이미 치환돼 있었고**(`${rows.length}건` 꼴) 장부가 36 을 한 뭉치로 들던 동안 **그 사실이
#   안 보였다.** 두 수가 한 이름으로 불리면 한쪽을 고치고 다른 쪽을 봤다고 생각한다(세샤트 §302).
# ★ **갈래 셋은 사람이 가른다.** `밖`(남의 사실 · 다른 저장소의 실측) · `면제`(방법 · 서술) ·
#   `치환예정`(이 저장소의 산출물에서 읽을 수 있다). **낱말 목록으로 가르면 그 비율이 자의
#   잡음이다** — `PLAN` 이 그렇게 경고했고, 실제로 「`baseline.json` 에 그 글자가 있나」 로
#   재 봤더니 **스무 개가 걸렸고 전부 거짓**이었다(`5` 가 어딘가에 있으면 `5초` 가 걸린다).
# ★ **양방향 톱니다.** 박은 수는 **늘면 막고**, `치환예정` 은 **줄기만 한다** — 치환하지 않고
#   `밖` 으로 옮겨 적으면 그것은 갚은 것이 아니다.
MAX_박은수 = 28
MAX_치환예정 = 5
본문파일 = ("part1.js", "part2.js", "part3.js")


def 본문소스(root: Path | None = None) -> str:
    """`part*.js` 를 글자로 읽는다. **렌더러가 아니라 소스를 본다** — 박았는지가 물음이다.

    ★ **온 줄 주석은 뺀다**(DECISIONS §167). 치환하고 나서 **왜 치환했는지를 주석에 적으면**
      그 주석의 수가 「아직 박혀 있다」 로 세어진다 — 실제로 `35%` 를 치환한 판에서 그랬다.
      주석은 안 그려지므로 산문이 아니다.
    ★ **온 줄만 뺀다.** 줄 끝 주석까지 지우려면 `//` 를 찾아야 하는데 **`https://` 가
      문자열 안에 있다** — 그것을 자르면 **멀쩡한 글이 사라지고 수가 조용히 줄어든다.**
    """
    root = root or ROOT
    글 = []
    for f in 본문파일:
        for 줄 in (root / "docs/proposal" / f).read_text(encoding="utf-8").split("\n"):
            if 줄.lstrip().startswith("//"):
                continue
            글.append(줄)
    return "\n".join(글)


def 박은수(지금: list[str], 소스: str) -> tuple[list[str], list[str]]:
    """(소스에 글자 그대로 있는 수, 없는 수). 뒤엣것은 **이미 산출물에서 읽고 있다.**"""
    return [x for x in 지금 if x in 소스], [x for x in 지금 if x not in 소스]


def 장부(root: Path | None = None) -> set[str]:
    """갈래 전부를 한 집합으로. **옛 부름자리가 그대로 돈다.**"""
    raw = _장부raw(root)
    return {x for k, v in raw.items() if not k.startswith("_") for x in v}


def _장부raw(root: Path | None = None) -> dict:
    p = (root or ROOT) / "docs/proposal/numbers.json"
    return json.loads(p.read_text(encoding="utf-8"))


def 갈래흠(박은것: list[str], raw: dict) -> list[str]:
    """박은 수마다 갈래가 **꼭 하나**인가. 그리고 갈래에 **없는 수**가 적혀 있지 않은가."""
    갈래들 = {k: set(v) for k, v in raw.items() if not k.startswith("_")}
    난것 = []
    for x in 박은것:
        든곳 = [k for k, v in 갈래들.items() if x in v]
        if not 든곳:
            난것.append(f"박은 수 `{x}` 에 갈래가 없다 — `밖` · `면제` · `치환예정` 중 하나에 적는다")
        elif len(든곳) > 1:
            난것.append(f"박은 수 `{x}` 가 갈래 둘에 있다({' · '.join(든곳)}) — 하나만 고른다")
    박은집합 = set(박은것)
    for k, v in sorted(갈래들.items()):
        for x in sorted(v - 박은집합):
            난것.append(f"`{k}` 의 `{x}` 는 **이제 산문에 없거나 치환됐다** — 장부에서 지운다")
    return 난것


def 견준다(지금: list[str], 적힌: set[str]) -> tuple[list[str], list[str]]:
    """(장부에 없는 것, 장부에 있는데 이제 안 쓰는 것). **둘 다 낸다** — 늘면 막고 줄면 알린다."""
    return [x for x in 지금 if x not in 적힌], [x for x in sorted(적힌) if x not in set(지금)]


def _canary() -> None:
    """★ **판별식이 사나.** 0건이 목표인 검사는 **깨끗해서 0 인지 죽어서 0 인지** 못 가른다."""
    t = {"블록이름": ["P"], "블록": [{"종류": "DOCX직접", "글": []}], "난것": []}
    if not 블록(t):
        print("    ★ 카나리아가 죽었다 — `docx` 직접 사용을 안 잡는다"); sys.exit(2)
    if not 블록({"블록이름": ["P"], "블록": [{"종류": "몰라", "글": []}], "난것": []}):
        print("    ★ 카나리아가 죽었다 — 선언 밖 블록을 안 잡는다"); sys.exit(2)
    t2 = {"블록": [{"종류": "P", "글": ["45유닛 과 $0.59 · 12. 개발 환경"]},
                  {"종류": "TBL", "글": ["99건"]}]}
    if 수들(t2) != ["$0.59", "45유닛"]:
        print(f"    ★ 카나리아가 죽었다 — 수를 못 읽는다 : {수들(t2)}"); sys.exit(2)
    if 견준다(["a"], {"b"}) != (["a"], ["b"]):
        print("    ★ 카나리아가 죽었다 — 장부를 못 견준다"); sys.exit(2)
    if 날짜흠("**2026-01-02**\n", '    "2026-01-03": "ㄱ",\n') != ["2026-01-02"]:
        print("    ★ 카나리아가 죽었다 — 빠진 날짜를 못 찾는다"); sys.exit(2)
    if 날짜흠("**2026-01-02**\n", '    "2026-01-02": "ㄱ",\n'):
        print("    ★ 카나리아가 죽었다 — 있는 이름표를 없다고 한다"); sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    a = argv if argv is not None else sys.argv[1:]
    _canary()
    if "--selftest" in a:
        print("  프로브 살아 있다 — docx 직접 · 선언 밖 블록 · 수 읽기 · 장부 견주기")
        return 0
    t = 나무()
    지금 = 수들(t)
    if "--list" in a:
        import collections
        c = collections.Counter(b["종류"] for b in t["블록"])
        print(f"  블록 {len(t['블록'])} — " + " · ".join(f"{k} {v}" for k, v in sorted(c.items())))
        박, 치환됨 = 박은수(지금, 본문소스())
        raw = _장부raw()
        print(f"  산문 속 단위를 든 수 {len(지금)} — 박은 것 {len(박)} · 산출물에서 읽는 것 {len(치환됨)}")
        for k in ("밖", "면제", "치환예정"):
            print(f"    {k} {len(raw.get(k, []))} : " + " · ".join(sorted(raw.get(k, []))))
        print(f"  이름표 없는 날짜 {len(날짜흠(DEC.read_text(encoding='utf-8'), CHARTS.read_text(encoding='utf-8')))}")
        for x in 지금:
            print(f"    {x}")
        return 0
    난것 = 문() + 블록(t) + 두렌더러(t, html_글())
    빠진 = 날짜흠(DEC.read_text(encoding="utf-8"), CHARTS.read_text(encoding="utf-8"))
    난것 += [f"DECISIONS 의 {d} 에 `charts.py` 이름표가 없다 — `LABEL` 에 더한다" for d in 빠진]
    raw = _장부raw()
    박, 치환됨 = 박은수(지금, 본문소스())
    난것 += 갈래흠(박, raw)
    # ★ **양방향 톱니**(DECISIONS §167). 박은 수는 늘면 막고, `치환예정` 은 줄기만 한다 —
    #   치환하지 않고 `밖` 으로 옮겨 적으면 그것은 **갚은 것이 아니다.**
    if len(박) > MAX_박은수:
        난것.append(f"박은 수가 {len(박)} 으로 바닥 {MAX_박은수} 를 넘었다 — "
                    f"산출물에서 읽게 고치거나 `MAX_박은수` 를 올린 까닭을 DECISIONS 에 적는다")
    예정 = len(raw.get("치환예정", []))
    if 예정 > MAX_치환예정:
        난것.append(f"`치환예정` 이 {예정} 으로 천장 {MAX_치환예정} 을 넘었다 — **빚은 늘지 않는다**")
    if len(박) < MAX_박은수 or 예정 < MAX_치환예정:
        print(f"  ※ 좋아졌다 — `MAX_박은수` 를 {len(박)} 으로, `MAX_치환예정` 을 {예정} 으로 내린다")
    print(f"  블록 {len(t['블록'])} · 산문 속 수 {len(지금)} "
          f"(박은 것 {len(박)} · 산출물에서 읽는 것 {len(치환됨)}) · 렌더러 2")
    for x in 난것:
        print(f"    {x}")
    return 1 if 난것 else 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다 — 같은 코드면 **도구가 깨진 것을
    #   검사가 실패한 것으로 읽는다**(DECISIONS §153 과 같은 자리).
    sys.exit(main())
