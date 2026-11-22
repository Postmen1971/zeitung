"""Einmalig: GraphQL-Schnittstelle des abfall.io-Widgets (AWB Göppingen) erkunden."""
import asyncio, json, urllib.request
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        pg = await b.new_page()
        async def antwort(r):
            if "graphql" in r.url:
                try:
                    print("REQ", r.request.headers.get("x-abfallplus-api-key", ""), r.request.post_data[:1500])
                    print("RESP", (await r.text())[:3000])
                except Exception as e:
                    print("ERR", e)
        pg.on("response", lambda r: asyncio.ensure_future(antwort(r)))
        await pg.goto("https://awb-gp.de/abfallabholung/abfuhrtermine", wait_until="networkidle")
        await pg.wait_for_timeout(3000)
        # Versuch: Ebersbach im Widget auswählen
        for sel in ["input[type=text]", "input"]:
            fs = await pg.query_selector_all(sel)
            print("INPUTS", len(fs))
            if fs:
                try:
                    await fs[0].click(); await fs[0].type("Ebersbach", delay=80)
                    await pg.wait_for_timeout(2500)
                    opts = await pg.query_selector_all("[role=option], li")
                    for o in opts:
                        t = (await o.inner_text()).strip()
                        if "Ebersbach" in t:
                            print("OPTION", t); await o.click(); break
                    await pg.wait_for_timeout(4000)
                except Exception as e:
                    print("KLICK-ERR", e)
                break
        print("TEXT", (await pg.inner_text("body"))[:2500])
        await b.close()

asyncio.run(main())
