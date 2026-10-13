"""인프라 지문 — `tools/lib/infra.sh` 의 `infra_hash`.

★ **지문은 양쪽이 안 틀리게 세는 것이 전부다.** 적는 쪽(`tf.sh apply`)과 보는 쪽
  (`doctor.sh`)이 같은 함수를 부르므로, 이 함수가 맞으면 둘이 갈릴 길이 없다.

★ **무는 것과 안 무는 것을 둘 다 잰다.** 모든 변화에 짖는 지문은 terraform 이
  스스로 쓰는 파일마다 경고를 내고, 그 경고는 곧 안 읽힌다 — 음성 대조가 없으면
  "짖는가" 만 보고 넘어간다(DECISIONS §133).
"""
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "tools/lib/infra.sh"


def 지문(d: pathlib.Path) -> str:
    r = subprocess.run(
        ["bash", "-c", f'. "{LIB}"; infra_hash "$1"', "_", str(d)],
        capture_output=True, text=True)
    return r.stdout.strip()


def 나무(tmp_path: pathlib.Path) -> pathlib.Path:
    i = tmp_path / "infra"
    i.mkdir()
    (i / "main.tf").write_text('resource "aws_lambda_function" "worker" {}\n')
    (i / "oidc.tf").write_text('data "aws_iam_policy_document" "ci" {}\n')
    (i / "terraform.tfvars").write_text('worker_token = "s3cret"\n')
    (i / ".terraform.lock.hcl").write_text('provider "aws" { version = "5.0.0" }\n')
    return tmp_path


def test_같은_나무는_같은_지문이다(tmp_path):
    r = 나무(tmp_path)
    assert 지문(r) == 지문(r) != ""


def test_tf_내용이_바뀌면_문다(tmp_path):
    r = 나무(tmp_path)
    before = 지문(r)
    (r / "infra/main.tf").write_text('resource "aws_lambda_function" "worker" { timeout = 30 }\n')
    assert 지문(r) != before


def test_tfvars_가_바뀌면_문다(tmp_path):
    # ★ **git 이 추적하지 않는 파일이다.** 추적 파일만 봤다면 토큰 · 엔진 교체가
    #   지문을 안 바꾸고, 그러면 `engine = "http"` 로 갈아 놓고 apply 를 잊어도
    #   `doctor` 가 초록이다 — **그 자리가 #59 다.**
    r = 나무(tmp_path)
    before = 지문(r)
    (r / "infra/terraform.tfvars").write_text('worker_token = "s3cret"\nengine = "http"\n')
    assert 지문(r) != before


def test_이름만_바뀌어도_문다(tmp_path):
    r = 나무(tmp_path)
    before = 지문(r)
    (r / "infra/oidc.tf").rename(r / "infra/iam.tf")
    assert 지문(r) != before


def test_파일을_지워도_문다(tmp_path):
    r = 나무(tmp_path)
    before = 지문(r)
    (r / "infra/oidc.tf").unlink()
    assert 지문(r) != before


def test_terraform_이_스스로_쓰는_것은_안_문다(tmp_path):
    # ★ 음성 대조. 상태 · plan 산출물 · 받아 둔 프로바이더가 지문을 흔들면
    #   `plan` 한 번에 경고가 뜨고, 그 경고는 기본값이 되어 안 읽힌다.
    r = 나무(tmp_path)
    before = 지문(r)
    (r / "infra/.terraform").mkdir()
    (r / "infra/.terraform/providers").write_text("아무거나")
    (r / "infra/terraform.tfstate").write_text('{"serial": 42}')
    (r / "infra/terraform.tfstate.backup").write_text('{"serial": 41}')
    (r / "infra/tfplan").write_bytes(b"\x00binary")
    (r / "infra/ci.tfplan").write_bytes(b"\x00binary")
    assert 지문(r) == before


def test_infra_가_없으면_빈손으로_통과하지_않는다(tmp_path):
    # ★ 없는 것을 0 으로 세면 `doctor` 가 "맞다" 고 말한다. 실패로 돌려
    #   SKIP 으로 떨어뜨린다(§59).
    r = subprocess.run(
        ["bash", "-c", f'. "{LIB}"; infra_hash "$1"', "_", str(tmp_path)],
        capture_output=True, text=True)
    assert r.returncode != 0
    assert r.stdout.strip() == ""


def test_infra_가_비어_있어도_끝난다(tmp_path):
    # ★ **`xargs` 가 인자 없이 `sha256sum` 을 부르면 멈춘다** 고 생각해 `-r` 을
    #   붙이고 그 멈춤을 재는 시험을 썼다. 깨뜨려 보니 **안 멈췄다** — `xargs` 는
    #   자식의 표준입력을 `/dev/null` 로 바꿔 준다. 없는 병에 관문을 세우고 있었다.
    #   `-r` 은 남겨 둔다(쓸모없는 프로세스 하나를 안 띄운다). 재는 것은 **끝나는가**
    #   하나다(DECISIONS §133).
    (tmp_path / "infra").mkdir()
    r = subprocess.run(
        ["bash", "-c", f'. "{LIB}"; infra_hash "$1"', "_", str(tmp_path)],
        capture_output=True, text=True, timeout=10, input="남의 입력")
    assert r.returncode == 0
    assert len(r.stdout.strip()) == 64


def test_도장_자리는_캐시_안이다(tmp_path):
    # ★ `.cache/` 는 gitignore 다. 도장이 커밋되면 **다른 기계의 적용 기록**이
    #   이 기계의 사실로 둔갑한다.
    r = subprocess.run(
        ["bash", "-c", f'. "{LIB}"; infra_stamp "$1"', "_", "/x"],
        capture_output=True, text=True)
    assert r.stdout.strip() == "/x/.cache/infra-applied"


def test_파일을_만든_차례가_달라도_같은_지문이다(tmp_path):
    """★ **`find` 는 디렉터리 항목 차례로 낸다** — 그 차례는 파일을 만든 순서와
    파일시스템에 달렸다. 정렬을 빼면 **같은 나무가 기계마다 다른 지문**을 내고,
    그러면 도장이 늘 어긋나 「인프라가 뒤처졌다」 가 **아무 이유 없이** 뜬다.

    ★ 돌연변이 `차례를 안 맞춘다` 가 이 자리를 문다(DECISIONS §179). 처음 판에는
      이 검사가 없어서 **`| LC_ALL=C sort -z` 를 `| cat` 으로 바꿔도 시험이 전부
      통과했다** — 정렬이 있다는 것을 아무도 안 보고 있었다.
    """
    def 짓는다(뿌리: pathlib.Path, 차례: list[str]) -> pathlib.Path:
        i = 뿌리 / "infra"
        i.mkdir(parents=True)
        for 이름 in 차례:
            (i / 이름).write_text(f"# {이름}\n", encoding="utf-8")
        return 뿌리

    이름들 = [f"z{n:02d}.tf" for n in range(40)]
    가 = 짓는다(tmp_path / "가", 이름들)
    나 = 짓는다(tmp_path / "나", list(reversed(이름들)))
    assert 지문(가) == 지문(나) != "", "만든 차례가 지문을 바꾼다 — 정렬이 빠졌다"


def test_해싱_앞에_정렬이_있다():
    """★ **이 기계에서는 그 성질을 못 잰다.** 위 검사는 만든 차례를 뒤집어도
    통과하고, **정렬을 빼도 통과한다** — 이 파일시스템의 `find` 가 이미 이름
    차례로 내주기 때문이다. 그래서 「같은 나무면 같은 지문」 은 **여기서는
    정렬 없이도 참**이다.

    ★ **못 재는 자리를 좁히고 그 자리를 적는다**(DECISIONS §73 · §179). 성질을
      못 재면 **기전을 잰다** — 해싱 앞에 정렬이 있는가. 정렬은 이 기계를 위한
      것이 아니라 **`find` 차례가 다른 기계**를 위한 것이고, 그 기계는 여기 없다.

    ★ **`LC_ALL=C` 까지 본다.** 로캘이 섞이면 같은 이름 집합이 기계마다 다른
      차례로 서고, 그러면 정렬을 넣고도 지문이 갈린다.
    """
    글 = LIB.read_text(encoding="utf-8")
    몸 = 글[글.index("infra_hash()"):글.index("infra_stamp()")]
    본문 = "\n".join(l for l in 몸.split("\n") if not l.lstrip().startswith("#"))
    정렬 = 본문.find("LC_ALL=C sort -z")
    해싱 = 본문.find("sha256sum")
    assert 정렬 >= 0, "해싱 앞에 `LC_ALL=C sort -z` 가 없다 — 기계마다 지문이 갈린다"
    assert 정렬 < 해싱, "정렬이 해싱 뒤에 있다"
    assert "-print0" in 본문 and "sort -z" in 본문, "널 구분자가 한쪽에만 있다"

# ── 186 : 커밋되는 적용 기록 ────────────────────────────────────────────────
#
# ★ **그 눈이 적용하는 기계에만 있었다.** 도장이 `.cache/` 라 clone 에 없고,
#   전체 지문은 `terraform.tfvars` 를 포함해 **CI 가 재현할 수 없다**(§186).
#   그래서 추적분 지문을 따로 내어 `tools/infra_applied.json` 으로 커밋한다.
#
# ★ **`plan` 으로 안 간 까닭 셋을 다 쟀다** — ① `-refresh=false` 는 실물을 안 읽어
#   콘솔 표류를 못 본다 ② 읽으려면 `lambda:GetFunction` 이 들고 거기
#   `WORKER_TOKEN` 이 평문이다(§131) ③ `tfvars` 없는 CI 의 plan 은 **없는 변경**이
#   떠서 거짓 빨강이 된다.

도장 = ROOT / "tools/infra_applied.json"


def _쉘(명령: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f". {LIB}; {명령}"],
                          cwd=ROOT, capture_output=True, text=True)


def test_추적분_지문이_난다():
    r = _쉘(f'infra_hash_tracked "{ROOT}"')
    assert r.returncode == 0, r.stderr
    assert len(r.stdout.strip()) == 64, r.stdout


def test_추적_안_되는_파일은_추적분_지문에_안_든다(tmp_path):
    # ★ **이것이 CI 가 잴 수 있다는 말의 전부다.** `terraform.tfvars` 가 들면
    #   clone 에서는 영원히 다른 값이 나온다 — 그러면 커밋해 둘 수가 없다.
    tf = ROOT / "infra/terraform.tfvars"
    있었나 = tf.exists()
    옛 = tf.read_bytes() if 있었나 else None
    전 = _쉘(f'infra_hash_tracked "{ROOT}"').stdout.strip()
    try:
        tf.write_text('engine = "echo"\n', encoding="utf-8")
        중 = _쉘(f'infra_hash_tracked "{ROOT}"').stdout.strip()
        전체 = _쉘(f'infra_hash "{ROOT}"').stdout.strip()
        tf.write_text('engine = "http"\n', encoding="utf-8")
        후 = _쉘(f'infra_hash_tracked "{ROOT}"').stdout.strip()
        전체2 = _쉘(f'infra_hash "{ROOT}"').stdout.strip()
    finally:
        if 있었나:
            tf.write_bytes(옛)
        else:
            tf.unlink(missing_ok=True)
    assert 전 == 중 == 후, "추적분 지문이 gitignore 된 파일을 보고 있다"
    # ★ **전체 지문은 여전히 본다** — 그 눈을 약하게 만든 것이 아니다.
    assert 전체 != 전체2, "전체 지문이 tfvars 변화를 못 본다 — 로컬 눈이 죽었다"


def test_전체_지문과_추적분_지문은_다른_값이다():
    a = _쉘(f'infra_hash "{ROOT}"').stdout.strip()
    b = _쉘(f'infra_hash_tracked "{ROOT}"').stdout.strip()
    assert a and b and a != b, "둘이 같으면 하나는 쓸모가 없다"


def test_커밋되는_도장이_있고_지금_추적분과_같다():
    assert 도장.is_file(), "커밋되는 적용 기록이 없다"
    d = json.loads(도장.read_text(encoding="utf-8"))
    지금 = _쉘(f'infra_hash_tracked "{ROOT}"').stdout.strip()
    assert d["추적지문"] == 지금, (
        "infra/ 의 추적 파일이 마지막 적용 기록과 다르다 — "
        "올렸으면 tools/tf.sh apply 를 돌리고 이 파일을 같이 커밋한다")


def test_도장이_못_보는_것을_적어_둔다():
    # ★ **「통과」 가 「맞다」 가 아니다**(§59). 한계가 안 적혀 있으면 다음 사람이
    #   이 초록을 「인프라가 실물과 같다」 로 읽는다.
    글 = 도장.read_text(encoding="utf-8")
    for 낱말 in ("tfvars", "표류", "못"):
        assert 낱말 in 글, f"도장이 한계를 안 적는다 — `{낱말}` 이 없다"


def test_도장에_비밀이_안_담긴다():
    # ★ 담기는 것은 **해시 하나와 때**뿐이다. 전체 지문조차 안 적는다 — tfvars 가
    #   바뀌었다는 사실까지 밖으로 낼 까닭이 없다.
    d = json.loads(도장.read_text(encoding="utf-8"))
    칸 = {k for k in d if not k.startswith("_")}
    assert 칸 == {"추적지문", "올린때"}, f"적는 칸이 늘었다 : {칸}"
    전체 = _쉘(f'infra_hash "{ROOT}"').stdout.strip()
    assert 전체 not in 도장.read_text(encoding="utf-8"), "전체 지문을 적어 뒀다"


def test_tf_가_두_도장을_다_찍는다():
    글 = (ROOT / "tools/tf.sh").read_text(encoding="utf-8")
    몸 = 글.split('if [ "$RC" = 0 ]; then')[1]
    assert "infra_stamp" in 몸 and "infra_hash " in 몸.replace("infra_hash_tracked", "")
    assert "infra_public_stamp" in 몸 and "infra_hash_tracked" in 몸
    # ★ **부르는 것만으로는 안 찍힌다.** 추적분 지문을 적는 줄이 **그 자리로** 흘러야
    #   한다 — `> /dev/null` 로 바꾸면 로컬은 멀쩡하고 **CI 만 빨개진다**(§186).
    적는줄 = [l for l in 몸.split("\n") if "infra_hash_tracked" in l]
    assert 적는줄, "추적분 지문을 적는 줄이 없다"
    assert '"$WHEN" > "$PUB"' in 몸, (
"추적분 지문이 도장 파일로 안 간다 — 적고도 버리면 CI 만 빨개진다")
    # ★ **올리다 만 것은 안 적는다.** 두 도장 다 `RC = 0` 안에 있어야 한다.
    밖 = 글.split('if [ "$RC" = 0 ]; then')[0]
    assert "infra_public_stamp" not in 밖, "실패한 apply 뒤에도 도장을 찍는다"


def test_doctor_가_두_범위에서_다_본다():
    글 = (ROOT / "tools/doctor.sh").read_text(encoding="utf-8")
    assert "infra_hash_tracked" in 글, "doctor 가 추적분 지문을 안 본다"
    # --repo(= CI) 범위에서 **SKIP 이 아니라 판정**이어야 한다
    자리 = 글.index("infra_hash_tracked")
    토막 = 글[자리 - 900:자리 + 1800]
    assert "인프라 적용 시차 (기계 상태다)" not in 토막, "CI 범위가 아직 통째로 SKIP 이다"
    assert "fail " in 토막, "CI 범위가 어긋남을 FAIL 로 안 낸다"


def test_변수_이름이_ASCII_다():
    # ★ **배시는 변수 이름에 한글을 안 받는다**(§123). `공개=...` 는 대입이 아니라
    #   **명령**으로 읽히고 `bash -n` 은 그것을 문법 오류로 안 본다 — shellcheck 가
    #   잡았다. 그 자리를 다시 만들지 않게 묻는다.
    import re
    for rel in ("tools/tf.sh", "tools/lib/infra.sh", "tools/doctor.sh"):
        글 = (ROOT / rel).read_text(encoding="utf-8")
        나쁜 = [l for l in 글.split("\n")
               if re.match(r'^\s*[^\x00-\x7f][^\s=]*=[^=]', l)]
        assert not 나쁜, f"{rel} 에 한글 변수 대입이 있다 : {나쁜[:2]}"


def test_커밋되는_도장이_정말_커밋되는_자리에_있다():
    # ★ **이 파일이 clone 에 없으면 전부 헛일이다.** 자리를 함수에 묻고, 그 자리가
    #   **git 이 무시하지 않는 곳**인지 확인한다 — `.cache/` 로 돌아가면 CI 는 다시
    #   눈을 잃고, 그런데도 로컬 검사는 통과한다(§186).
    r = _쉘(f'infra_public_stamp "{ROOT}"')
    자리 = pathlib.Path(r.stdout.strip())
    assert 자리.is_file(), f"도장이 없다 : {자리}"
    # ★ **묻는 것은 「무시되지 않음」 이지 「이미 추적됨」 이 아니다.** 패치를 막 붙인
    #   나무에서는 아직 `git add` 전이라 추적되지 않는다 — 거기서 빨개지면 **고칠
    #   것이 없는 빨강**이고, 그런 빨강은 검사를 끄게 만든다(§126).
    무시 = subprocess.run(["git", "check-ignore", "-q", str(자리)], cwd=ROOT)
    assert 무시.returncode != 0, f"도장 자리가 gitignore 다 — CI 가 못 본다 : {자리}"
