"""pairs_errors 의 판정. **셈이 비면 통과로 읽힌다**(DECISIONS §99)."""
import importlib.util
import json
import pathlib

_spec = importlib.util.spec_from_file_location(
    "pairs_errors", pathlib.Path(__file__).resolve().parents[2] / "tools/pairs_errors.py")
pe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pe)


def rec(raw: str) -> str:
    return json.dumps({"lastErrorCode": "DataFormatConversion.MalformedData", "rawData": raw})


def test_2026_09_16_실물이_제어_메시지다():
    # 필터 생성 직후 떨어진 객체의 모양 그대로다.
    obj = ('{"attemptsMade":1,"arrivalTimestamp":1789560304000,'
           '"lastErrorCode":"DataFormatConversion.MalformedData",'
           '"lastErrorMessage":"The record was empty or contained only whitespace.",'
           '"rawData":"","sequenceNumber":"4967"}')
    assert pe.classify(obj) == {"ctrl": 1, "real": 0, "unparsed": 0}


def test_쌍이_든_오류는_진짜다():
    assert pe.classify(rec("eyJrIjoicGFpciJ9"))["real"] == 1


def test_줄바꿈_없이_이어_붙은_레코드도_센다():
    assert pe.classify(rec("") + rec("eA==") + rec("")) == {"ctrl": 2, "real": 1, "unparsed": 0}


def test_못_읽은_줄은_0_이_아니라_따로_센다():
    c = pe.classify(rec("") + "\n깨진 줄\n" + rec(""))
    assert c == {"ctrl": 2, "real": 0, "unparsed": 1}


def test_빈_입력은_전부_0_이다():
    assert pe.classify("") == {"ctrl": 0, "real": 0, "unparsed": 0}
