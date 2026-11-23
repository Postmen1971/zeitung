import re, urllib.request, json, urllib.parse
UA = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"}
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
            return r.status, r.geturl(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, u, ""
cache = json.load(open("termine_cache.json")) if False else None
kopf = dict(UA); kopf.update({"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
s = get("https://www.ebersbach.de/veranstaltung")[2]
doc = re.search(r'document="([^"]+)"', s).group(1)
q = urllib.parse.urlencode([("document", doc), ("limit", "3"), ("page", "1"), ("filters[date][from]", "2026-11-23 00:00:00")])
with urllib.request.urlopen(urllib.request.Request("https://www.ebersbach.de/api/event/list/event-appointment?" + q, headers=kopf)) as r:
    karten = re.findall(r"(?s)<article.*?</article>", json.loads(r.read().decode())["results"])
for k in karten[:2]:
    roh = re.search(r'href="([^"]+)"', k).group(1)
    for u in (roh, roh.replace(".de//", ".de/")):
        st, ziel, t = get(u)
        h1 = re.search(r"(?s)<h1[^>]*>(.*?)</h1>", t)
        main = re.search(r"(?s)<main.*?</main>", t)
        print("URL", u, "->", st, ziel, "| H1:", re.sub(r"<[^>]+>|\s+", " ", h1.group(1)).strip() if h1 else None,
              "| main-Länge:", len(main.group(0)) if main else 0)
        if main:
            print("   ", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", main.group(0)))[:600])
