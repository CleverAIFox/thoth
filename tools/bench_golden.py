"""골든셋을 임의 엔진에 돌려 불변식 위반을 센다.

★ 번역의 '정확도' 를 재지 않는다. 측정할 수 없는 목표는 세우지 않는다
  (MASTER §8). 여기서 재는 것은 검증 가능한 불변식뿐이다.

★ 워커를 HTTP 로 때린다. 엔진을 import 하지 않는 이유는 캐시 · 가드 · 용어집을
  포함한 서빙 경로 전체가 측정 대상이기 때문이다. TestClient 로는 그 경로가
  검증되지 않는다(DECISIONS §10 의 연장).

  bash tools/run_worker.sh &          # 재려는 ENGINE 으로
  python3 tools/bench_golden.py
  python3 tools/bench_golden.py --json out.json    # 비교용 기록
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "worker"))
from app import glossary  # noqa: E402
CASES = ROOT / "worker/tests/golden/cases.json"
GLOSSARY = ROOT / "worker/app/glossary"

HANGUL = re.compile(r"[가-힣]")
# ★ 합니다체에는 의문형이 있다. 평서형(-니다)만 넣고 의문형(-니까)을 빠뜨려,
#   '무엇입니까?' 로 올바르게 끝난 문장을 위반으로 잡았다. 후처리가 만들어
#   내는 형태(인가요 → 입니까)를 검사가 위반으로 세고 있었다.
#   검사가 틀렸는데 숫자만 보고 모델 탓을 하던 것이다(DECISIONS §19 와 같다).
POLITE = re.compile(r"(니다|니까)[.!?)\"']*\s*$")


def load_terms() -> dict[str, str]:
    out: dict[str, str] = {}
    for f in sorted(GLOSSARY.glob("*.json")):
        out.update(json.loads(f.read_text(encoding="utf-8")))
    return out


def translate(url: str, texts: list[str], timeout: int) -> tuple[list[str], float]:
    body = json.dumps({"texts": texts, "target": "ko"}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token := os.environ.get("WORKER_TOKEN", ""):
        headers["X-Thoth-Token"] = token
    req = urllib.request.Request(url, data=body, headers=headers)
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    # ★ 부분 응답에서 계속하면 안 된다. 캐시 히트만으로 잰 품질·처리율은
    #   엔진의 값이 아니고, 그렇게 나온 수치가 baseline.json 에 들어가면
    #   기준선이 조용히 오염된다(DECISIONS §19).
    if data.get("partial"):
        raise SystemExit(f"워커가 부분 응답을 냈다: {data['partial']} — 측정을 멈춘다")
    # ★ **위 주석은 맞는 말을 하면서 `partial` 만 막고 있었다.** 캐시 히트는
    #   200 으로 멀쩡히 돌아오므로 여기를 그냥 지나간다. 2026-09-14 에 그렇게
    #   45유닛이 전부 히트로 돌아와 `199236자/초` 가 찍혔고, 그 수치는 전 엔진이
    #   남긴 번역을 읽은 시간이었다(DECISIONS §64).
    #
    # ★ 워커는 유닛마다 히트 여부를 실어 보낸다(MASTER §4). 계약에 있는 것을
    #   읽지 않아서 못 본 것이지 알 수 없었던 것이 아니다.
    cached = data.get("cached") or [False] * len(data["translations"])
    return data["translations"], time.monotonic() - t0, cached


def prompt_fingerprint(batch: int | None = None) -> str:
    """번역 결과를 정하는 입력의 지문.

    ★ 기준선이 늙었는지를 사람이 기억해서 표시하게 두면, 표시하지 않은 날은
      아무도 모른다. 프롬프트와 용어집이 바뀌면 위반 수가 바뀌므로, 그 둘을
      해시해 기준선에 박아 둔다. 코드가 스스로 늙었다고 말하게 한다.

    ★ 엔진 구현이 아니라 **모델이 보는 것**만 넣는다. 배치 파싱이나 후처리를
      고쳐도 지문이 흔들리면 관계없는 재측정을 요구하게 된다(DECISIONS §22).

    ★ **데이터만 넣으면 조립 로직의 변경을 놓친다.** `as_prompt` 가 용어를
      어떻게 배치하는지도 모델이 보는 것의 일부인데, 2026-09-13 에 그 로직을
      고쳤을 때 지문이 흔들리지 않았다. 고정 표본을 한 번 조립해 그 결과를
      함께 해시한다 — 로직이 바뀌면 출력이 바뀌고, 무관한 수정에는 흔들리지
      않는다(DECISIONS §33).
    """
    from app import engine, glossary

    parts = [engine.SYSTEM, engine.BATCH_RULE]
    for name in sorted(glossary._load()):
        book = glossary._load()[name]
        parts.append(name)
        parts += [f"{en}={ko}" for en, ko in sorted(book.items())]
    # 조립 로직의 지문. 값이 아니라 형태를 본다.
    parts.append(glossary.as_prompt(
        {"record": "레코드", "catalog": "카탈로그", "data catalog": "Data Catalog"}))
    # ★ **배치 크기도 결과를 정하는 입력이다.** 같은 프롬프트라도 몇 유닛을
    #   묶느냐에 따라 위반이 U자를 그린다 — 1·2·3·6·9 에서 9·6·3·5·6 이다
    #   (DECISIONS §51). 지문에 넣지 않으면 기준선이 다른 배치의 값인데도
    #   `doctor` 가 통과한다(DECISIONS §57).
    if batch is not None:
        parts.append(f"batch={batch}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]


def warmup(url: str, timeout: int) -> float:
    """모델을 올려 놓고 그 시간을 집계 밖에 둔다.

    ★ 콜드 실행의 첫 배치에는 번역이 아니라 **모델 로딩**이 들어 있다.
      2026-09-13 실측에서 같은 9유닛 배치가 156.6s 와 79.8s 로 두 배 갈렸고,
      차이 76.8초가 로딩이었다. 어느 쪽을 잡느냐로 처리율이 30 과 23 사이를
      오간다. 재는 사람이 직전에 ollama 를 건드렸는지가 수치를 정하면
      그것은 측정이 아니다(DECISIONS §27).

    ★ **매번 다른 문장을 쓴다.** 고정 문장이면 두 번째 실행부터 캐시 히트라
      모델을 태우지 않는다. 웜업이 조용히 아무것도 하지 않게 된다(§21).
      골든셋 캐시는 실행 전에 비우지만 웜업 문장은 그 대상이 아니다.

    ★ 호스팅 엔진에는 로딩이라는 개념이 없으므로 이 시간이 0 에 가깝다.
      그래도 같은 절차를 태운다 — 엔진마다 다른 절차로 잰 값은 비교되지 않는다.
    """
    nonce = uuid.uuid4().hex
    text = (f"Warm up the inference engine before measurement. "
            f"This sentence is not part of the golden set. Nonce {nonce}.")
    _, dt, _cached = translate(url, [text], timeout)
    return dt


def explain_failure(e: Exception) -> str:
    """실패의 원인을 가려 안내한다.

    ★ `HTTPError` 는 `URLError` 의 하위 클래스라 같은 `except` 에 걸린다.
      둘을 뭉뚱그리면 워커가 502 를 돌려준 경우에도 "워커에 닿지 못했다" 가
      나가고, 시킨 대로 워커를 다시 띄우면 502 가 또 난다. **메시지가 증상을
      말하는 데 그치지 않고 틀린 원인을 단정해 사람을 엉뚱한 곳으로 보낸다**
      (DECISIONS §37).
    """
    if isinstance(e, urllib.error.HTTPError):
        code = ""
        try:
            code = json.loads(e.read()).get("error", "")
        except Exception:
            pass
        if e.code == 502:
            return (f"워커가 엔진 호출에 실패했다 (502 {code}).\n"
                    "  워커는 살아 있다. 엔진 쪽을 본다 —\n"
                    "  ENGINE=local 이면 bash tools/run_ollama.sh & 로 띄운다")
        if e.code == 401:
            return "워커가 토큰을 거부했다 (401). .env 의 WORKER_TOKEN 을 확인한다"
        return f"워커가 {e.code} 를 돌려줬다 ({code})"
    return f"워커에 닿지 못했다: {e}\n  bash tools/run_worker.sh & 로 띄운다"


def worker_engine(url: str, timeout: int) -> str:
    """워커가 어느 엔진으로 떠 있는지. 못 물으면 빈 문자열.

    ★ **결과 파일이 어느 엔진의 값인지 스스로 말해야 한다.** 러너는 HTTP 로만
      붙으므로 엔진을 모르고, 파일 이름과 사람의 기억이 그것을 대신해 왔다.
      `/health` 가 이미 답하고 있었다(MASTER §12).
    """
    health = url.rsplit("/", 1)[0] + "/health"
    try:
        req = urllib.request.Request(health)
        with urllib.request.urlopen(req, timeout=min(timeout, 10)) as r:
            return json.loads(r.read()).get("engine", "")
    except (urllib.error.URLError, OSError, ValueError):
        return ""


# ★ **로컬 전용 축을 호스팅 실행에 적지 않는다.** CPU/GPU 배치 · VRAM · 스왑은
#   ollama 가 이 기계에서 돌 때만 뜻이 있다. 스왑 6400MB 와 123MB 인 두 판이
#   0.2% 안쪽으로 같았으므로, 호스팅에서 그 수치를 기록하면 읽는 사람이 없는
#   상관을 찾는다(DECISIONS §65).
LOCAL_ENGINES = {"local"}


def baseline() -> dict:
    """기준선 전체. 읽지 못하면 빈 dict."""
    try:
        return json.loads((ROOT / "docs/bench/baseline.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def baseline_engine(engine: str) -> dict:
    """엔진 하나의 기준선.

    ★ **엔진마다 파일을 나누지 않는다.** 비교가 목적인 정본이 갈라지면 대조할 때
      둘을 열어야 한다. 한 파일에 엔진 키를 두고 그 안에 배치 · 지문 · 속도 ·
      위반을 담는다(DECISIONS §65).
    """
    return (baseline().get("engines", {}) or {}).get(engine, {}) or {}


def baseline_batch(engine: str) -> int | None:
    """이 엔진의 기준선 배치.

    ★ **기본값을 기준선에서 읽는다.** 전에는 러너 기본이 9 이고 기준선은 3
      이었다. §51 에서 기본 배치를 3 으로 바꾸고 §57 에서 기준선을 갈아 넣으면서
      러너의 기본값만 남았고, `--batch` 를 빠뜨린 실행이 조용히 다른 조건에서
      쟀다. 같은 숫자를 두 곳에 두면 한쪽만 늙는다(DECISIONS §57 · §64).

    ★ **엔진마다 다르다.** `#45` 가 호스팅의 최적 배치를 다시 재면 그 값은 이
      엔진 블록에만 들어간다.
    """
    b = baseline_engine(engine).get("batch")
    try:
        return int(b) if b else None
    except (ValueError, TypeError):
        return None


def baseline_condition(engine: str) -> str:
    """이 엔진의 기준선이 어느 하드웨어 배치에서 나온 값인지. 없으면 빈 문자열."""
    return baseline_engine(engine).get("violations", {}).get("condition", "")


def env_snapshot() -> dict:
    """측정 **중**의 환경. 배치마다 찍어 결과와 함께 남긴다.

    ★ 2026-09-13 에 처리율이 32 → 16자/초로 떨어졌을 때, 원인을 보려고
      측정이 끝난 뒤에 `nvidia-smi` 와 `ollama ps` 를 쳤다. 모델은 이미
      언로드되어 있었고 VRAM 은 비어 있었다. **끝난 뒤의 환경은 측정 중
      환경이 아니다** — 그 진단으로는 아무것도 결론지을 수 없었다(§34).

    ★ 사람이 기억해서 재는 것이 아니라 러너가 같이 남긴다. 이상이 다시
      나타나도 사후 추측이 필요 없다(§31 과 같은 이유).

    ★ 도구가 없으면 조용히 건너뛴다. 이 기록은 측정을 돕는 부속이지
      측정의 전제가 아니다.
    """
    def run(cmd: list[str]) -> str:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return r.stdout.strip()
        except Exception:
            return ""

    snap: dict = {}
    gpu = run(["nvidia-smi",
               "--query-gpu=memory.used,memory.total,temperature.gpu,clocks.sm",
               "--format=csv,noheader,nounits"])
    if gpu:
        f = [x.strip() for x in gpu.splitlines()[0].split(",")]
        if len(f) == 4:
            snap["vram_used"], snap["vram_total"] = f[0], f[1]
            snap["gpu_temp"], snap["gpu_clock"] = f[2], f[3]

    ps = run(["ollama", "ps"]).splitlines()
    if len(ps) > 1:
        # NAME ID SIZE PROCESSOR CONTEXT UNTIL — 열 위치가 판마다 흔들리므로
        # CPU/GPU 가 든 칸을 찾는다. 비율은 **그 앞 칸**에 따로 있어서,
        # 칸 하나만 집으면 `38%/62%` 를 잃고 `CPU/GPU` 만 남는다.
        cols = ps[1].split()
        i = next((k for k, c in enumerate(cols) if "GPU" in c or "CPU" in c), None)
        if i is None:
            snap["processor"] = "?"
        elif i > 0 and "%" in cols[i - 1]:
            snap["processor"] = f"{cols[i - 1]} {cols[i]}"
        else:
            snap["processor"] = cols[i]
        # ★ 오프로딩 여부는 문자열이 아니라 불로 남긴다. 판마다 표기가 달라도
        #   기록을 읽는 쪽이 다시 파싱하지 않아야 한다.
        snap["offloaded"] = "CPU" in snap["processor"]
        # ★ VRAM 이 남아 있는데도 오프로딩되는 이유가 여기 있다. ollama 는
        #   가중치만이 아니라 KV 캐시와 컴퓨트 버퍼도 VRAM 에 넣는다.
        #   컨텍스트를 함께 남기지 않으면 "왜 전부 안 올라갔나" 를 사후에
        #   다시 추측하게 된다(DECISIONS §34 의 재발).
        if len(cols) > i + 1 and cols[i + 1].isdigit():
            snap["context"] = cols[i + 1]
    elif ps:
        snap["processor"] = "모델 없음"

    try:
        info = pathlib.Path("/proc/meminfo").read_text(encoding="utf-8")
        vals = {k: int(v.split()[0]) for k, v in
                (l.split(":", 1) for l in info.splitlines() if ":" in l)}
        snap["mem_free_mb"] = (vals.get("MemAvailable", 0)) // 1024
        snap["swap_used_mb"] = (vals.get("SwapTotal", 0) - vals.get("SwapFree", 0)) // 1024
    except (OSError, ValueError):
        pass
    return snap


def check(unit: dict, ko: str, book: dict[str, str]) -> list[str]:
    """불변식 위반 목록. 빈 리스트가 통과다."""
    src, bad = unit["text"], []
    low = src.lower()

    # 1. 고유명사 · API명은 영어로 남는다 (MASTER §7-2 규칙 1)
    for tok in unit.get("keep", []):
        if tok not in ko:
            bad.append(f"keep:{tok}")

    # 2. 등재 용어는 등재된 한국어 표기를 쓴다 (MASTER §8)
    #
    # ★ 세 가지를 먼저 뺀다. 실측에서 term 위반 4건이 전부 오탐이었다.
    #   - 긴 용어에 포함된 짧은 용어. consumer application 을 올바르게
    #     옮기면 consumer 검사가 반드시 실패한다
    #   - keep 토큰에 포함된 용어. Data Catalog 를 영어로 유지하는 것이
    #     규칙 1 이고, 그때 catalog 검사가 실패한다. 규칙 1 이 이긴다
    #   - 원문에 없는 용어. 케이스의 terms 가 넉넉하게 적혀 있어도 된다
    # ★ **케이스의 `terms` 를 보지 않는다.** 그것은 사람이 손으로 적는데
    #   프롬프트는 원문에서 자동으로 고른다. 두 목록이 다르면 차이나는 자리는
    #   **지시만 하고 검사하지 않는다** — 실측에서 15개 유닛이 그랬고 위반
    #   3건이 그 그늘에 있었다(DECISIONS §49).
    #
    # ★ 그래서 프롬프트가 쓰는 것과 같은 함수를 쓴다. 같은 질문에 답이 둘이면
    #   하나는 틀렸다(§28 · §30 · §32 의 재발).
    terms = list(glossary._hits(book, low))
    terms = [t for t in terms
             if not any(t != o and t in o for o in terms)]
    for en in terms:
        want = book.get(en)
        if not want:
            continue
        # ★ 규칙 1 이 우선하는지는 케이스의 keep 이 아니라 원문이 정한다.
        #   원문에 대문자로 시작하는 고유명사가 있으면 영어 유지가 맞고,
        #   그때 소문자 등재 용어 검사는 성립하지 않는다. keep 을 빠짐없이
        #   적으라는 규약은 사람 손에 기대므로 지켜지지 않는다(DECISIONS §18).
        if re.search(rf"\b[A-Z]\w*\s+{re.escape(en.split()[-1])}\b", src, re.I) \
           and en not in src:
            continue
        if want not in ko:
            bad.append(f"term:{en}→{want}")

    # 3. 물음표 보존. 원문이 물으면 번역도 물어야 한다 (MASTER §7-2 규칙 5)
    if src.rstrip().endswith("?") and not ko.rstrip().endswith("?"):
        bad.append("물음표 소실")

    # 4. 길이 비율.
    #
    # ★ 영한 번역의 정상 비율은 0.44~0.53 으로 좁다(2026-09-13 실측 18유닛).
    #   한국어가 영어보다 짧다는 것을 모르고 처음에 상한을 2.0 으로 잡았는데,
    #   그것은 정상의 네 배라 1.91 짜리 환각을 통과시켰다. 실측으로 다시
    #   잡는다 — 기준선을 모르고 정한 임계값은 검사가 아니다.
    ratio = len(ko) / max(len(src), 1)
    if ratio > unit["ratio_max"]:
        bad.append(f"길이 {ratio:.2f}배 (덧붙임)")
    elif ratio < unit.get("ratio_min", 0):
        bad.append(f"길이 {ratio:.2f}배 (누락)")

    # 5. 합니다체 (MASTER §7-2 규칙 3)
    if not POLITE.search(ko):
        bad.append("합니다체 아님")

    # 6. 번역이 되긴 했는가. echo 엔진은 여기서 전부 걸린다
    if not HANGUL.search(ko):
        bad.append("한글 없음")

    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000/translate")
    ap.add_argument("--batch", type=int, default=None,
                    help="한 요청에 실을 유닛 수. 기본은 기준선의 배치다")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--json", help="결과를 이 경로에 기록한다")
    ap.add_argument("--no-warmup", action="store_true",
                    help="웜업을 건너뛴다. 콜드 로딩 비용을 재려는 경우에만 쓴다")
    a = ap.parse_args()

    eng = worker_engine(a.url, a.timeout)
    print(f"  엔진 {eng or '(모름 — /health 에 닿지 못했다)'}")

    if a.batch is None:
        a.batch = baseline_batch(eng)
        if a.batch is None:
            print(f"기준선에 engines.{eng or '?'}.batch 가 없다 — --batch 를 직접 준다")
            return 1
        print(f"  배치 {a.batch} (기준선의 {eng} 값)")

    book = load_terms()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    units = [u for q in cases for u in q["units"]]
    if not units:
        print("케이스가 없다"); return 1

    # ★ 웜업은 집계 밖이다. 이 시간을 총 시간에 더하면 콜드 로딩이 처리율에
    #   섞인다. 값 자체는 버리지 않고 따로 보고한다 — 로딩 비용은 그 자체로
    #   알 만한 수치이고, 0 에 가까우면 이미 웜이었다는 뜻이다.
    warm = None
    if not a.no_warmup:
        try:
            warm = warmup(a.url, a.timeout)
        except urllib.error.URLError as e:
            print(explain_failure(e))
            return 1
        print(f"  웜업 {warm:6.1f}s  (집계 제외)", flush=True)

    rows, elapsed, chars, envs = [], 0.0, 0, []
    hits = 0
    for i in range(0, len(units), a.batch):
        chunk = units[i:i + a.batch]
        try:
            out, dt, cached = translate(a.url, [u["text"] for u in chunk], a.timeout)
            hits += sum(1 for c in cached if c)
        except urllib.error.URLError as e:
            print(explain_failure(e))
            return 1
        elapsed += dt
        for u, ko in zip(chunk, out):
            chars += len(u["text"])
            rows.append({"id": u["id"], "kind": u["kind"], "ko": ko,
                         "bad": check(u, ko, book)})
        # ★ 호스팅 엔진에서는 로컬 환경을 재지 않는다. 재면 없는 상관을 찾게 된다.
        env = env_snapshot() if eng in LOCAL_ENGINES else {}
        envs.append(env)
        tail = ""
        if env.get("offloaded"):
            tail += f"  [{env['processor']} — 오프로딩]"
        elif env.get("processor") and env["processor"] != "모델 없음":
            tail += f"  [{env['processor']}]"
        if env.get("vram_used"):
            tail += f"  VRAM {env['vram_used']}/{env['vram_total']}"
        if env.get("swap_used_mb", 0) > 0:
            tail += f"  swap {env['swap_used_mb']}MB"
        print(f"  {i + len(chunk):>3}/{len(units)}  {dt:6.1f}s{tail}", flush=True)

    # ---- 보고 ----
    fail = [r for r in rows if r["bad"]]
    print(f"\n{'=' * 60}\n유닛 {len(rows)} · 통과 {len(rows) - len(fail)} · 위반 {len(fail)}")
    # ★ **히트가 하나라도 있으면 속도를 적지 않는다.** 숫자를 적고 옆에 경고를
    #   붙이면 그 숫자가 인용된다. 재지 못한 자리에는 값을 쓰지 않는다
    #   (DECISIONS §59 · §64).
    if hits:
        print(f"총 {elapsed:.1f}s · {chars}자 · 처리율 없음 (캐시 히트 {hits}/{len(rows)})")
    else:
        print(f"총 {elapsed:.1f}s · {chars}자 · {chars / max(elapsed, 1e-9):.0f}자/초")
    print(f"프롬프트 지문 {prompt_fingerprint(a.batch)}  (배치 {a.batch})")
    if warm is None:
        print("웜업 없음 — 이 처리율에는 모델 로딩이 섞여 있다")
    else:
        print(f"웜업 {warm:.1f}s (집계 제외)")

    # ★ 오프로딩 자체는 결함이 아니다. VRAM 이 모델보다 작으면 그것이 이
    #   기계의 정상 상태다. 문제는 **배치가 실행마다 달라지는 것**이다 —
    #   비율이 달라지면 속도도 번역 결과도 달라진다(DECISIONS §36).
    # ★ **캐시 히트는 이 엔진이 낸 값이 아니다.** 속도만이 아니라 위반도
    #   그렇다 — 히트로 돌아온 문장은 전에 다른 엔진이 번역한 것이다. 한 판에서
    #   위반은 쓰고 속도는 버릴 수 있지만(MASTER §11-4), 그것은 같은 엔진이
    #   번역했을 때의 이야기다.
    if hits:
        print(f"\n경고 : 캐시 히트 {hits}/{len(rows)} — 이 값은 측정이 아니다")
        print("       히트한 유닛은 전 엔진이 남긴 번역이다. 속도도 위반도 쓰지 않는다.")
        print("       캐시를 비우거나 이번 실행만 다른 파일로 보낸다 :")
        print("       ENGINE=<엔진> CACHE_FILE=/tmp/bench-cache.json bash tools/run_worker.sh")

    # ★ **지문을 찍어만 두고 대조하지 않고 있었다.** §57 이 지문에 배치를 넣은
    #   이유가 기준선과 갈리는 것을 잡기 위해서인데, 러너는 출력만 하고 아무와도
    #   비교하지 않았다. 정본이 있는데 대조를 안 하면 정본이 아니다.
    base_fp = baseline_engine(eng).get("prompt_fingerprint", "")
    now_fp = prompt_fingerprint(a.batch)
    if base_fp and base_fp != now_fp:
        print(f"\n경고 : 프롬프트 지문이 기준선과 다르다 — 이번 {now_fp} · 기준선 {base_fp}")
        print("       프롬프트 · 용어집 · 배치 중 하나가 바뀌었다. 같은 조건이 아니다.")

    if eng not in LOCAL_ENGINES:
        print(f"\n엔진 {eng or '?'} — 로컬 환경(CPU/GPU 배치 · VRAM · 스왑)을 재지 않았다")
    else:
        procs = {e["processor"] for e in envs if e.get("processor")}
        if len(procs) > 1:
            print(f"\n경고 : 실행 중에 배치가 바뀌었다 — {' · '.join(sorted(procs))}")
            print("       한 실행 안에서 조건이 달라졌으므로 이 값은 쓸 수 없다.")
        elif procs:
            only = procs.pop()
            base = baseline_condition(eng)
            if base and base != only:
                print(f"\n경고 : 배치가 기준선과 다르다 — 이번 {only} · 기준선 {base}")
                print("       속도도 위반 수도 이 값으로 기준선을 갱신하지 않는다.")
            else:
                print(f"\n배치 {only} · 기준선과 같다")

    tally: dict[str, int] = {}
    for r in fail:
        for b in r["bad"]:
            tally[b.split(":")[0]] = tally.get(b.split(":")[0], 0) + 1
    if tally:
        print("\n위반 종류")
        for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
            print(f"  {k:12} {v}")

    if fail:
        print("\n상세 (앞 8건)")
        for r in fail[:8]:
            print(f"  [{r['id']}] {', '.join(r['bad'])}")
            print(f"    {r['ko'][:90]}")

    if a.json:
        pathlib.Path(a.json).write_text(
            json.dumps({"units": len(rows), "fail": len(fail),
                        "engine": eng,
                        # ★ 히트가 있으면 초 자체가 번역 시간이 아니다.
                        "cache_hits": hits,
                        "valid": hits == 0,
                        "seconds": round(elapsed, 1), "chars": chars,
                        "prompt_fingerprint": now_fp,
                        "baseline_fingerprint": base_fp,
                        "batch": a.batch,
                        "env": envs,
                        "warmup": warm is not None,
                        "warmup_seconds": None if warm is None else round(warm, 1),
                        "rows": rows}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"\n기록 → {a.json}")

    # 0 위반 없음 · 2 위반 있음 · 3 측정 무효(캐시 히트)
    if hits:
        return 3
    return 0 if not fail else 2


if __name__ == "__main__":
    sys.exit(main())
