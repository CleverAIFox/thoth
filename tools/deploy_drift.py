"""배포본이 이 커밋의 코드인지 본다.

  python3 tools/deploy_drift.py                      # AWS 에 묻는다
  python3 tools/deploy_drift.py --remote <해시>      # 해시를 받아 비교만 한다

Lambda 는 배포된 zip 의 `CodeSha256` 을 들고 있고 `package_lambda.sh` 가 만드는
zip 은 결정적이다(DECISIONS §72). 그래서 두 수가 같으면 배포본이 이 코드다.

★ **CI 에서 돈다. `doctor` 가 부르지 않는다.** 로컬에서는 네트워크 · 자격증명 ·
  zip 유무 · 작업 트리 상태가 제각각이라 "못 쟀다" 가 기본값이 되고, 못 쟀다는
  말이 기본값이면 아무도 읽지 않는다. ollama 가 죽자 무관한 검사까지 멈춘 것과
  같은 자리다(§60). **전제가 항상 참인 곳에 검사를 둔다.**

★ **못 재면 실패다.** 여기서는 네트워크도 자격증명도 항상 있다. 없으면 그것이
  고칠 일이지 넘어갈 일이 아니다. 로컬 `doctor` 의 WARN 관용을 그대로 옮기면
  **검사를 끄는 방법이 생긴다**(§54).

★ **zip 을 만들지 않는다.** 검사가 산출물을 만들면 상태를 바꾸는 검사가 된다.
  `package_lambda.sh` 를 먼저 부르는 것은 워크플로의 일이다.

★ **단가 · 리전 · 함수명을 기억으로 적지 않는다.** 함수명은 인자이고 기본값은
  terraform 의 `local.name` 과 같은 `thoth-worker` 다. 바뀌면 여기가 틀린다.

  0  같다
  1  못 쟀다 — AWS 에 묻지 못했거나 zip 이 없다
  2  다르다 — 배포본이 이 커밋의 코드가 아니다
"""
import argparse
import base64
import hashlib
import json
import pathlib
import subprocess
import sys

ZIP = "dist/worker.zip"
FUNCTION = "thoth-worker"
REGION = "ap-northeast-2"


def local_hash(path: str) -> str:
    """Lambda 의 `CodeSha256` 과 같은 형식 — sha256 원문을 base64 로 적는다.

    ★ 16진수가 아니다. `sha256sum` 의 출력과 비교하면 영원히 다르다.
    """
    return base64.b64encode(hashlib.sha256(pathlib.Path(path).read_bytes()).digest()).decode()


def parse_remote(stdout: str) -> str:
    """`aws lambda get-function` 의 응답에서 해시만 꺼낸다.

    ★ **`--query` 로 짜내지 않고 전체를 받아 여기서 읽는다.** CLI 의 질의 문법이
      바뀌면 조용히 빈 문자열이 오고, 빈 문자열은 비교에서 '다르다' 가 된다.
      **파싱 실패는 실패로 드러나야 한다.**
    """
    return json.loads(stdout)["Configuration"]["CodeSha256"]


def remote_hash(function: str, region: str, profile: str | None) -> tuple[str | None, str | None]:
    """AWS 에 묻는다. **이 함수 하나만 네트워크에 닿는다.**

    ★ 샌드박스에서 실행해 볼 수 없는 유일한 자리라 얇게 둔다. 판정과 형식은
      바깥에 있고 검사가 덮는다. `apply` 후 첫 실호출이 IAM 의 유일한 검사인
      것과 같은 구조다(§73).
    """
    cmd = ["aws", "lambda", "get-function", "--function-name", function, "--region", region]
    if profile:
        cmd += ["--profile", profile]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"aws 를 부르지 못했다 — {e}"
    if r.returncode != 0:
        return None, (r.stderr.strip().splitlines() or ["알 수 없는 실패"])[-1]
    try:
        return parse_remote(r.stdout), None
    except (ValueError, KeyError) as e:
        return None, f"응답을 읽지 못했다 — {e}"


def report(local: str, remote: str) -> tuple[int, str]:
    if local == remote:
        return 0, f"배포본이 이 코드다 — {local}"
    return 2, (
        "배포본이 이 커밋의 코드가 아니다\n"
        f"  이 커밋 : {local}\n"
        f"  배포본   : {remote}\n"
        "  bash tools/package_lambda.sh && bash tools/tf.sh apply"
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--zip", default=ZIP)
    ap.add_argument("--function", default=FUNCTION)
    ap.add_argument("--region", default=REGION)
    ap.add_argument("--profile", default=None)
    ap.add_argument("--remote", default=None, help="해시를 직접 넘긴다. AWS 를 부르지 않는다")
    a = ap.parse_args(argv)

    if not pathlib.Path(a.zip).exists():
        print(f"못 쟀다 : {a.zip} 이 없다 — bash tools/package_lambda.sh", file=sys.stderr)
        return 1

    remote, why = (a.remote, None) if a.remote else remote_hash(a.function, a.region, a.profile)
    if remote is None:
        print(f"못 쟀다 : {why}", file=sys.stderr)
        return 1

    code, text = report(local_hash(a.zip), remote)
    print(text, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
