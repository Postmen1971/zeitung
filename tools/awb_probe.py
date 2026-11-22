import json, urllib.request
KEY = "7a4730955599a7e7c0ceb39c548b6abbae874dc7e6a0afc5"
def gql(q, v=None):
    req = urllib.request.Request("https://widgets.abfall.io/graphql", data=json.dumps({"query": q, "variables": v or {}}).encode(),
        headers={"Content-Type": "application/json", "x-abfallplus-api-key": KEY, "User-Agent": "Mozilla/5.0",
                 "Origin": "https://awb-gp.de", "Referer": "https://awb-gp.de/"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.read().decode()
    except urllib.error.HTTPError as e:
        return "HTTP%s %s" % (e.code, "; ".join(m["message"] for m in json.loads(e.read().decode()).get("errors", [])))
for q in ['{appointments(idHouseNumber:"4021"){id}}',
          '{appointments(idHouseNumber:"4021"){date wasteType{id name color} xyz}}',
          '{appointments(idHouseNumber:"4021", xyz:1){id}}',
          '{appointments(idHouseNumber:"4021"){id date time location note wasteType{id name color internals{pdfLegend iconLow}}}}']:
    print("Q", q); print("  ->", gql(q)[:2500])
