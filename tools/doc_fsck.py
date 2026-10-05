"""문서가 가리키는 것이 실물로 있는가(DECISIONS §111).

  python3 tools/doc_fsck.py          검사한다. 위반이면 1, 도구 고장이면 2

★ `check_docs` 는 **문서 ↔ 문서**를 본다(참조가 실재하는 절을 가리키는가). 이 도구는
  **문서 ↔ 실물**을 본다. 하토르 `doc_fsck.py` 머리말의 말이 그대로 맞다 — "읽으면
  보이는데 아무도 안 읽었다."

| 검사 | 무엇 |
|---|---|
| 경로 | README · MASTER · PLAN 과 강제자 줄이 적은 `tools/x.py` · `worker/...` 가 실재하는가 |
| 테스트 | `파일::test_이름` 의 테스트가 그 파일에 실재하는가 |
| 인용 | 강제자 줄이 든 시험 이름 · 관문 레이블이 **그 줄이 적은 파일 안에** 실재하는가 |
| 죽은 도구 | `tools/` 의 스크립트가 README · MASTER · 다른 도구 · 워크플로 어딘가에서 불리는가 |

★ **DECISIONS 본문의 옛 경로는 안 본다.** 그때를 적는 문서다. 다만 `강제자` 줄은
  전수로 본다 — "이 검사가 지킨다" 는 **지금의 주장**이고, 그 검사가 없으면 주장이
  거짓이다.

★ **인용 검사가 왜 생겼나**(DECISIONS §159). §1~§89 에 강제자를 소급할 때 89줄을 쓰고
  **22줄이 틀렸다** — 시험 이름은 실재하는데 **다른 파일에 있었다**. `test_지금_저장소가_
  조용하다` 는 일곱 파일에 있고 그중 내가 적은 파일에는 없었다. 경로만 보는 종전 검사는
  **일곱 다 통과시킨다.** 「틀린 강제자는 없는 것보다 나쁘다」 를 적어 두고도 막는 자를
  안 붙여 두었던 자리다.
★ **그래서 「그 파일 안에」 가 핵심이다.** 저장소 어딘가에 있으면 통과시키면 22건 중
  **한 건도 안 잡힌다** — 전부 저장소 안에는 있었다.
★ **인용 뒤에 파일이 와도 받는다.** `` `check_refs` 는 … `tools/check_docs.py` 머리말이 ``
  처럼 순서가 뒤인 줄이 있다. 줄 단위로 모아 보므로 순서를 안 본다.

★ **낱말이 **무슨 뜻으로** 쓰였는지는 안 본다.** `` `위생` `` 이 `doctor.sh` 에 있으면
  통과하고, 그것이 절이 말하는 그 절인지는 사람이 본다.
★ **파일을 하나도 안 적은 강제자 줄의 인용은 안 본다.** 맞댈 자리가 없다 —
  `강제자 없음` 줄이 도구 이름만 흘리듯 드는 경우다.
★ **자연어 모순은 안 본다.** 구조만 대조한다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE_DOCS = ["README.md", "docs/MASTER.md", "docs/PLAN.md"]
TOP = ("tools", "worker", "extension", "infra", "docs", ".github")
# `tools/x.py` · `worker/tests/test_a.py::test_b` — 백틱 안만 본다. 글롭 · 자리표시자는 뺀다.
PATH = re.compile(r"`((?:%s)/[^`\s*<>{}$]+?)(?:::([\w가-힣]+))?`" % "|".join(re.escape(t) for t in TOP))
# ★ **`강제자 없음` 줄도 본다.** 거기도 「`check_refs` 는 번호만 본다」 처럼 **지금의 주장**을
#   들고, 그 이름이 사라지면 까닭이 거짓이 된다.
# ★ **이어진 줄까지 한 덩어리로 본다.** §158 의 강제자는 세 줄에 걸쳐 있고 시험 이름이
#   **둘째 줄에 있다** — 한 줄만 보면 그 인용이 영영 검사 밖이다. 빈 줄에서 끊는다.
ENFORCER_LINE = re.compile(r"^강제자(?: 없음)? — .*(?:\n(?!\s*$).*)*", re.M)
# ★ **전수다.** 2026-10-05 에 §1~§89 를 채워 바닥이 1 이 되었다(DECISIONS §159).
ENFORCER_FROM = 1
# 백틱 토막. 파일 후보 · 시험 이름 · 관문 레이블을 한 줄에서 함께 꺼낸다.
BACKTICK = re.compile(r"`([^`\n]+)`")
# `test_…`(pytest) 는 그 파일에 `def` 가 있어야 한다.
TESTNAME = re.compile(r"^test_[\w가-힣]+$")
# ★ **파일 후보를 `TOP/` 로 좁히지 않는다.** §124 가 `` `.env.example` 의 `OLLAMA_KEEP_ALSO` ``
#   를 들고 있는데 `PATH` 는 `.env.example` 을 못 봐서, 레이블이 **같은 줄의 엉뚱한 파일**과
#   맞대져 거짓 빨강이 났다. **거짓 빨강이 쌓이면 사람이 검사를 끈다**(§158).
#   후보로 모으고 **실재하는 것만** 건초로 쓴다 — 실재 판정은 `is_file` 이 하고 규칙이 아니다.
FILEISH = re.compile(r"^[\w./-]+\.[A-Za-z0-9]+$")
# 관문 레이블. 한글이 들었거나 맨 식별자인 것만 본다 — `output -raw` · `>&2` 처럼
# 공백이나 기호가 섞인 영문은 **무엇에 대조할지 정해지지 않아** 보지 않는다.
LABELISH = re.compile(r"[가-힣]|^[A-Za-z_][A-Za-z0-9_]*$")

# ★ **죽은 도구 예외는 사유를 적는다.** 사유 없는 예외는 "옮길 수 있는데 안 옮긴 것" 과
#   구별되지 않는다(파이어레인 DECISIONS §191).
# ★ **글로 읽지 않는 산출물**(§161). 강제자가 들 수 있고, 들어도 그 안을 못 맞댄다.
글자아님 = {".docx", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".xlsx", ".pptx", ".ico"}

TOOL_EXEMPT: dict[str, str] = {
    "__init__.py": "패키지 표식",
}


def _ignored(root: Path, path: str) -> bool:
    """git 이 무시하는 경로는 **기계마다 있는 파일**이다(`infra/backend.hcl` · `.terraform`).
    저장소에 없는 것이 정상이므로 실재를 요구하지 않는다."""
    import subprocess
    try:
        # 없는 디렉터리는 `dir/` 꼴 규칙에 안 걸린다. 끝에 `/` 를 붙여 한 번 더 묻는다.
        return any(subprocess.run(["git", "-C", str(root), "check-ignore", "-q", q],
                                  capture_output=True).returncode == 0
                   for q in (path, path.rstrip("/") + "/"))
    except OSError:
        return False


def _paths(text: str) -> list[tuple[str, str | None]]:
    return [(m.group(1).rstrip(".,)"), m.group(2)) for m in PATH.finditer(text)]


def _has_test(path: Path, name: str) -> bool:
    try:
        src = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return bool(re.search(rf"^\s*(?:async\s+)?def {re.escape(name)}\(", src, re.M)
                or re.search(rf"""test\(\s*["']{re.escape(name)}""", src))


def check_paths(root: Path, fails: list) -> None:
    sources: list[tuple[str, str]] = []
    for rel in LIVE_DOCS:
        p = root / rel
        if p.exists():
            sources.append((rel, p.read_text(encoding="utf-8")))
    dec = root / "docs/DECISIONS.md"
    if dec.exists():
        for b in re.split(r"^## §", dec.read_text(encoding="utf-8"), flags=re.M)[1:]:
            num = b.split(".")[0].strip()
            if num.isdigit() and int(num) >= ENFORCER_FROM:
                lines = "\n".join(m.group(0) for m in ENFORCER_LINE.finditer(b))
                sources.append((f"DECISIONS §{num} 강제자", lines))
    for where, text in sources:
        for path, test in _paths(text):
            p = root / path
            if not p.exists():
                if _ignored(root, path):
                    continue
                fails.append(f"{where} 가 없는 {path} 를 가리킨다")
            elif test and not _has_test(p, test):
                fails.append(f"{where} 가 없는 테스트 {path}::{test} 를 가리킨다")


def 인용(줄: str) -> tuple[list[str], list[str], list[str]]:
    """강제자 줄 하나를 (파일후보, 시험이름, 레이블) 셋으로 가른다.

    ★ **순서를 안 본다.** 줄 전체에서 파일을 먼저 모으고 나머지를 맞댄다 — `` `check_refs`
      는 … `tools/check_docs.py` 머리말이 적는다 `` 처럼 인용이 파일보다 앞서는 줄이 있다.
    """
    파일: list[str] = []
    시험: list[str] = []
    레이블: list[str] = []
    for t in BACKTICK.findall(줄):
        t = t.split("::")[0]
        if FILEISH.match(t):
            파일.append(t.rstrip(".,)"))
        elif TESTNAME.match(t):
            시험.append(t)
        elif LABELISH.search(t):
            레이블.append(t)
    return 파일, 시험, 레이블


def check_enforcer_quotes(root: Path, fails: list) -> None:
    """강제자 줄이 든 시험 이름 · 레이블이 **그 줄이 적은 파일 안에** 있는가."""
    dec = root / "docs/DECISIONS.md"
    if not dec.exists():
        return
    for b in re.split(r"^## §", dec.read_text(encoding="utf-8"), flags=re.M)[1:]:
        num = b.split(".")[0].strip()
        if not (num.isdigit() and int(num) >= ENFORCER_FROM):
            continue
        for m in ENFORCER_LINE.finditer(b):
            파일, 시험, 레이블 = 인용(m.group(0))
            본문 = {}
            못잼 = False
            for f in 파일:
                p = root / f
                if not p.is_file():
                    # ★ **git 이 무시하는 자리는 「없다」 가 아니라 「못 잰다」 다**(§161).
                    #   `data/domain/*.jsonl` 처럼 **만들어 쓰는 것**은 사본에 없는 것이
                    #   정상이고, 인용한 낱말이 **그 안에 살 수도 있다.** 그 줄의 인용은
                    #   맞댈 자리를 잃었으므로 **안 본다** — 없다고 단정하면 거짓 빨강이다.
                    if _ignored(root, f):
                        못잼 = True
                    continue
                if p.suffix.lower() in 글자아님:
                    # ★ **글이 아닌 산출물은 선언으로 못 잼이다**(§161). `docs/proposal.docx` 는
                    #   §129 가 드는 **제품**이고 글로 읽을 수 없다. 예외로 처리하면 매 판
                    #   소음이 한 줄 나고, 소음은 읽히지 않는다.
                    못잼 = True
                    continue
                try:
                    본문[f] = p.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as e:
                    # ★ **삼키지 않는다**(seshat DECISIONS §255). 선언 밖에서 못 읽은 것은
                    #   **뜻밖**이고, 뜻밖은 자국을 남긴다 — 조용히 넘어가면 통과로 읽힌다.
                    print(f"    DECISIONS §{num} 강제자 가 든 {f} 를 못 읽었다 ({e.__class__.__name__})")
                    못잼 = True
                    continue
            if not 본문 or 못잼:
                continue
            for name in 시험:
                if not any(_has_test(root / f, name) for f in 본문):
                    fails.append(f"DECISIONS §{num} 강제자 가 든 시험 {name} 이 "
                                 f"{' · '.join(본문)} 에 없다")
            for lab in 레이블:
                if not any(lab in src for src in 본문.values()):
                    fails.append(f"DECISIONS §{num} 강제자 가 든 '{lab}' 이 "
                                 f"{' · '.join(본문)} 에 없다")


def check_tools(root: Path, fails: list) -> None:
    tools = sorted(p for p in (root / "tools").glob("*") if p.suffix in {".py", ".sh", ".mjs"})
    corpus = []
    for rel in ("README.md", "docs/MASTER.md"):
        if (root / rel).exists():
            corpus.append((rel, (root / rel).read_text(encoding="utf-8")))
    for p in tools + sorted((root / ".github/workflows").glob("*.yml")):
        corpus.append((str(p.relative_to(root)), p.read_text(encoding="utf-8")))
    for t in tools:
        if t.name in TOOL_EXEMPT:
            continue
        me = str(t.relative_to(root))
        if not any(t.name in text for rel, text in corpus if rel != me):
            fails.append(f"tools/{t.name} 가 어디서도 불리지 않는다 — README 에 적거나 지운다")
    for name, why in TOOL_EXEMPT.items():
        if not why.strip():
            fails.append(f"TOOL_EXEMPT {name} 에 사유가 없다")


def _canary() -> None:
    a, b = TOP[0], TOP[1]
    got = _paths(f"`{a}/a.py` · `{b}/tests/t.py::test_b` · `{a}/*.py` · `{a}/<이름>.sh` · `x/y.py`")
    if got != [(f"{a}/a.py", None), (f"{b}/tests/t.py", "test_b")]:
        print(f"    ★ 카나리아가 죽었다 — PATH 가 {got} 를 찾았다")
        sys.exit(2)
    꺼낸 = 인용(f"강제자 — `{a}/x.py::test_나` 의 `test_가` · `레이블 하나` · `output -raw` · `.env.example`")
    if 꺼낸 != ([f"{a}/x.py", ".env.example"], ["test_가"], ["레이블 하나"]):
        print(f"    ★ 카나리아가 죽었다 — 인용이 {꺼낸} 를 찾았다")
        sys.exit(2)


def main() -> int:
    _canary()
    fails: list[str] = []
    check_paths(ROOT, fails)
    check_enforcer_quotes(ROOT, fails)
    check_tools(ROOT, fails)
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
