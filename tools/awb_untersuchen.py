"""Einmalige Untersuchung: Welche Datenquelle nutzt der AWB-Abfuhrkalender?"""
import asyncio, json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        pg = await b.new_page()
        anfragen = []
        pg.on("request", lambda r: anfragen.append(f"{r.method} {r.resource_type} {r.url}"))
        await pg.goto("https://awb-gp.de/abfallabholung/abfuhrtermine", wait_until="networkidle")
        await pg.wait_for_timeout(4000)
        print("=== IFRAMES ===")
        for f in pg.frames:
            print(f.url)
        print("=== ANFRAGEN ===")
        for a in anfragen:
            if not any(x in a for x in (".woff", ".png", ".jpg", ".svg", ".css", "google-analytics", "matomo")):
                print(a)
        html = await pg.content()
        import re
        for m in sorted(set(re.findall(r'(?:src|href|data-[a-z-]+)="([^"]+)"', html))):
            if any(k in m.lower() for k in ("abfall", "kalender", "termin", "ics", "ical", "api", "widget", "k4", "awido", "insert")):
                print("LINK", m)
        await pg.screenshot(path="awb.png", full_page=True)
        await b.close()

asyncio.run(main())
