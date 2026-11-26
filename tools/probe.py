import json, urllib.request, urllib.parse, re
UA = {"User-Agent": "MorgenKnaller/1.0 (https://github.com/Postmen1971/zeitung; private Zeitung)"}
def suche(q):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrsearch": f"filetype:bitmap {q}", "gsrnamespace": 6,
        "gsrlimit": 8, "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 640})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        d = json.loads(r.read().decode())
    out = []
    for p in sorted(d.get("query", {}).get("pages", {}).values(), key=lambda x: x.get("index", 99)):
        ii = p["imageinfo"][0]; m = ii.get("extmetadata", {})
        lic = m.get("LicenseShortName", {}).get("value", "")
        art = re.sub("<[^>]+>", "", m.get("Artist", {}).get("value", ""))[:40]
        out.append((p["title"][5:60], lic, art, ii.get("width"), ii.get("thumburl", "")[:90]))
    return out
for q in ["soft serve ice cream cone", "mango soft serve", "chocolate soft serve", "strawberry frozen yogurt", "pistachio gelato", "salep dondurma", "coffee ice cream", "pineapple soft serve dole whip"]:
    print("##", q)
    for x in suche(q)[:4]:
        print("   ", x)
