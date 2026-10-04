r"""**받았는데 안 붙은 패치가 있나**(DECISIONS §156).

  python3 tools/patch_state.py            미적용이 있으면 1
  python3 tools/patch_state.py --list     수신함의 패치와 상태를 전부 찍는다
  python3 tools/patch_state.py --selftest 판별식이 살아 있나

★ **2026-10-04 에 이것 때문에 거짓 제목이 밀렸다.** `apply_patch` 가 바탕 불일치로
  **막았는데** 뒤 명령들이 그 거절을 안 읽고 그대로 돌아, `ship` 이 **기획서 재빌드만 든
  커밋**에 `thoth-155: …` 라는 제목을 달아 밀었다. 저장소는 멀쩡했으므로 `doctor` 는
  초록이었다 — **「저장소가 맞나」 와 「하려던 일이 됐나」 는 다른 물음이다.**

★ **영수증은 붙은 것만 적는다.** `apply_patch` 는 성공한 뒤에 한 줄을 남기므로, 거기에
  **없는 것**이 곧 「안 붙었다」 는 뜻이 아니다 — 영수증이 생기기 전에 붙은 옛 패치도 없다.
  그래서 둘을 함께 본다 : **해시가 영수증에 있나** · **역적용이 되나**(이미 나무에 있나).

★ **밖 — 수신함 밖의 패치는 안 본다.** 절대경로로 받은 것은 여기 안 걸린다.
★ **밖 — 「붙었어야 하나」 는 안 묻는다.** 수신함에 남은 남의 저장소 패치나 옛 판은
  역적용으로 걸러지지 않으면 미적용으로 뜬다 — **그 수를 0 으로 만드는 일은 사람이 한다**
  (붙이거나 치운다). 그것이 이 자의 목적이다.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECEIPT = ROOT / ".cache/applied-patches.tsv"
무늬 = re.compile(r"^thoth-.*\.patch$")


def 씻은_해시(p: Path) -> str:
    """★ **줄끝을 벗기고 잡는다.** 브라우저를 거친 사본은 CRLF 가 되고, `apply_patch` 도
    같은 정규화를 한 뒤 영수증을 쓴다 — 두 곳이 다르게 씻으면 같은 패치가 달라 보인다."""
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def 영수증(path: Path | None = None) -> set[str]:
    p = path or RECEIPT
    if not p.exists():
        return set()
    return {x.split("\t")[0] for x in p.read_text(encoding="utf-8").splitlines() if x.strip()}


def 나무에_있나(p: Path, root: Path | None = None) -> bool:
    """역적용이 되면 그 내용은 이미 나무에 있다."""
    r = subprocess.run(["git", "apply", "--check", "-R", "-p1", str(p)],
                       cwd=root or ROOT, capture_output=True)
    return r.returncode == 0


def 미적용(수신함: Path, 적힌: set[str] | None = None,
          있나=나무에_있나) -> list[str]:
    """수신함의 패치 중 **영수증에도 없고 나무에도 없는 것**. 이름만 낸다."""
    적힌 = 영수증() if 적힌 is None else 적힌
    if not 수신함.is_dir():
        return []
    out = []
    for p in sorted(수신함.iterdir()):
        if not 무늬.match(p.name):
            continue
        if 씻은_해시(p) in 적힌 or 있나(p):
            continue
        out.append(p.name)
    return out


def _canary() -> None:
    """★ **0건이 목표인 검사는 깨끗해서 0 인지 죽어서 0 인지 못 가른다.**"""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "thoth-1.patch").write_text("x\n", encoding="utf-8")
        (d / "그밖.txt").write_text("x\n", encoding="utf-8")
        if 미적용(d, set(), 있나=lambda p, root=None: False) != ["thoth-1.patch"]:
            print("    ★ 카나리아가 죽었다 — 미적용을 못 찾는다"); sys.exit(2)
        if 미적용(d, {씻은_해시(d / "thoth-1.patch")}, 있나=lambda p, root=None: False):
            print("    ★ 카나리아가 죽었다 — 영수증을 안 본다"); sys.exit(2)
        if 미적용(d, set(), 있나=lambda p, root=None: True):
            print("    ★ 카나리아가 죽었다 — 나무를 안 본다"); sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    a = argv if argv is not None else sys.argv[1:]
    _canary()
    if "--selftest" in a:
        print("  프로브 살아 있다 — 미적용 찾기 · 영수증 · 나무 · 수신함 밖 거르기")
        return 0
    수신함 = os.environ.get("WIN_DOWNLOADS", "")
    if not 수신함:
        print("    .env 에 WIN_DOWNLOADS 가 없다 — 수신함을 못 본다")
        return 3
    난것 = 미적용(Path(수신함))
    if "--list" in a:
        적힌 = 영수증()
        for p in sorted(Path(수신함).iterdir()):
            if 무늬.match(p.name):
                상태 = ("영수증" if 씻은_해시(p) in 적힌
                        else "나무" if 나무에_있나(p) else "**미적용**")
                print(f"    {상태:<10} {p.name}")
        return 0
    for x in 난것:
        print(f"    받았는데 안 붙었다 : {x}")
    if 난것:
        print("    붙이거나 치운다 : bash tools/apply_patch.sh <이름>")
    return 1 if 난것 else 0


if __name__ == "__main__":
    # ★ 위반(1) · 도구 고장(2) · 못 잼(3) 을 다른 코드로 끝낸다(DECISIONS §153).
    sys.exit(main())
