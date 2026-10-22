"""**절과 그 절이 짚은 코드의 도장**이 살아 있는가(세샤트 DECISIONS §211).

★ 이 시험이 지키는 것은 「절이 참이다」 가 아니라 **「바뀌면 무효가 된다」** 다. 뜻은 사람이 본다.

★ **세샤트의 `tests/test_docseal.py` 에서 왔다. 정본은 세샤트다**(DECISIONS §163).
  갈린 자리는 넷이고 **넷을 여기 적는다**(세샤트 §296).
    · 도장 파일이 `tools/docseal.json` 이다 (세샤트는 `data/docseal.json`)
    · 무시되는 자리의 보기가 `.cache/` 다 (세샤트는 `data/domain/*.jsonl`)
    · 줄 대장이 `docs/PLAN.md` 하나다 — 이쪽에 `docs/hypotheses.md` 가 없다.
      기계는 그대로 둔다(사본이니까) — **없는 열쇠는 조용히 안 쓰인다**
    · MASTER 봉인 시험이 이쪽 절(`M6` 비용 가드 · `worker/app/guard.py`)을 든다
★ **아래 `★` 들의 `§N` 중 「세샤트」 가 안 붙은 것은 이 저장소의 절이다.**
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents
          if (p / "tools/docseal.py").exists())
_spec = importlib.util.spec_from_file_location("docseal", ROOT / "tools/docseal.py")
DS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(DS)

절 = ("## §9. 무엇이 있었나\n\n**2026-09-29**\n\n### 배운 것\n\n어떤 말.\n\n"
      "강제자 — `tools/docseal.py::로직_지문`\n")


def test_이름을_짚으면_그_몸만_잰다(tmp_path):
    """★ 파일로 재면 `check_docs.py` 를 짚은 절 스무 개가 한꺼번에 무효가 된다 — **소음이 된다.**"""
    p = tmp_path / "x.py"
    p.write_text("def a():\n    return 1\n\n\ndef b():\n    return 2\n", encoding="utf-8")
    앞 = DS.로직_지문(p, "a")
    p.write_text("def a():\n    return 1\n\n\ndef b():\n    return 99\n", encoding="utf-8")
    assert DS.로직_지문(p, "a") == 앞, "남의 몸이 바뀌었는데 내 도장이 찢어졌다"
    assert DS.로직_지문(p, "b") != 앞


def test_주석과_독스트링은_도장을_안_찢는다(tmp_path):
    p = tmp_path / "x.py"
    p.write_text("def a():\n    return 1\n", encoding="utf-8")
    앞 = DS.로직_지문(p, "a")
    p.write_text('def a():\n    """새 설명."""\n    # 새 주석\n    return 1\n', encoding="utf-8")
    assert DS.로직_지문(p, "a") == 앞


def test_짚은_이름이_사라지면_다시_보라고_한다(tmp_path):
    p = tmp_path / "x.py"
    p.write_text("def a():\n    return 1\n", encoding="utf-8")
    assert DS.로직_지문(p, "없는이름") == "없다"


def test_본문이_바뀌어도_무효다():
    """양쪽 다 도장이 덮는다 — 코드만이 아니라 **절 본문**도."""
    하나 = DS.절들(절)[0]
    둘 = DS.절들(절.replace("어떤 말", "다른 말"))[0]
    assert DS.지문(하나) != DS.지문(둘)


def test_강제자가_없는_절은_대상이_아니다():
    글 = "## §9. 무엇\n\n**2026-09-29**\n\n### 배운 것\n\n말.\n"
    assert DS.절들(글)[0]["파일"] == []


def test_저장소의_도장이_유효하다():
    """★ **찍어 놓고 안 보면 도장은 장식이다**(§170 과 같은 병)."""
    assert DS.main([]) == 0


def test_저장소에_없는_파일은_도장이_안_문다():
    """★ **도장이 기계를 타면 도장이 아니다**(세샤트 DECISIONS §212).

    `.cache/` 는 커밋하지 않는다 — 돌린 쪽에는 있고 받은 쪽에는 없다. 그것을 지문에
    넣으면 같은 커밋에서 한쪽만 무효가 된다. 세샤트가 2026-09-29 에 그렇게 떴다.
    """
    글 = ("## §9. 무엇\n\n**2026-09-29**\n\n### 배운 것\n\n말.\n\n"
          "강제자 — `.cache/translations.json` · `tools/docseal.py::지문`\n")
    파일 = DS.절들(글)[0]["파일"]
    assert not any(f.startswith(".cache/") for f in 파일), 파일
    assert any(f.startswith("tools/docseal.py") for f in 파일)


def test_없는_대장_열쇠는_조용히_안_쓰인다():
    """★ **세샤트는 `docs/hypotheses.md` 도 줄 단위로 문다**(세샤트 DECISIONS §215). 이쪽에는
    그 문서가 없다 — 기계는 사본이라 그대로 두고, **없는 열쇠가 조용히 안 쓰이는지**만 묻는다.
    열쇠가 늘 때 그 문서가 생기면 그날부터 저절로 돈다."""
    assert "docs/hypotheses.md" in DS.대장, "정본의 열쇠가 사라졌다 — 사본이 갈렸다"
    assert not (ROOT / "docs/hypotheses.md").exists()
    본문 = "## §9. 무엇\n\n**2026-09-29**\n\n### 배운 것\n\nH-079 를 연다.\n"
    파일 = DS.절들("## §9. 무엇\n\n**2026-09-29**\n\n### 배운 것\n\n말.\n\n"
                  "강제자 — `docs/hypotheses.md`\n")[0]["파일"]
    assert 파일 == [], f"실물이 없는 자리를 지문에 넣으면 받은 쪽에서 무효다 — {파일}"
    assert 본문

def test_무더기로_읽었다를_못_찍는다(tmp_path, monkeypatch, capsys):
    """★ **찍는 것과 읽는 것은 다르다**(세샤트 DECISIONS §217). 한꺼번에 「읽었다」 를 찍으면 그 표시가
    아무것도 안 말하고, 그 순간 감사의 수가 진도를 잃는다."""
    assert DS.main(["stamp", "--read"]) == 1
    assert "--only" in capsys.readouterr().err


def test_PLAN_도_부른_행만_문다():
    """★ §215 를 `hypotheses.md` 에만 적용하고 `PLAN.md` 는 파일째 뒀다(세샤트 DECISIONS §219)."""
    # ★ 합성 대장이다 — 실물 PLAN 의 행 번호를 쓰면 `doc_fsck` 가 「없는 행」 으로 읽는다
    대장 = "| 25 | ⏳ | 가 | |\n| 30 | ⏳ | 나 | |\n"
    본문 = "## §9. 무엇\n\n**2026-09-29**\n\n### 배운 것\n\n서른째 행이 든다.\n".replace(
        "서른째 행", "PLAN " + chr(35) + "30")
    앞 = DS._대장_조각("docs/PLAN.md", 본문, 대장)
    assert 앞
    assert DS._대장_조각("docs/PLAN.md", 본문, 대장.replace("| 25 | ⏳ |", "| 25 | ✅ |")) == 앞
    assert DS._대장_조각("docs/PLAN.md", 본문, 대장.replace("| 30 | ⏳ |", "| 30 | ✅ |")) != 앞


def test_아직_안_담긴_파일도_저장소의_파일이다(tmp_path, monkeypatch):
    """★ **찍자마자 무효가 됐다**(세샤트 DECISIONS §247). `git add` 전에 찍으면 그 파일이 지문 밖이고,
    `add` 하면 안으로 들어와 지문이 바뀐다 — **지문이 내용이 아니라 git 의 형편을 탄다.**"""
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("무시/\n", encoding="utf-8")
    (tmp_path / "담김.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore", "담김.py"], cwd=tmp_path, check=True)
    (tmp_path / "새것.py").write_text("y = 2\n", encoding="utf-8")        # 안 담겼다
    (tmp_path / "무시").mkdir()
    (tmp_path / "무시/데이터.jsonl").write_text("{}\n", encoding="utf-8")  # 무시 목록이다

    monkeypatch.setattr(DS, "ROOT", tmp_path)
    monkeypatch.setattr(DS, "_아는파일", [])
    아는 = DS._깃이_아는_파일()
    assert "담김.py" in 아는
    assert "새것.py" in 아는, "안 담긴 파일이 빠지면 새 도구를 적은 절이 찍자마자 무효가 된다"
    assert "무시/데이터.jsonl" not in 아는, "무시 목록은 기계마다 다르다(세샤트 DECISIONS §212)"


def test_한글_이름도_그대로_온다(tmp_path, monkeypatch):
    """★ **git 은 한글 이름을 따옴표 씌워 내놓는다** — 그러면 이름이 안 맞아 **조용히 지문 밖**이
    된다(세샤트 DECISIONS §247). 이 저장소는 판 이름에 한글을 쓴다(`H-083-대조-a`)."""
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "대조판.jsonl").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(DS, "ROOT", tmp_path)
    monkeypatch.setattr(DS, "_아는파일", [])
    assert "대조판.jsonl" in DS._깃이_아는_파일()


def test_MASTER_도_봉인이_붙는다():
    """★ **낡는 문서는 DECISIONS 가 아니라 MASTER 다**(세샤트 DECISIONS §281).

    DECISIONS 는 추가만 하니 구조상 안 낡는다. MASTER 는 「현재」 축이라 **정의상 실물을
    따라가야 하는 유일한 문서**인데 2026-10-02 까지 봉인이 안 걸려 있었고, 소급해서 읽으니
    아홉 자리가 낡아 있었다 — **아홉 다 이 봉인으로 잡히는 꼴**이었다.
    """
    마 = [x for x in DS.절들() if x["번호"].startswith("M") and x["파일"]]
    assert 마, "봉인을 든 MASTER 절이 하나도 없다 — 그 문서가 통째로 대상 밖이다"
    assert all(x["표시"].startswith("MASTER §") for x in 마)
    # 열쇠가 DECISIONS 와 안 겹친다 — 겹치면 옛 도장이 MASTER 절로 읽힌다
    모두 = [x["번호"] for x in DS.절들()]
    assert len(모두) == len(set(모두)), "절 번호가 겹친다"


def test_본문의_봉인_낱말을_봉인_줄로_안_읽는다():
    """★ MASTER 본문에는 「봉인」 이 그냥 나온다(§11-10 이 그렇다). DECISIONS 의 `rfind` 꼴을
    그대로 쓰면 그 절이 **거짓 양성**으로 걸린다 — 2026-10-02 실제로 §11 이 걸렸다."""
    assert DS._봉인_줄("## 11. 운영\n봉인은 옮겼다 — `tools/docseal.py` 가 그것이다.\n") == ""
    assert "tools/doctor.sh" in DS._봉인_줄("## 11. 운영\n봉인 — `tools/doctor.sh`\n  까닭.\n")


def test_봉인한_파일이_바뀌면_MASTER_절이_무효가_된다(tmp_path, monkeypatch):
    """**이 시험이 지키는 것은 「절이 참이다」 가 아니라 「바뀌면 무효가 된다」 다.**"""
    절 = next(x for x in DS.절들() if x["번호"] == "M6")        # §6 비용 가드
    before = DS.지문(절)
    원 = (ROOT / "worker/app/guard.py")
    글 = 원.read_text(encoding="utf-8")
    try:
        원.write_text(글.replace("def ", "def _", 1), encoding="utf-8")
        assert DS.지문(절) != before, "봉인한 파일이 바뀌었는데 지문이 같다 — 도장이 안 가른다"
    finally:
        원.write_text(글, encoding="utf-8")
    assert DS.지문(절) == before, "되돌렸는데 지문이 안 돌아왔다"


def test_글로_못_읽는_산출물은_지목에_안_든다():
    """★ **지문이 바이트가 되면 구울 때마다 도장이 찢어진다**(thoth 세샤트 DECISIONS §161 · §298).
    `docs/proposal.docx` 는 토트에서 강제자가 실제로 든다 — 사본이 거기 산다."""
    줄 = "강제자 — `docs/proposal.docx` 와 `tools/a.py` 와 `x/y.png` 와 `z/w.zip`"
    집은것 = [m[0] for m in DS.지목.findall(줄)]
    assert 집은것 == ["tools/a.py"], 집은것


def test_지목확장이_사본의_강제자를_다_덮는다():
    """★ **목록이 좁으면 그 줄들이 조용히 안 세어진다**(§298). 안 세어진 것은 **안 낡는
    것처럼 보인다** — 토트 강제자는 `.js` · `.json` · `.tf` · `.css` 를 든다."""
    for 확 in ("py", "sh", "js", "json", "jsonl", "md", "yml", "tf", "css", "toml"):
        assert 확 in DS.지목확장, 확
    # ★ 긴 것이 앞이다 — 짧은 쪽이 먼저면 `.jsonl` 이 백틱을 못 닫는다
    assert DS.지목확장.index("jsonl") < DS.지목확장.index("json")
    assert DS.지목확장.index("yaml") < DS.지목확장.index("yml")
    assert DS.지목.findall("`a/b.jsonl`")[0][0] == "a/b.jsonl"


def test_강제자_블록을_줄_머리로_못_박는다():
    """★ **`rfind("강제자")` 는 시험 이름에 그 낱말이 있으면 빈손이 된다**(§299).
    `test_지목확장이_사본의_강제자를_다_덮는다` 가 실제로 그랬다 — 창이 그 뒤부터
    열리고, 파일을 하나도 못 집은 절의 도장은 **아무것도 안 보며 영영 유효**하다."""
    본문 = ("## §1. 제목\n\n**2026-01-01**\n\n본문\n\n"
            "강제자 — `tools/a.py` 의 `무엇` ·\n`tests/test_a.py` 의 `test_강제자를_다_본다`\n")
    앵 = DS._강제자_뒤(본문)
    assert 앵.startswith("강제자 — "), 앵
    집은것 = sorted(m[0] for m in DS.지목.findall(앵))
    assert 집은것 == ["tests/test_a.py", "tools/a.py"], 집은것


def test_산문이_든_파일을_강제자로_안_센다():
    """★ **창이 너무 넓으면 반대로 틀린다**(§299). 본문에 「강제자」 가 먼저 나오면
    `rfind` 가 그 자리부터 열어 **산문이 든 파일까지** 집었다 — 실측 세 절."""
    본문 = ("## §1. 제목\n\n**2026-01-01**\n\n"
            "강제자가 없던 때 `tools/옛것.py` 를 봤다\n\n"
            "강제자 — `tools/지금것.py`\n")
    집은것 = [m[0] for m in DS.지목.findall(DS._강제자_뒤(본문))]
    assert 집은것 == ["tools/지금것.py"], 집은것


def test_강제자_없음도_블록이다():
    # ★ 「강제자 없음 — 설계 판단이다」 도 절의 끝 블록이다. 파일은 안 들지만 창은 거기 선다
    본문 = "## §1. 제목\n\n**2026-01-01**\n\n본문 `tools/산문.py`\n\n강제자 없음 — 설계 판단이다\n"
    앵 = DS._강제자_뒤(본문)
    assert 앵.startswith("강제자 없음 — ")
    assert DS.지목.findall(앵) == []
def test_도장_파일_자신은_강제자로_안_든다():
    """★ **찍을 수 없는 절이 된다**(세샤트 DECISIONS §300). 찍으면 도장 파일이 바뀌고, 바뀌면 그
    절이 무효가 되고, 다시 찍으면 또 바뀐다 — 토트에서 실제로 영구 진동으로 들어갔다.
    강제자는 **자**이고 도장 파일은 **그 자의 산출물**이다."""
    글 = ("## §9. 무엇\n\n**2026-09-29**\n\n### 배운 것\n\n말.\n\n"
          f"강제자 — `{DS._도장자리}` · `tools/docseal.py::지문`\n")
    파일 = DS.절들(글)[0]["파일"]
    assert DS._도장자리 not in 파일, 파일
    assert 파일 == ["tools/docseal.py::지문"], "남은 것은 그대로 들어야 한다"


def test_도장_자리를_손으로_안_적는다():
    """★ **같은 것이 두 곳에 살면 한쪽만 늙는다**(§283). `SEAL` 하나에서 끌어낸다 —
    사본은 그 자리가 다르다(세샤트는 `data/docseal.json`)."""
    assert DS._도장자리 == DS.SEAL.relative_to(DS.ROOT).as_posix()


# ★ **아래는 세샤트에서 왔다**(DECISIONS §163). 그쪽 §316 · §320 · §321 · §322 다.
#   **둘은 안 가져왔다** — 갈린 자리를 적는다(세샤트 §296) :
#     · `test_그_둘이_이제_묶인다` 는 그 저장소의 절 둘(세샤트 §210 · §211)을 든다
#     · `test_저장소의_절이_실제로_걸음으로_좁혀졌다` 는 「좁혀진 절 15 이상」 을 묻는데
#       **이 저장소는 0 이다** — `doctor.sh` 는 검사가 산문처럼 이어져 걸음 단위가 없고,
#       아무 강제자 줄도 「단계」 라는 표식을 안 쓴다(세샤트 §322). 그것이 맞는 상태다.
# ───────────────── 셸 · 워크플로 지문(세샤트 DECISIONS §316) ─────────────────

_셸 = ("step scope   uv run python tools/check_scope.py\n"
       "step dead    uv run python tools/check_dead.py\n")


def test_셸_주석_한_줄에_지문이_안_갈린다():
    """★ **약을 `.py` 에만 먹이고 있었다**(세샤트 DECISIONS §316).

    실측 : `verify.sh` 에 주석 한 줄을 더하면 절 **스물**이 무효가 됐고, `check_docs.py` 에
    같은 것을 더하면 **0** 이었다. `verify.sh` 는 절반이 주석인 파일이다.
    """
    assert DS._셸_지문(_셸) == DS._셸_지문("# 설명을 고쳤다\n" + _셸 + "\n   \n")


def test_셸의_뜻이_바뀌면_지문이_갈린다():
    """★ **다 같게 만들면 도장이 아니다.** 안 가르는 쪽이 더 나쁘다."""
    assert DS._셸_지문(_셸) != DS._셸_지문(_셸.replace("check_scope", "check_dead"))


def test_줄_안쪽의_우물정은_안_건드린다():
    """★ `${X#...}` 와 조각 주소가 거기 산다 — **온줄 주석만** 뗀다."""
    a = 'echo "${BR#papers/}"\n'
    assert DS._셸_지문(a) != DS._셸_지문('echo "${BR}"\n')


def test_들여쓰기는_센다():
    """★ **셸에서는 안 지지만 YAML 에서는 진다** — 떼면 거짓 초록이다."""
    assert DS._셸_지문("a: 1\n  b: 2\n") != DS._셸_지문("a: 1\nb: 2\n")


def test_옆_걸음이_늘어도_내_걸음은_그대로다():
    """★ **이것이 §316 의 전부다.** 걸음 하나가 붙었다고 스무 절을 다시 읽을 까닭이 없다."""
    늘린것 = _셸 + "step 새것   uv run python tools/새것.py\n"
    assert DS._셸_지문(_셸, "scope") == DS._셸_지문(늘린것, "scope")


def test_내_걸음이_바뀌면_운다():
    """★ **좁히는 것과 꺼 두는 것은 다르다.** 제 걸음은 여전히 문다."""
    바뀐것 = _셸.replace("step scope   uv run python tools/check_scope.py",
                       "step scope   uv run python tools/check_scope.py --list")
    assert DS._셸_지문(_셸, "scope") != DS._셸_지문(바뀐것, "scope")


def test_걸음이_사라지면_없다다():
    """★ **짚은 이름이 사라진 것 자체가 다시 볼 까닭이다**(파이썬 쪽과 같은 규칙)."""
    assert DS._셸_지문(_셸, "없는걸음") == "없다"


def test_if_else_안의_걸음도_찾는다():
    """★ **§315 가 바로 이 무늬에서 넘어졌다** — 여기서 되풀이하지 않는다."""
    글 = ('if [ "${CI:-}" = "true" ]; then NAMES+=("ci")\n'
          "else step ci   uv run python tools/ci_status.py; fi\n")
    assert DS._셸_몸(글, "ci") is not None
    assert "ci_status.py" in DS._셸_몸(글, "ci")


def test_함수도_찾는다():
    글 = 'shellcheck_step() {\n  local X=1\n  echo "$X"\n}\nstep a  b\n'
    몸 = DS._셸_몸(글, "shellcheck_step")
    assert 몸 is not None and 몸.startswith("shellcheck_step() {") and 몸.endswith("}")
    assert "step a" not in 몸, "함수 밖까지 먹으면 좁힌 뜻이 없다"


def test_강제자_줄이_적어_둔_걸음_이름을_읽는다():
    """★ **스물한 절을 고쳐 적지 않았다** — 뜻은 이미 그 줄에 있었고 읽는 쪽이 빠져 있었다."""
    assert DS._셸걸음("강제자 — `tools/doctor.sh` 의 `scope` 단계") == {"tools/doctor.sh": ["scope"]}
    assert DS._셸걸음("`tools/doctor.sh` 의 `shellcheck_step` 과 `check_prose` 단계") == \
        {"tools/doctor.sh": ["shellcheck_step", "check_prose"]}
    assert DS._셸걸음("`tools/doctor.sh` 의 `deadchecks` 단계") == {"tools/doctor.sh": ["deadchecks"]}
    # ★ **「단계」 가 표식이다**(세샤트 DECISIONS §322) — 없으면 걸음으로 안 읽는다.
    assert DS._셸걸음("`tools/doctor.sh` 의 `PKG_N`") == {}


def test_이름을_안_댄_줄에서는_걸음을_안_지어낸다():
    """★ **좁히지 못한 것은 넓게 둔다** — 지어내면 안 무는 자리가 생긴다."""
    assert DS._셸걸음("강제자 — `tools/doctor.sh` 의 두 갈래") == {}
    assert DS._셸걸음("강제자 — `tools/doctor.sh`") == {}


def test_카나리아가_산다():
    assert DS._canary() is None, "카나리아는 말없이 돌아온다 — 죽으면 SystemExit 다"


# ───────── 주석 머리가 꼴마다 다르다(세샤트 DECISIONS §320) ─────────

def test_js_는_슬래시_둘로_뗀다():
    """★ **이 저장소에 `.js` 가 없다 — 사본(토트)이 쓴다**(thoth §163).

    토트에서 재니 `extension/src/broker.js` 에 **주석 한 줄**이 절 **8** 을 무효로 만들었다.
    여기서 안 물으면 그 길은 **영영 안 물린다.**
    """
    assert DS._셸_지문("// 설명\nconst a = 1;\n", 머리="//") == DS._셸_지문("const a = 1;\n", 머리="//")


def test_꼴을_안_가르면_안_뗀다():
    """★ **`#` 로 `//` 를 떼면 아무것도 안 떼고 초록이 된다** — 가르는 것이 값이다."""
    assert DS._셸_지문("// 설명\nconst a = 1;\n") != DS._셸_지문("const a = 1;\n")


def test_js_의_뜻이_바뀌면_운다():
    assert DS._셸_지문("const a = 1;\n", 머리="//") != DS._셸_지문("const a = 2;\n", 머리="//")


def test_주소의_슬래시_둘은_안_건드린다():
    """★ `https://` 가 거기 산다 — **온줄만** 뗀다."""
    assert DS._셸_지문('const u = "https://a.b";\n', 머리="//") != DS._셸_지문("\n", 머리="//")


def test_표가_꼴마다_머리를_든다():
    """★ **목록이 좁으면 그 줄들이 조용히 안 세어진다**(`지목확장` 과 같은 까닭)."""
    assert DS.주석머리[".sh"] == "#" and DS.주석머리[".js"] == "//"
    assert {".sh", ".yml", ".yaml", ".js", ".tf"} <= set(DS.주석머리)
    assert ".md" not in DS.주석머리 and ".json" not in DS.주석머리, \
        "글자가 곧 내용인 꼴은 들면 안 된다 — 주석을 떼면 뜻이 준다"


# ───────── 못 푸는 걸음 이름(세샤트 DECISIONS §321) ─────────

def test_없는_걸음은_파일_전체에_묶인다(tmp_path):
    """★ **좁히려다 꺼 버리는 자리다**(세샤트 DECISIONS §321).

    없는 이름에 묶으면 지문이 `"없다"` 로 **굳고**, 그 뒤로 그 파일을 아무리 고쳐도
    영영 안 운다. 사본(토트)의 강제자 줄이 「`tools/doctor.sh` 의 `PKG_N`」 처럼 적는데
    그 파일에 `step PKG_N` 이 없다 — 그대로 옮겼으면 그쪽 절들이 통째로 잠들었다.

    ★ **합성으로 묻는다**(세샤트 DECISIONS §322) — 제 저장소의 파일을 읽으면 **사본에서 거짓으로
      죽는다.** 카나리아가 실제로 그렇게 죽었다.
    """
    샘 = tmp_path / "x.sh"
    샘.write_text("step docseal  uv run python tools/docseal.py\n", encoding="utf-8")
    assert not DS._걸음이있나(샘, "없는걸음이다")
    assert DS._걸음이있나(샘, "docseal")


def test_못_읽는_파일은_없다로_센다(tmp_path):
    """읽기가 실패한 것과 **걸음이 없는 것**은 같은 처리다 — 둘 다 넓게 묶는다."""
    assert not DS._걸음이있나(tmp_path / "없는파일.sh", "x")


def test_파일_이름은_걸음으로_안_읽는다():
    """★ 「`tools/make_patch.sh` 의 `mined.jsonl` 예외」 는 **자리**이지 걸음이 아니다."""
    assert DS._셸걸음("강제자 — `tools/make_patch.sh` 의 `mined.jsonl` 예외") == {}
    assert DS._셸걸음("강제자 — `tools/doctor.sh` 의 `docseal` 단계") == {"tools/doctor.sh": ["docseal"]}


def test_저장소에_못_푸는_걸음이_없다():
    """★ **실측으로 둘이 `tools/` 를 빠뜨려 강제자로 아예 안 묶여 있었다**(§210 · §211).

    그 줄들은 「verify.sh 가 지킨다」 고 적어 두고 도장은 그것을 안 물고 있었다.
    """
    난것 = DS.안풀리는_걸음()
    assert 난것 == [], 난것
