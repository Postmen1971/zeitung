"""Einmalig: Kennungen für Ebersbach im abfall.io-System des AWB Göppingen ermitteln."""
import re, urllib.parse, urllib.request, html

KEY = "f35bd08b1d18d9c81fcdee75dbcce5d3"
MODUS = "d6c5855a62cf32a4dadbc2831f0f295f"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def anfrage(waction, daten=None):
    url = "https://api.abfall.io/?" + urllib.parse.urlencode({"key": KEY, "modus": MODUS, "waction": waction})
    body = urllib.parse.urlencode(daten).encode() if daten is not None else None
    with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def auswahl(text):
    out = {}
    for name, inhalt in re.findall(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', text, re.S):
        out[name] = [(v, html.unescape(t).strip()) for v, t in re.findall(r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', inhalt, re.S)]
    return out

t = anfrage("init")
hidden = dict(re.findall(r'type="hidden" name="([^"]+)" value="([^"]*)"', t))
print("HIDDEN", hidden)
sel = auswahl(t)
for n, opts in sel.items():
    print("SELECT", n, len(opts), [o for o in opts if "bersbach" in o[1]] or opts[:5])
kommune = next((v for n, o in sel.items() for v, txt in o if "Ebersbach" in txt), None)
print("KOMMUNE", kommune)
daten = dict(hidden); daten["f_id_kommune"] = kommune
t2 = anfrage("auswahl_kommune_set", daten)
sel2 = auswahl(t2)
for n, opts in sel2.items():
    print("SELECT2", n, len(opts))
    for v, txt in opts:
        print("   ", v, txt)
hidden2 = dict(re.findall(r'type="hidden" name="([^"]+)" value="([^"]*)"', t2))
print("HIDDEN2", hidden2)
print("ABFALLARTEN", re.findall(r'name="(f_id_abfalltyp_\d+)" value="(\d+)"[^>]*>\s*(?:<[^>]+>)*\s*([^<]*)', t2)[:20])
print("ROH-AUSSCHNITT", re.sub(r"\s+", " ", t2)[:1500])
