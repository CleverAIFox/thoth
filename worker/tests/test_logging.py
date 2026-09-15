"""로그가 실제로 나가는지 본다.

★ **검사가 레벨을 올려 놓고 재면 배선을 재지 않는다.** `caplog.set_level` 은
  로거의 레벨을 바꾸고 자기 핸들러를 건다. 그러면 배선이 없어도 통과한다 —
  2026-09-15 에 그렇게 통과한 검사 둘이 `usage` 계기가 한 줄도 안 나가는 것을
  못 봤다(§79). 여기서는 **레벨도 핸들러도 건드리지 않고** 패키지가 놓은
  핸들러의 스트림만 바꿔 읽는다.
"""
import io
import logging
import os

os.environ["ENGINE"] = "echo"
os.environ["CACHE"] = "memory"

from app import engine  # noqa: E402  (환경 지정이 import 보다 먼저다)

log = logging.getLogger("thoth")


def capture(monkeypatch) -> io.StringIO:
    """패키지가 놓은 핸들러의 출구만 가로챈다. 레벨과 핸들러는 그대로 둔다."""
    buf = io.StringIO()
    monkeypatch.setattr(log.handlers[0], "stream", buf)
    return buf


def test_thoth_로거에_핸들러가_있다():
    # 없으면 파이썬이 lastResort 로 떨어지고 그것은 WARNING 이상만 흘린다.
    assert log.handlers
    assert logging.lastResort.level == logging.WARNING   # 그 문턱이 원인이었다


def test_info_가_상위로_새지_않는다():
    # 상위 핸들러는 uvicorn 이나 Lambda 런타임의 것이고 레벨을 우리가 정하지 못한다.
    assert log.propagate is False


def test_info_가_실제로_스트림까지_간다(monkeypatch):
    buf = capture(monkeypatch)
    log.info("도달했다")
    assert "도달했다" in buf.getvalue()


def test_usage_줄이_실제로_나간다(monkeypatch):
    # ★ 이 검사가 §79 의 재발을 막는 자리다. 계기가 찍히지 않으면 비용을
    #   못 재고, 못 잰 자리에 결과를 적게 된다.
    class C:
        def converse(self, **kw):
            return {"output": {"message": {"content": [{"text": "번역"}]}},
                    "usage": {"inputTokens": 11, "outputTokens": 22},
                    "metrics": {"latencyMs": 33}}

    monkeypatch.setattr(engine, "_bedrock_client", lambda: C())
    buf = capture(monkeypatch)
    engine._converse("A shard stores records.", "SYSTEM")
    out = buf.getvalue()
    assert "usage {" in out
    assert '"in_tok":11' in out
