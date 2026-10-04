"""Lambda zip 이 코드가 읽는 것을 전부 담는가 — `tools/lib/pkg.py` 의 족 가드.

★ **위치 무늬로 담고 있었다**(DECISIONS §145). 패키저는 `app/glossary/*.json` 만
  담았는데 코드는 `Path(__file__).parent / "<이름>.json"` 으로 **제 옆**에서 읽는다.
  `restore.json`(§139)과 `particle.json`(§143)이 **저장소에는 있고 zip 에는 없었다** —
  배포하면 그 자리에서 FileNotFoundError 다.

★ **묻는 것은 「이 파일이 담겼나」 가 아니라 「코드가 읽는데 안 담긴 것이 있나」** 다.
  목록이 아니라 **코드가 선언한 경로**에서 도출하므로, 새 데이터 파일이 `.json` 이
  아니어도 걸린다 — `rglob("*.json")` 으로 세는 가드는 **제가 담은 것을 제가 세어**
  영원히 안 운다(그 판을 한 번 썼다가 지웠다).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "lib"))
import pkg

ROOT = Path(__file__).resolve().parents[2]


def 가짜저장소(tmp: Path, 파일들: dict[str, str]) -> Path:
    app = tmp / "worker" / "app"
    for 이름, 내용 in 파일들.items():
        f = app / 이름
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(내용, encoding="utf-8")
    return tmp


# ── 지금 저장소 ─────────────────────────────────────────────────────────

def test_지금_저장소가_조용하다():
    assert pkg.missing(ROOT) == []


def test_코드가_읽는_자리를_전부_찾는다():
    찾은것 = {p.name for p in pkg.data_refs(ROOT)}
    assert {"glossary", "restore.json", "particle.json"} <= 찾은것, 찾은것


def test_담는_목록에_세_json_이_다_있다():
    담긴것 = {name for _, name in pkg.files(ROOT)}
    for x in ("app/glossary/aws.json", "app/restore.json", "app/particle.json"):
        assert x in 담긴것, f"{x} 가 zip 목록에 없다"


def test_뺄_것은_빼고_담는다():
    담긴것 = {name for _, name in pkg.files(ROOT)}
    for x in pkg.EXCLUDE:
        assert f"app/{x}" not in 담긴것
    assert "app/engine.py" in 담긴것


def test_하위_폴더_파일은_상대_경로로_담긴다(tmp_path):
    # ★ **지금 저장소로는 이 계약을 못 잰다** — `app/` 밑에 하위 폴더 `.py` 가 없어서
    #   이름만으로 담아도 결과가 같다. 그래서 가짜 나무로 잰다(돌연변이가 찾은 자리).
    root = 가짜저장소(tmp_path, {"engine.py": "x = 1\n", "어댑터/engine.py": "y = 2\n"})
    담긴것 = sorted(name for _, name in pkg.files(root))
    assert 담긴것 == ["app/engine.py", "app/어댑터/engine.py"], 담긴것


def test_상대_경로를_그대로_담는다():
    # ★ 처음 판은 `app/glossary/{f.name}` 으로 **이름만** 담았다. 하위 폴더가
    #   생기면 **다른 파일이 같은 이름으로 덮인다.**
    담긴것 = [name for _, name in pkg.files(ROOT)]
    assert len(담긴것) == len(set(담긴것)), "zip 안 이름이 겹친다"


# ── 무는가 ──────────────────────────────────────────────────────────────

def test_json_이_아닌_데이터_파일을_문다(tmp_path):
    # ★ **이것이 `rglob("*.json")` 가드가 못 잡는 자리다.**
    root = 가짜저장소(tmp_path, {
        "engine.py": 'import pathlib\nT = pathlib.Path(__file__).parent / "표.csv"\n',
        "표.csv": "a,b\n",
    })
    난것 = pkg.missing(root)
    assert any("표.csv" in x and "안 담긴다" in x for x in 난것), 난것


def test_담기지_않는_폴더를_문다(tmp_path):
    root = 가짜저장소(tmp_path, {
        "engine.py": 'import pathlib\nD = pathlib.Path(__file__).parent / "자료"\n',
        "자료/하나.txt": "x",
    })
    assert any("자료/하나.txt" in x for x in pkg.missing(root))


def test_폴더는_그_밑을_전부_요구한다(tmp_path):
    # ★ 통째로 훑는 자리는 **하나만 담겨도 조용히 반쪽**이 된다.
    root = 가짜저장소(tmp_path, {
        "glossary.py": 'import pathlib\nD = pathlib.Path(__file__).parent / "glossary"\n',
        "glossary/aws.json": "{}",
        "glossary/안담김.txt": "x",
    })
    난것 = pkg.missing(root)
    assert any("안담김.txt" in x for x in 난것)
    assert not any("aws.json" in x for x in 난것), "담기는 것까지 울면 음성 대조가 없다"


def test_없는_파일을_읽겠다면_문다(tmp_path):
    root = 가짜저장소(tmp_path, {
        "engine.py": 'import pathlib\nT = pathlib.Path(__file__).parent / "없다.json"\n',
    })
    assert any("저장소에 없다" in x for x in pkg.missing(root))


def test_resolve_가_끼어도_찾는다(tmp_path):
    # ★ 실제 코드가 두 꼴을 다 쓴다 — `glossary.py` 는 `.resolve().parent` 다.
    root = 가짜저장소(tmp_path, {
        "a.py": 'import pathlib\nT = pathlib.Path(__file__).resolve().parent / "없다.json"\n',
    })
    assert any("없다.json" in x for x in pkg.missing(root))


# ── 안 무는가 (음성 대조) ────────────────────────────────────────────────

def test_담기는_json_은_안_문다(tmp_path):
    root = 가짜저장소(tmp_path, {
        "engine.py": 'import pathlib\nT = pathlib.Path(__file__).parent / "표.json"\n',
        "표.json": "{}",
    })
    assert pkg.missing(root) == []


def test_읽는_자리가_없으면_조용하다(tmp_path):
    root = 가짜저장소(tmp_path, {"engine.py": "x = 1\n"})
    assert pkg.missing(root) == []


@pytest.mark.parametrize("무늬", ['Path(__file__).parent / "x.json"',
                                 'Path(__file__).resolve().parent / "x.json"'])
def test_두_꼴_다_읽는다(무늬, tmp_path):
    root = 가짜저장소(tmp_path, {"a.py": f"import pathlib\nT = pathlib.{무늬}\n"})
    assert [p.name for p in pkg.data_refs(root)] == ["x.json"]
