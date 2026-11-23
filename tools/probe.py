import re, urllib.request, urllib.parse, json, html
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131 Safari/537.36",
      "Accept": "application/json, text/html", "X-Requested-With": "XMLHttpRequest", "Referer": "https://www.ebersbach.de/veranstaltung"}
def req(u, data=None, ct=None):
    h = dict(UA)
    if ct: h["Content-Type"] = ct
    try:
        with urllib.request.urlopen(urllib.request.Request(u, data=data, headers=h), timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:
        return 0, str(e)
seite = req("https://www.ebersbach.de/veranstaltung")[1]
doc = re.search(r'document="([^"]+)"', seite).group(1)
ep = "https://www.ebersbach.de/api/event/list/event-appointment"
filters = json.dumps({"date": ["2026-11-23 00:00:00", None]})
params = {"document": doc, "limit": 24, "page": 1, "template": "default", "type": "EventAppointment", "filters": filters}
for name, (u, d, ct) in {
    "GET": (ep + "?" + urllib.parse.urlencode(params), None, None),
    "POSTjson": (ep, json.dumps(params).encode(), "application/json"),
    "POSTform": (ep, urllib.parse.urlencode(params).encode(), "application/x-www-form-urlencoded"),
    "GETnur": (ep + "?document=" + doc, None, None)}.items():
    st, t = req(u, d, ct)
    print("##", name, st, len(t)); print(re.sub(r"\s+", " ", t)[:2500])
# JS des Widgets finden
for s in sorted(set(re.findall(r'src="([^"]+\.js[^"]*)"', seite))):
    if "disgovery" in s.lower() or "widget" in s.lower() or "list" in s.lower():
        print("JS", s)
st, n = req("https://www.ebersbach.de/nachrichten")
n = re.sub(r"(?is)<(script|style|svg)[^>]*>.*?</\1>", "", n)
i = n.find("<main")
print("## NACHRICHTEN", st); print(re.sub(r"\s+", " ", n[i:])[:3500])
