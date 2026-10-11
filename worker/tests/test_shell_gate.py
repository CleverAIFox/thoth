"""`doctor.sh` 가 **제 글을 쉘에 먹이지 않나**(DECISIONS §182).

★ 2026-10-11 에 `doctor.sh:381` 이 이랬다 —

      warn "기획서가 생성기보다 낡았다 — 미는 날 `기획서 배포` 가 멈춘다"

  **마크다운으로 적은 백틱을 쉘이 명령 치환으로 읽었다.** `기획서 배포` 를 실행해
  `command not found` 를 뱉고, 메시지에는 그 자리가 **빈칸**으로 박혔다.

★ **왜 아무도 안 봤나** 두 겹이다.
  ① `shellcheck -S warning` 이 통째로 넘겼다 — 그 코드(`SC2006`)가 **style 등급**이다.
     주석에는 「info · style 은 취향이고 커밋을 막을 일이 아니다」 라고 **단정**돼
     있었고, 그 단정이 한 번 틀렸다.
  ② **그 줄이 그날 처음 실행됐다.** `DOCX_RC == 3` 가지는 「기획서가 생성기보다 낡았다」
     일 때만 도는데, 그 상태가 그날 처음 났다 — **`doctor` 의 WARN·FAIL 가지는 평소에
     안 돈다**는 것이 이 집안의 진짜 모양이다(§21).

★ **등급을 안 내린다.** `-S style` 로 내리면 65건이 같이 쏟아진다(실측 : SC2015 33 ·
  SC1091 18 …) — 넓은 검사는 끄는 방법부터 찾게 된다(§46 · §133). 대신 **「우리에게
  중요한 style 코드」 를 선언**하고 그것만 따로 묻는다.

★ 여기서는 **두 자로 묻는다** — 배선(`doctor` 가 그 코드를 고르나)과 성질(실제로 그런
  줄이 있나). 성질은 shellcheck 없이도 재지도록 손으로 훑는다. **진짜 관문은 파서**이고
  이쪽은 **그 관문이 꽂혀 있는지**를 본다.
"""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCTOR = ROOT / "tools/doctor.sh"


def 쉘파일들() -> list[pathlib.Path]:
    r = subprocess.run(["git", "ls-files", "-z", "*.sh"], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, "`git ls-files` 를 못 읽었다 — 못 쟀다는 뜻이다"
    것 = [ROOT / 이름 for 이름 in r.stdout.split("\0") if 이름]
    assert len(것) >= 10, f"쉘 파일이 {len(것)}개뿐이다 — 훑는 범위가 좁아졌다"
    return 것


def 쌍따옴표안_백틱(글: str) -> list[tuple[int, str]]:
    """쌍따옴표 **안**의 이스케이프 안 된 백틱이 있는 줄.

    ★ 주석의 백틱은 쉘이 안 읽으므로 센 데서 뺀다 — 이 저장소의 주석은 전부 한글
      마크다운이라 백틱이 흔하다. **글을 코드로 읽으면 제 주석에 걸린다**(§168 집안).
    """
    난것: list[tuple[int, str]] = []
    for n, 줄 in enumerate(글.split("\n"), 1):
        if 줄.lstrip().startswith("#"):
            continue
        안, i = False, 0
        while i < len(줄):
            c = 줄[i]
            if c == "\\":
                i += 2
                continue
            if c == '"':
                안 = not 안
            elif c == "`" and 안:
                난것.append((n, 줄.strip()))
                break
            i += 1
    return 난것


# ── 성질 ────────────────────────────────────────────────────────────────

def test_쉘_글에_먹히는_백틱이_없다():
    난것 = [(p.relative_to(ROOT), n, 줄)
            for p in 쉘파일들() for n, 줄 in 쌍따옴표안_백틱(p.read_text(encoding="utf-8"))]
    assert 난것 == [], f"쌍따옴표 안 백틱 : {난것}"


def test_훑는_자가_실제로_문다():
    """★ **음성 대조가 없으면 늘 빈손이라서 초록이다**(§21). 그 줄을 다시 지어 먹인다."""
    나쁜것 = 'warn "미는 날 ' + chr(96) + '기획서 배포' + chr(96) + ' 가 멈춘다"'
    assert 쌍따옴표안_백틱(나쁜것), "실제로 물었던 줄을 안 문다"
    # 작은따옴표로 적은 것이 고친 꼴이다
    assert not 쌍따옴표안_백틱("""warn "미는 날 '기획서 배포' 가 멈춘다" """)
    # 주석과 이스케이프는 센 데서 뺀다
    assert not 쌍따옴표안_백틱("# 주석의 " + chr(96) + "백틱" + chr(96) + " 은 안 읽힌다")
    assert not 쌍따옴표안_백틱('echo "\\' + chr(96) + 'escaped\\' + chr(96) + '"')
    # 쌍따옴표 **밖**의 백틱은 일부러 쓴 명령 치환이다 — 이 자가 볼 일이 아니다
    assert not 쌍따옴표안_백틱("X=" + chr(96) + "date" + chr(96))


# ── 배선 ────────────────────────────────────────────────────────────────

def 코드만(글: str) -> str:
    """줄 전체가 주석인 줄을 버린다.

    ★ **이 자가 제 설명에 걸렸다** — 아래 시험이 「`-S style` 이 없나」 를 묻는데
      `doctor.sh` 의 주석이 **「`-S style` 로 내리면 65건이 쏟아진다」** 고 적고 있다.
      「글을 코드로 읽는 검사는 글부터 지운다」 집안의 **열한 번째**다(§168 · §182).
    """
    return "\n".join(l for l in 글.split("\n") if not l.lstrip().startswith("#"))


def test_doctor_가_고른_style_코드를_따로_묻는다():
    """★ **단정을 관문으로 바꾼다.** 「style 은 취향이다」 는 주석이었고 한 번 틀렸다."""
    sh = 코드만(DOCTOR.read_text(encoding="utf-8"))
    코드 = [l for l in sh.split("\n") if l.strip().startswith("STYLE_CODES=")]
    assert len(코드) == 1, f"`STYLE_CODES` 선언이 {len(코드)}개다"
    assert "SC2006" in 코드[0], "백틱 코드가 고른 목록에 없다 — 그 줄이 또 샌다"
    assert 'shellcheck -i "$STYLE_CODES"' in sh, "고른 코드를 shellcheck 에 안 넘긴다"
    # ★ **등급을 내려서 때우지 않았는지** 본다 — 내리면 65건이 쏟아지고 곧 꺼진다
    assert "-S style" not in sh and "-S info" not in sh, "등급을 내려서 때웠다"
    assert "-S warning" in sh, "warning 등급을 잃었다"


def test_두_판을_다_보고_나서_초록을_낸다():
    """★ **둘 중 하나만 보면 나머지가 꺼진 줄 모른다.** 두 종료 코드를 함께 묻는지 본다."""
    sh = DOCTOR.read_text(encoding="utf-8")
    sh = 코드만(sh)
    몸 = sh[sh.index("STYLE_CODES="):sh.index("== 검사의 검사")]
    assert 'SC_SRC=$?' in 몸, "고른 style 판의 종료 코드를 안 받는다"
    assert '[ "$SC_RC" = 0 ] && [ "$SC_SRC" = 0 ]' in 몸, "둘을 함께 안 묻는다"


def test_apply_patch_가_기획서를_굽게_알려_준다():
    """★ **도구가 말해 줄 수 있는 것을 사람이 기억하게 두지 않는다**(§152 · §182).
    산출물은 패치에 안 들어오므로(바이너리 · 3MB) 받는 쪽이 굽는다 — 2026-10-11 에
    그 한 줄을 안 알려 줘서 `doctor` 가 「기획서가 생성기보다 낡았다」 로 WARN 했다."""
    sh = (ROOT / "tools/apply_patch.sh").read_text(encoding="utf-8")
    코드 = "\n".join(l for l in sh.split("\n") if not l.lstrip().startswith("#"))
    assert "docs/proposal" in 코드 and "build_proposal.sh" in 코드, \
        "패치가 기획서 생성기를 건드려도 굽는 법을 안 알려 준다"
