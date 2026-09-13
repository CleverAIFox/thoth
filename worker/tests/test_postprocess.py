"""후처리. 엔진 없이 검증한다 — 결정적이기 때문이다."""
import os
os.environ.setdefault("ENGINE", "echo")
os.environ.setdefault("CACHE", "memory")

from app.engine import postprocess


def test_물음표_뒤의_답을_잘라낸다():
    src = "Which condition must the team confirm?"
    ko = "팀이 확인해야 하는 조건은 무엇입니까?\n\n답은 다음과 같습니다: 체크포인트를 확인합니다."
    assert postprocess(src, ko) == "팀이 확인해야 하는 조건은 무엇입니까?"


def test_원문이_묻지_않으면_자르지_않는다():
    src = "The stream retains records for 168 hours."
    ko = "스트림은 레코드를 168시간 보관합니다. 왜 그럴까요? 설정 때문입니다."
    assert postprocess(src, ko) == ko


def test_하십시오체를_합니다체로():
    src = "Confirm the checkpoint position."
    assert postprocess(src, "체크포인트 위치를 확인하십시오.").endswith("확인합니다.")


def test_인가요를_입니까로():
    src = "Which change reduces latency?"
    out = postprocess(src, "지연 시간을 줄이는 변경은 무엇인가요?")
    assert out.endswith("무엇입니까?")


def test_이미_합니다체면_그대로다():
    src = "The change applies to the entire stream."
    ko = "변경은 전체 스트림에 적용됩니다."
    assert postprocess(src, ko) == ko


def test_여러_문단이면_마지막만_본다():
    src = "Explain the behavior."
    ko = "첫 문단입니다.\n\n두 번째 문단을 확인하십시오."
    out = postprocess(src, ko)
    assert out.startswith("첫 문단입니다.")
    assert out.endswith("확인합니다.")


def test_잘라낸_뒤에_종결어미를_본다():
    # 답을 먼저 잘라야 잘린 문장의 끝을 본다. 순서가 뒤집히면 지어낸 답의
    # 종결어미를 고치고 그 답이 그대로 남는다.
    src = "What must be confirmed?"
    ko = "무엇을 확인해야 하나요?\n답: 체크포인트를 보십시오."
    assert postprocess(src, ko) == "무엇을 확인해야 합니까?"


# ─── 배치 분할 ───────────────────────────────────────────────────────
# 정렬이 깨지면 1번 보기에 2번 번역이 붙는다. 없는 것보다 나쁘므로
# (DECISIONS §1) 조금이라도 어긋나면 None 을 돌려 개별 호출로 되돌린다.
from app.engine import _join, _split, BATCH_MARK


def test_정상_분할():
    raw = f"{BATCH_MARK} 0\n첫째입니다.\n\n{BATCH_MARK} 1\n둘째입니다."
    assert _split(raw, 2) == ["첫째입니다.", "둘째입니다."]


def test_조각이_모자라면_None():
    assert _split(f"{BATCH_MARK} 0\n하나뿐입니다.", 2) is None


def test_번호가_중복이면_None():
    raw = f"{BATCH_MARK} 0\n가.\n\n{BATCH_MARK} 0\n나."
    assert _split(raw, 2) is None


def test_번호가_건너뛰면_None():
    raw = f"{BATCH_MARK} 0\n가.\n\n{BATCH_MARK} 2\n나."
    assert _split(raw, 2) is None


def test_빈_조각이면_None():
    raw = f"{BATCH_MARK} 0\n\n\n{BATCH_MARK} 1\n나."
    assert _split(raw, 2) is None


def test_순서가_뒤바뀌어도_번호대로_돌려준다():
    raw = f"{BATCH_MARK} 1\n둘째.\n\n{BATCH_MARK} 0\n첫째."
    assert _split(raw, 2) == ["첫째.", "둘째."]


def test_join_이_분할_가능한_형태를_만든다():
    texts = ["alpha", "beta", "gamma"]
    assert _split(_join(texts), 3) == texts


# ─── 배치 분할 ───────────────────────────────────────────────────────
# 정렬이 깨지면 1번 보기에 2번 번역이 붙는다. 없는 것보다 나쁘므로
# (DECISIONS §1) 조금이라도 어긋나면 None 을 돌려 개별 호출로 되돌린다.
from app.engine import _join, _split, BATCH_MARK


def test_정상_분할():
    raw = f"{BATCH_MARK} 0\n첫째입니다.\n\n{BATCH_MARK} 1\n둘째입니다."
    assert _split(raw, 2) == ["첫째입니다.", "둘째입니다."]


def test_조각이_모자라면_None():
    assert _split(f"{BATCH_MARK} 0\n하나뿐입니다.", 2) is None


def test_번호가_중복이면_None():
    raw = f"{BATCH_MARK} 0\n가.\n\n{BATCH_MARK} 0\n나."
    assert _split(raw, 2) is None


def test_번호가_건너뛰면_None():
    raw = f"{BATCH_MARK} 0\n가.\n\n{BATCH_MARK} 2\n나."
    assert _split(raw, 2) is None


def test_빈_조각이면_None():
    raw = f"{BATCH_MARK} 0\n\n\n{BATCH_MARK} 1\n나."
    assert _split(raw, 2) is None


def test_순서가_뒤바뀌어도_번호대로_돌려준다():
    raw = f"{BATCH_MARK} 1\n둘째.\n\n{BATCH_MARK} 0\n첫째."
    assert _split(raw, 2) == ["첫째.", "둘째."]


def test_join_이_분할_가능한_형태를_만든다():
    texts = ["alpha", "beta", "gamma"]
    assert _split(_join(texts), 3) == texts
