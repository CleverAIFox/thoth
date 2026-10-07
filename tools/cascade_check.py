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
  // ★ **`[data-case]` 를 붙인 것만 본다**(§169). 안쪽 사다리의 호스트 넷도
  //   `.st-translation` 이라 그대로 긁으면 `dataset.case` 가 없어 터진다.
  for (const n of document.querySelectorAll(".st-translation[data-case]")) {
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


# ★ **안쪽은 「어디서부터 지는가」 가 아니라 「질 수가 있는가」 다**(DECISIONS §169).
#   `padding` · `border-radius` · `background` · `box-shadow` · `font-size` ·
#   `line-height` · `color` — 박스를 박스로 보이게 하는 것들이다. 넉 달 동안
#   **이것을 때리는 적수를 한 번도 세우지 않았다.** 재는 자가 안 보고 있었으므로
#   세울 생각도 안 했다 — 그래서 지메일에서 박스가 싼티나게 깨져 있는데 표는
#   초록이었다(§59 : 「못 쟀다」 를 「없다」 로 읽었다).
#
# ★ **같은 규칙 · 같은 값 · 다른 것은 경계 하나.**
#     대조 : `.st-몸` 을 **페이지에** 둔 것. §169 전의 박스다. **져야 한다.**
#     섀도 : 같은 것을 섀도 안에 둔 것. **이겨야 한다.**
# ★ **양방향이다.** 섀도가 지면 경계가 샌 것이고, **대조가 안 지면 적수가
#   무력해진 것**이다. 후자를 안 보면 이 검사는 초록을 내면서 아무것도 안 본다.
안쪽기대 = {("없음", "대조"): 0, ("없음", "섀도"): 0,
            ("KILL", "섀도"): 0}
# ★ **적수의 세기를 수로 못 박는다**(2026-10-06 실측 : 아홉). 늘면 **사이트가 셀 수
#   있는 자리가 늘었다**는 뜻이고, 줄면 **적수가 약해졌다**는 뜻이다 — 후자가 더
#   위험하다. 약해진 적수에게 안 진 섀도의 0 은 「이겼다」 가 아니라 「때린 적이
#   없다」 다. `비상구쓸모` 와 같은 양방향 톱니다.
안쪽적수세기 = {("KILL", "대조"): 9}

안쪽측정 = """() => {
  const 볼것 = window.__안쪽볼것;
  const 셋 = window.__안쪽;
  const 읽 = (el) => { const s = getComputedStyle(el); const o = {};
                       for (const k of 볼것) o[k] = s[k]; return o; };
  // ★ **기대값을 파이썬에 적지 않는다.** 「적수 없는 대조」 가 곧 설계가 말하는
  //   모양이고, 나머지는 그것과 **다른 자리**만 센다(§132).
  const 기준 = 읽(셋.find((x) => x.적수 === "없음" && x.꼴 === "대조").속);
  return 셋.map(({ 적수, 꼴, 속 }) => {
    const 값 = 읽(속);
    return { 적수, 꼴, 어긋남: 볼것.filter((k) => 값[k] !== 기준[k]) };
  });
}"""


def 잰다(fixture: pathlib.Path):
    """(행들, 안쪽행들, None) 또는 (None, None, 못 잰 까닭)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        return None, None, f"playwright 가 없다 ({e})"
    try:
        with sync_playwright() as p:
            # ★ **`--allow-file-access-from-files` 를 안 켠다.** 섀도 안의 `<link>` 는
            #   **문서 하위 리소스**라 `file://` 에서도 그냥 실린다 — 재 보고 지웠다.
            #   **없는 병에 깃발을 세우지 않는다**(§133). 대신 실제로 실렸는지를
            #   아래에서 `borderRadius` 로 **묻는다** — 그쪽이 진짜 관문이다.
            b = p.chromium.launch()
            try:
                pg = b.new_page(viewport={"width": 1100, "height": 900})
                pg.goto(fixture.as_uri())
                pg.wait_for_selector(".st-translation")
                # ★ **픽스처가 `cssaudit.js` 를 못 실었으면 거기서 멈춘다.** 안 실린 채
                #   0 건으로 통과하면 검사가 아무것도 안 보면서 초록을 낸다(§59).
                if not pg.evaluate("() => typeof window.ST?.cssMeasure === 'function'"):
                    return None, None, "픽스처가 src/cssaudit.js 를 싣지 못했다"
                if not pg.evaluate("() => Array.isArray(window.__안쪽) && window.__안쪽.length === 4"):
                    return None, None, "픽스처가 안쪽 사다리 넷을 세우지 못했다"
                # ★ **섀도가 스타일시트를 실제로 받았는지 먼저 묻는다.** 못 받았으면
                #   아래 「안 졌다」 는 참이지만 **아무 의미가 없다**(§59).
                핀 = pg.evaluate("""() => {
                  const 속 = window.__안쪽.find((x) => x.꼴 === "섀도").속;
                  return getComputedStyle(속).borderRadius;
                }""")
                if "16px" not in (핀 or ""):
                    return None, None, f"섀도가 content.css 를 못 받았다 (borderRadius={핀!r})"
                return pg.evaluate(측정), pg.evaluate(안쪽측정), None
            finally:
                b.close()
    except Exception as e:    # 까닭을 삼키지 않고 그대로 내보낸다(§70)
        # ★ **까닭을 「크로미움을 못 띄웠다」 로 뭉개지 않는다.** 띄우고 나서 재다
        #   터진 것까지 그 말로 적고 있었고, 그 말을 믿고 playwright 설치를
        #   다시 뒤지게 된다(§70 — 까닭을 삼키지 않는다).
        return None, None, f"재다 터졌다 ({str(e).splitlines()[0][:160]})"


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


def 안쪽판정(행들: list[dict]) -> list[str]:
    """경계가 제 일을 하는가 — 그리고 적수가 아직 센가."""
    fails = []
    본것 = set()
    for r in 행들:
        키 = (r["적수"], r["꼴"])
        본것.add(키)
        n = len(r["어긋남"])
        if 키 in 안쪽기대 and n != 안쪽기대[키]:
            말 = "·".join(r["어긋남"])
            fails.append(
                f"안쪽 {r['적수']} · {r['꼴']} : {n} 개가 어긋났다({말}) — 표는 "
                f"{안쪽기대[키]} 다. " + ("**섀도 경계가 샜다**" if r["꼴"] == "섀도"
                                          else "적수 없이 기준과 갈렸다"))
        if 키 in 안쪽적수세기 and n != 안쪽적수세기[키]:
            말 = "늘었으면 사이트가 셀 자리가 늘었고" if n > 안쪽적수세기[키] \
                 else "줄었으면 적수가 약해졌고 — 그러면 섀도의 0 은 「이겼다」 가 아니라 「때린 적이 없다」 다"
            fails.append(
                f"안쪽 {r['적수']} · {r['꼴']} : {n} 개가 어긋났다 — 표는 "
                f"{안쪽적수세기[키]} 다. {말} 둘 다 적어야 한다(§59)")
    for 키 in {*안쪽기대, *안쪽적수세기} - 본것:
        fails.append(f"안쪽 {키[0]} · {키[1]} 칸이 픽스처에 없다")
    return fails


def main() -> int:
    행들, 안쪽행들, 왜 = 잰다(FIXTURE)
    if 행들 is None:
        print(f"재지 못했다 — {왜}")
        # ★ **되는 명령을 적는다.** `uv run --with playwright` 는 **임시 환경**에
        #   깔므로, 그 뒤에 `python3` 로 다시 부르면 **똑같이 없다.** 크로미움만
        #   `~/.cache/ms-playwright` 에 남아 영영 안 맞는다(DECISIONS §136).
        print("  uv run --with playwright python -m playwright install chromium   # 한 번")
        print("  uv run --with playwright python tools/cascade_check.py           # 그 뒤로는 이렇게 부른다")
        print("  (시스템 파이썬에 두려면 : pip install --break-system-packages playwright)")
        return 2

    if "--json" in sys.argv:
        print(json.dumps({"호스트": 행들, "안쪽": 안쪽행들}, ensure_ascii=False, indent=2))

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

    print()
    print("안쪽 — 경계가 막는가 (어긋난 속성 수 / 기준은 「적수 없는 대조」)")
    for r in sorted(안쪽행들, key=lambda x: (x["적수"], x["꼴"])):
        말 = "·".join(r["어긋남"]) or "—"
        print(f"  {r['적수']:<5} {r['꼴']:<4} {len(r['어긋남']):>2}  {말}")

    fails = 판정(행들) + 안쪽판정(안쪽행들)
    if fails:
        print()
        print("표와 다르다 :")
        for f in fails:
            print(f"    {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
