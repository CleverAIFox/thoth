"""월 누적 문자 상한. Budgets 는 알림만 하고 호출을 막지 않는다(PLAN §2-3).
캐시 히트는 카운터를 올리지 않는다 — 과금되지 않으므로.
"""
import os

MAX_CHARS = int(os.environ.get("MAX_CHARS_PER_RUN", "2000000"))
MAX_TEXT = int(os.environ.get("MAX_TEXT_LEN", "5000"))
_used = 0


class QuotaExceeded(Exception):
    pass


class TooLong(Exception):
    pass


def check_and_add(texts: list[str]) -> int:
    global _used
    for t in texts:
        if len(t) > MAX_TEXT:
            raise TooLong()
    n = sum(len(t) for t in texts)
    if _used + n > MAX_CHARS:
        raise QuotaExceeded()
    _used += n
    return n


def used() -> int:
    return _used
