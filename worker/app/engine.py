"""번역 엔진. ENGINE 환경변수로 고른다.

echo      과금 없음. DOM · 렌더링 작업용.
translate AWS Translate. Custom Terminology 를 붙일 자리.
llm       미구현. A/B 비교 대상 (PLAN §3 #37).
"""
import os

ENGINE = os.environ.get("ENGINE", "echo")
REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
TERMINOLOGY = os.environ.get("TERMINOLOGY_NAME", "")

_client = None


def _translate_client():
    global _client
    if _client is None:
        import boto3
        _client = boto3.client("translate", region_name=REGION)
    return _client


def translate_batch(texts: list[str]) -> list[str]:
    if ENGINE == "echo":
        return [f"[KO] {t}" for t in texts]

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
