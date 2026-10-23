"""기획서의 화면 그림 — 실제 `extension/popup.html` · `preview.html` 을 헤드리스 크롬으로 찍는다.

★ **흉내내는 것은 크롬 API 와 `/health` 응답뿐이다.** 마크업 · CSS · 스크립트는 확장의 것
  그대로다. 그래서 화면 문구가 바뀌면 그림도 바뀐다 — 문구 하나를 사실로 선언해 둔다.

★ playwright 와 크로미움이 있어야 돈다. 없으면 이 그림만 건너뛰고 옛 그림이 남는다.
"""
import asyncio
import json
import subprocess
import time

from PIL import Image, ImageChops, ImageOps

from figlib import OUT, ROOT

EXT = ROOT / "extension"
# ★ **두 장을 가르는 것이 권한에서 「이 사이트에서 켰나」 로 바뀌었다**(DECISIONS §209).
#   종전에는 `permissions.contains` 를 `true`/`false` 로 갈랐는데, 권한이 `<all_urls>` 라
#   **그 값이 화면을 안 바꾼다** — 그대로 두면 **같은 상태를 두 장 찍고** 그림이 조용히
#   뜻을 잃는다. 이제 `st번역사이트` 지도로 가른다.
MOCK = """
window.chrome={storage:{local:{get:async()=>({st번역사이트:%s,stEndpoint:'https://****.lambda-url.ap-northeast-2.on.aws/translate',stToken:'tok'}),set:async()=>{}}},
tabs:{query:async()=>[{id:1,url:'%s'}]},permissions:{contains:async()=>true,request:(o,cb)=>cb(true)},
runtime:{getURL:s=>s,sendMessage:()=>{},lastError:null},scripting:{executeScript:async()=>{}}};
window.fetch=async()=>new Response(JSON.stringify({status:'ok',version:'0.1.0',engine:'bedrock',cache:'ddb',auth:true}),
  {status:200,headers:{'content-type':'application/json'}});
"""


# ★ **같은 소스에서 같은 바이트가 나와야 한다**(DECISIONS §189). `content.css` 의
#   `st-pulse 1.5s infinite` 이 `preview.html` 에서 돌고 있어서, 800ms 뒤에 찍은 한 장은
#   **애니메이션의 아무 프레임**이었다 — 소스를 한 글자도 안 고치고 다시 구워도
#   `f_preview_a.png` 가 달라지고, 그 그림이 base64 로 박히는 `proposal.docx` ·
#   `site/proposal.html` 도 달라졌다. 그 셋이 추적되므로 **나무 해시가 달라진다** —
#   `apply_patch.sh` 의 바탕 선언(§129 · §130)이 셋 때문에 세 번 어긋났고, 그때마다
#   「무엇이 틀렸나」 를 손으로 되짚었다. 까닭은 패치가 아니라 **여기**였다.
# ★ 멈춘 화면이 아니라 **첫 프레임**으로 고정한다 — `prefers-reduced-motion` 가지를
#   흉내내면 사람 대부분이 보는 화면과 **다른 가지**를 찍는다(content.css §333).
찍기 = {"full_page": True, "animations": "disabled"}


async def shoot():
    from playwright.async_api import async_playwright
    srv = subprocess.Popen(["python3", "-m", "http.server", "8765", "-d", str(EXT)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            pg = await b.new_page(viewport={"width": 900, "height": 1400}, device_scale_factor=2)
            await pg.goto(f"file://{EXT}/preview.html")
            await pg.wait_for_timeout(800)
            await pg.screenshot(path=str(OUT / "shot_preview.png"), **찍기)
            for name, url, 지도, adv in [
                    ("on", "https://www.udemy.com/course/x/learn/quiz/1", "{'www.udemy.com':true}", False),
                    ("off", "https://example.com/quiz", "{}", True)]:
                pg = await b.new_page(viewport={"width": 340, "height": 420}, device_scale_factor=2)
                await pg.add_init_script(MOCK % (지도, url))
                await pg.goto("http://127.0.0.1:8765/popup.html")
                await pg.wait_for_timeout(700)
                if adv:
                    await pg.evaluate("document.getElementById('advanced').open=true")
                else:
                    await pg.click("#check")
                await pg.wait_for_timeout(500)
                await pg.screenshot(path=str(OUT / f"shot_popup_{name}.png"), **찍기)
            await b.close()
    finally:
        srv.kill()


def trim(path):
    im = Image.open(path).convert("RGB")
    box = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    return ImageOps.expand(im.crop((0, 0, im.width, box[3] + 30)), border=2, fill=(191, 197, 204))


def facts(name, items):
    (OUT / f"{name}.facts.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


# ★ **이 그림이 무엇을 찍었는지 지문으로 남긴다**(DECISIONS §185). 사실 선언
#   (`*.facts.json`)은 「이 글자가 그 파일에 있나」 라서 **더해진 것을 못 잡는다** —
#   183 이 `popup.html` 에 버튼을 달았을 때 선언은 그대로 참이었고, 크로미움 없는
#   기계는 **버튼 없는 옛 그림**을 그대로 실었다. 목록의 정본은 `tools/shot_stale.py`
#   이고 여기서 **읽어 쓴다** — 두 곳에 적으면 한쪽만 늙는다(§91).
import importlib.util as _il

_몫 = _il.spec_from_file_location("shot_stale", ROOT / "tools" / "shot_stale.py")
_stale = _il.module_from_spec(_몫)
_몫.loader.exec_module(_stale)


def 원본지문(name):
    (OUT / f"{name}.원본.json").write_text(
        json.dumps(_stale.지금()[name], ensure_ascii=False, indent=1), encoding="utf-8")


try:
    asyncio.run(shoot())
except Exception as e:  # 도구가 없으면 옛 그림을 쓴다
    raise SystemExit(f"화면을 찍지 못했다 ({e}) — playwright · 크로미움을 확인한다")
a, b = trim(OUT / "shot_popup_on.png"), trim(OUT / "shot_popup_off.png")
s = Image.new("RGB", (a.width + b.width + 60, max(a.height, b.height)), "white")
s.paste(a, (0, 0)); s.paste(b, (a.width + 60, 0)); s.save(OUT / "f_popup.png")
원본지문("f_popup")
# ★ **권한 줄이 사라졌다**(DECISIONS §209). `host_permissions` 가 `<all_urls>` 라
#   `permissions.contains` 는 언제나 참이고, 그 줄은 **장식**이었다. 이 화면의
#   사실은 이제 **사이트 단위 번역 토글**과 **지금 모드**다.
facts("f_popup", ["file:extension/popup.html~이 사이트에서 번역", "file:extension/src/popup.js~수집만"])
p = Image.open(OUT / "shot_preview.png")
p.crop((0, 0, p.width, min(p.height, 2050))).save(OUT / "f_preview_a.png")
원본지문("f_preview_a")
facts("f_preview_a", ["file:extension/preview.html~content.css", "file:extension/content.css~st"])
print("shots ok")
