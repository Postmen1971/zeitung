import json, urllib.request, re
KEY = "7a4730955599a7e7c0ceb39c548b6abbae874dc7e6a0afc5"
def gql(q, v=None):
    req = urllib.request.Request("https://widgets.abfall.io/graphql", data=json.dumps({"query": q, "variables": v or {}}).encode(),
        headers={"Content-Type": "application/json", "x-abfallplus-api-key": KEY, "User-Agent": "Mozilla/5.0",
                 "Origin": "https://awb-gp.de", "Referer": "https://awb-gp.de/"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.read().decode()
    except urllib.error.HTTPError as e:
        return "HTTP%s %s" % (e.code, "; ".join(m["message"] for m in json.loads(e.read().decode()).get("errors", [])))
s = json.loads(gql('query{city(id:"907"){streets{id name}}}'))
st = s["data"]["city"]["streets"]
print("ANZAHL", len(st), [x for x in st if re.search(r"Haupt|Markt|Rathaus|Bahnhof|Kirch", x["name"])])
sid = next(x["id"] for x in st if x["name"] == "Hauptstraße")
for q in ['{appointments{id}}', '{appointments(cityId:"907"){id}}', '{street(id:"%s"){id name houseNumbers{id name}}}' % sid,
          '{street(id:"%s"){id name xyz}}' % sid, '{wasteTypes{id name}}', '{city(id:"907"){id xyz}}',
          '{appointments(id:"%s", wasteTypes:[], dateMin:"2026-11-22", dateMax:"2026-12-31"){date wasteType{id name color}}}' % sid,
          '{appointments(id:"%s"){xyz}}' % sid]:
    print("Q", q); print("  ->", gql(q)[:1500])
