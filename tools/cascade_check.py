#!/usr/bin/env python3
"""번역 박스가 사이트 CSS 에 어디서부터 지는가.

    python3 tools/cascade_check.py           표를 찍는다. 어긋나면 1
    python3 tools/cascade_check.py --json    기계가 읽을 꼴

★ **「브라우저에서 눈으로 확인」 으로 적혀 있던 행이 있었다 — 그것이 틀린 모양이다.**
  사람 눈은 한 페이지밖에 못 보고, 본 것을 기록으로 안 남기고, 사이트가 내일
  CSS 를 바꾸면 다시 봐야 한다. **같은 물음을 픽스처 한 장과 측정 한 번으로 바꾼다.**

★ **jsdom 으로는 안 된다.** 레이아웃을 안 해서 `width` 가 픽셀로 안 나오고
  명시도 다툼도 온전히 재현하지 못한다. 진짜 엔진이 필요하다 — playwright 와
  크로미움이 없으면 **SKIP 이 아니라 2 로 끝난다**(아래).

★ **구조는 유한하고 캐스케이드는 아니다.** 여기서 재는 것은 「전부 막았나」 가
  아니라 **「어디서부터 지는가」** 다. 그 수가 런타임 자가 신고(`broker.js`)가
  무엇을 봐야 하는지를 정한다 — 픽스처가 못 본 사이트는 그쪽이 잡는다.

★ **종료 코드가 상태를 든다**(DECISIONS §127).
    0  기대와 같다
    1  기대와 다르다 — 바탕 규칙이 못 이기는 자리가 늘었거나 줄었다
    2  재지 못했다 (playwright · 크로미움 없음). **통과로 세지 않는다**(§59)
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "extension/tests/fixtures/cascade.html"

# ★ **이 표가 이 검사의 정본이다.** 「어디서부터 지는가」 를 수로 못 박는다.
#   바뀌면 운다 — 사이트 CSS 가 아니라 **우리 규칙이 바뀌었다는 뜻**이기 때문이다.
#   (0,2,0) 인 바탕 규칙은 (0,1,2) 를 이기고 (0,2,2) · (1,0,2) · `!important` 에 진다.
#
# ★ **이 표가 한 번 틀렸었다.** `display` 를 바탕 규칙이 선언하지 않던 때는 L1 에서
#   block · cell · list 가 **졌다** — 명시도에서 진 것이 아니라 **싸움에 안 나간
#   속성**이 있었기 때문이다. 표를 그 사실에 맞춰 내리는 대신 `content.css` 가
#   `display: block` 을 적게 고쳤다. **재서 틀리면 코드를 고칠지 표를 고칠지부터
#   정한다**(DECISIONS §135).
이긴다 = {"L0": True, "L1": True, "L2": False, "L3": False, "L4": False}

# ★ **비상구는 「쓸모가 있는가」 로 잰다.** 구해 내는 자리가 0 이면 군살이다.
#   줄어도 운다 — 늘어난 것은 사이트가 세졌다는 뜻이고 줄어든 것은 **우리 비상구가
#   조용히 약해졌다**는 뜻이다(양방향 래칫).
비상구쓸모 = {"wide": 15}

# ★ **기대값을 여기 적지 않는다.** 확장이 실제로 쓰는 `extension/src/cssaudit.js` 의
#   `ST.cssFaults` 를 페이지에서 그대로 부른다 — 여기 또 적으면 같은 사실이 두 언어에
#   살고 언젠가 하나만 고쳐진다(DECISIONS §132 · §135). 픽스처가 그 파일을 싣는다.
측정 = """() => {
  const out = [];
  for (const n of document.querySelectorAll(".st-translation")) {
    const [구조, 사다리, 비상구] = n.dataset.case.split("|");
    const p = n.parentElement;
    const ps = getComputedStyle(p);
    const 그릇폭 = p.clientWidth - parseFloat(ps.paddingLeft) - parseFloat(ps.paddingRight);
    out.push({ 구조, 사다리, 비상구,
               어긋남: window.ST.cssMeasure(n),
               폭: n.offsetWidth, 그릇폭 });
  }
  return out;
}"""


def 잰다(fixture: pathlib.Path):
    """(행들, None) 또는 (None, 못 잰 까닭)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        return None, f"playwright 가 없다 ({e})"
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            try:
                pg = b.new_page(viewport={"width": 1100, "height": 900})
                pg.goto(fixture.as_uri())
                pg.wait_for_selector(".st-translation")
                # ★ **픽스처가 `cssaudit.js` 를 못 실었으면 거기서 멈춘다.** 안 실린 채
                #   0 건으로 통과하면 검사가 아무것도 안 보면서 초록을 낸다(§59).
                if not pg.evaluate("() => typeof window.ST?.cssMeasure === 'function'"):
                    return None, "픽스처가 src/cssaudit.js 를 싣지 못했다"
                return pg.evaluate(측정), None
            finally:
                b.close()
    except Exception as e:    # 까닭을 삼키지 않고 그대로 내보낸다(§70)
        return None, f"크로미움을 못 띄웠다 ({str(e).splitlines()[0][:120]})"


def 판정(행들: list[dict]) -> list[str]:
    """기대와 다른 자리만 돌려준다."""
    fails = []
    for r in 행들:
        if r["비상구"] != "없음":
            continue                      # 비상구가 붙은 행은 아래에서 따로 본다
        이김 = not r["어긋남"]
        want = 이긴다[r["사다리"]]
        if 이김 != want:
            말 = "이겼다" if 이김 else f"졌다({'·'.join(r['어긋남'])})"
            fails.append(
                f"{r['구조']} · {r['사다리']} : {말} — 표는 "
                f"{'이긴다' if want else '진다'} 로 적혀 있다")

    # ★ **비상구가 쓸모 있는지도 잰다.** 「있으니 괜찮다」 가 아니라
    #   「없으면 지고 있으면 이기는 자리가 실제로 있는가」 를 묻는다.
    #
    # ★ **처음에는 「L4 에서는 비상구도 져야 한다」 로 적었다가 틀렸다.**
    #   `!important` 끼리도 **명시도가 먼저**다 — `(0,2,0)!important` 가
    #   `(0,1,2)!important` 를 이긴다. 소스 순서는 그 다음이다. 시험이 아니라
    #   **내가 아는 CSS 가 틀렸던 자리**다(DECISIONS §135).
    쓸 = 쓸모(행들)
    for e, want in 비상구쓸모.items():
        got = 쓸.get(e)
        if got is None:
            fails.append(f"비상구 {e} 가 픽스처에 없다 — 지웠으면 `비상구쓸모` 에서도 뺀다")
        elif got != want:
            fails.append(
                f"비상구 {e} 가 구해 내는 자리가 {got} 다 — 표는 {want} 다. "
                f"{'늘었으면 사이트가 세진 것이고' if got > want else '줄었으면 비상구가 약해진 것이고'} "
                f"둘 다 적어야 한다")
    for e, got in sorted(쓸.items()):
        if e not in 비상구쓸모:
            fails.append(f"비상구 {e} 가 `비상구쓸모` 에 선언돼 있지 않다 — 새 비상구는 수를 적는다")
    return fails


def 쓸모(행들: list[dict]) -> dict:
    """비상구마다 「없으면 지고 있으면 이기는」 자리 수. 0 이면 지워도 된다."""
    없음 = {(r["구조"], r["사다리"]): bool(r["어긋남"])
            for r in 행들 if r["비상구"] == "없음"}
    out: dict[str, int] = {}
    for r in 행들:
        e = r["비상구"]
        if e == "없음":
            continue
        졌었나 = 없음.get((r["구조"], r["사다리"]), False)
        if 졌었나 and not r["어긋남"]:
            out[e] = out.get(e, 0) + 1
        else:
            out.setdefault(e, 0)
    return out


def main() -> int:
    행들, 왜 = 잰다(FIXTURE)
    if 행들 is None:
        print(f"재지 못했다 — {왜}")
        print("  uv run --with playwright python -m playwright install chromium")
        return 2

    if "--json" in sys.argv:
        print(json.dumps(행들, ensure_ascii=False, indent=2))

    구조들 = sorted({r["구조"] for r in 행들})
    print("바탕 규칙만 — 이기는가 (비상구 없음)")
    print("            " + "  ".join(f"{L:>5}" for L in 이긴다))
    for s in 구조들:
        칸 = []
        for L in 이긴다:
            r = next((x for x in 행들
                      if x["구조"] == s and x["사다리"] == L and x["비상구"] == "없음"), None)
            칸.append("    ○" if r and not r["어긋남"] else "    ×")
        print(f"  {s:<8}" + "  ".join(칸))

    print()
    print("비상구가 구해 내는 자리 수 (0 이면 지워도 된다)")
    for e, n in sorted(쓸모(행들).items()):
        print(f"  {e:<6} {n}")

    fails = 판정(행들)
    if fails:
        print()
        print("표와 다르다 :")
        for f in fails:
            print(f"    {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
