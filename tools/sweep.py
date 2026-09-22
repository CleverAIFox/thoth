"""저장소 밖에 남은 thoth 의 흔적을 센다.

  python3 tools/sweep.py          센다. 지우지 않는다
  python3 tools/sweep.py --fix    근거가 확실한 것만 지운다

★ **thoth 가 싼 것만 친다.** 실측(2026-09-13)에서 기계에 쌓인 10GB 중 thoth
  몫은 400KB 였다. `~/.cache/uv` 5.5G 는 계정 하나에 하나이고 다른 저장소가
  같이 쓰므로 이 저장소가 손댈 자리가 아니다. `~/.ollama/models` 4.5G 는
  자산이고 `doctor` 가 따로 본다(DECISIONS §42).

★ **층을 나누지 않는다.** 나눌 만큼 크지 않다. 400KB 를 치우려고 도구 셋과
  입구 하나를 두면 도구가 대상보다 비싸다.

★ **경로를 박지 않는다.** `.env` 의 `WIN_DOWNLOADS` 를 쓴다.

★ **근거 없이 지우지 않는다.** 패치는 영수증과 역적용으로, 로그는 그것을 쓰는
  프로세스가 떠 있는지로 판정한다. 판정할 수 없는 것은 나열만 한다.

★ **역적용 실패는 "적용 안 됐다" 의 증거가 아니다.** 붙은 뒤에 그 파일을 다음
  패치가 또 고치면 정방향도 역방향도 안 붙는다. 판정을 참·거짓 둘로 두면 그
  경우가 "아직 아니다" 로 떨어져 거짓말이 된다 — 셋으로 가른다(DECISIONS §61).

★ 닿지 못한 자리는 **0건이 아니라 못 잼**이다. 못 잰 것과 깨끗한 것은 다르다.
"""
import argparse
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_env() -> None:
    """`.env` 를 읽되 이미 환경에 있는 키는 덮지 않는다.

    ★ 직접 부를 때 수신함을 못 쟀다. `doctor` 와 `apply_patch` 는 셸 로더를
      거치는데 이 도구는 스스로 읽지 않아, `python3 tools/sweep.py` 만 치면
      `WIN_DOWNLOADS` 가 비어 `못 잼` 이 나왔다. **도구가 자기 입력을 스스로
      챙기지 않으면 부르는 방법마다 결과가 달라진다**(DECISIONS §43).

    ★ 우선순위는 `tools/lib/env.sh` 와 같다 — 셸에 앞세운 지정이 이긴다
      (DECISIONS §40). 두 로더가 다르게 굴면 그것이 또 하나의 갈림이다.
    """
    f = ROOT / ".env"
    if not f.exists():
        return
    try:
        lines = f.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", k) or k in os.environ:
            continue
        os.environ[k] = v.strip().strip('"').strip("'")


load_env()
TMP = pathlib.Path(os.environ.get("TMPDIR", "/tmp"))

# thoth 의 도구와 문서가 이 이름으로 쓴다. 이름이 근거다.
TMP_NAMES = ["w.log", "fx.log", "worker.log", "ollama.log", "thoth-patch.err", "scan.txt"]
TMP_GLOBS = ["thoth-*", "warm-*unit*.json", "base-*unit*.json", "smoke.*"]

# 이 프로세스가 떠 있으면 그것이 쓰는 로그는 남긴다.
LIVE = {"ollama.log": "ollama", "w.log": "uvicorn",
        "worker.log": "uvicorn", "fx.log": "http.server"}


def running(pattern: str) -> bool:
    return subprocess.run(["pgrep", "-f", pattern], capture_output=True).returncode == 0


RECEIPT = ROOT / ".cache" / "applied-patches.tsv"


def receipts() -> set[str]:
    """`apply_patch.sh` 가 적어 둔 해시. **관측이지 추론이 아니다.**

    ★ 기계 상태이므로 다른 기계에는 없다. 없으면 아래의 추론으로 내려간다 —
      영수증은 추론을 대신하는 것이 아니라 앞에 서는 것이다.
    """
    try:
        lines = RECEIPT.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    return {line.split("\t", 1)[0] for line in lines if line.strip()}


def _applies(body: bytes, reverse: bool) -> bool:
    cmd = ["git", "apply", "--check", "-p1"] + (["-R"] if reverse else []) + ["-"]
    r = subprocess.run(cmd, cwd=ROOT, input=body, capture_output=True, timeout=30)
    return r.returncode == 0


def judge(patch: pathlib.Path, seen: set[str]) -> tuple[bool, str]:
    """(지워도 되는가, 사유). **셋으로 가른다**(DECISIONS §61).

    | 근거 | 판정 |
    |---|---|
    | 영수증에 있다 | 적용됨 |
    | 역적용이 붙는다 | 적용됨 (§29 의 기법) |
    | 정방향이 붙는다 | 아직 아니다 |
    | 셋 다 아니다 | 판정 불가 |

    ★ 마지막 줄이 이 함수가 생긴 이유다. 전에는 그것이 "아직 아니다" 로
      떨어져, 이미 붙은 패치를 수신함에 영원히 남기고 다시 붙이게 했다.
    """
    try:
        body = patch.read_bytes().replace(b"\r\n", b"\n")
    except OSError:
        return False, "읽지 못했다"
    import hashlib
    if hashlib.sha256(body).hexdigest() in seen:
        return True, "적용됨"
    if _applies(body, reverse=True):
        return True, "적용됨"
    if _applies(body, reverse=False):
        return False, "아직 아니다"
    return False, "판정 불가"


def scan_tmp():
    """(지워도 되는가, 사유, 경로)"""
    seen, out = set(), []
    cand = [TMP / n for n in TMP_NAMES]
    for g in TMP_GLOBS:
        cand += sorted(TMP.glob(g))
    for p in cand:
        if p in seen or not p.is_file():
            continue
        seen.add(p)
        proc = LIVE.get(p.name)
        if proc and running(proc):
            out.append((False, f"{proc} 가 쓰는 중", p))
        else:
            out.append((True, "흔적", p))
    return out


def scan_lake():
    raw = os.environ.get("WIN_DOWNLOADS", "")
    if not raw:
        raise LookupError("WIN_DOWNLOADS 가 환경에 없다")
    d = pathlib.Path(raw)
    if not d.is_dir():
        raise LookupError(f"{d} 에 닿지 못한다")

    out = []
    seen = receipts()
    for p in sorted(d.glob("thoth-*")):
        if not p.is_file():
            continue
        if p.suffix == ".patch":
            ok, why = judge(p, seen)
            out.append((ok, why, p))
        else:
            # ★ zip 같은 것은 적용 개념이 없어 판정할 수 없다. 나열만 한다 —
            #   지울 만해 보이는 것과 지워도 되는 것은 다르다.
            out.append((False, "판정 불가", p))
    return out


def lock_packages(lock: pathlib.Path) -> set[str]:
    """uv.lock 에 잠긴 패키지 이름. 파싱이 아니라 발췌다 — `name = "x"` 줄만 본다."""
    try:
        text = lock.read_text(encoding="utf-8")
    except OSError:
        return set()
    return {m.group(1).lower()
            for m in re.finditer(r'^name = "([^"]+)"', text, re.M)}


def cache_dir() -> pathlib.Path:
    """uv 캐시 자리. `UV_CACHE_DIR` 가 있으면 그것, 없으면 `uv cache dir`."""
    if os.environ.get("UV_CACHE_DIR"):
        return pathlib.Path(os.environ["UV_CACHE_DIR"])
    try:
        r = subprocess.run(["uv", "cache", "dir"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise LookupError(f"uv 캐시 자리를 묻지 못했다 ({e})")
    if r.returncode != 0 or not r.stdout.strip():
        raise LookupError("uv cache dir 이 답하지 않았다")
    return pathlib.Path(r.stdout.strip())


def in_cache(name: str, root: pathlib.Path) -> bool:
    """캐시에 그 패키지의 항목이 실제로 있는가.

    ★ **lock 에 있다고 캐시에 있는 것이 아니다**(DECISIONS §118). 한 번 지우면 다시 받기 전까지
      없는데, 차집합만 보면 매번 "thoth 만 쓰는 것 5건" 을 세고 `--fix` 는 "No cache entries
      found" 로 끝났다. 세는 것과 지울 수 있는 것이 같아야 한다.
    """
    norm = re.sub(r"[-_.]+", "-", name.lower())
    pats = [f"wheels-v*/*/{norm}", f"sdists-v*/*/{norm}", f"simple-v*/*/{norm}.rkyv"]
    return any(any(root.glob(pat)) for pat in pats)


def scan_cache():
    """thoth 만 쓰는 패키지. 남과 겹치는 것은 공유 자산이라 건드리지 않는다.

    ★ **화장실을 같이 써도 내 것은 가릴 수 있다.** uv 캐시는 어느 프로젝트가
      받게 했는지를 기록하지 않지만, `uv.lock` 이 무엇을 요구하는지는 안다.
      이웃 저장소의 lock 과 빼면 이 저장소만 쓰는 것이 남는다.

    ★ **겹치는 것은 남긴다.** `fastapi` 를 이웃도 쓰면 그 캐시는 공유 자산이고,
      지우면 남의 재설치가 느려진다. 내 것이 아닌 것을 치우는 것은 위생이
      아니다(DECISIONS §42).

    ★ 이웃을 찾지 못하면 **못 잼**이다. 전부 내 것이라고 단정하지 않는다 —
      그렇게 단정하면 남의 것을 지운다.
    """
    mine = lock_packages(ROOT / "worker" / "uv.lock") | lock_packages(ROOT / "uv.lock")
    if not mine:
        raise LookupError("이 저장소의 uv.lock 을 읽지 못했다")

    siblings = sorted(p for p in ROOT.parent.iterdir()
                      if p.is_dir() and p.resolve() != ROOT.resolve())

    theirs, seen = set(), []
    for s in siblings:
        pkgs = set()
        for lock in list(s.glob("uv.lock")) + list(s.glob("*/uv.lock")):
            pkgs |= lock_packages(lock)
        # ★ `uv.lock` 이 없으면 이웃이 아니다. 부모 아래의 모든 폴더를 이웃으로
        #   세면 작업 사본이나 관계없는 디렉터리까지 들어와 판정이 흔들린다.
        #   잠근 것이 없는 곳은 캐시를 만들지도 않는다.
        if pkgs:
            seen.append(f"{s.name}({len(pkgs)})")
            theirs |= pkgs

    if not seen:
        raise LookupError(f"{ROOT.parent} 에서 uv.lock 을 가진 이웃을 찾지 못했다")

    # ★ 로컬 프로젝트 자신은 캐시된 배포판이 아니다. 목록에 자기 이름이 있으면
    #   판정이 덜 다듬어진 것이다. `pyproject.toml` 의 name 을 빼낸다.
    selves = set()
    for tm in list(ROOT.glob("pyproject.toml")) + list(ROOT.glob("*/pyproject.toml")):
        try:
            m = re.search(r'^name = "([^"]+)"', tm.read_text(encoding="utf-8"), re.M)
        except OSError:
            continue
        if m:
            selves.add(m.group(1).lower())

    root = cache_dir()
    only = sorted(n for n in mine - theirs - selves if in_cache(n, root))
    return only, sorted(mine & theirs), seen


def show(title, rows, fix) -> int:
    print(f"  {title}")
    if not rows:
        print("    깨끗하다")
        return 0
    n = 0
    for ok, why, p in rows:
        mark = "지운다" if (ok and fix) else ("지울 수 있다" if ok else "남긴다")
        print(f"    {why:14} {p.name:34} {mark}")
        if ok and fix:
            p.unlink(missing_ok=True)
        n += ok
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="근거가 확실한 것만 지운다")
    ap.add_argument("--brief", action="store_true", help="건수만 한 줄로")
    a = ap.parse_args()

    tmp = scan_tmp()
    try:
        lake, lake_err = scan_lake(), ""
    except LookupError as e:
        lake, lake_err = [], str(e)

    if a.brief:
        n = sum(ok for ok, _, _ in tmp) + sum(ok for ok, _, _ in lake)
        print(f"흔적 {n}건" + (" · 수신함 못 잼" if lake_err else ""))
        return 2 if lake_err else 0

    total = show(f"{TMP} — thoth 가 흘린 것", tmp, a.fix)
    print()
    if lake_err:
        print(f"  수신함 — 못 잼: {lake_err}")
    else:
        total += show("수신함 — 받아 둔 것", lake, a.fix)

    print()
    cache_err = ""
    try:
        only, shared, seen = scan_cache()
    except LookupError as e:
        cache_err = str(e)
    if cache_err:
        print(f"  uv 캐시 — 못 잼: {cache_err}")
    else:
        print(f"  uv 캐시 — 이웃 {' · '.join(seen) or '없음'}")
        print(f"    공유 {len(shared)}건 남긴다 · thoth 만 쓰는 것 {len(only)}건")
        if only:
            print("    " + ", ".join(only))
            if a.fix:
                # ★ **실패를 조용히 넘기지 않는다.** 종료 코드를 본다. 이웃이
                #   `uv run` 으로 돌고 있으면 캐시 락을 쥐고 있어 정리가
                #   타임아웃 난다 — 일시적 충돌이지 결함이 아니고, 남이 쓰는
                #   중에는 비키는 것이 맞다. 다만 **비켰다는 사실은 적는다**
                #   (DECISIONS §44).
                r = subprocess.run(["uv", "cache", "clean", *only],
                                   capture_output=True, text=True)
                out = (r.stdout + r.stderr).strip()
                if r.returncode == 0:
                    print("    " + (out.splitlines()[-1] if out else "지웠다"))
                else:
                    cache_err = "uv cache clean 이 실패했다"
                    print("    못 잼 — uv 가 캐시 락을 내주지 않는다")
                    for line in out.splitlines()[-3:]:
                        print("      " + line)
                    busy = subprocess.run(["pgrep", "-a", "uv"],
                                          capture_output=True, text=True).stdout.strip()
                    mine = [l for l in busy.splitlines() if "uvicorn app.main:app" in l]
                    if busy:
                        print("      쥐고 있는 것 : " + (mine or busy.splitlines())[0][:80])
                    # ★ **쥔 것이 이 저장소 자신이면 대응이 다르다.** `run_worker.sh`
                    #   가 `uv run` 으로 띄우므로 워커가 살아 있는 동안 락이 잡힌다.
                    #   개발 중에는 워커를 띄워 두는 것이 정상이라, 기다리라고만
                    #   하면 캐시를 털 기회가 영영 오지 않는다(DECISIONS §53).
                    if mine:
                        print("      이 저장소의 워커다. 내리고 다시 돌린다 —")
                        print("      fuser -k 8000/tcp && python3 tools/sweep.py --fix")
                    else:
                        print("      다른 저장소가 쓰는 중이다. 끝난 뒤 다시 돌린다")
            else:
                print(f"    지우려면 --fix  (uv cache clean {len(only)}건)")

    print()
    # ★ **세는 것과 쓴 것이 같아야 한다.** 캐시를 못 지웠는데 그 수를 합계에
    #   넣으면 그 수를 보고 한 판단도 틀린다. 합계는 `/tmp` 와 수신함만 센다
    #   — 캐시는 건수가 아니라 패키지 수라 단위도 다르다(DECISIONS §44).
    if total:
        print(f"  {total}건 " + ("지웠다" if a.fix else "— 지우려면 --fix"))
    if cache_err:
        print("  uv 캐시는 재지 못했다")
    return 2 if (lake_err or cache_err) else 0


if __name__ == "__main__":
    sys.exit(main())
