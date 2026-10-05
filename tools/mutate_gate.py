#!/usr/bin/env python3
"""가드를 망가뜨려 시험이 우는지 본다 — **선언된 돌연변이를 전부 돌린다**.

    python3 tools/mutate_gate.py              전부
    python3 tools/mutate_gate.py --only pkg   한 가드만
    python3 tools/mutate_gate.py --list       무엇이 선언돼 있나

★ **「검사를 더했다」 와 「검사가 문다」 는 다른 말이다**(DECISIONS §152). 2026-10-04
  하루에 가드 일곱을 세우면서 돌연변이를 손으로 돌렸는데, **세 번은 첫 판이 안 물었다**
  (§145 · §147 · §150). 저장소가 깨끗하면 **검사를 꺼도 조용하기** 때문이다 —
  시험이 가드를 붙들고 있지 않아도 초록이 뜬다.

★ **그런데 그 돌연변이가 전부 휘발됐다.** 손으로 돌리면 다음 사람이 안 돌리고,
  안 돌린 줄도 모른다. 하토르가 `tools/mutate_gate.py` 를 가진 까닭이 이것이다.

★ **자동 생성이 아니라 선언이다.** `mutmut` 류는 모든 토막을 뒤집어 보므로 느리고
  시끄럽다. 오늘 물린 돌연변이는 전부 **가드의 하중을 받는 한 줄**을 겨눈 것이었다.
  겨냥은 사람이 하고, **빠뜨리지 않는 일만 기계가 한다.**

★ **시험을 좁혀 부른다.** 돌연변이마다 「어느 시험이 울어야 하나」 를 선언하므로
  한 건이 0.5초 안쪽이다. 전부 돌려도 `doctor` 안에서 돌 만하다.

★ **양방향 톱니다.** 살아남은 것이 **0 이 아니면** 울고, 선언이 **줄어도** 운다 —
  안 그러면 안 무는 돌연변이를 지워서 초록을 만들 수 있다.

★ **종료코드를 가른다**(DECISIONS §153). 종전에는 `!= 0` 을 「물었다」 로 셌다. pytest 는
  **1만 「시험이 울었다」** 고 2·3·4·5 는 **도구가 깨진 것**이다 — 선언한 시험 이름이 하나
  틀리면 4 로 죽고, 그러면 **가드를 완전히 망가뜨려도 「물었다」 로 찍힌다.** 실물로 확인했다.

★ **신호를 받아 되돌린다**(§153). `try/finally` 는 `SIGINT`/`SIGTERM` 에 안 돈다 — seshat 이
  같은 도구를 `timeout` 으로 끊었다가 **검사기 한 파일이 주석 269줄을 잃은 채 남았고**, 그
  망가진 도구가 **조용히 틀린 일을 했다.** 되돌린 뒤 **해시로 확인**한다.

★ **밖 — 선언한 것만 돌린다.** 겨냥은 사람이 하므로 **선언 안 된 자리는 안 본다** — 그 수는
  `미선언` 이 든다. 그리고 **단언을 뒤집는 것은 돌연변이가 아니므로 시험 자체는 안 잰다.**

★ **덮는 가드를 선언한다.** 「선언 안 된 가드가 있나」 를 묻는다(족 가드). 아직 안
  덮은 것은 `미선언` 에 적어 두고 **그 수가 늘면 운다** — 못 보는 자리를 좁히고
  그 자리를 적는다(§73).
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
선언파일 = ROOT / "tools" / "mutations.json"

# ★ **덮은 가드가 줄면 운다.** 돌연변이를 지워서 초록을 만드는 길을 막는다.
MIN_돌연변이 = 128
MIN_가드 = 21


# pytest 의 종료코드 — **1만 「시험이 울었다」 다**
#   0 전부 통과 · 1 실패 · 2 끊김 · 3 내부 오류 · 4 쓰는 법 틀림 · 5 모은 시험이 0
_울었다 = 1
# ★ 지금 뚫어 놓은 파일과 그 원본. 신호를 받으면 이것을 되돌리고 죽는다.
_뚫린것: dict[pathlib.Path, str] = {}


def _바이트코드를_버린다(파일: pathlib.Path) -> None:
    """★ **길이가 같은 돌연변이는 `__pycache__` 를 중독시킨다**(DECISIONS §157).

    2026-10-05 에 `return 3` 을 `return 0` 으로 바꿨다. **글자 수가 같다.** 파이썬은 소스의
    크기와 mtime 으로 캐시를 쓰는데 둘 다 같으면 **복원한 뒤에도 뚫린 바이트코드를 다시
    쓴다.** 해시로 소스를 확인해도 안 잡힌다 — 소스는 멀쩡하기 때문이다.

    그 뒤의 모든 판정이 거짓이 된다. 실제로 시험 하나가 **설명 없이** 틀렸고 원인을
    엉뚱한 데서 찾았다.
    """
    for q in 파일.parent.glob(f"__pycache__/{파일.stem}.*.pyc"):
        q.unlink(missing_ok=True)


def _이름(p: pathlib.Path) -> str:
    """보기 좋은 이름. ★ **되돌리는 길에서 이름 때문에 죽지 않는다** — `relative_to` 는
    ROOT 밖 경로에 `ValueError` 를 던지고, 그러면 **남은 파일을 못 되돌린다.**"""
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def _되돌리고_죽는다(signum: int, _frame: object) -> None:
    """★ **끊겨도 소스를 남기지 않는다.** `finally` 는 신호에 안 돈다(DECISIONS §153).

    ★ **한 파일이 실패해도 나머지를 끝까지 되돌린다.** 되돌리는 길에서 예외가 새면
      그 뒤의 파일이 뚫린 채로 남는다 — 이 함수가 막으려던 바로 그 상태다.
    """
    for p, 원 in list(_뚫린것.items()):
        try:
            p.write_text(원, encoding="utf-8")
            _바이트코드를_버린다(p)
            print(f"\n  신호 {signum} — {_이름(p)} 을 되돌렸다", file=sys.stderr)
        except Exception as e:
            print(f"\n  ★ 신호 {signum} — **{_이름(p)} 을 못 되돌렸다**({e}) : "
                  f"git checkout -- {_이름(p)}", file=sys.stderr)
    sys.exit(130)


def 읽기() -> dict:
    raw = json.loads(선언파일.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def 가드들(선언: dict) -> dict:
    """★ **「가드란 무엇인가」 를 한 곳이 정한다.** 여기와 시험이 각각 정하면
    시험이 세는 수와 관문이 도는 수가 갈린다(§132 · §145 가 같은 모양이었다)."""
    return {k: v for k, v in 선언.items() if k != "미선언"}


def 한건(파일: pathlib.Path, 전: str, 후: str, 시험: list[str]) -> tuple[bool, str]:
    """한 줄을 바꾸고 선언된 시험을 돌린다. (물었나, 까닭)."""
    원 = 파일.read_text(encoding="utf-8")
    if 전 not in 원:
        return False, "바꿀 자리를 못 찾았다 — 코드가 바뀌었으면 선언도 고친다"
    if 원.count(전) > 1:
        return False, f"바꿀 자리가 {원.count(전)}곳이다 — 겨냥이 흐리다"
    앞해시 = hashlib.sha256(원.encode()).hexdigest()
    _뚫린것[파일] = 원
    파일.write_text(원.replace(전, 후, 1), encoding="utf-8")
    try:
        # ★ **뚫린 동안 바이트코드를 남기지 않는다**(§157). 막는 것이 치우는 것보다 싸다.
        r = subprocess.run(시험, cwd=ROOT, capture_output=True, text=True, timeout=300,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    finally:
        파일.write_text(원, encoding="utf-8")
        _바이트코드를_버린다(파일)
        _뚫린것.pop(파일, None)
    # ★ **되돌린 것을 확인한다.** 쓰기가 실패해도 `finally` 는 조용하다 — 그러면 뚫린
    #   소스가 남고 **그 뒤의 모든 판정이 거짓**이 된다.
    if hashlib.sha256(파일.read_text(encoding="utf-8").encode()).hexdigest() != 앞해시:
        print(f"  ★ **{_이름(파일)} 을 못 되돌렸다** : git checkout -- {_이름(파일)}",
              file=sys.stderr)
        raise SystemExit(2)
    # ★ **도구 고장을 「물었다」 로 세지 않는다**(§153). 선언한 시험 이름이 하나 틀리면
    #   pytest 는 4 로 죽고, `!= 0` 은 그것도 「물었다」 로 센다 — **가드를 완전히
    #   망가뜨려도 초록이다.** 실물로 확인했다.
    if r.returncode not in (0, _울었다):
        print(f"  ★ **러너가 {r.returncode} 로 끝났다 — 시험이 운 것이 아니라 도구가 "
              f"깨졌다.**\n     {' '.join(시험)}\n{r.stdout[-500:]}", file=sys.stderr)
        raise SystemExit(2)
    # ★ **건너뛴 시험은 안 문다**(DECISIONS §158). 의존성이 없는 기계에서 `skip` 된
    #   시험은 통과로 끝나므로 **「약해서 안 물었다」 와 구별이 안 된다** — 2026-10-05 에
    #   CI 가 그렇게 빨개졌고 진단에 시간을 썼다. 까닭을 가른다.
    if r.returncode == 0 and 전부_건너뛰었나(r.stdout):
        return False, "시험이 **전부 건너뛰어졌다** — 건너뛴 시험은 안 문다. 의존성을 깐다"
    return r.returncode == _울었다, "" if r.returncode else "시험이 통과했다 — 가드를 안 붙들고 있다"


def 전부_건너뛰었나(out: str) -> bool:
    """통과가 **하나도 없이** 건너뛰기만 했나.

    ★ **러너마다 말이 다르다**(DECISIONS §160). 종전 판은 `"skipped" in out and " passed"
      not in out` 하나였는데 그것은 **pytest 의 말투**다. `node --test` 는 언제나
      `# skipped N` 과 `# pass N` 을 찍으므로, 멀쩡히 통과한 node 판이 **「전부
      건너뛰어졌다」 로 읽힌다** — 살아남은 돌연변이가 **딴 까닭으로 보고된다.**
    ★ **셀 수 있으면 센다.** 두 러너 다 수를 찍으므로 글자가 있나가 아니라 **수가 0 인가**를
      본다. 수를 못 읽으면 종전 어림으로 돌아간다 — 모르는 러너를 못 잼으로 두지 않는다.
    """
    노드건너 = re.search(r"^# skipped (\d+)$", out, re.M)
    노드통과 = re.search(r"^# pass (\d+)$", out, re.M)
    if 노드건너 and 노드통과:
        return int(노드건너.group(1)) > 0 and int(노드통과.group(1)) == 0
    파이건너 = re.search(r"(\d+) skipped", out)
    파이통과 = re.search(r"(\d+) passed", out)
    if 파이건너:
        return int(파이건너.group(1)) > 0 and not (파이통과 and int(파이통과.group(1)) > 0)
    return False


def _canary() -> None:
    """★ **판별식이 사나.** 0 이 목표인 검사는 **깨끗해서 0 인지 죽어서 0 인지** 못 가른다."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "a.py"
        f.write_text("x = 1\n", encoding="utf-8")
        물었나, _ = 한건(f, "x = 1", "x = 2", ["false"])
        if not 물었나 or f.read_text(encoding="utf-8") != "x = 1\n":
            print("    ★ 카나리아가 죽었다 — 뚫거나 되돌리지 못한다"); sys.exit(2)
        if 한건(f, "없는 줄", "y", ["false"])[0]:
            print("    ★ 카나리아가 죽었다 — 못 찾은 것을 물었다고 센다"); sys.exit(2)


def main() -> int:
    _canary()
    for _sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(_sig, _되돌리고_죽는다)
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="가드 이름 하나만")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="판별식이 살아 있나")
    a = ap.parse_args()

    if a.selftest:
        print("  프로브 살아 있다 — 뚫기 · 되돌리기 · 못 찾은 것 가르기")
        return 0

    선언 = 읽기()
    가드 = 가드들(선언)
    미선언 = 선언.get("미선언", [])

    if a.list:
        for 이름, g in 가드.items():
            print(f"{이름:<14} {g['파일']:<42} 돌연변이 {len(g['돌연변이'])}")
        print(f"\n미선언 가드 {len(미선언)} : " + " ".join(미선언))
        return 0

    셈 = {"돌": 0, "산것": 0}
    난것: list[str] = []
    for 이름, g in 가드.items():
        if a.only and a.only != 이름:
            continue
        파일 = ROOT / g["파일"]
        for m in g["돌연변이"]:
            셈["돌"] += 1
            물었나, 까닭 = 한건(파일, m["전"], m["후"], g["시험"])
            if not 물었나:
                셈["산것"] += 1
                난것.append(f'  LIVE [{이름}] {m["이름"]} — {까닭}')
            print(f'  {"OK  " if 물었나 else "LIVE"} [{이름}] {m["이름"]}')

    print(f'\n돌연변이 {셈["돌"]}건 · 살아남음 {셈["산것"]}건')
    for x in 난것:
        print(x)

    # ★ 양방향 — 선언이 줄면 운다
    전체 = sum(len(g["돌연변이"]) for g in 가드.values())
    if not a.only:
        if 전체 < MIN_돌연변이:
            난것.append(f"선언된 돌연변이가 {전체}건으로 바닥 {MIN_돌연변이} 아래다 — "
                        f"안 무는 돌연변이를 지워 초록을 만드는 길이다")
        if len(가드) < MIN_가드:
            난것.append(f"덮는 가드가 {len(가드)}개로 바닥 {MIN_가드} 아래다")
        if 전체 > MIN_돌연변이 or len(가드) > MIN_가드:
            print(f"\n※ 좋아졌다 — MIN_돌연변이 를 {전체} 로, MIN_가드 를 {len(가드)} 로 올린다")
    return 1 if 난것 else 0


if __name__ == "__main__":
    sys.exit(main())
