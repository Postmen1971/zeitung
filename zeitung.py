#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MORGEN-KNALLER – deine persönliche Boulevard-Tageszeitung aus RSS-Feeds.

Holt morgens News zu deinen Themen (Galatasaray, Fußball, Boxen, KI, Welt,
Gentherapie-Forschung, Technik & Erfindungen, Visionen), sortiert, entfernt
Doppelte, markiert Neues, sucht Fotos und baut daraus
  • eine Webseite im Boulevard-Look (index.html) und
  • auf Wunsch eine PDF-Zeitung mit Titelseite und Rubrikseiten (zeitung.pdf).

Nur Python-Standardbibliothek (3.8+). Für das PDF wird Chrome, Chromium oder
Edge benutzt (ist auf den meisten Rechnern schon da).

Benutzung:
    python3 zeitung.py                  # Webseite bauen -> ausgaben/index.html
    python3 zeitung.py --pdf --oeffnen  # + PDF-Zeitung, danach öffnen
    python3 zeitung.py --demo --pdf     # Layout mit Platzhaltern testen (ohne Internet)
    python3 zeitung.py --ausgabe /var/www/html   # z. B. Raspberry Pi + Webserver

Jeden Morgen automatisch (Linux / Raspberry Pi, `crontab -e`):
    30 6 * * *  cd /home/pi/zeitung && /usr/bin/python3 zeitung.py --pdf
Windows: Aufgabenplanung -> täglich 06:30 -> Programm: python, Argument: zeitung.py --pdf --oeffnen
"""

import argparse
import base64
import concurrent.futures
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
MAX_PRO_RESSORT = 8          # so viele Meldungen pro Rubrik werden gesammelt
WEB_PRO_RESSORT = 6          # ... davon auf der Webseite gezeigt
MAX_ALTER_STUNDEN = 36       # ältere Meldungen fliegen raus
TIMEOUT_SEKUNDEN = 15
FOTOS_SUCHEN = True          # fehlende Fotos von der Artikelseite holen (og:image)
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
     "feeds": [F("https://newsfeed.kicker.de/news/fussball"), F(gnews("Bundesliga")),
               F(gnews("Champions League")), F(gnews("Süper Lig", "tr"))]},
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

# Aufbau der PDF-Zeitung: Seite 1 = Titelseite, danach je Seite eine oder zwei Rubriken
PDF_SEITEN = [["gs"], ["fussball", "boxen"], ["welt"], ["ki", "forschung"], ["technik", "visionen"]]

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

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36 MorgenKnaller/1.1"


def laden(url: str, max_bytes: int = 0):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*",
                                               "Accept-Language": "de,en;q=0.8,tr;q=0.6"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEKUNDEN) as r:
        daten = r.read(max_bytes) if max_bytes else r.read()
        return daten, r.headers.get("Content-Type", ""), r.geturl()


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
        t = daten.decode("utf-8", errors="replace").lstrip("\ufeff \r\n\t")
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
        return r["id"], f, feed_lesen(laden(f["url"])[0], f["url"])

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


# ════════════════════════════════════════════════════════════════════
#  FOTOS & TEXTE VON DER ARTIKELSEITE ERGÄNZEN
# ════════════════════════════════════════════════════════════════════

def meta_wert(seite: str, *namen) -> str:
    for n in namen:
        for muster in (rf'<meta[^>]+(?:property|name)=["\']{re.escape(n)}["\'][^>]*content=["\']([^"\']+)',
                       rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']{re.escape(n)}["\']'):
            m = re.search(muster, seite, re.I)
            if m:
                return html.unescape(m.group(1)).strip()
    return ""


def anreichern(ausgabe):
    """Holt für Meldungen ohne Foto/Text das Vorschaubild (og:image) und die Kurzbeschreibung."""
    if not FOTOS_SUCHEN:
        return
    offen = [a for _, liste in ausgabe for a in liste
             if (not a["bild"] or not a["teaser"]) and a["link"].startswith("http")]

    def hole(a):
        daten, _, ziel = laden(a["link"], 400_000)
        if "news.google.com" in urllib.parse.urlparse(ziel).netloc:
            return a, "", ""          # Google-News-Weiterleitung ohne echte Artikelseite
        seite = daten.decode("utf-8", errors="replace")
        bild = meta_wert(seite, "og:image", "og:image:url", "twitter:image")
        text = meta_wert(seite, "og:description", "description", "twitter:description")
        return a, urllib.parse.urljoin(ziel, bild) if bild else "", saeubern(text)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        for fut in concurrent.futures.as_completed([pool.submit(hole, a) for a in offen]):
            try:
                a, bild, text = fut.result()
            except Exception:
                continue
            if bild and not a["bild"]:
                a["bild"] = bild
            if text and not a["teaser"] and not text.lower().startswith(a["titel"].lower()[:40]):
                a["teaser"] = text


# ════════════════════════════════════════════════════════════════════
#  DEMO-DATEN (zum Testen ohne Internet)
# ════════════════════════════════════════════════════════════════════

DEMO_FARBEN = {"gs": ("#a90432", "#fdb912"), "sport": ("#d0021b", "#5a0010"), "digital": ("#111", "#555"),
               "welt": ("#00305e", "#3a7bd5"), "forschung": ("#0a7d5a", "#7dd3b0"),
               "technik": ("#333", "#999"), "visionen": ("#3a0ca3", "#b5179e")}


def demo_bild(stil: str, nr: int) -> str:
    a, b = DEMO_FARBEN.get(stil, ("#444", "#999"))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500"><defs><linearGradient id="g" '
           f'x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/>'
           f'</linearGradient></defs><rect width="800" height="500" fill="url(#g)"/>'
           f'<circle cx="{560 - nr * 90}" cy="{180 + nr * 30}" r="{150 - nr * 20}" fill="#fff" opacity=".12"/>'
           f'<text x="40" y="460" font-family="Arial" font-weight="bold" font-size="40" fill="#fff" opacity=".7">'
           f'FOTO {nr + 1}</text></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def demo_sammeln():
    jetzt = dt.datetime.now(dt.timezone.utc)
    ausgabe = []
    for i, r in enumerate(RESSORTS):
        liste = []
        for n in range(MAX_PRO_RESSORT):
            liste.append({
                "titel": f"HIER STEHT DIE GRÖSSTE {r['titel'].upper()}-SCHLAGZEILE DES TAGES" if n == 0 else
                         f"Platzhalter-Schlagzeile {n + 1}: So sieht eine Meldung aus {r['titel']} aus",
                "link": "#",
                "teaser": "Beispieltext: So sieht der Anreißer aus, wenn der Feed eine Beschreibung "
                          "mitliefert. Im echten Lauf steht hier der Anfang der Meldung aus der Quelle.",
                "datum": jetzt - dt.timedelta(hours=n * 3 + i), "quelle": "Demo-Quelle",
                "bild": demo_bild(r["stil"], n) if n in (0, 1, 3) else "", "neu": n < 2,
                "punkte": 20 - n - (0 if r["id"] == "gs" else 1)})
        ausgabe.append((r, liste))
    return ausgabe, []


# ════════════════════════════════════════════════════════════════════
#  GEMEINSAME HELFER
# ════════════════════════════════════════════════════════════════════

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link href="https://fonts.googleapis.com/css2?family=Anton&family=Roboto+Condensed:wght@400;700;900'
         '&family=PT+Serif:wght@400;700&display=swap" rel="stylesheet">')


def e(s) -> str:
    return html.escape(s or "", quote=True)


def datum_heute() -> str:
    h = dt.datetime.now()
    return f"{WOCHENTAGE[h.weekday()]}, {h.day}. {MONATE[h.month - 1]} {h.year}"


def zeit_text(d) -> str:
    return d.astimezone().strftime("%d.%m. %H:%M Uhr") if d else ""


def meta(a) -> str:
    teile = [x for x in (a.get("quelle"), zeit_text(a.get("datum"))) if x]
    return f'<div class="meta">{e(" · ".join(teile))}</div>'


def neu_tag(a) -> str:
    return '<span class="neu">NEU</span>' if a.get("neu") else ""


def kuerzen(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + " …"


def aufmacher_finden(ausgabe):
    alle = [(r, a) for r, liste in ausgabe for a in liste]
    if not alle:
        return None, None
    # Aufmacher möglichst mit Foto
    return max(alle, key=lambda x: x[1]["punkte"] + (3 if x[1]["bild"] else 0))


# ════════════════════════════════════════════════════════════════════
#  WEBSEITE IM BOULEVARD-LOOK
# ════════════════════════════════════════════════════════════════════

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#e9e6df;font-family:"Roboto Condensed",Helvetica,Arial,sans-serif;color:#111}
a{color:inherit;text-decoration:none}
.H{font-family:Anton,Impact,"Arial Black",sans-serif;font-weight:400;text-transform:uppercase}
.blatt{max-width:1100px;margin:0 auto;background:#fff;box-shadow:0 0 30px rgba(0,0,0,.15)}
.kopf{display:flex;align-items:stretch;border-bottom:6px solid #111}
.logo{background:#d0021b;color:#fff;padding:14px 22px;font-size:clamp(34px,7vw,68px);line-height:.9;
 letter-spacing:-.5px;transform:skewX(-4deg);margin-left:6px}
.kopfinfo{flex:1;padding:10px 16px;display:flex;flex-direction:column;justify-content:center;font-size:13px}
.kopfinfo b{font-size:15px}.kopfinfo .unter{color:#d0021b;font-weight:900;text-transform:uppercase;letter-spacing:.5px}
.pdflink{display:inline-block;margin-top:5px;background:#111;color:#fff;font-weight:900;padding:4px 10px;align-self:flex-start}
.pdflink:hover{background:#d0021b}
.ticker{background:#111;color:#fff;overflow:hidden;white-space:nowrap;font-weight:700;font-size:14px;padding:7px 0}
.ticker span{display:inline-block;padding-left:100%;animation:lauf 90s linear infinite}
.ticker i{color:#ffd400;font-style:normal;margin:0 10px}
@keyframes lauf{to{transform:translateX(-100%)}}
.inhalt{padding:18px}
.aufmacher{display:grid;grid-template-columns:1.3fr 1fr;gap:18px;border-bottom:4px solid #111;padding-bottom:18px;margin-bottom:18px}
.aufmacher .bildbox{min-height:260px;background:#111 center/cover no-repeat;position:relative}
.aufmacher .bildbox.leer{background:repeating-linear-gradient(-45deg,#d0021b 0 22px,#b00016 22px 44px)}
.stoerer{position:absolute;top:14px;left:-8px;background:#ffd400;color:#111;font-size:22px;
 padding:6px 14px;transform:rotate(-4deg);box-shadow:3px 3px 0 #111}
.aufmacher h1{font-size:clamp(32px,5vw,58px);line-height:1;margin:6px 0 10px}
.aufmacher h1 a:hover{color:#d0021b}
.dach{color:#d0021b;font-weight:900;text-transform:uppercase;font-size:13px;letter-spacing:.5px}
.teaser{font-family:"PT Serif",Georgia,serif;font-size:15px;line-height:1.45}
.meta{font-size:11.5px;color:#666;margin-top:6px}
.neu{background:#d0021b;color:#fff;font-weight:900;font-size:10.5px;padding:1px 5px;margin-right:5px;vertical-align:2px}
.spruch{background:#ffd400;padding:12px 16px;font-weight:900;margin-bottom:18px;border-left:10px solid #111;font-size:16px}
.spruch small{display:block;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px}
.raster{display:grid;grid-template-columns:repeat(2,1fr);gap:22px}
.ressort{border-top:3px solid #111}
.ressort.breit{grid-column:1/-1}
.rkopf{display:flex;align-items:baseline;gap:10px;background:#d0021b;color:#fff;padding:6px 10px;margin:0 0 10px}
.rkopf b{font-size:24px;letter-spacing:.5px}
.rkopf span{font-size:12px;font-weight:700;opacity:.85;text-transform:uppercase}
.ressort.gs .rkopf{background:linear-gradient(90deg,#a90432 0 50%,#fdb912 50%);}
.ressort.gs .rkopf b{color:#fff;text-shadow:2px 2px 0 #a90432}
.ressort.gs .rkopf span{color:#a90432;margin-left:auto;opacity:1;background:#fff;padding:1px 6px}
.ressort.gs{border-top-color:#fdb912}
.ressort.digital .rkopf{background:#111}.ressort.welt .rkopf{background:#00305e}
.ressort.forschung .rkopf{background:#0a7d5a}.ressort.technik .rkopf{background:#4b4b4b}
.ressort.visionen .rkopf{background:linear-gradient(90deg,#3a0ca3,#7209b7)}
.top{display:flex;gap:12px;padding-bottom:10px;border-bottom:1px solid #ccc;margin-bottom:8px}
.top .tb{flex:0 0 130px;height:96px;background:#ddd center/cover}
.top h2{font-size:23px;line-height:1.05}
.top h2 a:hover,.liste a:hover{color:#d0021b}
.liste li{list-style:none;padding:7px 0;border-bottom:1px dotted #bbb;font-weight:700;font-size:15.5px;line-height:1.25}
.liste li::before{content:"■ ";color:#d0021b}
.ressort.gs .liste li::before{color:#fdb912}
.leer{color:#888;font-style:italic;font-size:14px;padding:6px 0}
.fuss{border-top:6px solid #111;margin-top:24px;padding:12px 18px;font-size:12px;color:#555;background:#f4f2ed}
.fuss details{margin-top:6px}
@media(max-width:720px){.aufmacher,.raster{grid-template-columns:1fr}.aufmacher .bildbox{min-height:190px}
 .kopf{flex-direction:column}.logo{margin:8px}.top .tb{flex-basis:96px;height:74px}}
"""


def html_bauen(ausgabe, fehler, demo=False, pdf_name="") -> str:
    heute = dt.datetime.now()
    alle = [(r, a) for r, liste in ausgabe for a in liste[:WEB_PRO_RESSORT]]
    aufmacher_r, aufmacher = aufmacher_finden([(r, l[:WEB_PRO_RESSORT]) for r, l in ausgabe])
    spruch = SPRUECHE[heute.toordinal() % len(SPRUECHE)]
    ticker = " ".join(f'<i>+++</i>{e(a["titel"])}' for _, a in
                      sorted(alle, key=lambda x: x[1]["datum"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
                             reverse=True)[:14])
    pdf = f'<a class="pdflink" href="{e(pdf_name)}">📰 ALS ZEITUNG LESEN (PDF)</a>' if pdf_name else ""

    teile = [f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(ZEITUNG_NAME)} – {e(datum_heute())}</title>{FONTS}<style>{CSS}</style></head><body><div class="blatt">
<header class="kopf"><div class="logo H">{e(ZEITUNG_NAME)}</div>
<div class="kopfinfo"><span class="unter">{e(UNTERTITEL)}</span><b>{e(datum_heute())}</b>
<span>{len(alle)} Meldungen · {sum(1 for _, a in alle if a.get("neu"))} neu seit der letzten Ausgabe{" · DEMO" if demo else ""}</span>{pdf}</div></header>
<div class="ticker"><span>{ticker or "+++ Keine Meldungen +++"}</span></div><main class="inhalt">"""]

    if aufmacher:
        bild = f' style="background-image:url(\'{e(aufmacher["bild"])}\')"' if aufmacher["bild"] else ""
        teile.append(f"""<section class="aufmacher">
<a class="bildbox{'' if bild else ' leer'}" href="{e(aufmacher['link'])}" target="_blank" rel="noopener"{bild}>
<span class="stoerer H">{e(aufmacher_r['dach'])}!</span></a>
<div><div class="dach">{neu_tag(aufmacher)}{e(aufmacher_r['titel'])}</div>
<h1 class="H"><a href="{e(aufmacher['link'])}" target="_blank" rel="noopener">{e(aufmacher['titel'])}</a></h1>
<p class="teaser">{e(kuerzen(aufmacher['teaser'], 320))}</p>{meta(aufmacher)}</div></section>""")

    teile.append(f'<div class="spruch"><small>Spruch des Tages</small>{e(spruch)}</div><div class="raster">')

    for r, liste in ausgabe:
        liste = [a for a in liste[:WEB_PRO_RESSORT] if a is not aufmacher]
        klasse = f"ressort {r['stil']}" + (" breit" if r["id"] in ("gs", "welt") else "")
        teile.append(f'<section class="{klasse}"><div class="rkopf"><b class="H">{e(r["dach"])}</b><span>{e(r["titel"])}</span></div>')
        if not liste:
            teile.append('<p class="leer">Heute nichts Neues – oder der Feed schläft noch.</p></section>')
            continue
        top, rest = liste[0], liste[1:]
        tb = f'<a class="tb" href="{e(top["link"])}" target="_blank" rel="noopener" style="background-image:url(\'{e(top["bild"])}\')"></a>' if top["bild"] else ""
        teile.append(f"""<div class="top">{tb}<div><div class="dach">{neu_tag(top)}{e(r['titel'])}</div>
<h2 class="H"><a href="{e(top['link'])}" target="_blank" rel="noopener">{e(top['titel'])}</a></h2>
<p class="teaser">{e(kuerzen(top['teaser'], 200))}</p>{meta(top)}</div></div><ul class="liste">""")
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
#  PDF-ZEITUNG (Druck-Layout, wird mit Chrome/Edge zu PDF)
# ════════════════════════════════════════════════════════════════════

DRUCK_CSS = """
@page{size:A4;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
html,body{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:"PT Serif",Georgia,"Times New Roman",serif;color:#111;background:#fff}
a{color:inherit;text-decoration:none}
.H{font-family:Anton,Impact,"Arial Narrow",sans-serif;font-weight:400;text-transform:uppercase;line-height:.98;letter-spacing:.1px}
.C{font-family:"Roboto Condensed","Arial Narrow",Arial,sans-serif}
.seite{width:210mm;height:297mm;padding:8mm 9mm 7mm;display:flex;flex-direction:column;overflow:hidden;
 page-break-after:always;break-after:page;position:relative}
.seite:last-child{page-break-after:auto;break-after:auto}
.dach{font-family:"Roboto Condensed",Arial,sans-serif;font-weight:900;color:#d0021b;text-transform:uppercase;font-size:8.5pt;letter-spacing:.3px}
.neu{background:#d0021b;color:#fff;padding:0 3px;margin-right:4px;font-size:7.5pt}
.meta{font-family:"Roboto Condensed",Arial,sans-serif;font-size:7pt;color:#666;margin-top:1.2mm}
.foto{background:#222 center/cover no-repeat;position:relative}
.foto.leer{background:repeating-linear-gradient(-45deg,var(--a) 0 7mm,var(--b) 7mm 14mm);display:flex;align-items:center;justify-content:center}
.foto.leer .wort{color:#fff;opacity:.9;font-size:26pt;transform:rotate(-6deg);text-shadow:1mm 1mm 0 rgba(0,0,0,.35)}

/* ── Titelseite ── */
.tkopf{display:flex;align-items:stretch;border-bottom:2.2mm solid #111;padding-bottom:2mm}
.tlogo{background:#d0021b;color:#fff;font-size:38pt;white-space:nowrap;padding:3mm 6mm 2mm;transform:skewX(-5deg);margin-left:2mm;letter-spacing:-.5pt}
.tinfo{flex:1;min-width:52mm;padding-left:3mm;display:flex;flex-direction:column;justify-content:center;align-items:flex-end;text-align:right;font-size:9pt;gap:.6mm}
.tinfo b{font-size:12pt}.tinfo .rot{color:#d0021b;font-weight:900;text-transform:uppercase}
.tticker{background:#111;color:#fff;font-weight:700;font-size:8.5pt;padding:1.6mm 3mm;white-space:nowrap;overflow:hidden;margin:2mm 0 3mm}
.tticker i{color:#ffd400;font-style:normal;margin:0 2mm}
.tauf h1{margin:1mm 0 2.5mm}
.tauf .foto{height:80mm;border-bottom:1.5mm solid #d0021b}
.stoerer{position:absolute;top:5mm;left:-2mm;background:#ffd400;color:#111;font-size:19pt;padding:1.5mm 4mm;
 transform:rotate(-5deg);box-shadow:1mm 1mm 0 #111}
.taufunten{display:flex;gap:5mm;margin-top:2.5mm}
.taufunten .tteaser{flex:1;font-size:11pt;line-height:1.38;font-weight:700}
.tdrei{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;border-top:1mm solid #111;padding-top:3mm;margin-top:3mm;flex:1;min-height:0;overflow:hidden}
.tdrei article .foto{height:30mm;margin:1mm 0 1.5mm}
.tdrei h3{font-size:14pt;margin:.5mm 0 1.2mm}
.tdrei p{font-size:8.6pt;line-height:1.35}
.tfuss{display:grid;grid-template-columns:1fr 1fr;gap:4mm;border-top:1mm solid #111;padding-top:2.5mm;margin-top:2mm}
.spruch{background:#ffd400;padding:2.5mm 3.5mm;border-left:3mm solid #111;font-family:"Roboto Condensed",Arial,sans-serif;font-weight:900;font-size:10.5pt}
.spruch small{display:block;font-size:7pt;letter-spacing:.6pt;text-transform:uppercase;margin-bottom:.8mm}
.index{font-family:"Roboto Condensed",Arial,sans-serif;font-size:9pt}
.index b{display:block;background:#111;color:#fff;padding:.6mm 2mm;margin-bottom:1mm;font-size:8pt;letter-spacing:.5pt}
.index div{display:flex;justify-content:space-between;border-bottom:.2mm dotted #999;padding:.4mm 1mm}
.index div i{font-style:normal;font-weight:900;color:#d0021b}

/* ── Innenseiten ── */
.ikopf{display:flex;justify-content:space-between;align-items:baseline;border-bottom:.8mm solid #111;padding-bottom:1mm;margin-bottom:3mm;font-size:8pt}
.ikopf .H{font-size:15pt;color:#d0021b}
.ikopf .nr{font-weight:900;font-size:10pt}
.block{display:flex;flex-direction:column;min-height:0;overflow:hidden}
.block.voll{flex:1}
.block.halb{flex:1}
.block.halb + .block.halb{border-top:1mm solid #111;padding-top:3mm;margin-top:3mm}
.bkopf{display:flex;align-items:baseline;gap:3mm;background:var(--k);color:#fff;padding:1.4mm 3mm;margin-bottom:2.5mm}
.bkopf b{font-size:20pt;line-height:1}
.bkopf span{font-family:"Roboto Condensed",Arial,sans-serif;font-weight:700;font-size:9pt;text-transform:uppercase;opacity:.9}
.gs .bkopf{background:linear-gradient(90deg,#a90432 0 55%,#fdb912 55%)}
.gs .bkopf span{margin-left:auto;background:#fff;color:#a90432;padding:.3mm 2mm;opacity:1}
.gs .dach{color:#a90432}
.btop{position:relative;margin-bottom:3mm}
.voll .btop .foto{height:104mm}
.voll .btop .ueber{position:absolute;left:0;right:12mm;bottom:0;background:#111;color:#fff;padding:2.5mm 3.5mm 2mm}
.voll .btop .ueber .dach{color:#ffd400}
.voll .btop h2{font-size:24pt}
.voll .btop .bteaser{font-size:10pt;line-height:1.4;font-weight:700;margin-top:2mm}
.halb .btop{display:grid;grid-template-columns:1.1fr 1fr;gap:4mm}
.halb .btop .foto{height:52mm}
.halb .btop h2{font-size:18pt;margin:.6mm 0 1.6mm}
.halb .btop .bteaser{font-size:9pt;line-height:1.38}
.spalten{flex:1;min-height:0;column-gap:5mm;column-rule:.25mm solid #bbb;column-fill:balance}
.voll .spalten{column-count:3}.halb .spalten{column-count:3}
.spalten article{break-inside:avoid;margin-bottom:3mm;padding-bottom:2.2mm;border-bottom:.25mm solid #ddd}
.spalten article .foto{height:24mm;margin:.8mm 0 1.2mm}
.spalten h4{font-size:11.5pt;margin:.4mm 0 1mm}
.spalten p{font-size:8.3pt;line-height:1.33}
.leerbox{font-family:"Roboto Condensed",Arial,sans-serif;color:#888;font-style:italic;font-size:10pt;padding:4mm 0}
.impressum{font-family:"Roboto Condensed",Arial,sans-serif;font-size:6.8pt;color:#777;border-top:.3mm solid #999;padding-top:1mm;margin-top:2mm}
"""

KOPF_FARBE = {"gs": "#a90432", "sport": "#d0021b", "digital": "#111", "welt": "#00305e",
              "forschung": "#0a7d5a", "technik": "#4b4b4b", "visionen": "#5a189a"}


def bild_einbetten(ausgabe):
    """Lädt Fotos herunter und bettet sie ins Druck-HTML ein (PDF wird dadurch eigenständig)."""
    offen = [a for _, l in ausgabe for a in l if a["bild"].startswith("http")]

    def hole(a):
        daten, typ, _ = laden(a["bild"], 4_000_000)
        typ = typ.split(";")[0].strip()
        if not typ.startswith("image/") or len(daten) >= 4_000_000:
            raise ValueError("kein Bild")
        return a, f"data:{typ};base64," + base64.b64encode(daten).decode()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        for fut in concurrent.futures.as_completed([pool.submit(hole, a) for a in offen]):
            try:
                a, uri = fut.result()
                a["bild_druck"] = uri
            except Exception:
                pass


def foto(a, r, klasse="foto", extra=""):
    src = a.get("bild_druck") or (a["bild"] if a["bild"].startswith("data:") else "")
    if src:
        return f'<div class="{klasse}" style="background-image:url(\'{src}\')">{extra}</div>'
    a_farbe, b_farbe = DEMO_FARBEN.get(r["stil"], ("#d0021b", "#b00016"))
    return (f'<div class="{klasse} leer" style="--a:{a_farbe};--b:{b_farbe}">{extra}'
            f'<span class="wort H">{e(r["dach"])}</span></div>')


def groesse(titel: str, basis: float) -> str:
    n = len(titel)
    faktor = 1.0 if n <= 45 else .85 if n <= 70 else .72 if n <= 100 else .62
    return f"font-size:{basis * faktor:.1f}pt"


def druck_bauen(ausgabe, demo=False) -> str:
    heute = dt.datetime.now()
    r_nach_id = {r["id"]: (r, l) for r, l in ausgabe}
    auf_r, auf = aufmacher_finden(ausgabe)
    benutzt = {id(auf)} if auf else set()
    spruch = SPRUECHE[heute.toordinal() % len(SPRUECHE)]
    nr = heute.timetuple().tm_yday
    alle = [a for _, l in ausgabe for a in l]
    ticker = "".join(f"<i>+++</i>{e(a['titel'])} " for a in
                     sorted(alle, key=lambda x: x["datum"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
                            reverse=True)[:6])

    s = [f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><title>{e(ZEITUNG_NAME)} – {e(datum_heute())}</title>
{FONTS}<style>{DRUCK_CSS}</style></head><body>"""]

    # ── Titelseite ──
    s.append(f"""<div class="seite"><header class="tkopf"><div class="tlogo H">{e(ZEITUNG_NAME)}</div>
<div class="tinfo C"><b>{e(datum_heute())}</b><span>Nr. {nr} · {heute.year} · {"DEMO-AUSGABE" if demo else "Persönliche Ausgabe"}</span>
<span class="rot">{e(UNTERTITEL)}</span></div></header>
<div class="tticker C">{ticker}</div>""")
    if auf:
        s.append(f"""<section class="tauf"><div class="dach">{neu_tag(auf)}{e(auf_r['titel'])}</div>
<h1 class="H" style="{groesse(auf['titel'], 40)}"><a href="{e(auf['link'])}">{e(auf['titel'])}</a></h1>
{foto(auf, auf_r, extra=f'<span class="stoerer H">{e(auf_r["dach"])}!</span>')}
<div class="taufunten"><p class="tteaser C">{e(kuerzen(auf['teaser'], 330))}</p></div>{meta(auf)}</section>""")

    # drei weitere Top-Meldungen aus verschiedenen Rubriken, bevorzugt mit Foto
    kandidaten = []
    for r, l in ausgabe:
        if auf_r and r["id"] == auf_r["id"]:
            continue
        beste = [a for a in l if a is not auf]
        if beste:
            a = max(beste[:3], key=lambda x: x["punkte"] + (3 if x["bild"] else 0))
            kandidaten.append((r, a))
    kandidaten.sort(key=lambda x: x[1]["punkte"] + (3 if x[1]["bild"] else 0), reverse=True)
    drei = kandidaten[:3]
    s.append('<section class="tdrei">')
    for r, a in drei:
        benutzt.add(id(a))
        s.append(f"""<article><div class="dach">{neu_tag(a)}{e(r['titel'])}</div>{foto(a, r)}
<h3 class="H" style="{groesse(a['titel'], 15)}"><a href="{e(a['link'])}">{e(a['titel'])}</a></h3>
<p>{e(kuerzen(a['teaser'], 170))}</p>{meta(a)}</article>""")
    s.append("</section>")
    index = "".join(f'<div><span>{e(" & ".join(r_nach_id[i][0]["titel"] for i in seite if i in r_nach_id))}</span><i>{n}</i></div>'
                    for n, seite in enumerate(PDF_SEITEN, start=2))
    s.append(f"""<footer class="tfuss"><div class="spruch"><small>Spruch des Tages</small>{e(spruch)}</div>
<div class="index"><b>HEUTE IN IHRER ZEITUNG</b>{index}</div></footer></div>""")

    # ── Rubrikseiten ──
    for seitennr, ids in enumerate(PDF_SEITEN, start=2):
        art = "voll" if len(ids) == 1 else "halb"
        s.append(f"""<div class="seite"><header class="ikopf C"><span class="H">{e(ZEITUNG_NAME)}</span>
<span>{e(datum_heute())}</span><span class="nr">SEITE {seitennr}</span></header>""")
        for rid in ids:
            if rid not in r_nach_id:
                continue
            r, liste = r_nach_id[rid]
            liste = [a for a in liste if id(a) not in benutzt] or liste
            farbe = KOPF_FARBE.get(r["stil"], "#d0021b")
            s.append(f'<section class="block {art} {r["stil"]}" style="--k:{farbe}">'
                     f'<div class="bkopf"><b class="H">{e(r["dach"])}</b><span>{e(r["titel"])}</span></div>')
            if not liste:
                s.append('<p class="leerbox">Heute keine Meldungen in dieser Rubrik.</p></section>')
                continue
            top = max(liste[:3], key=lambda a: a["punkte"] + (4 if a["bild"] else 0))
            rest = [a for a in liste if a is not top][: (7 if art == "voll" else 3)]
            if art == "voll":
                s.append(f"""<article class="btop">{foto(top, r, extra=f'''<div class="ueber"><div class="dach">{neu_tag(top)}{e(r["titel"])}</div>
<h2 class="H" style="{groesse(top['titel'], 24)}"><a href="{e(top['link'])}">{e(top['titel'])}</a></h2></div>''')}
<p class="bteaser C">{e(kuerzen(top['teaser'], 300))}</p>{meta(top)}</article>""")
            else:
                s.append(f"""<article class="btop">{foto(top, r)}<div><div class="dach">{neu_tag(top)}{e(r["titel"])}</div>
<h2 class="H" style="{groesse(top['titel'], 18)}"><a href="{e(top['link'])}">{e(top['titel'])}</a></h2>
<p class="bteaser">{e(kuerzen(top['teaser'], 260))}</p>{meta(top)}</div></article>""")
            s.append('<div class="spalten">')
            for i, a in enumerate(rest):
                bild = foto(a, r) if (a.get("bild_druck") or a["bild"].startswith("data:")) and (art == "voll" or i == 0) else ""
                s.append(f"""<article><div class="dach">{neu_tag(a)}{e(a.get('quelle') or r['titel'])}</div>{bild}
<h4 class="H" style="{groesse(a['titel'], 12)}"><a href="{e(a['link'])}">{e(a['titel'])}</a></h4>
<p>{e(kuerzen(a['teaser'], 210 if art == 'voll' else 150))}</p>{meta(a)}</article>""")
            s.append("</div></section>")
        if seitennr == len(PDF_SEITEN) + 1:
            s.append(f'<div class="impressum">{e(ZEITUNG_NAME)} wird automatisch aus RSS-Feeds erstellt '
                     f'({heute.strftime("%d.%m.%Y, %H:%M Uhr")}). Texte und Fotos gehören den jeweiligen Quellen; '
                     f'Schlagzeilen sind anklickbar und führen zum Originalartikel. Nur für den privaten Gebrauch.</div>')
        s.append("</div>")
    s.append("</body></html>")
    return "\n".join(s)


def browser_finden():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome",
              "msedge", "microsoft-edge"):
        p = shutil.which(n)
        if p:
            return p
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"):
        if Path(p).exists():
            return p
    return None


def pdf_drucken(html_datei: Path, pdf_datei: Path) -> bool:
    browser = browser_finden()
    if not browser:
        print("⚠ Kein Chrome/Chromium/Edge gefunden – PDF übersprungen (Pfad über Umgebungsvariable CHROME setzbar).")
        return False
    with tempfile.TemporaryDirectory() as profil:
        cmd = [browser, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
               "--no-pdf-header-footer", "--print-to-pdf-no-header", "--run-all-compositor-stages-before-draw",
               "--virtual-time-budget=15000", f"--user-data-dir={profil}",
               f"--print-to-pdf={pdf_datei}", html_datei.resolve().as_uri()]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as ex:
            print(f"⚠ PDF fehlgeschlagen: {ex}")
            return False
    return pdf_datei.exists() and pdf_datei.stat().st_size > 1000


# ════════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description=f"{ZEITUNG_NAME} – persönliche Tageszeitung aus RSS")
    ap.add_argument("--ausgabe", default=str(BASIS / "ausgaben"), help="Ordner für die Ausgabe")
    ap.add_argument("--pdf", action="store_true", help="zusätzlich PDF-Zeitung erzeugen")
    ap.add_argument("--oeffnen", action="store_true", help="danach öffnen (PDF, sonst Webseite)")
    ap.add_argument("--demo", action="store_true", help="Platzhalter statt echter Feeds")
    args = ap.parse_args()

    if args.demo:
        ausgabe, fehler = demo_sammeln()
    else:
        ausgabe, fehler = zeitung_sammeln()
        anreichern(ausgabe)

    ordner = Path(args.ausgabe)
    ordner.mkdir(parents=True, exist_ok=True)
    tag = dt.date.today().isoformat()

    pdf_ok = False
    if args.pdf:
        if not args.demo:
            bild_einbetten(ausgabe)
        druck = ordner / f"druck_{tag}.html"
        druck.write_text(druck_bauen(ausgabe, demo=args.demo), "utf-8")
        pdf_tag = ordner / f"zeitung_{tag}.pdf"
        pdf_ok = pdf_drucken(druck, pdf_tag)
        druck.unlink(missing_ok=True) if pdf_ok else None
        if pdf_ok:
            shutil.copyfile(pdf_tag, ordner / "zeitung.pdf")   # immer die neueste
            print(f"✔ PDF-Zeitung -> {pdf_tag}")

    seite = html_bauen(ausgabe, fehler, demo=args.demo, pdf_name="zeitung.pdf" if pdf_ok else "")
    datei = ordner / f"zeitung_{tag}.html"
    datei.write_text(seite, "utf-8")
    (ordner / "index.html").write_text(seite, "utf-8")   # immer die neueste Ausgabe

    print(f"✔ {sum(len(l) for _, l in ausgabe)} Meldungen -> {datei}")
    for r, liste in ausgabe:   # kurze Inhaltsübersicht
        fotos = sum(1 for a in liste if a["bild"])
        print(f"\n■ {r['titel']} ({len(liste)} Meldungen, {fotos} mit Foto)")
        for a in liste[:3]:
            print(f"   {'NEU ' if a.get('neu') else ''}{a['titel']}  [{a.get('quelle', '')}]")
    if fehler:
        print(f"⚠ {len(fehler)} Feed(s) nicht erreichbar:", *fehler, sep="\n   ")
    if args.oeffnen:
        webbrowser.open((ordner / "zeitung.pdf" if pdf_ok else datei).resolve().as_uri())


if __name__ == "__main__":
    sys.exit(main())
