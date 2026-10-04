"""부른 쉘이 들고 온 것을 **한 번만** 잰다 (DECISIONS §154).

★ `doctor` 가 제 안에서 재면, **`load_env` 를 먼저 하고 `doctor` 를 부르는 쪽**에서
  `.env` 값이 전부 「쉘 오염」 으로 찍힌다. 2026-10-04 에 `ship.sh` 로 돌린 판이 스물셋을
  경고했고, **같은 초에 `doctor` 를 따로 돌리면 OK 였다.**

★ **늘 울리는 경보는 아무도 안 읽는다.** §147 이 잡으려던 것은 쉘에 꽂아 둔
  `WORKER_TOKEN` 하나인데, 그것이 스물셋 속에 묻힌다.

★ **고친 것과 끈 것은 다르다.** 그래서 네 경우를 다 본다 — 특히 **진짜 오염이 여전히
  우는지**를.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_SH = ROOT / "tools/lib/env.sh"


def _재다(예제: str, 환경: dict[str, str]) -> str:
    """`ambient_keys` 를 그 .env.example 과 그 환경으로 돌린다."""
    r = subprocess.run(
        ["bash", "-c", f'. "{ENV_SH}"; ambient_keys "$1"', "_", "/dev/stdin"],
        input=예제, env={"PATH": "/usr/bin:/bin", **환경}, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


예제 = "ENGINE=echo\nWORKER_TOKEN=\nCACHE=file\n"


def test_쉘에_있는_키만_센다():
    assert _재다(예제, {"ENGINE": "bedrock"}) == "ENGINE"


def test_빈_값은_안_센다():
    # ★ `WORKER_TOKEN=` 는 「인증 없음」 이라 해롭지 않다. 세면 경보가 늘 운다.
    assert _재다(예제, {"WORKER_TOKEN": ""}) == ""


def test_선언_안_된_키는_안_센다():
    # ★ 정본은 `.env.example` 이다 — 거기 없는 변수는 이 저장소의 것이 아니다.
    assert _재다(예제, {"HOME": "/x", "LANG": "ko"}) == ""


def test_아무것도_없으면_빈_문자열이다():
    assert _재다(예제, {}) == ""


# ── 부르는 자리 ───────────────────────────────────────────────────────────

def _글(p: str) -> str:
    return (ROOT / p).read_text(encoding="utf-8")


def test_doctor_가_물려받은_측정을_쓴다():
    몸 = _글("tools/doctor.sh")
    assert 'AMBIENT="${THOTH_AMBIENT-$(ambient_keys .env.example)}"' in 몸, (
        "물려받은 측정을 안 쓴다")
    assert "${THOTH_AMBIENT:-" not in 몸, (
        "`:-` 는 **「재 봤는데 없었다」(빈 문자열)** 를 **「안 쟀다」** 로 읽는다 — "
        "그러면 깨끗한 쉘에서 다시 재고, 다시 재는 그 자리가 틀린 자리다")


def test_doctor_가_제_안에서_따로_재지_않는다():
    # ★ **같은 판단이 두 곳에 살면 갈린다**(§14 · §132). 재는 일은 `env.sh` 하나다.
    몸 = _글("tools/doctor.sh")
    assert 몸.count("ambient_keys") == 1, "재는 자리가 둘 이상이다"
    # ★ `.env.example` 에서 키를 뽑는 꼴이 `doctor` 안에 **하나도** 남으면 안 된다 —
    #   전에는 `keys()`(grep) · `ENV_KEYS`(sed) · 떠 있는 키 재기까지 **셋**이었고
    #   꼴이 조금씩 달랐다. 정본은 `tools/lib/env.sh::env_keys` 다.
    assert "[A-Z0-9_]" not in 몸, "doctor 가 아직 제 손으로 키를 뽑는다"
    assert 몸.count("env_keys") >= 2, "doctor 가 공통 함수를 안 쓴다"


def test_ship_이_load_env_보다_먼저_잰다():
    """★ **순서가 전부다.** `load_env` 뒤에 재면 `.env` 에서 온 것과 쉘에서 온 것이
    구별되지 않는다 — 이 패치가 고치는 결함이 정확히 그것이다."""
    몸 = _글("tools/ship.sh")
    잰다 = 몸.index('THOTH_AMBIENT="$(ambient_keys')
    읽는다 = 몸.index('load_env "$ROOT/.env"')
    assert 잰다 < 읽는다, "`load_env` 뒤에 재고 있다 — 고치기 전과 같은 상태다"


def test_env_sh_가_재는_함수를_연다():
    assert "ambient_keys()" in _글("tools/lib/env.sh")
