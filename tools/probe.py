import json, urllib.request, urllib.parse, re
UA = {"User-Agent": "MorgenKnaller/1.0 (https://github.com/Postmen1971/zeitung; private Zeitung)"}
def suche(q):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:bitmap {q}", "gsrnamespace": 6,
        "gsrlimit": 12, "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 640})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        d = json.loads(r.read().decode())
    out = []
    for p in sorted(d.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 99)):
        ii = p["imageinfo"][0]; m = ii.get("extmetadata", {})
        lic = m.get("LicenseShortName", {}).get("value", "")
        art = re.sub("<[^>]+>", "", m.get("Artist", {}).get("value", ""))[:40]
        out.append((p["title"][5:], lic, art, ii.get("width"), ii.get("thumburl", "")[:90]))
    return out
QS = ["pistachio ice cream", "pistachio ice cream cone", "lemon ice cream", "lemon sorbet cone", "speculoos", "cookie butter ice cream",
      "spekulatius", "lebkuchen", "gingerbread", "cookies and cream ice cream", "oreo ice cream", "soft serve cup", "soft-serve ice cream swirl"]
for q in QS:
    print("##", q)
    for x in suche(q)[:7]:
        if x[3] and x[3] >= 500 and any(l in x[1] for l in ("CC BY", "CC0", "Public domain")):
            print("   ", x[0], "|", x[1], "|", x[2])
