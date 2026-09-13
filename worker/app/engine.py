"""번역 엔진. ENGINE 환경변수로 고른다.

echo      과금 없음. DOM · 렌더링 작업용.
translate AWS Translate. 비교 대상이다. Custom Terminology 는 쓰지 않는다
          — AWS 전용이라 엔진을 바꾸면 이식되지 않는다(PLAN §4). TERMINOLOGY_NAME
          은 비교 실험용 훅으로만 남긴다.
local     Ollama. 로컬 GPU 추론이라 호출 비용이 0 이다.
bedrock   Bedrock Converse. 배포본 후보다. 로컬과 같은 프롬프트·후처리를
          타므로 골든셋으로 `docs/bench/baseline.json` 과 직접 비교된다.

★ temperature 0 + 고정 seed 를 쓴다. LLM 은 같은 입력에 다른 출력을 내는데,
  캐시가 최초 결과를 영구 고정하므로 흔들린 결과가 그대로 박제된다.

★ 긴 지문에서 모델이 번역을 마친 뒤 스스로 답을 이어 붙인다. 문풀 도구에서는
  정답 누설이고, 지어낸 답이 틀리기까지 한다. 규칙 5 로 금지한다.

★ 서비스명을 영어로 두라고만 지시하면 뒤에 조사가 붙지 않아 비문이 된다
  ("Kinesis Data Streams 거의 즉시..."). 조사 부착을 예시와 함께 명시한다.
"""
import json
import logging
import os
import re
import urllib.request

from . import glossary

log = logging.getLogger("thoth")


ENGINE = os.environ.get("ENGINE", "echo")
REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
TERMINOLOGY = os.environ.get("TERMINOLOGY_NAME", "")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "exaone3.5:7.8b")

# ★ 리전을 AWS_REGION 과 따로 둔다. Bedrock 은 모델마다 제공 리전이 다르고,
#   ap-northeast-2 에 없는 모델을 골랐다는 이유로 캐시·카운터까지 다른 리전으로
#   옮기게 되면 안 된다.
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", REGION)
BEDROCK_MODEL = os.environ.get("BEDROCK_MODEL", "apac.amazon.nova-lite-v1:0")
BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "2048"))

# 용어 보존을 학습이 아니라 지시로 한다. Custom Terminology 와 달리
# 이 프롬프트는 어느 모델에나 그대로 옮겨간다.
SYSTEM = (
    "Translate English to Korean.\n"
    "Rules:\n"
    "1. Keep AWS service names, API names, and parameter names in English "
    "(e.g. Kinesis Data Streams, DecreaseStreamRetentionPeriod, shard).\n"
    "2. Attach Korean particles to them naturally "
    "(예: Kinesis Data Streams는, S3에). Write grammatical Korean.\n"
    "3. Use the 합니다 style.\n"
    "4. Output ONLY the translation. No notes, no original text.\n"
    "5. Translate ONLY what is written. Never answer, explain, continue, "
    "or add information that is not in the source. If the source ends with "
    "a question, the translation ends with that question.\n"
    "6. Keep the output length close to the source."
)

# ─── 후처리 ───────────────────────────────────────────────────────────
#
# ★ 프롬프트로 잡히지 않는 것을 코드로 잡는다. 규칙 5(원문에 없는 내용 추가
#   금지)와 규칙 3(합니다체)은 실측에서 각각 새어 나갔다(PLAN §2-2 #14).
#   프롬프트를 더 만지는 것은 값이 싸지 않다 — 규칙을 추가하면 다른 규칙의
#   결과가 달라진다(DECISIONS §4).
#
# ★ 후처리는 결정적이다. 같은 입력에 같은 출력이므로 골든셋으로 검증되고,
#   엔진을 바꿔도 그대로 따라간다. 엔진별로 다시 만들 필요가 없다.

# 하십시오체 · 해요체 종결을 합니다체로. 문장 끝에서만 바꾼다.
_ENDINGS = [
    (re.compile(r"하십시오(\s*[.!?]*)\s*$"), r"합니다\1"),
    (re.compile(r"하시기 바랍니다(\s*[.!?]*)\s*$"), r"합니다\1"),
    (re.compile(r"하세요(\s*[.!?]*)\s*$"), r"합니다\1"),
    (re.compile(r"([가-힣])세요(\s*[.!?]*)\s*$"), r"\1십니다\2"),
    (re.compile(r"인가요(\s*[?]*)\s*$"), r"입니까\1"),
    # ★ '하나요' 는 '하'+'나요' 가 아니라 어간 '하' 에 -나요 가 붙은 것이다.
    #   일반 규칙(\1습니까)을 태우면 '하습니까' 라는 비문이 나온다. 어간이
    #   모음으로 끝나는 경우를 따로 둔다.
    (re.compile(r"하나요(\s*[?]*)\s*$"), r"합니까\1"),
    (re.compile(r"되나요(\s*[?]*)\s*$"), r"됩니까\1"),
    (re.compile(r"([가-힣])나요(\s*[?]*)\s*$"), r"\1습니까\2"),
    (re.compile(r"([가-힣])까요(\s*[?]*)\s*$"), r"\1습니까\2"),
]


def _truncate_after_question(src: str, ko: str) -> str:
    """원문이 물음표로 끝나면 번역도 거기서 끝난다.

    긴 지문에서 모델이 번역을 마친 뒤 스스로 답을 이어 붙인다. 문풀 도구에서
    이것은 정답 누설이고, 지어낸 답이 틀리기까지 한다(DECISIONS §4).
    """
    if not src.rstrip().endswith("?"):
        return ko
    cut = ko.rfind("?")
    if cut == -1:
        return ko
    # 물음표 뒤에 뭔가 더 있으면 그것은 원문에 없던 것이다.
    return ko[: cut + 1].rstrip()


def _fix_endings(ko: str) -> str:
    """마지막 문장의 종결어미를 합니다체로 맞춘다."""
    lines = ko.split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if not lines[i].strip():
            continue
        for pat, rep in _ENDINGS:
            new = pat.sub(rep, lines[i])
            if new != lines[i]:
                lines[i] = new
                break
        break
    return "\n".join(lines)


# 원문에 없는 마크다운을 모델이 붙인다. 오버레이는 평문을 그대로 렌더하므로
# 별표가 화면에 보인다. 원문에 없는 강조만 벗긴다.
_MD = re.compile(r"\*\*(.+?)\*\*", re.S)


def _strip_markdown(src: str, ko: str) -> str:
    if "**" in src:
        return ko
    return _MD.sub(r"\1", ko).replace("**", "")


def postprocess(src: str, ko: str) -> str:
    """엔진 출력에 공통으로 거는 후처리. 순서가 중요하다 —
    답을 잘라낸 뒤에 종결어미를 보아야 잘린 문장의 끝을 본다."""
    ko = _strip_markdown(src, ko.strip())
    ko = _truncate_after_question(src, ko)
    return _fix_endings(ko)


# ─── 배치 ─────────────────────────────────────────────────────────────
#
# ★ 항목마다 따로 호출하면 모델이 앞 항목을 보지 못해 같은 용어가 갈린다.
#   한 페이지 안에서 Data Catalog 를 유지한 항목과 번역한 항목이 섞였고,
#   producer 가 한 곳에서만 오타로 나왔다(PLAN §2-2 #14 실측).
#
# ★ 묶으면 정렬이 깨질 위험이 생긴다. 1번 보기 자리에 2번 번역이 붙는 것은
#   없는 것보다 나쁘다(DECISIONS §1). 그래서 번호를 붙여 보내고, 파싱이
#   어긋나면 개별 호출로 되돌린다. 느려지는 것이 틀리는 것보다 낫다.

BATCH_MARK = "§"          # 원문에 나타나지 않는 문자를 구분자로 쓴다
_MARK_RE = re.compile(rf"^\s*{BATCH_MARK}\s*(\d+)\s*$", re.M)

BATCH_RULE = (
    "\n\nThe input contains multiple numbered segments. Each segment starts "
    f"with a line containing only {BATCH_MARK} followed by its number.\n"
    f"Output the same markers in the same order, each on its own line, "
    "followed by the translation of that segment.\n"
    "Translate every segment. Do not merge, reorder, or skip any segment.\n"
    "Use consistent terminology across all segments."
)


def _join(texts: list[str]) -> str:
    return "\n\n".join(f"{BATCH_MARK} {i}\n{t}" for i, t in enumerate(texts))


def _split(raw: str, n: int) -> list[str] | None:
    """번호 표시로 되쪼갠다. 하나라도 어긋나면 None — 호출자가 되돌린다."""
    parts: dict[int, str] = {}
    marks = list(_MARK_RE.finditer(raw))
    if len(marks) != n:
        return None
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(raw)
        idx = int(m.group(1))
        if idx in parts:
            return None                 # 번호 중복
        body = raw[m.end():end].strip()
        if not body:
            return None                 # 빈 조각
        parts[idx] = body
    if set(parts) != set(range(n)):
        return None                     # 번호 누락
    return [parts[i] for i in range(n)]


_client = None


def _translate_client():
    global _client
    if _client is None:
        import boto3
        _client = boto3.client("translate", region_name=REGION)
    return _client


def _ollama(text: str, system: str) -> str:
    body = json.dumps({
        "model": OLLAMA_MODEL,
        "system": system,
        "prompt": text,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "seed": 42},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())["response"].strip()


_bedrock = None


def _bedrock_client():
    global _bedrock
    if _bedrock is None:
        import boto3
        _bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    return _bedrock


def _converse(text: str, system: str) -> str:
    """Bedrock Converse API.

    ★ `invoke_model` 을 쓰지 않는다. 요청 본문 스키마가 모델마다 달라
      모델을 바꾸면 이 함수를 다시 쓰게 된다. Converse 는 그 차이를 감추므로
      #35 에서 모델을 바꿔도 `BEDROCK_MODEL` 값만 바뀐다.

    ★ seed 를 넘기지 않는다. Converse 의 공통 필드가 아니고 모델마다 지원이
      갈린다. 결정성은 temperature 0 에 기댄다.
    """
    r = _bedrock_client().converse(
        modelId=BEDROCK_MODEL,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": text}]}],
        inferenceConfig={"temperature": 0, "maxTokens": BEDROCK_MAX_TOKENS},
    )
    return r["output"]["message"]["content"][0]["text"].strip()


def _llm_batch(texts: list[str], call) -> list[str]:
    """LLM 공통 배치 경로. 엔진은 '한 프롬프트를 처리하는 함수' 만 다르다.

    ★ 이 경로를 엔진 분기 안에 두면 엔진을 추가할 때마다 용어집 선택 · 배치
      규약 · 폴백이 복제된다. 그것들은 엔진의 성질이 아니라 이 도구의 성질이다.
    """
    # 배치 전체로 용어집을 고른다. 항목별로 고르면 같은 페이지 안에서
    # 서로 다른 용어집이 걸려 표기가 갈린다.
    _, terms = glossary.match(texts)
    system = SYSTEM + glossary.as_prompt(terms)

    if len(texts) > 1:
        # ★ 용어집을 배치 규칙 뒤에 다시 둔다. 프롬프트가 길어지면 중간에
        #   놓인 지시가 묻힌다. 실측에서 배치 전환 후 term 위반이 2 → 4 로
        #   늘었고, 일관성은 생겼으나 용어집과 다른 표기로 통일됐다.
        batch_system = SYSTEM + BATCH_RULE + glossary.as_prompt(terms)
        try:
            out = _split(call(_join(texts), batch_system), len(texts))
        except Exception:
            out = None
        if out is not None:
            return out
        log.warning("배치 파싱 실패 — 개별 호출로 되돌린다 (n=%d)", len(texts))

    # ★ 개별 폴백은 과금 엔진에서 호출 수가 n 배가 된다. 로컬에서는 시간만
    #   잃지만 호스팅에서는 그대로 돈이므로 경고로 남겨 빈도를 보게 한다.
    return [call(t, system) for t in texts]


def translate_batch(texts: list[str]) -> list[str]:
    return [postprocess(src, ko) for src, ko in zip(texts, _raw_batch(texts))]


def _raw_batch(texts: list[str]) -> list[str]:
    if ENGINE == "echo":
        return [f"[KO] {t}" for t in texts]

    if ENGINE == "local":
        # ollama 는 슬롯 하나로 직렬 처리하므로 개별 폴백을 병렬화해도
        # GPU 에서 다시 줄을 선다.
        return _llm_batch(texts, _ollama)

    if ENGINE == "bedrock":
        return _llm_batch(texts, _converse)

    if ENGINE == "translate":
        c = _translate_client()
        out = []
        for t in texts:
            kw = {"Text": t, "SourceLanguageCode": "en", "TargetLanguageCode": "ko"}
            if TERMINOLOGY:
                kw["TerminologyNames"] = [TERMINOLOGY]
            out.append(c.translate_text(**kw)["TranslatedText"])
        return out

    raise NotImplementedError(f"engine={ENGINE}")
