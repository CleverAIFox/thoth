# ★ **세샤트의 `tools/docseal.py` 에서 왔다. 정본은 세샤트다**(DECISIONS §163).
#   고칠 것이 있으면 거기서 고치고 다시 옮긴다. 이 저장소에서 갈린 자리는 셋뿐이다 —
#   **셋을 여기 적는다**(세샤트 §296 — 「사본이다」 만 적어 두면 다음 사람이 통째로 덮는다).
#     · 도장 파일이 `tools/docseal.json` 이다. 세샤트는 `data/docseal.json` — 이쪽에
#       `data/` 가 없고, 선언 자료는 `tools/mutations.json` 처럼 자 옆에 산다
#     · 강제자가 `tools/doctor.sh` 다. 세샤트는 `tools/verify.sh`
#     · 아래 `★` 들의 `§N` 은 **세샤트의 절 번호**다. 이쪽에서 그 번호는 딴 절이다
#   ★ **MASTER 축의 봉인 열셋은 이 저장소가 §163 에서 박았다.** 기계는 사본이고 **글은
#     이쪽 것**이다 — `docs/MASTER.md` 의 `봉인 — ` 줄을 본다.
"""문서 절과 **그 절이 강제자로 지목한 코드**에 정합 도장을 찍는다(DECISIONS §211).

  python3 tools/docseal.py                 무효가 된 도장을 낸다(rc 1) ← 기본
  python3 tools/docseal.py status          유효 · 무효 · 미날인이 몇인가
  python3 tools/docseal.py audit           **날인 전 감사** — git 이 아는 「절 뒤에 바뀐 파일」
  python3 tools/docseal.py stamp           지금 상태로 전부 찍는다(**읽었다는 뜻이 아니다**)
  python3 tools/docseal.py stamp --only 209 --read   **읽고 나서** 찍는다 — 감사에서 빠진다

★ **파이어레인 `tools/docseal.py` 의 축을 옮긴 것이다**(파이어레인 DECISIONS §265). 거기가 적은
  진단이 이 저장소에도 그대로 맞는다 — **문서↔코드 강제자가 전부 한 방향**이다. `check_docs` 와
  `doc_fsck` 는 「문서가 가리킨 것이 **실재하는가**」 만 묻는다. **뜻이 낡은 것은 아무도 안 본다.**
★ 2026-09-29 하루에 그 증거가 둘 나왔다. §169 가 `_블록을_고친다` 의 「주석 자리」 를 고쳤고 그 뒤
  주석의 **뜻**이 거짓이 됐다(§208). §173 이 선 줄에 해시를 더했고 `set` 자리를 안 갈아 **선까지의
  차가 조용히 사라졌다**(§209). 둘 다 강제자 파일이 **그 절이 적힌 뒤에 바뀌었다** — 그것 하나만
  알았어도 사람이 다시 봤을 자리다.
★ **뜻이 옳은지는 이 도구가 모른다.** 아는 것은 「확인한 뒤로 바뀌었는가」 하나다. 무효는
  「틀렸다」 가 아니라 **「다시 봐야 한다」** 이고, 사람이 보고 `stamp` 로 다시 찍는다.
★ **자주 무효가 되는 것과 쓸모없는 것은 다르다.** 자주 흔들리는 절이 있다는 사실 자체가 정보다.

★ **이 머리말과 아래 주석의 `§N` 은 전부 세샤트의 절 번호다**(DECISIONS §163).
  이 저장소의 같은 번호를 가리키는 것이 **아니다** — 옮겨 온 글이라 그쪽 역사를 든다.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEAL = ROOT / "tools/docseal.json"
DEC = ROOT / "docs/DECISIONS.md"
#: 도장 파일의 저장소 상대 자리. **강제자로 들 수 없는 유일한 파일이다**(DECISIONS §300)
_도장자리 = SEAL.relative_to(ROOT).as_posix()

# (열쇠앞, 자리, 절머리, 앵커낱말, 표시) — **봉인이 두 문서를 본다**(DECISIONS §281).
#
# ★ **낡는 문서는 DECISIONS 가 아니라 MASTER 다.** DECISIONS 는 추가만 하니 구조상 안 낡는다.
#   MASTER 는 「현재」 축이라 **정의상 실물을 따라가야 하는 유일한 문서**인데 봉인이 안 걸려 있었다.
#   2026-10-02 소급해서 읽으니 아홉 자리가 낡아 있었고 **아홉 다 이 봉인으로 잡히는 꼴**이었다 —
#   라이선스 대장 · 온톨로지 수 · 관문 수 · 기록판 팔 · 백엔드 표 · 학습 원문 · 가설 판정 ·
#   `verify` 단계 · 머리줄 칸. 전부 「코드가 바뀌었는데 절이 안 바뀌었다」 다.
# ★ **열쇠앞이 다르다**(`M14` 대 `279`). 같은 번호 공간을 쓰면 옛 도장이 MASTER 절로 읽힌다.
# ★ **앵커 낱말이 다르다** — DECISIONS 는 `강제자`(이 절을 지키는 코드), MASTER 는 `봉인`(이 절이
#   서술하는 코드). 방향이 반대라 같은 말을 쓰면 안 된다.
# ★ **앵커를 뽑는 방식이 문서마다 다르다.** DECISIONS 는 「강제자」 가 절 끝에 한 번 나오므로
#   `rfind` 로 족하다 — **그 꼴을 바꾸면 찍어 둔 도장 열한 개가 전부 무효가 된다.** MASTER 는
#   본문에 「봉인」 이라는 낱말이 그냥 나올 수 있어(§11-10 이 그렇다) **줄 머리로 못 박는다.**
#   2026-10-02 `rfind` 로 두었더니 §11 이 거짓 양성으로 걸렸다.
_봉인줄 = re.compile(r"^봉인 — .*(?:\n[ \t]+.*)*", re.M)


# ★ **강제자 블록 정규식의 정본은 `tools/doc_fsck.py::ENFORCER_LINE` 하나다**(DECISIONS
#   §283 · §299). 처음에는 여기 제 손으로 적었고 `dupcheck` 가 **그 판에서** 잡았다 —
#   저쪽이 §159 에서 세운 것과 **글자까지 같았다.** 「줄 머리로 못 박는다」 는 규칙이
#   두 자에 걸려 있으므로 **규칙도 한 자리에 있어야 한다.**
# ★ **빌리는 꼴로 적는다 — 짓지 않는다.** `dupcheck` 는 「부름의 결과」 를 짓는 것으로 세고
#   `남.ATTR` 은 **남이 지은 물건에 이름만 붙인 것**으로 본다(§266). 함수로 감싸 돌려받으면
#   그 자가 **빌려 온 것까지 사본으로 센다** — 그리고 반환 꼴을 모르는 함수가 하나 늘어
#   `mutate` 의 **못 잴 자리**가 는다(§287 의 양방향 톱니).
_정본틀 = importlib.util.spec_from_file_location("doc_fsck", ROOT / "tools/doc_fsck.py")
_정본 = importlib.util.module_from_spec(_정본틀)
_정본틀.loader.exec_module(_정본)
_강제자줄 = _정본.ENFORCER_LINE


def _강제자_뒤(본문: str) -> str:
    """절의 강제자 블록. **마지막 블록**을 든다 — 한 절에 둘이면 뒤가 최신이다.

    ★ **종전에는 `rfind("강제자")` 였다**(DECISIONS §299). 그 낱말이 **시험 이름 안에**
      나오면(`test_지목확장이_사본의_강제자를_다_덮는다`) 창이 그 뒤부터 열려 **파일을
      하나도 못 집는다** — 그러면 그 절의 도장은 **아무것도 안 보며 영영 유효**하다.
      반대로 본문에 그 낱말이 먼저 나오면 창이 너무 넓어 **산문이 든 파일까지** 집었다.
      실측 : 314 절 중 **열다섯**이 틀렸고 그중 **여덟이 빈손**이었다.
    ★ MASTER 쪽(`_봉인_줄`)은 2026-10-02 에 이미 줄 머리로 못 박았다 — **같은 덫을
      한쪽에서만 피해 놓고 다른 쪽을 아흐레 뒀다.**
    """
    m = None
    for m in _강제자줄.finditer(본문):
        pass
    return m.group(0) if m else ""


def _봉인_줄(본문: str) -> str:
    m = _봉인줄.search(본문)
    return m.group(0) if m else ""


문서 = [
    ("", "docs/DECISIONS.md", re.compile(r"^## §(\d+)\. (.+)$", re.M), _강제자_뒤, "§"),
    ("M", "docs/MASTER.md", re.compile(r"^## (\d+)\. (.+)$", re.M), _봉인_줄, "MASTER §"),
]
절머리 = 문서[0][2]
날짜 = re.compile(r"\*\*(20\d\d-\d\d-\d\d)\*\*")
# 강제자 줄이 백틱으로 지목한 자리. `tools/gate.py::_선을_박는다` 의 앞쪽만 본다
#
# ★ **글로 읽는 산출물만 든다**(thoth DECISIONS §161 의 `글자아님`). `.docx` · `.png` 같은
#   것을 들면 지문이 **바이트**가 되고, 그러면 **구울 때마다 도장이 전부 찢어진다** —
#   `docs/proposal.docx` 는 토트에서 강제자가 실제로 한 번 든다.
# ★ **목록을 적어 둔다 — 정규식 안에 묻어 두지 않는다.** 이 자의 사본이 토트에 살고
#   (thoth §163) 거기 강제자는 `.js` 33 · `.json` 10 · `.tf` 6 · `.css` 1 을 든다.
#   목록이 좁으면 **그 줄들이 조용히 안 세어지고, 안 세어진 것은 안 낡는 것처럼 보인다.**
#   여기서 넓혀도 이 저장소의 도장은 **하나도 안 바뀐다**(재 봤다 — 새로 잡히는 자리 0).
# ★ `jsonl` · `json` 과 `yaml` · `yml` 은 **긴 것을 앞에** 둔다. 짧은 쪽이 먼저면
#   `.jsonl` 이 `.json` 으로 맞고 뒤의 `l` 에서 백틱을 못 닫는다.
지목확장 = ("jsonl", "json", "yaml", "yml", "toml", "py", "sh", "js", "md", "tf", "css")
지목 = re.compile(r"`([\w./-]+\.(?:%s))(?:::([^`\s]+))?`" % "|".join(지목확장))


def _짧게(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _몸을_찾는다(나무: ast.AST, 이름: str):
    """`파일::이름` 이 가리키는 함수 · 클래스. 없으면 None."""
    끝 = 이름.split(".")[-1].split("::")[-1]
    for n in ast.walk(나무):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == 끝:
            return n
    return None


def 로직_지문(p: pathlib.Path, 이름: str = "") -> str:
    """파일(또는 짚은 이름)의 **로직** 지문. 주석 · 독스트링을 뺀 **글자**로 잰다.

    ★ 바이트로 재면 **주석 한 줄에 도장이 전부 찢어진다.** 이 저장소는 주석이 절반이고 그것을
      고치는 것이 일과다 — 무효가 소음이 되면 안 읽힌다(파이어레인 `shardseal.logic_print`).
    ★ **`ast.dump` 로는 안 잰다**(DECISIONS §211). 그 글은 파이썬 판마다 다르다 — 2026-09-29
      `python3`(3.11)로 찍은 도장이 `uv run`(3.12)에서 전부 무효로 나왔다. **도장이 기계를 타면
      그것은 도장이 아니다.** 낱말만 남겨 세면 판이 달라도 같다.
    ★ 반대로 **`.md` · `.toml` 은 글자 그대로** 잰다 — 거기서는 글자가 곧 내용이다.
    """
    글 = p.read_text(encoding="utf-8")
    if p.suffix != ".py":
        return _짧게(글)
    나무: ast.AST = ast.parse(글)
    if 이름:
        # ★ **강제자가 이름을 짚으면 그 몸만 잰다**(DECISIONS §211). 파일로 재면 `check_docs.py` 를
        #   고칠 때마다 그 파일을 짚은 절 스무 개가 한꺼번에 무효가 된다
        몸 = _몸을_찾는다(나무, 이름)
        if 몸 is None:
            return "없다"            # 짚은 이름이 사라졌다 — 그 자체가 다시 볼 까닭이다
        조각 = ast.get_source_segment(글, 몸) or ""
        return _낱말지문(조각, 몸.lineno - 1)
    return _낱말지문(글, 0)


def _독스트링_줄(나무: ast.AST) -> set[int]:
    """독스트링이 차지한 줄 번호. **뜻이 아니라 설명이므로 지문에서 뺀다.**"""
    줄: set[int] = set()
    for n in ast.walk(나무):
        몸 = getattr(n, "body", None)
        if (isinstance(몸, list) and 몸 and isinstance(몸[0], ast.Expr)
                and isinstance(getattr(몸[0], "value", None), ast.Constant)
                and isinstance(몸[0].value.value, str)):
            줄 |= set(range(몸[0].lineno, (몸[0].end_lineno or 몸[0].lineno) + 1))
    return 줄


def _낱말지문(글: str, 밀림: int = 0) -> str:
    """주석과 독스트링을 뺀 **남은 글자**. 들여쓰기와 빈 줄은 안 센다.

    ★ **낱말로 쪼개지 않는다**(DECISIONS §211). 2026-09-29, 토큰으로 세니 3.11 과 3.12 가 갈렸다 —
      3.12 가 f-문자열을 여러 토큰으로 쪼갠다. 주석의 **자리**는 판을 안 타므로 그것만 지운다.
    """
    import io
    import tokenize
    try:
        뺄줄 = _독스트링_줄(ast.parse(글))
        주석 = [tok for tok in tokenize.generate_tokens(io.StringIO(글).readline)
                if tok.type == tokenize.COMMENT]
    except (SyntaxError, tokenize.TokenError, IndentationError):
        return _짧게(글)                      # 조각이 홀로 못 서면 글자로 잰다
    줄 = 글.splitlines()
    for tok in reversed(주석):               # 뒤에서부터 지워야 앞의 자리가 안 밀린다
        n = tok.start[0] - 1
        if 0 <= n < len(줄):
            줄[n] = 줄[n][:tok.start[1]]
    남은 = [x.rstrip() for k, x in enumerate(줄, 1) if k not in 뺄줄 and x.strip()]
    return _짧게("\n".join(남은))


_아는파일: list[frozenset[str]] = []


def _깃이_아는_파일() -> frozenset[str]:
    """git 이 든 파일만 도장의 대상이다(DECISIONS §212).

    ★ **저장소에 없는 파일은 기계마다 다르다.** `data/domain/*.jsonl` 은 커밋하지 않는다 —
      만드는 쪽에는 있고 받는 쪽에는 없으니, 그것을 지문에 넣으면 **도장이 기계를 탄다.**
      2026-09-29 §192 가 이 기계에서 무효로 떴다 — `d002` 가 여기 있고 저기 없었다.
    ★ **묻는 것은 「git 이 이미 아는가」 가 아니라 「이 저장소의 파일인가」 다**(DECISIONS §247).
      `--others --exclude-standard` 로 **아직 안 담긴 파일도 센다** — 무시 목록에 든 것만 뺀다.
      2026-09-30 그러지 않아서 **새 도구를 적은 절이 찍자마자 무효**가 됐다. `git add` 전에 찍으면
      그 파일이 지문 밖이고, `add` 하면 안으로 들어와 지문이 바뀐다 — **지문이 내용이 아니라
      git 의 형편을 탔다**(§238 과 같은 병).
    """
    if not _아는파일:                      # 절마다 git 을 부르면 194 번이다
        # ★ **`-z` 다**(DECISIONS §247). git 은 한글 이름을 기본으로 `"\353\213\264…"` 로 따옴표
        #   씌워 내놓는다 — 그러면 그 파일은 **이름이 안 맞아 조용히 지문 밖**이 된다. 이 저장소는
        #   판 이름에 한글을 쓴다(`H-083-대조-a`). NUL 로 끊으면 이름이 그대로 온다
        r = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                           capture_output=True, text=True, cwd=ROOT)
        _아는파일.append(frozenset(x for x in r.stdout.split("\0") if x))
    return _아는파일[0]


def _한_문서(글: str, 앞: str, 머리: re.Pattern, 뽑는다, 표시: str) -> list[dict]:
    자리 = [(m.start(), m.group(1), m.group(2)) for m in 머리.finditer(글)]
    out = []
    아는 = _깃이_아는_파일()
    for i, (s, 번호, 제목) in enumerate(자리):
        끝 = 자리[i + 1][0] if i + 1 < len(자리) else len(글)
        본문 = 글[s:끝]
        줄 = 뽑는다(본문)
        파일 = []
        for 곳, 심볼 in 지목.findall(줄):        # `자리` 를 덮어쓰면 바깥 목록이 날아간다
            짚은 = f"{곳}::{심볼}" if 심볼 else 곳
            # ★ **도장 파일 자신은 안 든다**(DECISIONS §300). 들면 **찍을 수 없는 절**이 된다 —
            #   찍으면 그 파일이 바뀌고, 바뀌면 그 절이 무효가 되고, 다시 찍으면 또 바뀐다.
            #   강제자는 **자**이고 도장 파일은 **그 자의 산출물**이다. 토트에서 실제로 그 절을
            #   적었고 영구 진동으로 들어갔다(thoth §163).
            if 곳 == _도장자리:
                continue
            if (ROOT / 곳).is_file() and 곳 in 아는 and 짚은 not in 파일:
                파일.append(짚은)
        날 = 날짜.search(본문)
        out.append({"번호": f"{앞}{번호}", "제목": 제목, "날짜": 날.group(1) if 날 else "",
                    "본문": 본문, "파일": 파일, "표시": f"{표시}{번호}"})
    return out


def 절들(글: str | None = None) -> list[dict]:
    """두 문서의 (번호, 제목, 날짜, 본문, 지목한 자리들).

    ★ **앵커 줄이 없는 절은 대상이 아니다** — DECISIONS 는 `강제자`, MASTER 는 `봉인`.
    ★ `글` 을 주면 DECISIONS 한 문서만 본다(시험이 합성 글을 먹인다).
    """
    if 글 is not None:
        return _한_문서(글, *문서[0][0:1], *문서[0][2:])
    out = []
    for 앞, 자리, 머리, 뽑는다, 표시 in 문서:
        out += _한_문서((ROOT / 자리).read_text(encoding="utf-8"), 앞, 머리, 뽑는다, 표시)
    return out


# ★ **줄 대장은 줄 단위로 문다**(DECISIONS §215). `hypotheses.md` 는 194 행짜리 대장이라 가설 하나를
#   열고 닫을 때마다 바뀐다 — 그 파일을 짚은 절이 **전부 한꺼번에 무효**가 되고, 그 무효는 아홉 중
#   여덟이 「내가 안 건드린 남의 행」 때문이다. **소음이 된 무효는 안 읽힌다**(§211 과 같은 규율).
# ★ **PLAN 도 줄 대장이다**(DECISIONS §219). `hypotheses.md` 만 좁혀 놓고 PLAN 은 파일째 물었더니,
#   행 하나의 수를 고치자 그 문서를 짚은 절이 또 무효가 됐다 — §215 를 한쪽에만 적용한 것이다.
대장 = {"docs/hypotheses.md": (r"^\| (H-\d+) \|", r"H-\d+"),
        "docs/PLAN.md": (r"^\| (\d+) \|", r"(?<![\w§-])#(\d+)(?!\d)")}


def _대장_조각(자리: str, 본문: str, 글: str) -> str:
    """절이 이름으로 부른 행만 남긴다. **아무 행도 안 부르면 그 파일은 지문 밖이다.**"""
    행꼴, 부름꼴 = 대장[자리]
    번호 = set(re.findall(부름꼴, 본문))
    if not 번호:
        return ""
    줄 = [x for x in 글.splitlines()
          if (m := re.match(행꼴, x)) and m.group(1) in 번호]
    return _짧게("\n".join(줄)) if 줄 else ""


def 지문(절: dict) -> str:
    """절 본문 + 그 절이 지목한 파일들의 로직. **둘 중 하나만 바뀌어도 도장이 무효다.**"""
    조각 = [_짧게(절["본문"])]
    for f in 절["파일"]:
        자리, _, 심볼 = f.partition("::")
        if 자리 in 대장:
            몫 = _대장_조각(자리, 절["본문"], (ROOT / 자리).read_text(encoding="utf-8"))
            if 몫:
                조각.append(f"{f}\0{몫}")
            continue                      # 이름으로 안 부른 대장은 안 문다
        조각.append(f"{f}\0{로직_지문(ROOT / 자리, 심볼)}")
    return _짧게("\n".join(조각))


def 다시_봐야_할_절(찍힌: dict | None = None) -> list[tuple[dict, list[str]]]:
    """**찍은 뒤에 강제자 파일이 바뀐 절**(DECISIONS §211 · PLAN #47 의 수).

    ★ **읽은 절은 뺀다**(§217). 무더기 도장은 안 빼 준다 — 그래야 이 수가 진도다.
    ★ **판별식을 두 벌 두지 않는다**(DECISIONS §237). `audit` 이 찍는 수와 `tools/docgen.py` 가
      문서에 채우는 수가 **같은 함수**에서 나와야 한다 — 두 벌이면 언젠가 갈린다.
    """
    찍힌 = 도장들() if 찍힌 is None else 찍힌
    return [(절, 바뀐) for 절 in 절들()
            if 절["파일"] and not 찍힌.get(절["번호"], {}).get("읽음")
            and (바뀐 := 뒤에_바뀐_파일(절))]


def 도장들() -> dict:
    if SEAL.is_file():
        return json.loads(SEAL.read_text(encoding="utf-8"))
    return {}


def 가른다(찍힌: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """(유효, 무효, 미날인). **강제자가 파일을 안 짚는 절은 아예 대상이 아니다.**"""
    유효, 무효, 미날인 = [], [], []
    for 절 in 절들():
        if not 절["파일"]:
            continue
        옛 = 찍힌.get(절["번호"])
        if 옛 is None:
            미날인.append(절)
        elif 옛.get("지문") == 지문(절):
            유효.append(절)
        else:
            무효.append(절)
    return 유효, 무효, 미날인


def 뒤에_바뀐_파일(절: dict) -> list[str]:
    """**git 이 아는 감사** — 이 절이 적힌 날 뒤에 그 파일이 바뀌었나(DECISIONS §211).

    ★ 도장을 처음 찍는 날에는 전부 「미날인」 이라 감사가 안 나온다. **소급 감사는 이력이 한다** —
      절의 날짜와 파일의 마지막 손댄 날을 견준다. 완전하지 않다(같은 날 바뀐 것은 못 본다).
    """
    if not 절["날짜"]:
        return []
    out = []
    for f in 절["파일"]:
        자리, _, 심볼 = f.partition("::")
        # ★ **이름을 짚었으면 그 몸의 이력만 본다**(`git log -L`). 파일 전체의 마지막 손댄 날로
        #   재면 `check_docs.py` 를 짚은 절이 전부 걸려 **감사가 목록이 아니라 소음**이 된다
        argv = (["git", "log", "-1", "--format=%cs", f"-L:{심볼}:{자리}", "--no-patch"] if 심볼
                else ["git", "log", "-1", "--format=%cs", "--", 자리])
        r = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT)
        마지막 = r.stdout.strip().splitlines()[0].strip() if r.stdout.strip() else ""
        if 마지막[:10] > 절["날짜"] and len(마지막) >= 10:
            out.append(f"{f}({마지막[:10]})")
    return out


def _canary() -> None:
    """★ **지문이 못 가르면 낡은 절이 전부 유효로 보인다** — 무효 0 이 「깨끗하다」 인지 묻는다."""
    본 = "def f():\n    return 1\n"
    주석만 = "def f():\n    # 설명을 고쳤다\n    return 1\n"
    뜻바꿈 = "def f():\n    return 2\n"
    if _낱말지문(본) != _낱말지문(주석만):
        print("    ★ 카나리아가 죽었다 — 주석만 고쳤는데 지문이 갈렸다(무효가 소음이 된다)")
        sys.exit(2)
    if _낱말지문(본) == _낱말지문(뜻바꿈):
        print("    ★ 카나리아가 죽었다 — 뜻이 바뀌었는데 지문이 같다(도장이 안 가른다)")
        sys.exit(2)
    if _몸을_찾는다(ast.parse(본), "없는이름") is not None:
        print("    ★ 카나리아가 죽었다 — 사라진 이름을 찾았다고 한다")
        sys.exit(2)
    if not 지목.findall("`tools/gate.py::_선을_박는다` 를 본다"):
        print("    ★ 카나리아가 죽었다 — 강제자 줄에서 지목을 못 뽑는다(절이 통째로 미지목이 된다)")
        sys.exit(2)
    # ★ **MASTER 가 조용히 빠지면 「무효 0」 이 「깨끗하다」 가 아니라 「안 봤다」 다**(DECISIONS §281).
    #   절머리 정규식 한 글자나 봉인 줄 꼴이 어긋나면 이 문서가 통째로 대상 밖이 되고, 그래도 초록이다
    전부 = 절들()
    마 = [x for x in 전부 if x["번호"].startswith("M") and x["파일"]]
    if not 마:
        print("    ★ 카나리아가 죽었다 — 봉인을 든 MASTER 절이 하나도 안 잡힌다(그 문서가 대상 밖이다)")
        sys.exit(2)
    if _봉인_줄("## 11. 데이터 관리\n봉인이라는 낱말이 본문에 그냥 나온다.\n"):
        print("    ★ 카나리아가 죽었다 — 본문의 「봉인」 낱말을 봉인 줄로 읽는다(거짓 양성)")
        sys.exit(2)
    if not _봉인_줄("## 5. 점검\n봉인 — `tools/verify.sh`\n  까닭.\n"):
        print("    ★ 카나리아가 죽었다 — 진짜 봉인 줄을 못 읽는다")
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _canary()
    말 = args[0] if args and not args[0].startswith("-") else ""
    찍힌 = 도장들()

    if 말 == "audit":
        의심 = 다시_봐야_할_절(찍힌)
        읽은 = sum(1 for v in 찍힌.values() if v.get("읽음"))
        print(f"  절 {len([x for x in 절들() if x['파일']])} 중 **그 뒤에 강제자 파일이 바뀐 절 "
              f"{len(의심)}** — 「틀렸다」 가 아니라 **「다시 봐야 한다」** 다 (읽고 찍은 절 {읽은})")
        for 절, 바뀐 in 의심:
            print(f"    {절['표시']} {절['제목'][:40]} ({절['날짜']})\n        {' · '.join(바뀐)}")
        print("\n  ※ 하나씩 읽고, 지금도 참이면 `python3 tools/docseal.py stamp --only <번호>`")
        return 0

    if 말 == "stamp":
        만 = args[args.index("--only") + 1] if "--only" in args else ""
        읽었나 = "--read" in args
        if 읽었나 and not 만:
            print("    ✗ `--read` 는 한 절씩만 쓴다 — `--only <번호>` 를 같이 준다\n"
                  "       무더기로 「읽었다」 를 찍으면 그 표시가 아무것도 안 말한다", file=sys.stderr)
            return 1
        n = 0
        for 절 in 절들():
            if not 절["파일"] or (만 and 절["번호"] != 만):
                continue
            # ★ **찍는 것과 읽는 것은 다르다**(DECISIONS §217). 무더기로 찍은 도장은 「그때 이랬다」
            #   일 뿐이고 **사람이 그 절을 다시 읽었다는 뜻이 아니다.** 읽은 것만 감사에서 뺀다
            읽음 = 읽었나 or bool(찍힌.get(절["번호"], {}).get("읽음"))
            찍힌[절["번호"]] = {"지문": 지문(절), "날짜": 절["날짜"], "파일": 절["파일"],
                              "읽음": 읽음}
            n += 1
        SEAL.parent.mkdir(parents=True, exist_ok=True)
        SEAL.write_text(json.dumps(찍힌, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")
        print(f"  도장 {n} 개를 찍었다 — {SEAL.relative_to(ROOT)}")
        return 0

    유효, 무효, 미날인 = 가른다(찍힌)
    if 말 == "status":
        print(f"  유효 {len(유효)} · **무효 {len(무효)}** · 미날인 {len(미날인)}")
        for 절 in 미날인[:10]:
            print(f"    미날인 {절['표시']} {절['제목'][:50]}")
        return 0
    for 절 in 무효:
        print(f"    ✗ {절['표시']} {절['제목'][:50]} — 찍은 뒤로 본문이나 봉인이 바뀌었다\n"
              f"        {' · '.join(절['파일'])}\n"
              f"        읽고 지금도 참이면 : python3 tools/docseal.py stamp --only {절['번호']}")
    if 무효:
        print(f"\n  **무효는 「틀렸다」 가 아니라 「다시 봐야 한다」 다**(DECISIONS §211). {len(무효)} 절")
    return 1 if 무효 else 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다(DECISIONS §21 · §232). 같은 코드면
    #   **도구가 깨진 것을 검사가 실패한 것으로 읽는다**
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("    ✗ 도구가 깨졌다 — 위 역추적이 자리를 든다\n"
              "      고치고 다시 돌린다 : bash tools/doctor.sh", file=sys.stderr)
        sys.exit(2)
