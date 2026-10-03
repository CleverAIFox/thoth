"""인프라 지문 — `tools/lib/infra.sh` 의 `infra_hash`.

★ **지문은 양쪽이 안 틀리게 세는 것이 전부다.** 적는 쪽(`tf.sh apply`)과 보는 쪽
  (`doctor.sh`)이 같은 함수를 부르므로, 이 함수가 맞으면 둘이 갈릴 길이 없다.

★ **무는 것과 안 무는 것을 둘 다 잰다.** 모든 변화에 짖는 지문은 terraform 이
  스스로 쓰는 파일마다 경고를 내고, 그 경고는 곧 안 읽힌다 — 음성 대조가 없으면
  "짖는가" 만 보고 넘어간다(DECISIONS §133).
"""
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
