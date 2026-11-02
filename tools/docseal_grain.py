# ★ **세샤트의 `tools/docseal_grain.py` 에서 왔다. 정본은 세샤트다**(seshat DECISIONS §330 · §335).
#   고칠 것이 있으면 거기서 고치고 다시 옮긴다. 갈린 자리는 **하나**다 — 글 속 `DECISIONS §N` 앞에
#   `seshat` 를 달았다(이 저장소의 같은 번호와 충돌한다). 나머지는 글자까지 같다. 아래 `§N` 은 세샤트의 절 번호다.
"""지문의 **입자** — 무엇을 같다고 보나(seshat DECISIONS §330).

`docseal` 은 **무엇을 무나**(`docseal_refs`), **어떻게 무나**(`docseal`) 외에 **얼마나 굵게 무나**를
따로 든다. 해시 · 마이너 · 패치는 봇이 주마다 바꾸는 값이고 절의 주장이 아니다.

★ **밖 — 지문을 엮지 않는다.** 글을 접어 돌려줄 뿐이다. 이 파일도 `docseal` 을 안 들여온다(순환).
"""
from __future__ import annotations

import json
import re
import sys

# ★ **`uses:` 는 「누구의 어느 메이저」 까지만 문다**(seshat DECISIONS §330). 지문이 문 것은 **절이 주장하는
#   구조**다 — 어느 액션을 쓰나, 어느 메이저인가. 40자 해시와 마이너 · 패치는 **Dependabot 이
#   주마다 바꾸는 값**이고 절의 주장이 아니다. 2026-11-01 액션 bump 하나가 워크플로 파일만 만지고
#   도장 여덟을 깼다 — 코드의 뜻도 절도 안 바뀌었는데.
# ★ **SHA 고정 자체는 여기서 안 본다.** `tests/test_workflows.py::test_액션을_SHA_로_고정한다` 가
#   본다. 같은 수를 두 곳에 적으면 한쪽만 늙는다(§57 · §91) — 도장은 구조만 든다.
# ★ **소유자 · 저장소는 남긴다**(`actions/checkout` → `evil/checkout` 은 깨져야 한다). **메이저도
#   남긴다**(`v7` → `v8` 은 절을 실제로 깰 수 있다).
# ★ **판본 주석 없는 SHA 는 안 건드린다** — 메이저를 못 읽는다. 해시째 문다(넓은 쪽이 안전하다).
#   그런 줄이 있는지는 위 시험이 따로 운다.
_uses줄 = re.compile(r"^(?P<앞>\s*(?:-\s+)?uses:\s*)(?P<따옴>['\"]?)(?P<이름>[^\s'\"#@]+)@(?P<가리킴>[^\s'\"#]+)(?P=따옴)"
                    r"(?P<뒤>\s*#\s*(?P<주석>.*))?\s*$")
_해시40 = re.compile(r"[0-9a-f]{40}")
_판본 = re.compile(r"v?(\d+)(?:\.\d+)*(?:[-+].*)?")


def _uses_입자(글: str) -> str:
    """워크플로의 `uses: 이름@해시  # vX.Y.Z` / `이름@vX.Y.Z` 를 `이름@vX` 로 접는다."""
    out = []
    for 줄 in 글.splitlines():
        m = _uses줄.match(줄)
        if m is None or m["이름"].startswith(("./", "docker://")):
            out.append(줄)
            continue
        if _해시40.fullmatch(m["가리킴"]):
            본 = _판본.match((m["주석"] or "").strip())
        else:
            본 = _판본.fullmatch(m["가리킴"])
        out.append(f'{m["앞"]}{m["이름"]}@v{본.group(1)}' if 본 else 줄)
    return "\n".join(out)


#: **기계가 쓰는 잠금 파일은 봉인 대상이 될 수 없다**(seshat DECISIONS §330). 사람이 거기 주장을 안 적고,
#: 의존성 봇이 돌 때마다 바뀐다. 판본은 `lock` 걸음과 `npm ci` 와 Dependabot 이 본다.
#: ★ **이 목록을 비우면 `_canary` 가 운다** — 목록 자체가 돌연변이로 물린다.
잠금이름 = frozenset({"package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock",
                    "uv.lock", "poetry.lock", "Pipfile.lock", "Cargo.lock", "composer.lock",
                    "Gemfile.lock", "go.sum"})


def _잠금을_든_곳(줄: str, 지목: re.Pattern) -> list[str]:
    """강제자 · 봉인 줄이 짚은 자리 중 잠금 파일."""
    return [곳 for 곳, _ in 지목.findall(줄) if 곳.rsplit("/", 1)[-1] in 잠금이름]


def 잠금이면_죽는다(줄: str, 지목: re.Pattern, 표시: str) -> None:
    """잠금 파일을 강제자로 들면 **도구 고장(rc 2)** 으로 죽는다. 기계가 쓰고 봇이 바꾸는 파일이다."""
    잠금 = _잠금을_든_곳(줄, 지목)
    if 잠금:
        print(f"    ★ 도구 고장 — {표시} 가 잠금 파일을 강제자로 든다 : {잠금}\n"
              f"      잠금 파일은 기계가 쓰고 봇이 바꾼다. 매니페스트(`package.json` · "
              f"`pyproject.toml`)를 든다 (seshat DECISIONS §330)", file=sys.stderr)
        sys.exit(2)


#: 의존성 칸 — 판본 **범위**는 봇이 바꾸고(`^30.1.1` → `^30.1.3`) 이름은 사람이 정한다.
_의존칸 = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")


def _package_json_입자(글: str) -> str:
    """`package.json` 의 의존성은 **이름만** 문다. 범위 숫자는 접는다(seshat DECISIONS §335).

    ★ 2026-11-02 Dependabot PR #7 이 잠금뿐 아니라 `package.json` 의 `jsdom` 범위도 올렸다 — 통째로 물면
      잠금을 봉인 밖으로 뺀 보람이 없다. 키를 지우거나 더하면 지문이 갈린다(이름은 주장이다).
    ★ 못 읽으면(JSON 이 아니면) 글자 그대로 돌려준다 — 넓게 두는 쪽이 안전하다.
    """
    try:
        데이터 = json.loads(글)
    except ValueError:
        return 글
    if not isinstance(데이터, dict):
        return 글
    for 칸 in _의존칸:
        if isinstance(데이터.get(칸), dict):
            데이터[칸] = {이름: "" for 이름 in 데이터[칸]}
    return json.dumps(데이터, ensure_ascii=False, sort_keys=True)


def 접는다(글: str, 이름: str) -> str:
    """파일 이름에 맞는 입자로 접는다 — 워크플로(`.yml` · `.yaml`)는 `uses:`, `package.json` 은 의존 범위.
    다른 꼴은 그대로."""
    if 이름.endswith((".yml", ".yaml")):
        return _uses_입자(글)
    return _package_json_입자(글) if 이름 == "package.json" else 글


def _canary(지목: re.Pattern) -> None:
    # ★ **입자 — 해시와 마이너는 안 문다 · 소유자와 메이저는 문다**(seshat DECISIONS §330). 부정 단언만으로는
    #   「조용히 전부 지우는」 쪽을 못 잡는다 — 지우면 `a == a` 가 되어 첫째 물음이 거짓 초록이 된다.
    #   그래서 **긍정으로 셋을 더 묻는다**(소유자 · 메이저 · 줄 삭제).
    _줄 = "      - uses: actions/checkout@" + "a" * 40 + "  # v7.0.1\n"
    if _uses_입자(_줄) != _uses_입자(_줄.replace("a" * 40, "b" * 40).replace("v7.0.1", "v7.2.0")):
        print("    ★ 카나리아가 죽었다 — 해시 · 마이너만 바뀌었는데 지문이 갈린다(봇 PR 마다 도장이 깨진다)")
        sys.exit(2)
    if _uses_입자(_줄) == _uses_입자(_줄.replace("actions/", "evil/")):
        print("    ★ 카나리아가 죽었다 — 소유자가 바뀌었는데 지문이 같다")
        sys.exit(2)
    if _uses_입자(_줄) == _uses_입자(_줄.replace("v7.0.1", "v8.0.0")):
        print("    ★ 카나리아가 죽었다 — 메이저가 바뀌었는데 지문이 같다")
        sys.exit(2)
    if _uses_입자(_줄 + _줄) == _uses_입자(_줄):
        print("    ★ 카나리아가 죽었다 — `uses:` 줄이 하나 사라졌는데 지문이 같다(조용히 전부 지운다)")
        sys.exit(2)
    # ★ **`package.json` 은 이름은 문다 · 범위는 접는다**(seshat DECISIONS §335).
    _pj = '{"devDependencies": {"jsdom": "^30.1.1", "x": "^1"}, "scripts": {"test": "a"}}'
    if _package_json_입자(_pj) != _package_json_입자(_pj.replace("^30.1.1", "^30.1.3")):
        print("    ★ 카나리아가 죽었다 — 범위만 바뀌었는데 package.json 지문이 갈린다(봇 PR 마다 도장이 깨진다)")
        sys.exit(2)
    if _package_json_입자(_pj) == _package_json_입자(_pj.replace('"x": "^1"', '"y": "^1"')):
        print("    ★ 카나리아가 죽었다 — 의존성 이름이 바뀌었는데 package.json 지문이 같다")
        sys.exit(2)
    if _package_json_입자(_pj) == _package_json_입자(_pj.replace('"a"', '"b"')):
        print("    ★ 카나리아가 죽었다 — 스크립트가 바뀌었는데 package.json 지문이 같다(조용히 다 접는다)")
        sys.exit(2)
    # ★ **잠금 파일은 봉인 밖이다**(seshat DECISIONS §330). 목록이 비면 아래가 울어야 한다.
    if not _잠금을_든_곳("강제자 — `extension/package-lock.json` · `tools/x.py`", 지목) or \
            _잠금을_든_곳("강제자 — `extension/package.json`", 지목):
        print("    ★ 카나리아가 죽었다 — 잠금 파일을 못 가리거나 매니페스트를 잠금으로 읽는다")
        sys.exit(2)
