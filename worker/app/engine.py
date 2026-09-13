"""번역 엔진. ENGINE 환경변수로 고른다.

echo      과금 없음. DOM · 렌더링 작업용.
translate AWS Translate. 비교 대상이다. Custom Terminology 는 쓰지 않는다
          — AWS 전용이라 엔진을 바꾸면 이식되지 않는다(PLAN §4). TERMINOLOGY_NAME
          은 비교 실험용 훅으로만 남긴다.
local     Ollama. 로컬 GPU 추론이라 호출 비용이 0 이다.

★ temperature 0 + 고정 seed 를 쓴다. LLM 은 같은 입력에 다른 출력을 내는데,
  캐시가 최초 결과를 영구 고정하므로 흔들린 결과가 그대로 박제된다.

★ 긴 지문에서 모델이 번역을 마친 뒤 스스로 답을 이어 붙인다. 문풀 도구에서는
  정답 누설이고, 지어낸 답이 틀리기까지 한다. 규칙 5 로 금지한다.

★ 서비스명을 영어로 두라고만 지시하면 뒤에 조사가 붙지 않아 비문이 된다
  ("Kinesis Data Streams 거의 즉시..."). 조사 부착을 예시와 함께 명시한다.
"""
import json
import os
import re
import urllib.request

from . import glossary

ENGINE = os.environ.get("ENGINE", "echo")
REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
TERMINOLOGY = os.environ.get("TERMINOLOGY_NAME", "")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "exaone3.5:7.8b")

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


def translate_batch(texts: list[str]) -> list[str]:
    return [postprocess(src, ko) for src, ko in zip(texts, _raw_batch(texts))]


def _raw_batch(texts: list[str]) -> list[str]:
    if ENGINE == "echo":
        return [f"[KO] {t}" for t in texts]

    if ENGINE == "local":
        # 배치 전체로 용어집을 고른다. 항목별로 고르면 같은 페이지 안에서
        # 서로 다른 용어집이 걸려 표기가 갈린다.
        _, terms = glossary.match(texts)
        system = SYSTEM + glossary.as_prompt(terms)
        # 순차 호출이다. ollama 는 슬롯 하나로 직렬 처리하므로 병렬화해도
        # GPU 에서 다시 줄을 선다.
        return [_ollama(t, system) for t in texts]

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
