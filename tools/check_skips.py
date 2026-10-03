#!/usr/bin/env python3
"""건너뛰는 자리가 전부 선언돼 있는가.

    python3 tools/check_skips.py       0 통과 · 1 어긋남

★ **SKIP 은 「통과」 가 아니라 「안 봤다」 다.** 그런데 화면에서는 OK 와 나란히
  노랗게 지나가고, 수가 늘어도 아무도 안 센다. **검사를 끄는 가장 쉬운 길이
  `skip` 한 줄을 더하는 것**이다 — 그러면 그 자리는 영원히 안 보이면서 doctor 는
  「이상 없음」 을 낸다.

★ **2026-10-03 에 실제로 당했다.** jsdom 이 없는 기계에서 확장 검사 69건이 skip
  된 채 `30 pass` 가 나왔고 그것을 통과로 읽었다. 사용자 기계에서는 2 fail
  이었다(DECISIONS §135). **SKIP 이 섞인 초록은 초록이 아니다.**

★ **묻는 것은 「이 skip 이 옳은가」 가 아니라 「선언 안 된 skip 이 있나」 다**(족 가드).
  전자로 적으면 **새로 들어온 skip 이 검사를 비켜 간다.** 건너뛸 수는 있다 — 다만
  **왜 건너뛰는지를 적어야** 하고, 적는 순간 그것이 범위인지 도구인지 빚인지 갈린다.

★ **런타임 수를 못 박지 않는다.** SKIP 건수는 기계마다 다르다(CI 에는 `gh` 도
  terraform 도 없다). 대신 **`doctor.sh` 안의 `skip` 호출 자리**를 못 박는다 —
  그것은 기계와 무관하고 CI 가 볼 수 있다.

갈래 넷 :
  범위  그 범위에서 안 보는 것이 **맞다**. `--repo` 가 기계 설정을 안 보는 것 등
  도구  그 기계에 도구가 없다. **깔면 사라진다** — 그 기계의 빚이지 저장소의 빚이 아니다
  조건  도구는 있는데 **잴 대상이 없거나 조건이 안 섰다**. 일시적이다
  빚    **닫아야 할 것이다.** 반드시 PLAN 행이나 DECISIONS 절을 들어야 한다
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCTOR = ROOT / "tools/doctor.sh"

_호출 = re.compile(r'(?<!\w)skip\s+"((?:[^"\\]|\\.)*)"')

# ── 선언 ────────────────────────────────────────────────────────────────────
#
# 열쇠는 **`doctor.sh` 에 적힌 그대로의 문자열**이다. 말을 고치면 선언도 다시
# 해야 한다 — 귀찮지만 그것이 목적이다. **건너뛰는 말을 고칠 때 왜 건너뛰는지를
# 다시 생각하게 한다.**
선언: dict[str, tuple[str, str]] = {
    # ── 범위 : --repo 는 기계 설정을 안 본다. CI 에는 그 기계가 없다(§22) ──
    ".env 존재 (기계 설정이다)": ("범위", "CI 에 .env 는 언제나 없다"),
    "SSD 비밀 검사 (기계 설정이다)": ("범위", "CI 에 SSD 마운트가 없다"),
    "토큰 검사 (기계 설정이다)": ("범위", "로컬 .env 를 본다"),
    "셸 오염 · 훅 · 홈 규약 · 산출물 · 모델 (--repo 범위 밖)": ("범위", "한 작업 기계의 불변식이다"),
    "인프라 적용 시차 (기계 상태다)": ("범위", "도장이 .cache/ 에 있다 — PLAN #68"),
    "배포 게이트 (GitHub 설정이다)": ("범위", "커밋이 네트워크에 기대면 안 된다(§98 · §110)"),
    "합친 가지 자동 삭제 (GitHub 설정이다)": ("범위", "같은 까닭"),

    # ── 도구 : 깔면 사라진다 ────────────────────────────────────────────
    "uv 가 없어 엔진 전제를 보지 못한다": ("도구", "uv"),
    "shellcheck 가 없어 보지 못한다 (CI 에서는 돈다)": ("도구", "shellcheck · CI 에서는 돈다"),
    "terraform 이 없어 보지 못한다": ("도구", "terraform"),
    "gh 가 없어 배포 게이트를 보지 못한다": ("도구", "gh"),
    "uv 가 없어 잠금을 보지 못했다 (CI 에서는 돈다)": ("도구", "uv · CI 에서는 돈다"),
    "ruff 를 부르지 못해 파이썬을 보지 못한다": ("도구", "ruff"),
    "node 가 없어 JS 문법을 보지 못한다": ("도구", "node"),
    "node 가 없어 확장 테스트를 돌리지 못한다": ("도구", "node · jsdom"),
    "uv 가 없어 테스트를 돌리지 못한다": ("도구", "uv"),

    # ── 조건 : 잴 대상이나 조건이 없다 ──────────────────────────────────
    "SSD 에 닿지 못해 재지 못했다": ("조건", "SSD 미연결"),
    ".env 가 없어 비교하지 않는다": ("조건", ".env 가 없는 기계"),
    "규약 밖: $OUT": ("조건", "홈에 규약 밖 이름이 있다 — 사람이 치운다"),
    "engine=${ENGINE:-echo} 전제 — bash tools/preflight.sh 가 본다": ("조건", "preflight 가 본다"),
    "${PF_FACT:-전검사가 없다}": ("조건", "전검사가 없거나 미등록 엔진이다"),
    "ollama 에 묻지 못해 미채택 모델을 재지 못했다": ("조건", "ollama 미기동"),
    "셸 파일을 찾지 못했다": ("조건", "셸 파일이 없는 나무"),
    "infra 가 없다": ("조건", "infra/ 가 없는 나무"),
    "infra/.terraform 이 없다 — bash tools/tf.sh init 후에 본다": ("조건", "init 전이다(§73)"),
    "infra/ 지문을 뜨지 못했다": ("조건", "infra/ 를 읽지 못했다"),
    "배포 게이트를 재지 못했다 — ${GATE_OUT}": ("조건", "gh 응답 실패"),
    "합친 가지 설정을 재지 못했다": ("조건", "gh 응답 실패"),
    "캐스케이드 — ${CAS_1}": ("조건", "playwright · 크로미움 — CI 에는 없다"),
    "위생을 재지 못했다": ("조건", "sweep 을 부르지 못했다"),

    # ── 빚 : 닫아야 한다. 행이나 절을 들어야 한다 ───────────────────────
    "기준선이 stale 이다 ($STALE) — 재측정 후 값을 채우고 플래그를 지운다": (
        "빚", "MASTER §7-1 이 「다시 재는 것은 자체 모델이 들어올 때」 로 정했다 — PLAN #59"),
    "$SWEEP_N — python3 tools/sweep.py": (
        "빚", "흔적은 쌓이면 치운다. FAIL 로 올리지 않는 까닭은 DECISIONS §41"),
    "$l": ("빚", "건수를 재지 못한 자리 — `check_counts` 가 낸 줄을 그대로 옮긴다. PLAN #63"),
}

_근거참조 = re.compile(r"PLAN #(\d+)|DECISIONS §\d+|MASTER §[\d-]+")


def 호출들(글: str) -> list[str]:
    """`doctor.sh` 에 적힌 `skip "..."` 의 인자들. 주석 줄은 뺀다."""
    out = []
    for 줄 in 글.split("\n"):
        if 줄.lstrip().startswith("#"):
            continue
        out += _호출.findall(줄.split(" #", 1)[0] if " #" in 줄 else 줄)
    return out


def _plan_rows() -> set[int]:
    """살아 있는 PLAN 행. 셈은 `docx_check.py` 하나다 — 두 번 세지 않는다(§132)."""
    spec = importlib.util.spec_from_file_location("docx_check", ROOT / "tools/docx_check.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.plan_rows(ROOT)


def fails(글: str, 산행: set[int]) -> list[str]:
    난것 = []
    본것 = 호출들(글)
    쓴것 = set()

    for arg in 본것:
        if arg not in 선언:
            난것.append(
                f'선언 안 된 skip : "{arg}" — **왜 건너뛰는지를 적는다.** '
                f"`check_skips.py` 의 `선언` 에 갈래(범위 · 도구 · 조건 · 빚)와 근거를 더한다")
            continue
        쓴것.add(arg)

    for arg in 선언:
        if arg not in 본것:
            난것.append(f'죽은 선언 : "{arg}" — `doctor.sh` 에 그 skip 이 없다. 선언에서 뺀다')

    for arg in sorted(쓴것):
        갈래, 근거 = 선언[arg]
        if 갈래 not in ("범위", "도구", "조건", "빚"):
            난것.append(f'갈래가 어휘 밖이다 : "{arg}" → {갈래}')
        if 갈래 != "빚":
            continue
        m = list(_근거참조.finditer(근거))
        if not m:
            난것.append(
                f'빚인데 근거가 없다 : "{arg}" — **닫아야 할 것은 PLAN 행이나 '
                f'DECISIONS 절을 들어야 한다.** 안 들면 영원히 노란 채로 남는다')
            continue
        for x in m:
            if x.group(1) and int(x.group(1)) not in 산행:
                난것.append(
                    f'빚이 죽은 행을 가리킨다 : "{arg}" → PLAN #{x.group(1)} 는 '
                    f"§1 에 없다. 닫혔으면 이 skip 도 없어져야 한다")
    return 난것


def main() -> int:
    글 = DOCTOR.read_text(encoding="utf-8")
    난것 = fails(글, _plan_rows())
    본것 = 호출들(글)
    셈: dict[str, int] = {}
    for arg in 본것:
        갈래 = 선언.get(arg, ("안 선언됨", ""))[0]
        셈[갈래] = 셈.get(갈래, 0) + 1
    print("    건너뛰는 자리 " + str(len(본것)) + "곳 — "
          + " · ".join(f"{k} {v}" for k, v in sorted(셈.items())))
    for x in 난것:
        print(f"    {x}")
    return 1 if 난것 else 0


if __name__ == "__main__":
    sys.exit(main())
