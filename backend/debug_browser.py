import asyncio
from app.services.browser_service import browser_service

async def main():
    await browser_service.start()
    p = await browser_service.get_page()
    try:
        r = await p.goto("https://html.duckduckgo.com/html/?q=artificial+intelligence", wait_until="domcontentloaded", timeout=20000)
        print("STATUS", r.status if r else None)
        t = await p.evaluate("() => document.body.innerText.slice(0,600)")
        print("TEXT:", repr(t))
        h = await p.evaluate("() => document.querySelectorAll('.result').length")
        print("RESULT NODES", h)
        a = await p.evaluate("() => document.querySelectorAll('a').length")
        print("ANCHORS", a)
    finally:
        await p.close()
        await browser_service.stop()

asyncio.run(main())
