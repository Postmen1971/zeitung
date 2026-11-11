#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MORGEN-KNALLER – deine persönliche Boulevard-Tageszeitung aus RSS-Feeds.

Holt morgens News zu deinen Themen (Galatasaray, Fußball, Boxen, KI, Welt,
Gentherapie-Forschung, Technik & Erfindungen, Visionen), sortiert, entfernt
Doppelte, markiert Neues und baut daraus eine HTML-Zeitung im Boulevard-Look.

Nur Python-Standardbibliothek (3.8+), keine Installation nötig.

Benutzung:
    python3 zeitung.py                 # Zeitung bauen  -> ausgaben/zeitung_JJJJ-MM-TT.html
    python3 zeitung.py --oeffnen       # ... und direkt im Browser öffnen
    python3 zeitung.py --demo          # Layout mit Platzhaltern testen (ohne Internet)
    python3 zeitung.py --ausgabe /var/www/html   # z. B. für Raspberry Pi + Webserver

Jeden Morgen automatisch (Linux / Raspberry Pi, `crontab -e`):
    30 6 * * *  cd /home/pi/zeitung && /usr/bin/python3 zeitung.py
Windows: Aufgabenplanung -> täglich 06:30 -> Programm: python, Argument: zeitung.py --oeffnen
"""

import argparse
import concurrent.futures
import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import webbrowser
import xml.etree.ElementTree as ET
from pathlib import Path

# ════════════════════════════════════════════════════════════════════
#  EINSTELLUNGEN – hier anpassen
# ════════════════════════════════════════════════════════════════════

ZEITUNG_NAME = "MORGEN-KNALLER"
UNTERTITEL = "Deine Zeitung. Nur deine Themen."
MAX_PRO_RESSORT = 6          # Artikel pro Rubrik
MAX_ALTER_STUNDEN = 36       # ältere Meldungen fliegen raus
TIMEOUT_SEKUNDEN = 15
BASIS = Path(__file__).resolve().parent
STATUS_DATEI = BASIS / "gelesen.json"   # merkt sich, was schon da war (für "NEU")

# Lieblings-Stichwörter: erhöhen die Wichtigkeit (Wert = Bonuspunkte)
FAVORITEN = {
    "galatasaray": 6, "cimbom": 6, "derby": 3, "fenerbahçe": 2, "champions league": 3,
    "durchbruch": 4, "weltrekord": 3, "weltmeister": 3, "k.o.": 3, "titel": 2,
    "gentherapie": 4, "crispr": 4, "heilung": 3, "zulassung": 2,
    "künstliche intelligenz": 2, "ki-modell": 2, "roboter": 2, "erfindung": 3,
    "fusion": 2, "raumfahrt": 2, "mars": 2, "quanten": 2,
}

# Meldungen mit diesen Wörtern werden ausgeblendet
SPERRLISTE = ["horoskop", "gewinnspiel", "anzeige", "sponsored", "rabattcode"]


def gnews(suche: str, sprache: str = "de") -> str:
    """Google-News-Suche als RSS (letzte 2 Tage)."""
    q = urllib.parse.quote(f"{suche} when:2d")
    region = {"de": "hl=de&gl=DE&ceid=DE:de",
              "tr": "hl=tr&gl=TR&ceid=TR:tr",
              "en": "hl=en-US&gl=US&ceid=US:en"}[sprache]
    return f"https://news.google.com/rss/search?q={q}&{region}"


def F(url: str, filtern: bool = False) -> dict:
    """Feed-Eintrag. filtern=True: nur Artikel behalten, die ein Ressort-Stichwort enthalten."""
    return {"url": url, "filtern": filtern}


RESSORTS = [
    {"id": "gs", "dach": "CİMBOM", "titel": "Galatasaray", "stil": "gs",
     "stichwoerter": ["galatasaray", "cimbom", "cim bom"],
     "feeds": [F(gnews("Galatasaray"), True), F(gnews("Galatasaray", "tr"), True),
               F(gnews("Galatasaray", "en"), True)]},
    {"id": "fussball", "dach": "SPORT", "titel": "Fußball", "stil": "sport",
     "stichwoerter": [],
     "feeds": [F(gnews("Bundesliga")), F(gnews("Champions League")),
               F(gnews("Süper Lig", "tr")), F(gnews("Fußball Nationalmannschaft"))]},
    {"id": "boxen", "dach": "SPORT", "titel": "Boxen", "stil": "sport",
     "stichwoerter": ["box", "boxing", "kampf", "fight", "ko", "wbc", "wba", "ibf", "wbo"],
     "feeds": [F(gnews("Boxen Kampf")), F(gnews("boxing fight", "en"))]},
    {"id": "ki", "dach": "DIGITAL", "titel": "Neues von der KI", "stil": "digital",
     "stichwoerter": [" ki", "ki-", "künstliche intelligenz", " ai ", "ai-", "chatgpt", "openai",
                      "anthropic", "claude", "gemini", "llm", "sprachmodell", "machine learning"],
     "feeds": [F(gnews("Künstliche Intelligenz")), F(gnews("artificial intelligence", "en")),
               F("https://www.heise.de/rss/heise-atom.xml", True)]},
    {"id": "welt", "dach": "NACHRICHTEN", "titel": "Die Welt heute", "stil": "welt",
     "stichwoerter": [],
     "feeds": [F("https://www.tagesschau.de/xml/rss2/"),
               F("https://rss.dw.com/rdf/rss-de-all")]},
    {"id": "forschung", "dach": "MEDIZIN", "titel": "Forschung & Gentherapie", "stil": "forschung",
     "stichwoerter": [],
     "feeds": [F(gnews("Gentherapie")), F(gnews("gene therapy", "en")), F(gnews("CRISPR")),
               F("https://www.sciencedaily.com/rss/health_medicine/gene_therapy.xml")]},
    {"id": "technik", "dach": "TECHNIK", "titel": "Technik & Erfindungen", "stil": "technik",
     "stichwoerter": [],
     "feeds": [F("https://rss.golem.de/rss.php?feed=RSS2.0"), F(gnews("Erfindung")),
               F(gnews("neue Technologie Durchbruch"))]},
    {"id": "visionen", "dach": "ZUKUNFT", "titel": "Visionen – morgen ist heute", "stil": "visionen",
     "stichwoerter": [],
     "feeds": [F(gnews("Zukunftstechnologie")), F(gnews("Raumfahrt")),
               F(gnews("Kernfusion")), F(gnews("future technology breakthrough", "en"))]},
]

SPRUECHE = [  # Sprichwörter (gemeinfrei)
    "Damlaya damlaya göl olur. – Tropfen für Tropfen wird ein See.",
    "Übung macht den Meister.",
    "Sabrın sonu selamettir. – Am Ende der Geduld wartet das Glück.",
    "Wer nicht wagt, der nicht gewinnt.",
    "Bin bilsen de bir bilene danış. – Weißt du tausend Dinge, frag trotzdem einen, der es weiß.",
    "Steter Tropfen höhlt den Stein.",
    "Ağaç yaşken eğilir. – Den Baum biegt man, solange er jung ist.",
    "Morgenstund hat Gold im Mund.",
    "Ne ekersen onu biçersin. – Was du säst, das erntest du.",
    "Aller Anfang ist schwer.",
]

# ════════════════════════════════════════════════════════════════════
#  FEEDS LADEN & LESEN
# ════════════════════════════════════════════════════════════════════

UA = "Mozilla/5.0 (X11; Linux x86_64) MorgenKnaller/1.0 (+lokales RSS-Skript)"


def laden(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, */*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEKUNDEN) as r:
        return r.read()


def lokal(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def kind(el, *namen):
    for c in el:
        if lokal(c.tag) in namen:
            return c
    return None


def text_von(el, *namen) -> str:
    c = kind(el, *namen)
    return (c.text or "").strip() if c is not None and c.text else ""


TAG_RE = re.compile(r"<[^>]+>")


def saeubern(s: str) -> str:
    s = html.unescape(TAG_RE.sub(" ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def datum_lesen(s: str):
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        d = None
    if d is None:
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d


def bild_finden(item, roh_html: str) -> str:
    for c in item.iter():
        t = lokal(c.tag)
        if t in ("content", "thumbnail") and c.get("url"):
            typ = c.get("type", "") or c.get("medium", "")
            if not typ or "image" in typ:
                return c.get("url")
        if t == "enclosure" and "image" in (c.get("type") or "") and c.get("url"):
            return c.get("url")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', roh_html or "")
    return html.unescape(m.group(1)) if m else ""


def xml_parsen(daten: bytes):
    try:
        return ET.fromstring(daten)
    except ET.ParseError:
        # HTML-Entities wie &nbsp; reparieren, die XML nicht kennt
        t = daten.decode("utf-8", errors="replace").lstrip("﻿ \r\n\t")
        t = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)([a-zA-Z]+);",
                   lambda m: html.escape(html.unescape(m.group(0))), t)
        return ET.fromstring(t.encode("utf-8"))


def feed_lesen(daten: bytes, feed_url: str):
    root = xml_parsen(daten)
    feed_titel = ""
    ch = kind(root, "channel")
    if ch is not None:
        feed_titel = text_von(ch, "title")
    elif lokal(root.tag) == "feed":
        feed_titel = text_von(root, "title")
    artikel = []
    for item in root.iter():
        if lokal(item.tag) not in ("item", "entry"):
            continue
        titel = saeubern(text_von(item, "title"))
        if not titel:
            continue
        link = text_von(item, "link")
        if not link:
            for c in item:
                if lokal(c.tag) == "link" and c.get("href") and c.get("rel", "alternate") == "alternate":
                    link = c.get("href")
                    break
        roh = text_von(item, "encoded") or text_von(item, "description") or \
            text_von(item, "summary") or text_von(item, "content")
        datum = datum_lesen(text_von(item, "pubdate", "published", "updated", "date"))
        quelle = text_von(item, "source") or feed_titel
        if "news.google.com" in feed_url and " - " in titel:   # "Schlagzeile - Quelle"
            titel, quelle = titel.rsplit(" - ", 1)
        teaser = saeubern(roh)
        if teaser.lower().startswith(titel.lower()[:40]) or len(teaser) < 25:
            teaser = ""          # Google News wiederholt nur den Titel
        artikel.append({"titel": titel.strip(), "link": link.strip(), "teaser": teaser,
                        "datum": datum, "quelle": saeubern(quelle), "bild": bild_finden(item, roh)})
    return artikel


# ════════════════════════════════════════════════════════════════════
#  SORTIEREN, FILTERN, DOPPELTE RAUS
# ════════════════════════════════════════════════════════════════════

def schluessel(titel: str) -> str:
    t = re.sub(r"[^a-z0-9äöüßçğışö ]", "", titel.lower())
    return re.sub(r"\s+", " ", t)[:70]


def punkte(a: dict, jetzt: dt.datetime) -> float:
    p = 0.0
    if a["datum"]:
        stunden = (jetzt - a["datum"]).total_seconds() / 3600
        p += max(0.0, 10 - stunden / 3)        # frisch = mehr Punkte
    text = f" {a['titel']} {a['teaser']} ".lower()
    p += sum(w for k, w in FAVORITEN.items() if k in text)
    if a["bild"]:
        p += 1.5
    if a.get("neu"):
        p += 2
    return p


def status_laden() -> dict:
    try:
        return json.loads(STATUS_DATEI.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def status_speichern(status: dict, jetzt: dt.datetime):
    grenze = (jetzt - dt.timedelta(days=7)).timestamp()
    status = {k: v for k, v in status.items() if v > grenze}
    try:
        STATUS_DATEI.write_text(json.dumps(status), "utf-8")
    except OSError:
        pass


def zeitung_sammeln():
    jetzt = dt.datetime.now(dt.timezone.utc)
    auftraege = [(r, f) for r in RESSORTS for f in r["feeds"]]
    ergebnisse, fehler = {}, []

    def hole(rf):
        r, f = rf
        return r["id"], f, feed_lesen(laden(f["url"]), f["url"])

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for fut, (r, f) in zip([pool.submit(hole, rf) for rf in auftraege], auftraege):
            try:
                rid, feed, liste = fut.result()
                ergebnisse.setdefault(rid, []).append((feed, liste))
            except Exception as e:  # Feed down? Egal, weiter.
                fehler.append(f"{r['titel']}: {urllib.parse.urlparse(f['url']).netloc} ({type(e).__name__})")

    status = status_laden()
    gesehen_global = set()
    ausgabe = []
    for r in RESSORTS:
        kandidaten = []
        for feed, liste in ergebnisse.get(r["id"], []):
            for a in liste:
                text = f" {a['titel']} {a['teaser']} ".lower()
                if any(s in text for s in SPERRLISTE):
                    continue
                if feed["filtern"] and r["stichwoerter"] and not any(s in text for s in r["stichwoerter"]):
                    continue
                if a["datum"] and (jetzt - a["datum"]).total_seconds() > MAX_ALTER_STUNDEN * 3600:
                    continue
                kandidaten.append(a)
        auswahl = []
        for a in sorted(kandidaten, key=lambda x: x["datum"] or jetzt, reverse=True):
            k = schluessel(a["titel"])
            if k in gesehen_global:
                continue
            gesehen_global.add(k)
            h = hashlib.sha1(k.encode()).hexdigest()[:16]
            a["neu"] = h not in status
            status.setdefault(h, jetzt.timestamp())
            a["punkte"] = punkte(a, jetzt)
            auswahl.append(a)
        auswahl.sort(key=lambda x: x["punkte"], reverse=True)
        ausgabe.append((r, auswahl[:MAX_PRO_RESSORT]))
    status_speichern(status, jetzt)
    return ausgabe, fehler


def demo_sammeln():
    jetzt = dt.datetime.now(dt.timezone.utc)
    ausgabe = []
    for i, r in enumerate(RESSORTS):
        liste = []
        for n in range(4):
            liste.append({
                "titel": f"Platzhalter-Schlagzeile {n + 1} für {r['titel']}" if n else
                         f"HIER STEHT DIE GRÖSSTE {r['titel'].upper()}-SCHLAGZEILE DES TAGES",
                "link": "#", "teaser": "Beispieltext: So sieht der Anreißer aus, wenn der Feed eine "
                                      "Beschreibung mitliefert. Im echten Lauf steht hier die Meldung.",
                "datum": jetzt - dt.timedelta(hours=n * 3 + i), "quelle": "Demo-Quelle",
                "bild": "", "neu": n < 2, "punkte": 20 - n - (0 if r["id"] == "gs" else 1)})
        ausgabe.append((r, liste))
    return ausgabe, []


# ════════════════════════════════════════════════════════════════════
#  HTML IM BOULEVARD-LOOK
# ════════════════════════════════════════════════════════════════════

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#e9e6df;font-family:Helvetica,Arial,sans-serif;color:#111}
a{color:inherit;text-decoration:none}
.blatt{max-width:1100px;margin:0 auto;background:#fff;box-shadow:0 0 30px rgba(0,0,0,.15)}
.kopf{display:flex;align-items:stretch;border-bottom:6px solid #111}
.logo{background:#d0021b;color:#fff;padding:14px 22px;font:900 italic clamp(34px,7vw,68px)/.9 Impact,"Arial Black",sans-serif;
 letter-spacing:-1px;text-transform:uppercase;transform:skewX(-4deg);margin-left:6px}
.kopfinfo{flex:1;padding:10px 16px;display:flex;flex-direction:column;justify-content:center;font-size:13px}
.kopfinfo b{font-size:15px}.kopfinfo .unter{color:#d0021b;font-weight:800;text-transform:uppercase;letter-spacing:.5px}
.ticker{background:#111;color:#fff;overflow:hidden;white-space:nowrap;font-weight:700;font-size:14px;padding:7px 0}
.ticker span{display:inline-block;padding-left:100%;animation:lauf 90s linear infinite}
.ticker i{color:#ffd400;font-style:normal;margin:0 10px}
@keyframes lauf{to{transform:translateX(-100%)}}
.inhalt{padding:18px}
.aufmacher{display:grid;grid-template-columns:1.3fr 1fr;gap:18px;border-bottom:4px solid #111;padding-bottom:18px;margin-bottom:18px}
.aufmacher .bildbox{min-height:260px;background:#111 center/cover no-repeat;position:relative}
.aufmacher .bildbox.leer{background:repeating-linear-gradient(-45deg,#d0021b 0 22px,#b00016 22px 44px)}
.stoerer{position:absolute;top:14px;left:-8px;background:#ffd400;color:#111;font:900 20px Impact,"Arial Black",sans-serif;
 padding:6px 14px;transform:rotate(-4deg);box-shadow:3px 3px 0 #111;text-transform:uppercase}
.aufmacher h1{font:900 clamp(30px,5vw,54px)/1 Impact,"Arial Black",sans-serif;text-transform:uppercase;margin:6px 0 10px}
.aufmacher h1 a:hover{color:#d0021b}
.dach{color:#d0021b;font-weight:900;text-transform:uppercase;font-size:13px;letter-spacing:.5px}
.teaser{font-size:15px;line-height:1.4}
.meta{font-size:11.5px;color:#666;margin-top:6px}
.neu{background:#d0021b;color:#fff;font-weight:900;font-size:10.5px;padding:1px 5px;margin-right:5px;vertical-align:2px}
.spruch{background:#ffd400;padding:12px 16px;font-weight:800;margin-bottom:18px;border-left:10px solid #111;font-size:15px}
.spruch small{display:block;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px}
.raster{display:grid;grid-template-columns:repeat(2,1fr);gap:22px}
.ressort{border-top:3px solid #111}
.ressort.breit{grid-column:1/-1}
.rkopf{display:flex;align-items:baseline;gap:10px;background:#d0021b;color:#fff;padding:6px 10px;margin:0 0 10px}
.rkopf b{font:900 22px Impact,"Arial Black",sans-serif;text-transform:uppercase;letter-spacing:.5px}
.rkopf span{font-size:12px;font-weight:700;opacity:.85;text-transform:uppercase}
.ressort.gs .rkopf{background:linear-gradient(90deg,#a90432 0 50%,#fdb912 50%);}
.ressort.gs .rkopf b{color:#fff;text-shadow:2px 2px 0 #a90432}
.ressort.gs .rkopf span{color:#a90432;margin-left:auto;opacity:1;background:#fff;padding:1px 6px}
.ressort.gs{border-top-color:#fdb912}
.ressort.digital .rkopf{background:#111}.ressort.welt .rkopf{background:#00305e}
.ressort.forschung .rkopf{background:#0a7d5a}.ressort.technik .rkopf{background:#4b4b4b}
.ressort.visionen .rkopf{background:linear-gradient(90deg,#3a0ca3,#7209b7)}
.top{display:flex;gap:12px;padding-bottom:10px;border-bottom:1px solid #ccc;margin-bottom:8px}
.top .tb{flex:0 0 120px;height:90px;background:#ddd center/cover}
.top h2{font:900 22px/1.05 Impact,"Arial Black",sans-serif;text-transform:uppercase}
.top h2 a:hover,.liste a:hover{color:#d0021b}
.liste li{list-style:none;padding:7px 0;border-bottom:1px dotted #bbb;font-weight:700;font-size:15px;line-height:1.25}
.liste li::before{content:"■ ";color:#d0021b}
.ressort.gs .liste li::before{color:#fdb912}
.leer{color:#888;font-style:italic;font-size:14px;padding:6px 0}
.fuss{border-top:6px solid #111;margin-top:24px;padding:12px 18px;font-size:12px;color:#555;background:#f4f2ed}
.fuss details{margin-top:6px}
@media(max-width:720px){.aufmacher,.raster{grid-template-columns:1fr}.aufmacher .bildbox{min-height:170px}
 .kopf{flex-direction:column}.logo{margin:8px}.top .tb{flex-basis:90px;height:70px}}
"""


def e(s) -> str:
    return html.escape(s or "", quote=True)


def zeit_text(d) -> str:
    if not d:
        return ""
    return d.astimezone().strftime("%d.%m. %H:%M Uhr")


def meta(a) -> str:
    teile = [x for x in (a.get("quelle"), zeit_text(a.get("datum"))) if x]
    return f'<div class="meta">{e(" · ".join(teile))}</div>'


def neu_tag(a) -> str:
    return '<span class="neu">NEU</span>' if a.get("neu") else ""


def html_bauen(ausgabe, fehler, demo=False) -> str:
    heute = dt.datetime.now()
    datum = f"{WOCHENTAGE[heute.weekday()]}, {heute.day}. {MONATE[heute.month - 1]} {heute.year}"
    alle = [(r, a) for r, liste in ausgabe for a in liste]
    aufmacher_r, aufmacher = (max(alle, key=lambda x: x[1]["punkte"]) if alle else (None, None))
    spruch = SPRUECHE[heute.toordinal() % len(SPRUECHE)]

    ticker = " ".join(f'<i>+++</i>{e(a["titel"])}' for _, a in
                      sorted(alle, key=lambda x: x[1]["datum"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
                             reverse=True)[:14])

    teile = [f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(ZEITUNG_NAME)} – {e(datum)}</title><style>{CSS}</style></head><body><div class="blatt">
<header class="kopf"><div class="logo">{e(ZEITUNG_NAME)}</div>
<div class="kopfinfo"><span class="unter">{e(UNTERTITEL)}</span><b>{e(datum)}</b>
<span>{len(alle)} Meldungen · {sum(1 for _, a in alle if a.get("neu"))} neu seit der letzten Ausgabe{" · DEMO" if demo else ""}</span></div></header>
<div class="ticker"><span>{ticker or "+++ Keine Meldungen +++"}</span></div><main class="inhalt">"""]

    if aufmacher:
        bild = f' style="background-image:url(\'{e(aufmacher["bild"])}\')"' if aufmacher["bild"] else ""
        teile.append(f"""<section class="aufmacher">
<a class="bildbox{'' if bild else ' leer'}" href="{e(aufmacher['link'])}" target="_blank" rel="noopener"{bild}>
<span class="stoerer">{e(aufmacher_r['dach'])}!</span></a>
<div><div class="dach">{neu_tag(aufmacher)}{e(aufmacher_r['titel'])}</div>
<h1><a href="{e(aufmacher['link'])}" target="_blank" rel="noopener">{e(aufmacher['titel'])}</a></h1>
<p class="teaser">{e(aufmacher['teaser'][:320])}</p>{meta(aufmacher)}</div></section>""")

    teile.append(f'<div class="spruch"><small>Spruch des Tages</small>{e(spruch)}</div><div class="raster">')

    for r, liste in ausgabe:
        liste = [a for a in liste if a is not aufmacher]
        klasse = f"ressort {r['stil']}" + (" breit" if r["id"] in ("gs", "welt") else "")
        teile.append(f'<section class="{klasse}"><div class="rkopf"><b>{e(r["dach"])}</b><span>{e(r["titel"])}</span></div>')
        if not liste:
            teile.append('<p class="leer">Heute nichts Neues – oder der Feed schläft noch.</p></section>')
            continue
        top, rest = liste[0], liste[1:]
        tb = f'<a class="tb" href="{e(top["link"])}" target="_blank" rel="noopener" style="background-image:url(\'{e(top["bild"])}\')"></a>' if top["bild"] else ""
        teile.append(f"""<div class="top">{tb}<div><div class="dach">{neu_tag(top)}{e(r['titel'])}</div>
<h2><a href="{e(top['link'])}" target="_blank" rel="noopener">{e(top['titel'])}</a></h2>
<p class="teaser">{e(top['teaser'][:200])}</p>{meta(top)}</div></div><ul class="liste">""")
        for a in rest:
            teile.append(f'<li>{neu_tag(a)}<a href="{e(a["link"])}" target="_blank" rel="noopener">{e(a["titel"])}</a>{meta(a)}</li>')
        teile.append("</ul></section>")

    fehl = ""
    if fehler:
        fehl = "<details><summary>{} Feed(s) nicht erreichbar</summary><ul>{}</ul></details>".format(
            len(fehler), "".join(f"<li>{e(x)}</li>" for x in fehler))
    teile.append(f"""</div></main><footer class="fuss">Erstellt {heute.strftime('%d.%m.%Y, %H:%M Uhr')} aus RSS-Feeds.
Alle Meldungen verlinken auf die Original-Quelle.{fehl}</footer></div></body></html>""")
    return "\n".join(teile)


# ════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description=f"{ZEITUNG_NAME} – persönliche Tageszeitung aus RSS")
    ap.add_argument("--ausgabe", default=str(BASIS / "ausgaben"), help="Ordner für die HTML-Datei")
    ap.add_argument("--oeffnen", action="store_true", help="danach im Browser öffnen")
    ap.add_argument("--demo", action="store_true", help="Platzhalter statt echter Feeds")
    args = ap.parse_args()

    ausgabe, fehler = demo_sammeln() if args.demo else zeitung_sammeln()
    seite = html_bauen(ausgabe, fehler, demo=args.demo)

    ordner = Path(args.ausgabe)
    ordner.mkdir(parents=True, exist_ok=True)
    datei = ordner / f"zeitung_{dt.date.today().isoformat()}.html"
    datei.write_text(seite, "utf-8")
    (ordner / "index.html").write_text(seite, "utf-8")   # immer die neueste Ausgabe

    anzahl = sum(len(l) for _, l in ausgabe)
    print(f"✔ {anzahl} Meldungen -> {datei}")
    if fehler:
        print(f"⚠ {len(fehler)} Feed(s) nicht erreichbar:", *fehler, sep="\n   ")
    if args.oeffnen:
        webbrowser.open(datei.resolve().as_uri())


if __name__ == "__main__":
    sys.exit(main())
