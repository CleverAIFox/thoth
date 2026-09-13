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
    return data["translations"], time.monotonic() - t0


def prompt_fingerprint() -> str:
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
    _, dt = translate(url, [text], timeout)
    return dt


def baseline_condition() -> str:
    """기준선이 어느 배치에서 나온 값인지. 없으면 빈 문자열."""
    try:
        d = json.loads((ROOT / "docs/bench/baseline.json").read_text(encoding="utf-8"))
        return d.get("violations", {}).get("condition", "")
    except (OSError, ValueError):
        return ""


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
    # ★ 원문에 용어가 있는지를 `t in low` 로 보면 단어 내부에 박힌 것까지
    #   걸린다. `ProvisionedThroughputExceededException` 안의 throughput 이
    #   그렇게 잡혀, 원문에 단독으로 나오지도 않는 용어의 표기를 요구했다.
    #   같은 질문에 `glossary._hits` 는 굴절 패턴으로 답하고 여기는 부분
    #   문자열로 답하고 있었다. 답이 둘이면 하나는 틀렸다(DECISIONS §28).
    terms = [t for t in unit.get("terms", [])
             if re.search(rf"\b{re.escape(t)}(s|es|ing|ed)?\b", low)]
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
    ap.add_argument("--batch", type=int, default=9,
                    help="한 요청에 실을 유닛 수. 9 는 실사용 한 문항")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--json", help="결과를 이 경로에 기록한다")
    ap.add_argument("--no-warmup", action="store_true",
                    help="웜업을 건너뛴다. 콜드 로딩 비용을 재려는 경우에만 쓴다")
    a = ap.parse_args()

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
            print(f"워커에 닿지 못했다: {e}\n  bash tools/run_worker.sh & 로 띄운다")
            return 1
        print(f"  웜업 {warm:6.1f}s  (집계 제외)", flush=True)

    rows, elapsed, chars, envs = [], 0.0, 0, []
    for i in range(0, len(units), a.batch):
        chunk = units[i:i + a.batch]
        try:
            out, dt = translate(a.url, [u["text"] for u in chunk], a.timeout)
        except urllib.error.URLError as e:
            print(f"워커에 닿지 못했다: {e}\n  bash tools/run_worker.sh & 로 띄운다")
            return 1
        elapsed += dt
        for u, ko in zip(chunk, out):
            chars += len(u["text"])
            rows.append({"id": u["id"], "kind": u["kind"], "ko": ko,
                         "bad": check(u, ko, book)})
        env = env_snapshot()
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
    print(f"총 {elapsed:.1f}s · {chars}자 · {chars / max(elapsed, 1e-9):.0f}자/초")
    print(f"프롬프트 지문 {prompt_fingerprint()}")
    if warm is None:
        print("웜업 없음 — 이 처리율에는 모델 로딩이 섞여 있다")
    else:
        print(f"웜업 {warm:.1f}s (집계 제외)")

    # ★ 오프로딩 자체는 결함이 아니다. VRAM 이 모델보다 작으면 그것이 이
    #   기계의 정상 상태다. 문제는 **배치가 실행마다 달라지는 것**이다 —
    #   비율이 달라지면 속도도 번역 결과도 달라진다(DECISIONS §36).
    procs = {e["processor"] for e in envs if e.get("processor")}
    if len(procs) > 1:
        print(f"\n경고 : 실행 중에 배치가 바뀌었다 — {' · '.join(sorted(procs))}")
        print("       한 실행 안에서 조건이 달라졌으므로 이 값은 쓸 수 없다.")
    elif procs:
        only = procs.pop()
        base = baseline_condition()
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
                        "seconds": round(elapsed, 1), "chars": chars,
                        "prompt_fingerprint": prompt_fingerprint(),
                        "env": envs,
                        "warmup": warm is not None,
                        "warmup_seconds": None if warm is None else round(warm, 1),
                        "rows": rows}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"\n기록 → {a.json}")

    return 0 if not fail else 2


if __name__ == "__main__":
    sys.exit(main())
