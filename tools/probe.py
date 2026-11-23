import re, urllib.request, html
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36"}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
        return r.read().decode("utf-8", "replace")
for u in ["https://www.ebersbach.de/veranstaltung", "https://www.ebersbach.de/Aktuelles"]:
    t = get(u)
    t = re.sub(r"(?is)<(script|style|svg)[^>]*>.*?</\1>", "", t)
    i = max(t.find("<main"), 0)
    body = t[i:]
    print("=====", u, len(t))
    # komprimiertes HTML eines Ausschnitts
    print(re.sub(r"\s+", " ", body)[:6000])
    print("LINKS:", sorted(set(l for l in re.findall(r'href="([^"]+)"', body) if "veranstaltung" in l.lower() or "aktuelles/" in l.lower()))[:40])
