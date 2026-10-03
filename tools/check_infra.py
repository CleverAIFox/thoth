#!/usr/bin/env python3
"""인프라 선언 ↔ 인프라 선언 — 같은 부모에 같은 종류가 둘 붙었는가.

    python3 tools/check_infra.py        0 통과 · 1 어긋남

★ **AWS 의 설정 자원 상당수는 부모마다 하나다.** S3 의 lifecycle · versioning ·
  public access block · policy · encryption, 람다의 function URL … `Put...` 호출이
  **전체를 덮어쓴다.** 같은 부모에 둘을 선언하면 terraform 이 둘 다 만들려 들고
  **나중에 돈 쪽만 살아남는다.** plan 은 매번 바꾸겠다고 나오지만 apply 는
  **영원히 수렴하지 않는다** — 그리고 `fmt` 도 `validate` 도 이것을 모른다.

★ **2026-09-28 에 실제로 났다**(DECISIONS §134). `aws_s3_bucket_lifecycle_configuration`
  이 같은 버킷에 둘이었고 닷새 동안 `errors/` · `athena/` 가 만료 없이 쌓였다.

★ **종류 목록을 들지 않는다.** 「lifecycle 이 둘인가」 로 적으면 **다음에 versioning 이
  둘이어도 조용하다.** 묻는 것은 **「같은 부모에 같은 종류가 둘 있나」** 하나다(족 가드).
  겹쳐도 되는 자리(`aws_iam_role_policy` 를 한 역할에 여럿 등)는 자원에
  `# 겹침 허용 : <까닭>` 을 적어 선언한다 — **지금 그 선언이 하나도 없다.** 병을 재고
  관문을 세웠다.

★ **부모를 못 찾은 짝도 센다 — 다만 「붙는 자원」 만.** 처음에는 부모 인자가 없는 자원을
  전부 울렸더니 `aws_iam_role` 다섯과 로그 그룹 둘이 걸렸다. 그것들은 **부모가 없는 것이
  정상인 윗자리 자원**이다. **모든 것에 우는 규칙은 아무 말도 안 하는 규칙과 같다.**
  그래서 다른 자원을 가리키는 것(`aws_X.Y.Z`)이 **있는데** 그 인자 이름을 모르는 짝만
  말한다 — 그것이 진짜 시야 밖이다(§59).

★ **파일만 읽는다.** AWS 에 닿지 않고 자격증명도 안 쓴다 — 그래서 `--repo` 범위 안이고
  **CI 가 이것은 볼 수 있다.** §133 이 못 한 자리를 이 검사는 덮는다.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

_자원 = re.compile(r'^resource\s+"([a-z0-9_]+)"\s+"([a-z0-9_]+)"\s*\{', re.M)

# ★ **몸은 다음 **아무** 최상위 블록에서 끝난다.** 처음에는 다음 `resource` 까지로 잘랐더니
#   사이에 낀 `data` 블록이 앞 자원의 몸으로 딸려 들어왔다 — `aws_iam_role` 다섯이 전부
#   「다른 자원을 가리킨다」 로 읽힌 까닭이다. 그 자원들의 `data.aws_iam_policy_document`
#   가 가리키고 있었다. **답은 맞았는데 몸이 틀렸다**(DECISIONS §134).
_블록 = re.compile(
    r'^(?:resource|data|locals|variable|output|module|provider|terraform)\b', re.M)

# 부모를 가리키는 인자 이름. AWS 공급자가 쓰는 관용 이름들이다.
부모이름 = (
    "bucket", "function_name", "role", "role_name", "user_name", "group_name",
    "repository", "repository_name", "log_group_name", "table_name", "api_id",
    "rest_api_id", "domain_name", "cluster_name", "queue_url", "topic_arn",
    "vpc_id", "load_balancer_arn", "listener_arn", "distribution_id",
    "stream_name", "delivery_stream_name", "db_instance_identifier",
    "secret_id", "parameter_group_name", "resource_arn", "policy_arn",
)
_부모 = re.compile(
    r'^\s*(' + "|".join(부모이름) + r')\s*=\s*(\S.*?)\s*$', re.M)

# ★ 다른 **자원**을 가리키는 꼴. `data.` 로 시작하는 것은 자료원이지 부모가 아니다.
_자원참조 = re.compile(r'(?<!\w)(?<!\.)aws_[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+')

_겹침허용 = re.compile(r'#\s*겹침 허용\s*:')


def 민몸(몸: str) -> str:
    """주석을 지운다. 주석 속 예시가 부모로 읽히면 안 된다."""
    return "\n".join(줄.split("#", 1)[0] for 줄 in 몸.split("\n"))


def 자원들(글: str):
    """(종류, 이름, 부모, 겹침 허용인가, 붙는 자원인가) 를 선언 순서로 낸다.

    부모는 아는 인자 이름에서 읽는다. 못 읽었을 때 **다른 자원을 가리키기는 하는지**가
    「윗자리 자원」 과 「모르는 이름으로 붙은 자원」 을 가른다.
    """
    경계 = [m.start() for m in _블록.finditer(글)] + [len(글)]
    for m in _자원.finditer(글):
        끝 = next(b for b in 경계 if b > m.start() + 1)
        몸 = 글[m.end():끝]
        속 = 민몸(몸)
        부모 = _부모.search(속)
        yield (m.group(1), m.group(2),
               부모.group(2) if 부모 else None,
               bool(_겹침허용.search(몸)),
               bool(_자원참조.search(속)))


def duplicate_parents(파일들: dict[str, str]) -> list[str]:
    """같은 종류 · 같은 부모가 둘 이상인 자리. 선언한 것은 뺀다."""
    묶음: dict[tuple[str, str], list[tuple[str, str, bool]]] = {}
    눈먼: dict[str, list[tuple[str, str]]] = {}
    for 파일, 글 in sorted(파일들.items()):
        for 종류, 이름, 부모, 허용, 붙는다 in 자원들(글):
            if 부모 is not None:
                묶음.setdefault((종류, 부모), []).append((파일, 이름, 허용))
            elif 붙는다:
                눈먼.setdefault(종류, []).append((파일, 이름))

    fails = []
    for (종류, 부모), 것들 in sorted(묶음.items()):
        if len(것들) < 2 or all(허용 for _, _, 허용 in 것들):
            continue
        자리 = " · ".join(f"{f}:{n}" for f, n, _ in 것들)
        fails.append(
            f"{종류} 가 같은 부모({부모})에 {len(것들)}개다 — {자리}. "
            f"**부모마다 하나인 설정이면 둘이 서로를 덮어쓰고 apply 가 수렴하지 않는다.** "
            f"하나로 합치거나, 겹쳐도 되는 자리면 그 자원에 `# 겹침 허용 : <까닭>` 을 적는다")

    for 종류, 것들 in sorted(눈먼.items()):
        if len(것들) < 2:
            continue
        자리 = " · ".join(f"{f}:{n}" for f, n in 것들)
        fails.append(
            f"{종류} 가 {len(것들)}개이고 다른 자원을 가리키는데 **부모 인자를 못 찾았다** — {자리}. "
            f"이 짝은 이 검사의 시야 밖이다. 부모 인자 이름을 `check_infra.py` 의 "
            f"`부모이름` 에 더하거나, 부모가 없는 자원이면 그대로 둔다")
    return fails


def 읽기(root: pathlib.Path = ROOT) -> dict[str, str]:
    d = root / "infra"
    if not d.is_dir():
        return {}
    return {f.name: f.read_text(encoding="utf-8") for f in sorted(d.glob("*.tf"))}


def main() -> int:
    파일들 = 읽기()
    if not 파일들:
        print("infra/ 에 .tf 가 없다")
        return 0
    fails = duplicate_parents(파일들)
    for x in fails:
        print(f"    {x}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
