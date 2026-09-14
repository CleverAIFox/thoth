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
app = root / "worker" / "app"
EXCLUDE = {"main.py", "preflight.py"}

# ★ **결정적으로 만든다.** 타임스탬프가 들어가면 내용이 같아도 해시가 매번
#   달라지고, terraform 이 `source_code_hash` 로 그것을 보므로 **고친 것이
#   없어도 배포가 돈다.** 시각을 고정하고 순서를 정렬한다(DECISIONS §72).
FIXED = (1980, 1, 1, 0, 0, 0)      # zipfile 이 담을 수 있는 가장 이른 시각

files = []
for f in sorted(app.glob("*.py")):
    if f.name not in EXCLUDE:
        files.append((f, f"app/{f.name}"))
for f in sorted((app / "glossary").rglob("*.json")):
    files.append((f, f"app/glossary/{f.name}"))

out.unlink(missing_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for src, name in files:
        info = zipfile.ZipInfo(name, date_time=FIXED)
        info.external_attr = 0o644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, src.read_bytes())

print(f"zip : {out}")
print(f"      {out.stat().st_size // 1024}KB · 파일 {len(files)}개")
print(f"      뺀 것 : {' '.join(sorted(EXCLUDE))}")
EOF

echo
echo "== 의존성 없이 도는가 =="
VERIFY="$(mktemp -d)"
trap 'rm -rf "$VERIFY"' EXIT
python3 -c "import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" \
  "$OUT" "$VERIFY"

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
