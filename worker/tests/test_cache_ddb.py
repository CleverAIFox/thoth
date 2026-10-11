"""`cache.py` 의 **DynamoDB 가지**(DECISIONS §181).

★ **이 가지에 시험이 하나도 없었다.** `test_contract` 가 `guard.REMOTE` 만 보고 있었고
  `get_many` · `put_many` 의 ddb 쪽은 **한 번도 안 돌아 봤다** — 캐시가 돈을 아끼는
  자리인데 **재는 자가 없는 자리**였다.

★ **그래서 못 보고 있던 것** : `while pending:` 이 **횟수도 사이도 없이** 돌았다.
  `PAY_PER_REQUEST` 에서는 조름이 드물어 안 드러나지만, 2026-10-11 에 테이블을
  `PROVISIONED` 25/25 로 내리면서 **조름이 정상 상태**가 됐다. Lambda 는 벽시계로
  과금되므로 제자리 회전은 **무료 몫을 아끼려고 다른 무료 몫을 태우는 짓**이다.

★ **boto3 없이 먹인다.** 자원 객체를 가짜로 끼운다 — 「부른 횟수」 와 「무엇을 보냈나」 가
  여기서 보려는 전부이고, 실제 DynamoDB 의 동작은 여기서 안 본다(그것은 밖이다).
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


def _켠다(monkeypatch, 가짜):
    """ddb 모드로 돌리고 자원을 가짜로 끼운다.

    ★ **`importlib.reload` 를 쓰지 않는다.** 모듈을 다시 읽으면 `MODE` 가 `ddb` 로
      **시험 뒤에도 남고**, `contract` 가 들고 있던 모듈 객체와도 갈린다. `monkeypatch`
      는 끝나면 되돌려 준다 — 「시험이 시험 밖을 더럽히지 않는다」.
    """
    from app import cache
    monkeypatch.setattr(cache, "MODE", "ddb")
    monkeypatch.setattr(cache, "TABLE", "T")
    monkeypatch.setattr(cache, "_resource", lambda: 가짜)
    monkeypatch.setattr(cache, "_사이두기", lambda 번: 잠깐.append(번))
    cache._mem.clear()
    return cache


잠깐: list[int] = []


class 읽는가짜:
    """`UnprocessedKeys` 를 `조름` 번 돌려주고 그 뒤에 내준다."""

    def __init__(self, 값: dict, 조름: int = 0):
        self.값, self.조름, self.부름 = 값, 조름, 0
        self.받은키들: list[list[str]] = []

    def batch_get_item(self, RequestItems):
        self.부름 += 1
        키들 = RequestItems["T"]["Keys"]
        self.받은키들.append([k["h"] for k in 키들])
        if self.조름 > 0:
            self.조름 -= 1
            # ★ 조르면 **아무것도 안 주고** 키를 그대로 돌려준다
            return {"Responses": {}, "UnprocessedKeys": RequestItems}
        된것 = [{"h": k["h"], "ko": self.값[k["h"]]} for k in 키들 if k["h"] in self.값]
        return {"Responses": {"T": 된것}}


class 쓰는가짜:
    def __init__(self, 조름: int = 0):
        self.조름, self.부름, self.받은것 = 조름, 0, []

    def batch_write_item(self, RequestItems):
        self.부름 += 1
        self.받은것.append(RequestItems["T"])
        if self.조름 > 0:
            self.조름 -= 1
            return {"UnprocessedItems": RequestItems}
        return {}


def setup_function(_f):
    잠깐.clear()


# ── 읽기 ────────────────────────────────────────────────────────────────

def test_조름_없이_읽는다(monkeypatch):
    가짜 = 읽는가짜({})
    cache = _켠다(monkeypatch, 가짜)
    가짜.값[cache.key("cat")] = "고양이"
    assert cache.get_many(["cat", "dog"]) == {"cat": "고양이"}
    assert 가짜.부름 == 1 and 잠깐 == []


def test_조르면_사이를_두고_다시_던진다(monkeypatch):
    """★ **사이를 둔다.** 25 RCU 는 초마다 다시 차므로 **기다리는 것이 답**이고,
    사이 없이 다시 던지는 것은 조름을 조름으로 갚는 것이다."""
    가짜 = 읽는가짜({}, 조름=2)
    cache = _켠다(monkeypatch, 가짜)
    가짜.값[cache.key("cat")] = "고양이"
    assert cache.get_many(["cat"]) == {"cat": "고양이"}
    assert 가짜.부름 == 3
    assert 잠깐 == [0, 1], "사이를 배로 늘리지 않는다"


def test_끝까지_조르면_빈손으로_끝낸다(monkeypatch):
    """★ **멈추지 않는다.** 캐시 미스는 재번역이고 멈춤은 요청 실패다 — 둘 다 나쁘지만
    **둘 중 하나는 돌아온다.** 180 전에는 여기서 영원히 돌았다."""
    가짜 = 읽는가짜({}, 조름=99)
    cache = _켠다(monkeypatch, 가짜)
    assert cache.get_many(["cat"]) == {}
    assert 가짜.부름 == cache.재시도 + 1, "횟수 상한을 안 지킨다"


def test_마지막_판_뒤에는_안_기다린다(monkeypatch):
    """★ 돌려주지도 않을 것을 기다리면 그 시간이 그대로 Lambda 과금이다."""
    가짜 = 읽는가짜({}, 조름=99)
    cache = _켠다(monkeypatch, 가짜)
    cache.get_many(["cat"])
    assert len(잠깐) == cache.재시도


def test_빈_입력은_아예_안_부른다(monkeypatch):
    가짜 = 읽는가짜({})
    cache = _켠다(monkeypatch, 가짜)
    assert cache.get_many([]) == {}
    assert 가짜.부름 == 0


def test_같은_원문은_한_번만_묻는다(monkeypatch):
    """캐시 열쇠가 sha256(원문)이라 중복은 저절로 합쳐진다 — 왕복이 줄어든다."""
    가짜 = 읽는가짜({})
    cache = _켠다(monkeypatch, 가짜)
    가짜.값[cache.key("cat")] = "고양이"
    assert cache.get_many(["cat", "cat", "cat"]) == {"cat": "고양이"}
    assert 가짜.부름 == 1 and 가짜.받은키들 == [[cache.key("cat")]]


def test_100_건씩_끊어_읽는다(monkeypatch):
    """`batch_get_item` 은 100건이 상한이다."""
    가짜 = 읽는가짜({})
    cache = _켠다(monkeypatch, 가짜)
    assert cache.get_many([f"t{i}" for i in range(250)]) == {}
    assert 가짜.부름 == 3


# ── 쓰기 ────────────────────────────────────────────────────────────────

def test_25_건씩_끊어_쓴다(monkeypatch):
    """★ **`batch_write_item` 은 25건이 상한이고 읽기(100)와 다르다.** 한 수로 묶어
    쓰면 26건째부터 조용히 거절된다."""
    가짜 = 쓰는가짜()
    cache = _켠다(monkeypatch, 가짜)
    cache.put_many({f"t{i}": f"ko{i}" for i in range(60)})
    assert 가짜.부름 == 3
    assert [len(x) for x in 가짜.받은것] == [25, 25, 10]


def test_같은_해시는_한_번만_쓴다(monkeypatch):
    """★ 같은 열쇠가 한 배치에 두 번 들어가면 DynamoDB 가 **요청째로** 거절한다 —
    `batch_writer(overwrite_by_pkeys=["h"])` 가 해 주던 일이다."""
    가짜 = 쓰는가짜()
    cache = _켠다(monkeypatch, 가짜)
    cache.put_many({"cat": "고양이", "cat ": "고양이"})     # 서로 다른 원문
    보낸것 = 가짜.받은것[0]
    해시들 = [x["PutRequest"]["Item"]["h"] for x in 보낸것]
    assert len(해시들) == len(set(해시들))


def test_쓰기도_조름을_묶는다(monkeypatch):
    """★ `batch_writer.__exit__` 가 `while self._items_buffer:` 로 **횟수도 사이도 없이**
    다시 던진다 — 그래서 그것을 안 쓰고 직접 돈다(DECISIONS §181)."""
    가짜 = 쓰는가짜(조름=99)
    cache = _켠다(monkeypatch, 가짜)
    cache.put_many({"cat": "고양이"})
    assert 가짜.부름 == cache.재시도 + 1
    assert len(잠깐) == cache.재시도


def test_조름이_풀리면_마친다(monkeypatch):
    가짜 = 쓰는가짜(조름=1)
    cache = _켠다(monkeypatch, 가짜)
    cache.put_many({"cat": "고양이"})
    assert 가짜.부름 == 2


def test_빈_쓰기는_아예_안_부른다(monkeypatch):
    가짜 = 쓰는가짜()
    cache = _켠다(monkeypatch, 가짜)
    cache.put_many({})
    assert 가짜.부름 == 0


# ── 배선 ────────────────────────────────────────────────────────────────

def test_batch_writer_로_돌아가지_않는다():
    """★ **이 시험이 상환을 붙들고 있다.** `batch_writer` 가 돌아오면 묶이지 않은
    되던지기도 같이 돌아온다.

    ★ **글로 찾지 않는다.** 첫 판은 `cache.py` 글자에서 `batch_writer` 를 찾았고
      **제 모듈 머리말이 그 이름을 적고 있어서** 걸렸다 — 「글을 코드로 읽는 검사는
      글부터 지운다」 집안의 열 번째다(§168 · §171 · §173 · §178 · §179 · §180).
      이번에는 글을 지우는 대신 **코드 객체에 묻는다** : `co_names` 는 그 함수가
      실제로 집는 속성 이름만 든다. 머리말도 주석도 거기엔 없다.
    ★ 묶였다는 것 자체는 글이 아니라 **동작**이 든다 — 위의 `부름 == 재시도 + 1` 둘.
    """
    from app import cache
    이름들 = set()
    for f in (cache.get_many, cache.put_many, cache._resource):
        이름들 |= set(f.__code__.co_names)
    assert "batch_writer" not in 이름들, "`batch_writer` 가 돌아왔다"
    assert "batch_write_item" in 이름들, "쓰기가 아예 안 돈다"


def test_사이를_배로_늘린다(monkeypatch):
    """★ **위 시험들은 `_사이두기` 를 통째로 갈아끼운다** — 그래서 그 몸이 한 번도 안
    돌았고, 돌연변이 `[캐시조름] 사이를 배로 안 늘린다` 가 살아남았다. 몸을 직접 돈다.
    ★ **배로 늘리는 까닭** : 조름이 안 풀리는데 같은 사이로 다섯 번 던지면 그 다섯 번이
      다 조름을 맞는다. 25 RCU 는 초마다 차므로 **기다리는 폭을 늘려야** 만난다."""
    from app import cache
    잔것: list[float] = []
    monkeypatch.setattr(cache.time, "sleep", 잔것.append)
    for 번 in range(4):
        cache._사이두기(번)
    assert 잔것 == [cache.사이 * 1, cache.사이 * 2, cache.사이 * 4, cache.사이 * 8]


def test_재시도가_선언돼_있다():
    """상한과 사이가 **수로 적혀** 있어야 한다 — 글로만 적히면 아무 일도 안 한다."""
    from app import cache
    assert cache.재시도 >= 1 and cache.사이 > 0
    assert cache.쓰기묶음 == 25 and cache.BATCH == 100
