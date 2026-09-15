"""워커 패키지. **로깅 배선이 여기 있다.**

★ **두 진입점이 모두 이 패키지를 거친다.** `main.py` 도 `lambda_handler.py` 도
  `from . import contract` 로 들어오므로 이 파일이 한 번 돈다. 배선을 한쪽에
  두면 다른 쪽이 다른 로그를 낸다 — 계약을 한 자리에 모은 이유와 같다(§68).

★ **핸들러가 없으면 `log.info` 는 사라진다.** 파이썬은 핸들러를 못 찾으면
  `lastResort` 로 떨어지고 그것은 WARNING 이상만 흘린다. 2026-09-15 에 토큰
  계기가 그렇게 조용히 아무것도 하지 않았다 — 워커는 정상이고 번역도 됐는데
  `usage` 줄만 통째로 없었다(§79).

★ **`propagate` 를 끄고 우리 핸들러 하나만 쓴다.** 켜 두면 출력이 상위 로거의
  핸들러에 달리는데, 그 핸들러는 uvicorn 이 놓은 것일 수도 Lambda 런타임이 놓은
  것일 수도 있고 **레벨을 우리가 정하지 못한다.** 로컬과 배포본에서 같은 호출이
  다르게 보이면 계기가 아니다.

★ **stdout 에 쓴다.** Lambda 는 stdout 을 CloudWatch 로 담는다. 런타임 핸들러를
  쓰면 RequestId 가 붙지만 그 대가가 위의 '레벨을 우리가 정하지 못한다' 이다.
  `usage` 줄은 스스로 배치와 문자 수를 싣고 있어 RequestId 없이 집계된다.

★ **레벨을 환경변수로 열지 않는다.** 키를 늘리면 `.env.example` 과 `.env` 가
  갈려 `doctor` 가 다른 기계에서 FAIL 한다. 끌 이유가 생기면 그때 연다.
"""
import logging
import sys

log = logging.getLogger("thoth")
log.setLevel(logging.INFO)
if not log.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    log.addHandler(_h)
log.propagate = False
