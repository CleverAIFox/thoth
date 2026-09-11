"""월 누적 문자 상한.

★ 카운터를 프로세스 메모리에 두면 안 된다. Lambda 는 콜드스타트마다 프로세스가
  새로 뜨므로 전역 변수는 0 으로 리셋되고, 동시 실행 시 인스턴스마다 따로 센다.
  즉 상한이 사실상 걸리지 않는다. 카운터는 DynamoDB 에 두고 원자적으로 올린다.

★ 번역 '전에' 예약한다. 호출 뒤에 올리면 그 사이에 들어온 동시 요청이 같은
  잔여를 보고 둘 다 통과한다. 예약 후 번역이 실패하면 약간 과다 계상되지만,
  과소 계상보다 안전한 방향이다.

★ Budgets 는 알림만 보내고 호출을 막지 않는다. 실제 차단은 여기서 한다.
★ 캐시 히트는 카운터를 올리지 않는다. 과금되지 않으므로.
"""
import os
from datetime import datetime, timedelta, timezone

MODE = os.environ.get("CACHE", "memory")
TABLE = os.environ.get("CACHE_TABLE", "thoth-translations")
MAX_CHARS = int(os.environ.get("MAX_CHARS_PER_MONTH", "2000000"))
MAX_TEXT = int(os.environ.get("MAX_TEXT_LEN", "5000"))

_mem: dict[str, int] = {}
_table = None


class QuotaExceeded(Exception):
    pass


class TooLong(Exception):
    pass


def _period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _key() -> str:
    return f"quota#{_period()}"


def _ddb():
    global _table
    if _table is None:
        import boto3
        _table = boto3.resource("dynamodb").Table(TABLE)
    return _table


def _expire_at() -> int:
    """다음 달 + 7일. TTL 로 지난 달 카운터가 저절로 사라진다."""
    now = datetime.now(timezone.utc)
    return int((now + timedelta(days=38)).timestamp())


def reserve(texts: list[str]) -> int:
    """번역할 문자 수를 미리 차감한다. 상한을 넘으면 QuotaExceeded."""
    for t in texts:
        if len(t) > MAX_TEXT:
            raise TooLong()

    n = sum(len(t) for t in texts)
    if n == 0:
        return 0
    if n > MAX_CHARS:
        raise QuotaExceeded()

    if MODE == "memory":
        cur = _mem.get(_key(), 0)
        if cur + n > MAX_CHARS:
            raise QuotaExceeded()
        _mem[_key()] = cur + n
        return n

    # 조건부 원자 증가. 잔여가 모자라면 DynamoDB 가 거절한다.
    from botocore.exceptions import ClientError

    try:
        _ddb().update_item(
            Key={"h": _key()},
            UpdateExpression="ADD chars :n SET expires_at = :e",
            ConditionExpression="attribute_not_exists(chars) OR chars <= :room",
            ExpressionAttributeValues={
                ":n": n,
                ":e": _expire_at(),
                ":room": MAX_CHARS - n,
            },
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise QuotaExceeded() from e
        raise
    return n


def used() -> int:
    if MODE == "memory":
        return _mem.get(_key(), 0)
    item = _ddb().get_item(Key={"h": _key()}).get("Item")
    return int(item["chars"]) if item else 0


def remaining() -> int:
    return max(0, MAX_CHARS - used())
