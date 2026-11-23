import re, urllib.request, html
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36"}
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
            return r.geturl(), r.read().decode("utf-8", "replace")
    except Exception as e:
        return u, f"FEHLER {e}"
for start in ["https://www.ebersbach.de/", "https://www.ebersbach.de/Veranstaltungen", "https://www.ebersbach.de/Aktuelles"]:
    u, t = get(start)
    print("=== ", start, "->", u, len(t), t[:80] if t.startswith("FEHLER") else "")
    links = sorted(set(re.findall(r'href="([^"]+)"', t)))
    for l in links:
        if re.search(r"veranstalt|termin|aktuell|news|rss|ical|ics|stadtblatt|kalender|event", l, re.I):
            print("   ", html.unescape(l))
