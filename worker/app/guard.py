"""월 누적 문자 상한.

★ 카운터를 프로세스 메모리에 두면 안 된다. Lambda 는 콜드스타트마다 프로세스가
  새로 뜨므로 전역 변수는 0 으로 리셋되고, 동시 실행 시 인스턴스마다 따로 센다.
  즉 상한이 사실상 걸리지 않는다. 카운터는 DynamoDB 에 두고 원자적으로 올린다.

★ 번역 '전에' 예약한다. 호출 뒤에 올리면 그 사이에 들어온 동시 요청이 같은
  잔여를 보고 둘 다 통과한다. 예약 후 번역이 실패하면 약간 과다 계상되지만,
  과소 계상보다 안전한 방향이다.

★ 백엔드 판정을 CACHE 값에 그대로 얹지 않는다. CACHE 는 memory · file · ddb
  세 값인데 'memory 가 아니면 DynamoDB' 로 분기하면 CACHE=file 에서 카운터만
  AWS 로 나간다(DECISIONS §10). 원격은 ddb 하나뿐이고 나머지는 로컬이다.

★ file 모드는 카운터도 파일에 남긴다. 메모리에 두면 워커를 재시작할 때마다
  월 사용량이 0 이 되어 상한이 무의미해진다. 캐시와 같은 이유다(DECISIONS §5).

★ Budgets 는 알림만 보내고 호출을 막지 않는다. 실제 차단은 여기서 한다.
★ 캐시 히트는 카운터를 올리지 않는다. 과금되지 않으므로.
"""
import json
import os
import pathlib
from datetime import datetime, timedelta, timezone

MODE = os.environ.get("CACHE", "memory")
REMOTE = MODE == "ddb"
TABLE = os.environ.get("CACHE_TABLE", "thoth-translations")
MAX_CHARS = int(os.environ.get("MAX_CHARS_PER_MONTH", "2000000"))
MAX_TEXT = int(os.environ.get("MAX_TEXT_LEN", "5000"))
FILE = pathlib.Path(os.environ.get("QUOTA_FILE", ".cache/quota.json"))

_mem: dict[str, int] = {}
_loaded = False
_table = None


class QuotaExceeded(Exception):
    pass


class TooLong(Exception):
    pass


class GuardUnavailable(Exception):
    """카운터 저장소에 닿지 못했다. 세지 못하면 번역하지 않는다."""


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


def _local_load() -> dict[str, int]:
    global _loaded
    if MODE == "file" and not _loaded:
        _loaded = True
        if FILE.exists():
            try:
                _mem.update(json.loads(FILE.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass   # 깨진 카운터는 0 으로 본다. 과다 계상보다 과소가 낫진 않으나
                       # 여기서 죽으면 번역 자체가 멈춘다
    return _mem


def _local_save() -> None:
    if MODE != "file":
        return
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(_mem), encoding="utf-8")
    tmp.replace(FILE)      # 원자적 교체. 중간에 죽어도 반쪽 파일이 남지 않는다


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

    if not REMOTE:
        m = _local_load()
        cur = m.get(_key(), 0)
        if cur + n > MAX_CHARS:
            raise QuotaExceeded()
        m[_key()] = cur + n
        _local_save()
        return n

    # 조건부 원자 증가. 잔여가 모자라면 DynamoDB 가 거절한다.
    from botocore.exceptions import BotoCoreError, ClientError

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
        raise GuardUnavailable(type(e).__name__) from e
    except BotoCoreError as e:
        # 자격증명 없음 · 엔드포인트 불통 등. 세지 못하는 상태로 번역하면
        # 상한이 없는 것과 같다. 열어주지 않고 닫는다.
        raise GuardUnavailable(type(e).__name__) from e
    return n


def used() -> int:
    if not REMOTE:
        return _local_load().get(_key(), 0)
    from botocore.exceptions import BotoCoreError, ClientError

    try:
        item = _ddb().get_item(Key={"h": _key()}).get("Item")
    except (BotoCoreError, ClientError) as e:
        raise GuardUnavailable(type(e).__name__) from e
    return int(item["chars"]) if item else 0


def remaining() -> int:
    return max(0, MAX_CHARS - used())
