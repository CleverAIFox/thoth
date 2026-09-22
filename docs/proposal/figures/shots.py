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
MOCK = """
window.chrome={storage:{local:{get:async()=>({stOff:false,stEndpoint:'https://****.lambda-url.ap-northeast-2.on.aws/translate',stToken:'tok'}),set:async()=>{}}},
tabs:{query:async()=>[{id:1,url:'%s'}]},permissions:{contains:async()=>%s,request:(o,cb)=>cb(true)},
runtime:{getURL:s=>s,sendMessage:()=>{},lastError:null},scripting:{executeScript:async()=>{}}};
window.fetch=async()=>new Response(JSON.stringify({status:'ok',version:'0.1.0',engine:'bedrock',cache:'ddb',auth:true}),
  {status:200,headers:{'content-type':'application/json'}});
"""


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
            await pg.screenshot(path=str(OUT / "shot_preview.png"), full_page=True)
            for name, url, granted, adv in [("on", "https://www.udemy.com/course/x/learn/quiz/1", "true", False),
                                            ("off", "https://example.com/quiz", "false", True)]:
                pg = await b.new_page(viewport={"width": 340, "height": 420}, device_scale_factor=2)
                await pg.add_init_script(MOCK % (url, granted))
                await pg.goto("http://127.0.0.1:8765/popup.html")
                await pg.wait_for_timeout(700)
                if adv:
                    await pg.evaluate("document.getElementById('advanced').open=true")
                else:
                    await pg.click("#check")
                await pg.wait_for_timeout(500)
                await pg.screenshot(path=str(OUT / f"shot_popup_{name}.png"), full_page=True)
            await b.close()
    finally:
        srv.kill()


def trim(path):
    im = Image.open(path).convert("RGB")
    box = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    return ImageOps.expand(im.crop((0, 0, im.width, box[3] + 30)), border=2, fill=(191, 197, 204))


def facts(name, items):
    (OUT / f"{name}.facts.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


try:
    asyncio.run(shoot())
except Exception as e:  # noqa: BLE001 — 도구가 없으면 옛 그림을 쓴다
    raise SystemExit(f"화면을 찍지 못했다 ({e}) — playwright · 크로미움을 확인한다")
a, b = trim(OUT / "shot_popup_on.png"), trim(OUT / "shot_popup_off.png")
s = Image.new("RGB", (a.width + b.width + 60, max(a.height, b.height)), "white")
s.paste(a, (0, 0)); s.paste(b, (a.width + 60, 0)); s.save(OUT / "f_popup.png")
facts("f_popup", ["file:extension/popup.html~이 사이트에서 켜기", "file:extension/src/popup.js~아직 권한이 없다"])
p = Image.open(OUT / "shot_preview.png")
p.crop((0, 0, p.width, min(p.height, 2050))).save(OUT / "f_preview_a.png")
facts("f_preview_a", ["file:extension/preview.html~content.css", "file:extension/content.css~st"])
print("shots ok")
