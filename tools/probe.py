import re, urllib.request, urllib.parse, json, html
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36",
      "Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
for seite, ep, extra in [("veranstaltung", "event/list/event-appointment", [("filters[date][from]", "2026-11-23 00:00:00")]),
                         ("nachrichten", "news/list/news-article", [])]:
    s = get("https://www.ebersbach.de/" + seite)[1]
    doc = re.search(r'document="([^"]+)"', s).group(1)
    q = [("document", doc), ("limit", "12"), ("page", "1")] + extra
    st, t = get(f"https://www.ebersbach.de/api/{ep}?" + urllib.parse.urlencode(q))
    print("##", seite, st)
    if st != 200:
        print(t); continue
    d = json.loads(t)
    print("KEYS", [k for k in d if k != "results"], {k: d[k] for k in d if k not in ("results", "buckets")})
    res = d["results"]
    arts = re.findall(r"(?s)<article.*?</article>", res)
    print("ANZAHL", len(arts))
    for a in arts[:3]:
        print("---", re.sub(r"\s+", " ", a)[:1500])
