"""번역 캐시. 키는 sha256(text) — 사이트를 섞지 않는다(PLAN §2-3).

CACHE=memory  로컬 개발
CACHE=ddb     DynamoDB
"""
import hashlib
import os

MODE = os.environ.get("CACHE", "memory")
TABLE = os.environ.get("CACHE_TABLE", "st-translations")
_mem: dict[str, str] = {}
_table = None


def key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ddb():
    global _table
    if _table is None:
        import boto3
        _table = boto3.resource("dynamodb").Table(TABLE)
    return _table


def get_many(texts: list[str]) -> dict[str, str]:
    if MODE == "memory":
        return {t: _mem[key(t)] for t in texts if key(t) in _mem}
    hits = {}
    for t in texts:
        r = _ddb().get_item(Key={"h": key(t)}).get("Item")
        if r:
            hits[t] = r["ko"]
    return hits


def put_many(pairs: dict[str, str]) -> None:
    if MODE == "memory":
        _mem.update({key(k): v for k, v in pairs.items()})
        return
    with _ddb().batch_writer() as b:
        for k, v in pairs.items():
            b.put_item(Item={"h": key(k), "ko": v})
