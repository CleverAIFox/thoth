#!/usr/bin/env bash
# Lambda 배포 zip 을 만든다.
#
#   bash tools/package_lambda.sh
#
# ★ **의존성을 넣지 않는다.** `app` 이 모듈 최상위에서 부르는 서드파티는 없고,
#   `boto3` · `botocore` 는 `cache` · `guard` · `engine` 이 함수 안에서 늦게
#   부르며 Lambda 런타임이 제공한다. 그래서 패키지가 우리 코드와 용어집 JSON
#   뿐이고 콜드스타트가 짧다(DECISIONS §68).
#
# ★ **`main.py` 와 `preflight.py` 는 뺀다.** 전자는 FastAPI 를 최상위에서 부르고
#   후자는 개발 도구다. 넣어도 import 되지 않아 무해하나, **넣지 않는 것과 넣고
#   안 쓰는 것은 다르다** — 넣어 두면 언젠가 누가 import 한다.
#
# ★ **주장을 검사로 만든다.** 만든 zip 을 풀어 `fastapi` · `pydantic` ·
#   `starlette` · `uvicorn` import 를 막은 상태에서 핸들러를 실제로 부른다.
#   "의존성이 없다" 는 말은 그렇게만 확인된다(DECISIONS §17).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

OUT="$ROOT/dist/worker.zip"

# ★ **`zip` · `unzip` 을 부르지 않는다.** 저장소는 이미 `python3` 에 의존하고
#   `zipfile` 이 표준 라이브러리다. 외부 도구를 하나 더 요구하면 그것이 없는
#   기계에서 배포가 막힌다 — 실제로 막혔다.
mkdir -p "$ROOT/dist"
python3 - "$ROOT" "$OUT" <<'EOF'
import pathlib
import sys
import zipfile

root, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
# ★ **담을 것을 한 곳이 센다**(DECISIONS §145). 패키저가 목록을 들고 검사가 따로 들면
#   둘 다 초록이면서 갈린다 — §132 · §133 과 같은 자리다.
sys.path.insert(0, str(root / "tools" / "lib"))
import pkg                                    # noqa: E402

# ★ **결정적으로 만든다.** 타임스탬프가 들어가면 내용이 같아도 해시가 매번
#   달라지고, terraform 이 `source_code_hash` 로 그것을 보므로 **고친 것이
#   없어도 배포가 돈다.** 시각을 고정하고 순서를 정렬한다(DECISIONS §72).
FIXED = (1980, 1, 1, 0, 0, 0)      # zipfile 이 담을 수 있는 가장 이른 시각

# ★ **코드가 읽겠다고 적은 것이 전부 담기는지 먼저 본다**(DECISIONS §145). 담고 나서
#   보면 늦다 — 틀린 zip 이 이미 만들어져 있고 그것이 배포된다.
빠진것 = pkg.missing(root)
if 빠진것:
    print("코드가 읽는데 zip 에 안 담기는 것이 있다 :", file=sys.stderr)
    for x in 빠진것:
        print(f"  {x}", file=sys.stderr)
    raise SystemExit(2)

files = pkg.files(root)

out.unlink(missing_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for src, name in files:
        info = zipfile.ZipInfo(name, date_time=FIXED)
        info.external_attr = 0o644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, src.read_bytes())

print(f"zip : {out}")
print(f"      {out.stat().st_size // 1024}KB · 파일 {len(files)}개")
print(f"      뺀 것 : {' '.join(sorted(pkg.EXCLUDE))}")
EOF

echo
echo "== 의존성 없이 도는가 =="
VERIFY="$(mktemp -d)"
trap 'rm -rf "$VERIFY"' EXIT
python3 -c "import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" \
  "$OUT" "$VERIFY"

# ★ **부른 쉘을 안 읽는다**(DECISIONS §194). 전에는 `ENGINE` · `CACHE` 만 못 박고
#   나머지는 그대로 물려받았다. 2026-10-15 에 `WORKER_TOKEN` 을 export 해 둔 쉘에서
#   부르자 핸들러가 인증을 켰고, 아래 탐침은 `headers: {}` 로 부르므로 **401 이 맞는
#   답**이 됐다 — 그런데 터진 모양은 맨 `AssertionError` 였다. **코드는 멀쩡하고
#   검사가 제 환경을 안 통제한 것**인데, 읽는 사람에게는 「배포 꾸러미가 깨졌다」 로 보인다.
# ★ **CI 에는 그 변수가 없어 영영 안 밟히는 가지였다**(§182). 사람 손에서만 터진다.
# ★ `env -i` 로 전부 끊고 **필요한 것만 도로 넣는다.** 목록을 늘리려면 **왜 필요한지**를
#   여기 적는다 — 안 적히면 그 줄이 다음 사고의 입구다.
env -i PATH="$PATH" HOME="$HOME" LANG="${LANG:-C.UTF-8}" \
    ENGINE=echo CACHE=memory python3 - "$VERIFY" <<'EOF'
import importlib.abc
import json
import sys

BLOCK = {"fastapi", "pydantic", "starlette", "uvicorn"}


class Block(importlib.abc.MetaPathFinder):
    """Lambda 런타임에 없는 것을 부르면 여기서 죽는다."""

    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCK:
            raise ImportError(f"배포 패키지가 {name} 을 import 한다")
        return None


sys.meta_path.insert(0, Block())
sys.path.insert(0, sys.argv[1])

from app import lambda_handler as lh   # noqa: E402


def ev(method, path, body=None):
    return {"rawPath": path,
            "requestContext": {"http": {"method": method, "path": path}},
            "headers": {}, "body": body, "isBase64Encoded": False}


health = lh.handler(ev("GET", "/health"))
assert health["statusCode"] == 200, health
print("  OK   /health", json.loads(health["body"])["version"])

tr = lh.handler(ev("POST", "/translate", json.dumps({"texts": ["hello"]})))
assert tr["statusCode"] == 200, tr
print("  OK   /translate", json.loads(tr["body"])["translations"])

bad = lh.handler(ev("POST", "/translate", "{"))
assert bad["statusCode"] == 400, bad
print("  OK   깨진 본문 400")

print("  OK   fastapi · pydantic · starlette · uvicorn 없이 돈다")
EOF

echo
echo "다음 : cd infra && terraform apply"
