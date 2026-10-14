"""`doctor` 의 기계 층 — **키가 아니라 값** · **이름이 아니라 꼴**(DECISIONS §188).

★ **두 도구가 같은 파일에 다른 말을 하고 있었다.** 기계 층(`~/.local/bin/hygiene.sh`)이
  thoth 의 `.env` 에서 **빈 값 넷**을 짚는 동안, thoth 의 `doctor` 는 「빠진 키 없음」 으로
  초록이었다 — **키가 있는지만** 봤기 때문이다. 그래서 `CACHE_TABLE=` 가 비어도 통과했다.
  **남의 도구가 내 사각을 보는 동안 내 검사는 통과를 내고 있었다.**

★ **비어도 되는 키의 정본은 `.env.example` 이다.** 거기서 **비운 채 배포한 키**
  (`TERMINOLOGY_NAME` · `HTTP_*` · `WORKER_TOKEN`)는 비어도 되고, **값을 들고 배포한 키**는
  비면 안 된다. 목록을 손으로 들지 않는다(족 가드 · §91).

★ **홈 규약은 이름 목록이라 썩었다.** `projects` 하나만 허락하고 나머지를 전부 찍어서
  2026-10-13 에 **35줄**이었다 — 그 줄은 아무도 안 읽고, `musicfm` 이 하나 늘어도 안 보였다.
  **꼴로 묶고 안 묶이는 것만 이름을 찍는다.**
"""
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "tools/lib/env.sh"
DOCTOR = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")


def _쉘(명령: str) -> str:
    r = subprocess.run(["bash", "-c", f'. {LIB}; {명령}'], cwd=ROOT,
                       capture_output=True, text=True)
    return r.stdout


def test_값이_있어야_하는_키를_뽑는다(tmp_path):
    보기 = tmp_path / "ex"
    보기.write_text("A=1\nB=\nC=hello world\nD=\n# E=1\n", encoding="utf-8")
    난것 = _쉘(f'env_valued_keys "{보기}"').split()
    assert 난것 == ["A", "C"], 난것


def test_빈_값은_값이_있어야_하는_키가_아니다(tmp_path):
    # ★ `.env.example` 이 **비운 채 배포한 키**는 비어도 된다 — 그게 선언이다.
    보기 = tmp_path / "ex"
    보기.write_text("WORKER_TOKEN=\nHTTP_TOKEN=\nCACHE=file\n", encoding="utf-8")
    assert _쉘(f'env_valued_keys "{보기}"').split() == ["CACHE"]


def test_실물_example_의_선택키_넷이_비어_있다():
    # ★ **이 넷이 비어 있는 것이 정상이라는 선언**이다. 채우면 골든셋과 스모크가 401 을
    #   받는다고 `.env.example` 이 적어 뒀다(WORKER_TOKEN).
    값있는 = set(_쉘(f'env_valued_keys "{ROOT}/.env.example"').split())
    for k in ("TERMINOLOGY_NAME", "WORKER_TOKEN", "HTTP_MODEL", "HTTP_TOKEN"):
        assert k not in 값있는, f"{k} 가 값을 들고 배포된다 — 비어 있어야 한다"


def test_doctor_가_빈_값을_본다():
    # ★ **키 존재만 보던 자리.** 글로 묻는다 — 이 가지는 `.env` 가 있는 기계에서만 돈다.
    토막 = DOCTOR.split("== .env 키 정합 ==")[1].split("== .env 로더 ==")[0]
    assert "env_valued_keys" in 토막, "doctor 가 값 있는 키를 안 뽑는다"
    assert "값이 비었다" in 토막, "빈 값을 알리는 말이 없다"


def test_홈_규약이_이름_목록이_아니다():
    토막 = DOCTOR.split("== 홈 규약 ==")[1].split("echo \"==")[0]
    assert "*.log)" in 토막 and "*.wav|*.mid)" in 토막, "꼴로 안 묶는다"
    # ★ 디렉터리는 **이름을 찍는다** — 새 디렉터리가 홈에 생기는 것은 알아야 할 일이다.
    assert "HOME_DIR" in 토막, "디렉터리를 따로 안 센다"
    assert "projects" in 토막, "저장소가 사는 곳을 규약 안으로 안 둔다"


def test_배시_변수에_한글이_없다():
    # ★ **§186 에 적어 놓고 §188 에서 또 했다.** 배시는 변수 이름에 한글을 안 받는다 —
    #   `로그=0` 은 대입이 아니라 **명령**이고 `bash -n` 은 그것을 문법 오류로 안 본다.
    for rel in ("tools/doctor.sh", "tools/lib/env.sh", "tools/tf.sh", "tools/lib/infra.sh"):
        글 = (ROOT / rel).read_text(encoding="utf-8")
        나쁜 = [l for l in 글.split("\n")
               if re.match(r'^\s*[^\x00-\x7f][^\s=]*=[^=]', l)]
        assert not 나쁜, f"{rel} 에 한글 변수 대입 : {나쁜[:2]}"


def test_배포_게이트의_눈_밖을_적는다():
    # ★ **조직 소유자는 Environment 보호를 지나갈 수 있고 그 사실은 응답에 안 담긴다.**
    #   「승인 없이는 못 민다」 로 읽히면 안 된다(§188).
    # ★ **주석을 지우고 묻는다.** 처음 판은 바로 위 주석에 같은 말이 있어서, `echo` 를
    #   지운 돌연변이가 **그대로 살아남았다** — 「글을 코드로 읽는 검사는 글부터
    #   지운다」 집안의 열두 번째다(§168 · §182 · §185).
    코드 = "\n".join(l for l in DOCTOR.split("\n") if not l.lstrip().startswith("#"))
    토막 = 코드.split("production 에 승인")[1][:600]
    assert 'echo "       이 눈 밖' in 토막, "게이트가 못 보는 것을 **찍지** 않는다"
    assert "지나갈 수 있다" in 토막
