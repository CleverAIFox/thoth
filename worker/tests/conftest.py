"""시험은 **부른 쉘을 안 본다**.

★ **2026-10-04 실측 — `WORKER_TOKEN` 하나가 떠 있으면 시험 41개가 깨진다**
  (DECISIONS §147). `guard` 가 인증을 요구하게 되고, 시험은 토큰 없이 부르므로
  401 이 나고, 번역이 안 나가니 쌍 줄도 안 쌓인다. **코드는 멀쩡한데 빨갛다.**

★ **그 변수를 쉘에 꽂는 것은 이 저장소가 제 문서로 시키는 일이다** — 배포 뒤
  `tools/smoke.sh` 를 돌리려면 `export WORKER_TOKEN=...` 가 필요하다. 그 쉘에서
  `doctor` 를 돌리면 **doctor 의 판정이 쉘에 달린다.**

★ **D-0066 이 같은 병을 `~/.bashrc` 에서 막고 있었다.** 막은 것은 **파일**이고
  들어온 문은 **살아 있는 환경**이었다 — **같은 병에 문이 둘이었다.**

★ **목록을 손으로 안 적는다.** `.env.example` 이 키의 정본이므로 거기서 읽는다
  (§132 · §145 가 「두 데가 같은 것을 다르게 적으면 갈린다」 로 겪은 자리).
  새 키가 생기면 **고칠 것 없이** 함께 비워진다.

★ **모듈 몸통에서 지운다. 픽스처로는 늦다** — pytest 는 `conftest.py` 를 시험
  모듈보다 먼저 들이지만 **픽스처는 그 뒤에 돈다.** `tests/test_pairs.py` 처럼
  임포트 시점에 `ENGINE`·`CACHE` 를 제 손으로 박는 모듈이 있어서, 픽스처로 지우면
  **그 모듈이 박은 값까지 지운다.**
"""
import os
import pathlib
import re

ENV_EXAMPLE = pathlib.Path(__file__).resolve().parents[2] / ".env.example"
_키 = re.compile(r"^([A-Z_][A-Z0-9_]*)=", re.M)


def 선언된_키(path: pathlib.Path = ENV_EXAMPLE) -> list[str]:
    """`.env.example` 이 선언한 키. 이것이 「이 저장소의 설정」 의 정본이다."""
    if not path.exists():
        return []
    return sorted(set(_키.findall(path.read_text(encoding="utf-8"))))


def 환경을_비운다(env: dict | None = None, path: pathlib.Path = ENV_EXAMPLE) -> list[str]:
    """선언된 키를 환경에서 지운다. 지운 키를 돌려준다."""
    env = os.environ if env is None else env
    지운것 = [k for k in 선언된_키(path) if k in env]
    for k in 지운것:
        del env[k]
    return 지운것


# ★ **여기서 돈다 — 어떤 시험 모듈이 들어오기도 전에.**
비운것 = 환경을_비운다()
