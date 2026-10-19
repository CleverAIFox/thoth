"""**값이 안 온 것**과 **서버가 안 뜬 것**을 가른다(DECISIONS §194).

★ 2026-10-15 에 이렇게 됐다 :

      export WORKER_URL="$(terraform -chdir=infra output -raw worker_url)"   # 자격증명 만료 → 빈 문자열
      bash tools/smoke.sh
      워커에 닿지 못했다: http://127.0.0.1:8000

  람다를 때리려던 실행이 **로컬 워커 얘기**로 끝났다. 읽는 사람은 `run_worker.sh` 를
  의심하게 되고, **까닭은 URL 이 안 왔다는 것**이었다 — §59 의 세 갈래가 둘로 뭉갠 자리다.

★ **안 설정한 것과 빈 값은 다르다.** 안 설정했으면 로컬 기본값이 맞다. **설정했는데
  비었으면 그것은 사고**이고, 그 자리에서 멈춘다.

그리고 같은 날 **꾸러미 자가진단이 부른 쉘을 읽었다** — `WORKER_TOKEN` 을 export 한
자리에서 핸들러가 인증을 켜고, 탐침은 헤더를 비워 보내므로 401 이 **맞는 답**이 됐다.
코드는 멀쩡하고 검사가 제 환경을 안 통제한 것인데, 터진 모양은 맨 `AssertionError` 였다.
"""
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
SMOKE = ROOT / "tools/smoke.sh"
PKG = ROOT / "tools/package_lambda.sh"


def _돌린다(환경: dict) -> subprocess.CompletedProcess:
    e = dict(os.environ)
    e.pop("WORKER_URL", None)
    e.update(환경)
    return subprocess.run(["bash", str(SMOKE)], cwd=ROOT, env=e,
                          capture_output=True, text=True, timeout=120)


def test_설정했는데_비면_멈춘다():
    r = _돌린다({"WORKER_URL": ""})
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert "설정됐는데 비었다" in r.stderr, r.stderr


def test_멈출_때_값을_만든_명령을_적는다():
    # ★ **잡는 것과 고치는 것은 다른 일이다**(§180). 무엇을 쳐야 하는지 적는다.
    r = _돌린다({"WORKER_URL": ""})
    assert "tf.sh output" in r.stderr, r.stderr


def test_안_설정하면_로컬_기본값으로_간다():
    # ★ **없는 병에 관문을 세우지 않는다**(§133). 안 설정한 것은 사고가 아니다 —
    #   로컬 워커를 때리려는 정상 경로이고, 그 길을 막으면 거짓 빨강이 된다.
    r = _돌린다({})
    assert r.returncode != 2, (r.returncode, r.stdout, r.stderr)
    assert "설정됐는데 비었다" not in r.stderr
    assert "127.0.0.1:8000" in (r.stdout + r.stderr)


def test_빈_값과_안_설정이_다른_말을_한다():
    빈 = _돌린다({"WORKER_URL": ""})
    없 = _돌린다({})
    assert 빈.returncode != 없.returncode, (빈.returncode, 없.returncode)


# ── 꾸러미 자가진단의 환경 ────────────────────────────────────────────────


def _자가진단줄() -> str:
    글 = PKG.read_text(encoding="utf-8")
    i = 글.index('python3 - "$VERIFY"')
    j = 글.rindex("\n", 0, i)
    k = 글.rindex("\n", 0, j)
    return 글[k:i + 40]


def test_자가진단이_환경을_끊는다():
    # ★ **부른 쉘을 안 읽는다.** `env -i` 로 전부 끊고 필요한 것만 도로 넣는다.
    assert "env -i" in _자가진단줄(), _자가진단줄()


def test_자가진단이_엔진과_캐시를_못_박는다():
    # ★ 끊고 나서 **도로 안 넣으면** 이번엔 엔진이 달라진다. 둘 다 있어야 한다.
    줄 = _자가진단줄()
    assert "ENGINE=echo" in 줄 and "CACHE=memory" in 줄, 줄


def test_자가진단이_토큰을_물려받지_않는다():
    # ★ **이것이 2026-10-15 에 터진 자리다.** `env -i` 가 있으면 참이고, 없으면 거짓이다.
    줄 = _자가진단줄()
    assert "WORKER_TOKEN" not in 줄, "토큰을 명시적으로 넘긴다 — 인증이 켜진다"
    assert 줄.strip().startswith("env -i"), 줄


def test_실물로_더러운_쉘에서_돌려_본다():
    # ★ **글만 재면 배선을 안 잰다**(§173). 토큰을 넣고 실제로 굽는다 — `env -i` 가
    #   없으면 여기서 401 로 죽는다.
    e = dict(os.environ, WORKER_TOKEN="시험용가짜토큰")
    r = subprocess.run(["bash", str(PKG)], cwd=ROOT, env=e,
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    assert "fastapi · pydantic · starlette · uvicorn 없이 돈다" in r.stdout
