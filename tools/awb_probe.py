import json, urllib.request
KEY = "7a4730955599a7e7c0ceb39c548b6abbae874dc7e6a0afc5"
def gql(q, v=None):
    req = urllib.request.Request("https://widgets.abfall.io/graphql", data=json.dumps({"query": q, "variables": v or {}}).encode(),
        headers={"Content-Type": "application/json", "x-abfallplus-api-key": KEY, "User-Agent": "Mozilla/5.0",
                 "Origin": "https://awb-gp.de", "Referer": "https://awb-gp.de/"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return r.read().decode()
    except urllib.error.HTTPError as e: return "HTTP%s %s" % (e.code, e.read().decode()[:800])
s = gql('{__schema{queryType{fields{name args{name type{name kind ofType{name kind ofType{name}}}} type{name kind ofType{name}}}}}}')
print("SCHEMA", s[:4000])
for t in ["City", "Appointment", "WasteType", "Street", "AppointmentFilter"]:
    print("TYPE", t, gql('query($n:String!){__type(name:$n){fields{name type{name kind ofType{name}}} inputFields{name type{name kind ofType{name}}}}}', {"n": t})[:1500])
print("STREETS", gql('query{city(id:"907"){id name streets{id name}}}')[:1500])
print("STREETS2", gql('query($id:ID!){streets(cityId:$id){id name}}', {"id": "907"})[:1500])
