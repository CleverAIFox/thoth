"""Lambda zip 에 무엇이 담기나 — **한 곳이 센다**.

★ **담는 쪽과 재는 쪽이 갈리면 둘 다 초록이면서 틀린다**(DECISIONS §132 · §133 과
  같은 자리). `package_lambda.sh` 가 목록을 들고 `doctor` 가 따로 들면 언젠가
  갈린다. 여기 하나만 둔다.

★ **위치 무늬로 담지 않는다**(DECISIONS §145). 처음엔 `app/glossary/*.json` 만 담았는데
  코드는 `pathlib.Path(__file__).parent / "<이름>.json"` 으로 **제 옆**에서 읽는다.
  `restore.json`(§139)과 `particle.json`(§143)이 **저장소에는 있고 zip 에는 없었다.**

★ **그래서 묻는 것은 「이 파일이 담겼나」 가 아니라 「코드가 읽는데 안 담긴 것이
  있나」 다**(족 가드). 목록이 아니라 **코드가 선언한 경로**에서 도출하므로, 새 데이터
  파일이 `.json` 이 아니어도(`.csv`·`.txt`) 걸린다 — `rglob("*.json")` 은 못 잡는다.
"""
import pathlib
import re

# 패키지에서 빼는 것. `main.py` 는 FastAPI 를 최상위에서 부르고 `preflight.py` 는 개발 도구다.
EXCLUDE = {"main.py", "preflight.py"}

# `pathlib.Path(__file__)[.resolve()].parent / "이름"` — 코드가 제 옆에서 읽는 자리.
_옆 = re.compile(r'Path\(__file__\)(?:\.resolve\(\))?\.parent\s*/\s*"([^"]+)"')


def app_dir(root: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(root) / "worker" / "app"


def files(root: pathlib.Path) -> list[tuple[pathlib.Path, str]]:
    """zip 에 담을 (실파일, zip 안 이름) 목록. 이름은 `app/` 아래 상대 경로 그대로다."""
    app = app_dir(root)
    out: list[tuple[pathlib.Path, str]] = []
    for f in sorted(app.rglob("*.py")):
        if f.name in EXCLUDE:
            continue
        out.append((f, f"app/{f.relative_to(app).as_posix()}"))
    for f in sorted(app.rglob("*.json")):
        out.append((f, f"app/{f.relative_to(app).as_posix()}"))
    return out


def data_refs(root: pathlib.Path) -> list[pathlib.Path]:
    """코드가 **제 옆에서 읽겠다고 적은** 경로. 파일일 수도 디렉터리일 수도 있다."""
    app = app_dir(root)
    out: set[pathlib.Path] = set()
    for py in sorted(app.rglob("*.py")):
        for 이름 in _옆.findall(py.read_text(encoding="utf-8")):
            out.add(py.parent / 이름)
    return sorted(out)


def missing(root: pathlib.Path) -> list[str]:
    """코드가 읽는데 zip 에 안 담기는 것. 빈 리스트가 통과다.

    ★ 참조가 디렉터리면 **그 밑의 모든 파일**을 요구한다 — 용어집처럼 통째로 훑는
      자리는 하나만 담겨도 조용히 반쪽이 된다.
    """
    app, 담긴것 = app_dir(root), {name for _, name in files(root)}
    난것: list[str] = []
    for ref in data_refs(root):
        if not ref.exists():
            난것.append(f"{ref.relative_to(app)}: 코드가 읽겠다는데 저장소에 없다")
            continue
        실물 = sorted(ref.rglob("*")) if ref.is_dir() else [ref]
        for f in 실물:
            if not f.is_file():
                continue
            name = f"app/{f.relative_to(app).as_posix()}"
            if name not in 담긴것:
                난것.append(f"{name}: 코드가 읽는데 zip 에 안 담긴다")
    return 난것
