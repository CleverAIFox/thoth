"""문서가 가리키는 것이 실물로 있는가(DECISIONS §111).

  python3 tools/doc_fsck.py          검사한다. 위반이면 1, 도구 고장이면 2

★ `check_docs` 는 **문서 ↔ 문서**를 본다(참조가 실재하는 절을 가리키는가). 이 도구는
  **문서 ↔ 실물**을 본다. 하토르 `doc_fsck.py` 머리말의 말이 그대로 맞다 — "읽으면
  보이는데 아무도 안 읽었다."

| 검사 | 무엇 |
|---|---|
| 경로 | README · MASTER · PLAN 과 강제자 줄이 적은 `tools/x.py` · `worker/...` 가 실재하는가 |
| 테스트 | `파일::test_이름` 의 테스트가 그 파일에 실재하는가 |
| 죽은 도구 | `tools/` 의 스크립트가 README · MASTER · 다른 도구 · 워크플로 어딘가에서 불리는가 |

★ **DECISIONS 본문의 옛 경로는 안 본다.** 그때를 적는 문서다. 다만 §108 부터의
  `강제자` 줄은 본다 — "이 검사가 지킨다" 는 **지금의 주장**이고, 그 검사가 없으면
  주장이 거짓이다.

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
ENFORCER_LINE = re.compile(r"^강제자 — (.+)$", re.M)
ENFORCER_FROM = 108

# ★ **죽은 도구 예외는 사유를 적는다.** 사유 없는 예외는 "옮길 수 있는데 안 옮긴 것" 과
#   구별되지 않는다(파이어레인 DECISIONS §191).
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
    got = _paths("`tools/a.py` · `worker/tests/t.py::test_b` · `tools/*.py` · `tools/<이름>.sh` · `x/y.py`")
    if got != [("tools/a.py", None), ("worker/tests/t.py", "test_b")]:
        print(f"    ★ 카나리아가 죽었다 — PATH 가 {got} 를 찾았다")
        sys.exit(2)


def main() -> int:
    _canary()
    fails: list[str] = []
    check_paths(ROOT, fails)
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
