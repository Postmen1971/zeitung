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
import time
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
WEB_PRO_RESSORT = 7          # ... davon auf der Webseite gezeigt
MAX_ALTER_STUNDEN = 36       # ältere Meldungen fliegen raus
TIMEOUT_SEKUNDEN = 15
FOTOS_SUCHEN = True          # fehlende Fotos von der Artikelseite holen (og:image)
BASIS = Path(__file__).resolve().parent
STATUS_DATEI = BASIS / "gelesen.json"   # merkt sich, was schon da war (für "NEU")

# Lieblings-Stichwörter: erhöhen die Wichtigkeit (Wert = Bonuspunkte)
FAVORITEN = {
    "galatasaray": 6, "cimbom": 6, "derby": 3, "fenerbahçe": 2, "champions league": 3,
    "bayern": 2, "real madrid": 2, "barcelona": 2, "nationalmannschaft": 2, "milli takım": 3,
    "durchbruch": 4, "weltrekord": 3, "weltmeister": 3, "k.o.": 3, "titel": 2,
    "gentherapie": 4, "crispr": 4, "heilung": 3, "zulassung": 2,
    "claude code": 5, "tutorial": 2, "anleitung": 2, "automatisier": 3,
    "claude": 5, "anthropic": 4, "künstliche intelligenz": 2, "ki-modell": 2,
    "tuya": 6, "smart life": 5, "home assistant": 4, "matter": 2, "zigbee": 2,
    "balkonkraftwerk": 4, "angebot": 2, "deal": 2, "rabatt": 2, "tiefstpreis": 3, "bestpreis": 3,
    "beamer": 4, "projektor": 3, "oled": 2, "fernseher": 2, "4k": 1,
    "roboter": 2, "erfindung": 3, "fusion": 2, "raumfahrt": 2, "quanten": 2,
}

# Meldungen mit diesen Wörtern werden ausgeblendet
SPERRLISTE = ["horoskop", "gewinnspiel", "anzeige", "sponsored", "rabattcode", "live hören", "quoten", "tipp, prognose", "wettbasis"]


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


CLUBS = ["real madrid", "barcelona", "barça", "atlético", "atletico", "manchester city", "man city",
         "manchester united", "liverpool", "arsenal", "chelsea", "tottenham", "newcastle", "psg",
         "paris saint-germain", "inter ", "inter mailand", "ac milan", "juventus", "napoli", "bayern",
         "dortmund", "leverkusen", "benfica", "porto", "ajax", "champions league", "europa league",
         "premier league", "la liga", "serie a", "ligue 1"]

# Reihenfolge zählt: kommt eine Meldung in mehreren Rubriken vor, landet sie in der ersten.
RESSORTS = [
    # ── SPORT ──
    {"id": "gs", "dach": "CİMBOM", "titel": "Galatasaray", "stil": "gs",
     "stichwoerter": ["galatasaray", "cimbom", "cim bom"],
     "feeds": [F("https://www.fotomac.com.tr/rss/galatasaray.xml"),
               F("https://www.aspor.com.tr/rss/galatasaray.xml"),
               F("https://www.hurriyet.com.tr/rss/spor", True),
               F("https://www.haberturk.com/rss/spor.xml", True),
               F("https://www.sabah.com.tr/rss/spor.xml", True),
               F(gnews("Galatasaray"), True)]},
    {"id": "national", "dach": "LÄNDERSPIEL", "titel": "Nationalmannschaften", "stil": "sport",
     "stichwoerter": ["nationalmannschaft", "nationalelf", "nationalteam", "dfb-team", "dfb-elf", "länderspiel",
                      "milli takım", "a milli", "ay-yıldızlı", "nations league", "qualifikation", "national team",
                      "bundestrainer", "teknik direktör", "em 2028", "euro 2028"],
     "feeds": [F(gnews("DFB-Team Nationalmannschaft"), True), F(gnews("A Milli Takım", "tr"), True),
               F(gnews("Länderspiel Nationalmannschaft"), True),
               F("https://www.sportschau.de/fussball/index~rss2.xml", True)]},
    {"id": "bundesliga", "dach": "BUNDESLIGA", "titel": "Bundesliga", "stil": "sport",
     "stichwoerter": ["bundesliga", "bayern", "dortmund", "bvb", "leverkusen", "leipzig", "stuttgart", "vfb",
                      "frankfurt", "eintracht", "gladbach", "wolfsburg", "freiburg", "hoffenheim", "bremen",
                      "union berlin", "mainz", "augsburg", "heidenheim", "hamburger sv", "hsv", "köln", "st. pauli"],
     "feeds": [F("https://www.sportschau.de/fussball/index~rss2.xml", True),
               F("https://newsfeed.kicker.de/news/fussball", True),
               F(gnews("Fußball Bundesliga")), F(gnews("VfB Stuttgart"))]},
    {"id": "europa", "dach": "EUROPAS TOP-KLUBS", "titel": "Champions League & Top-Ligen", "stil": "sport",
     "stichwoerter": CLUBS,
     "feeds": [F("https://feeds.bbci.co.uk/sport/football/rss.xml", True),
               F(gnews("Champions League")), F(gnews("Real Madrid Barcelona")),
               F(gnews("Premier League", "en"), True), F(gnews("Serie A Inter Milan Juventus", "en"), True),
               F("https://newsfeed.kicker.de/news/fussball", True)]},
    {"id": "boxen", "dach": "BOXEN", "titel": "Boxen", "stil": "sport",
     "stichwoerter": ["box", "boxing", "kampf", "fight", "ko", "wbc", "wba", "ibf", "wbo"],
     "feeds": [F("https://www.boxingnews24.com/feed/"), F("https://www.badlefthook.com/rss/index.xml"),
               F(gnews("Boxen Kampf"))]},
    # ── NACHRICHTEN ──
    {"id": "welt", "dach": "NACHRICHTEN", "titel": "Die Welt heute", "stil": "welt",
     "stichwoerter": [],
     "feeds": [F("https://www.tagesschau.de/xml/rss2/"),
               F("https://rss.dw.com/rdf/rss-de-all")]},
    # ── DIGITAL ──
    {"id": "werkstatt", "dach": "WERKSTATT", "titel": "KI-Werkstatt", "stil": "werkstatt",
     "stichwoerter": ["claude", "anthropic", "tutorial", "anleitung", "guide", "how to", "how i", "workflow",
                      "automat", "prompt", "tipps", "tips", "mcp", "agent", "skill", "hook"],
     "feeds": [F("https://dev.to/feed/tag/claudecode"), F("https://dev.to/feed/tag/claude", True),
               F("https://www.reddit.com/r/ClaudeCode/top/.rss?t=day"),
               F("https://github.com/anthropics/claude-code/releases.atom"),
               F(gnews("Claude Code Anleitung")), F(gnews("Claude Code tutorial", "en"), True),
               F(gnews("KI Automatisierung Anleitung")), F(gnews("Claude Code Tipps"))]},
    {"id": "claude", "dach": "CLAUDE", "titel": "Ideen & Neues für Claude", "stil": "claude",
     "stichwoerter": ["claude", "anthropic"],
     "feeds": [F(gnews("Claude Anthropic")), F(gnews("Claude AI Anthropic", "en"), True),
               F(gnews("Claude Code tips", "en"), True),
               F("https://the-decoder.de/feed/", True), F("https://simonwillison.net/atom/everything/", True)]},
    {"id": "ki", "dach": "KI", "titel": "Neues von der KI", "stil": "digital",
     "stichwoerter": [" ki", "ki-", "künstliche intelligenz", " ai ", "ai-", "chatgpt", "openai",
                      "gemini", "llm", "sprachmodell", "machine learning", "nvidia"],
     "feeds": [F("https://the-decoder.de/feed/"), F("https://t3n.de/tag/kuenstliche-intelligenz/rss.xml"),
               F("https://www.heise.de/rss/heise-atom.xml", True), F(gnews("Künstliche Intelligenz"))]},
    {"id": "smarthome", "dach": "SMART HOME", "titel": "Smart Home & Tuya", "stil": "smarthome",
     "stichwoerter": ["smart home", "smarthome", "smart-home", "tuya", "smart life", "home assistant",
                      "zigbee", "homekit", "philips hue", "matter-", "saugroboter", "smarte steckdose",
                      "heizkörperthermostat", "smart-thermostat", "video-türklingel"],
     "feeds": [F(gnews("Tuya")), F(gnews("Tuya smart", "en")), F(gnews("Smart Home Neuheiten")), F(gnews("Smart Life App")),
               F(gnews("Home Assistant")), F("https://www.home-assistant.io/atom.xml"),
               F("https://stadt-bremerhaven.de/feed/", True), F("https://www.smartdroid.de/feed/", True)]},
    {"id": "balkon", "dach": "SOLAR", "titel": "Balkonkraftwerk-Angebote", "stil": "balkon",
     "stichwoerter": ["balkonkraftwerk", "balkon-kraftwerk", "steckersolar", "stecker-solar", "mini-pv",
                      "mini-solar", "solarmodul", "solaranlage für den balkon", "balkonsolar", "pv-speicher",
                      "anker solix", "ecoflow", "zendure", "growatt", "hoymiles", "deye", "wechselrichter"],
     "feeds": [F(gnews("Balkonkraftwerk Angebot")), F(gnews("Balkonkraftwerk Deal Preis")),
               F(gnews("Balkonkraftwerk mit Speicher Angebot")), F(gnews("Balkonkraftwerk Test")),
               F("https://www.mydealz.de/rss/gruppe/balkonkraftwerk", True),
               F("https://www.mydealz.de/rss/hot", True)]},
    {"id": "tv", "dach": "BEAMER & TV", "titel": "Beamer, Fernseher & Heimkino", "stil": "tv",
     "stichwoerter": ["beamer", "projektor", "projector", "fernseher", " tv", "tv-", "oled", "qled", "mini-led",
                      "micro-led", "heimkino", "soundbar", "fire tv", "google tv", "streaming-stick", "hdmi",
                      "dolby vision", "television"],
     "feeds": [F(gnews("Beamer")), F(gnews("Fernseher OLED neu")), F(gnews("Heimkino Projektor")),
               F(gnews("4K projector", "en"), True), F("https://www.areadvd.de/feed/", True),
               F("https://stadt-bremerhaven.de/feed/", True)]},
    # ── WISSEN & ZUKUNFT ──
    {"id": "forschung", "dach": "MEDIZIN", "titel": "Forschung & Gentherapie", "stil": "forschung",
     "stichwoerter": [],
     "feeds": [F(gnews("Gentherapie")), F(gnews("CRISPR")),
               F("https://medicalxpress.com/rss-feed/genetics-news/"),
               F("https://www.spektrum.de/alias/rss/spektrum-de-rss-feed/996406"),
               F("https://www.scinexx.de/feed/"),
               F("https://www.deutschlandfunk.de/forschung-aktuell-100.rss")]},
    {"id": "technik", "dach": "TECHNIK", "titel": "Technik & Erfindungen", "stil": "technik",
     "stichwoerter": [],
     "feeds": [F("https://rss.golem.de/rss.php?feed=RSS2.0"), F("https://t3n.de/rss.xml"),
               F("https://newatlas.com/index.rss"), F("https://www.ingenieur.de/feed/"),
               F(gnews("Erfindung"))]},
    {"id": "visionen", "dach": "ZUKUNFT", "titel": "Visionen – morgen ist heute", "stil": "visionen",
     "stichwoerter": ["zukunft", "raumfahrt", "weltraum", "mars", "mond", "rakete", "fusion", "roboter",
                      "quanten", "vision", "durchbruch", "2030", "2040", "2050", "energie"],
     "feeds": [F("https://www.trendsderzukunft.de/feed/"), F("https://www.raumfahrer.net/feed/"),
               F("https://www.futurezone.de/feed/", True),
               F(gnews("Zukunftstechnologie")), F(gnews("Kernfusion"))]},
]

# Schöne Quellennamen (nach Internetadresse des Feeds)
QUELLEN = {"fotomac": "Fotomaç", "aspor": "A Spor", "hurriyet": "Hürriyet", "haberturk": "Habertürk",
           "sabah": "Sabah", "sportschau": "Sportschau", "kicker": "kicker", "boxingnews24": "Boxing News 24",
           "badlefthook": "Bad Left Hook", "the-decoder": "The Decoder", "t3n": "t3n", "heise": "heise online",
           "tagesschau": "tagesschau", "dw.com": "Deutsche Welle", "medicalxpress": "Medical Xpress",
           "spektrum": "Spektrum", "scinexx": "scinexx", "deutschlandfunk": "Deutschlandfunk",
           "golem": "Golem", "newatlas": "New Atlas", "ingenieur.de": "ingenieur.de",
           "trendsderzukunft": "Trends der Zukunft", "raumfahrer": "Raumfahrer.net", "futurezone": "Futurezone",
           "bbci": "BBC Sport", "simonwillison": "Simon Willison", "reddit.com/r/ClaudeAI": "r/ClaudeAI",
           "home-assistant.io": "Home Assistant", "stadt-bremerhaven": "Caschys Blog", "smartdroid": "smartdroid",
           "areadvd": "AREA DVD", "flatpanelshd": "FlatpanelsHD", "dev.to": "DEV Community",
           "reddit.com/r/ClaudeCode": "r/ClaudeCode", "mydealz": "mydealz", "anthropics/claude-code": "Claude Code (GitHub)"}

# Reihenfolge der Rubriken auf der Webseite
WEB_REIHENFOLGE = ["werkstatt", "claude", "ki", "gs", "bundesliga", "europa", "national", "boxen", "welt",
                   "smarthome", "balkon", "tv", "forschung", "technik", "visionen"]

# Aufbau der PDF-Zeitung: Seite 1 = Titelseite, danach je Seite eine oder zwei Rubriken
PDF_SEITEN = [["werkstatt"], ["gs"], ["bundesliga"], ["europa", "national", "boxen"], ["welt"], ["claude", "ki"],
              ["smarthome", "balkon", "tv"], ["forschung", "technik", "visionen"]]

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
    url = urllib.parse.quote(url, safe=":/?&=%#+,;@~!$'()*[]")   # Umlaute in Adressen
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
        else:
            quelle = next((n for k, n in QUELLEN.items() if k in feed_url), "") or \
                re.split(r"\s+[-–|:]\s+", quelle.strip(" -–|"))[0]
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
    titel = re.sub(r"^\s*-?\d+°\s*-\s*", "", titel)          # mydealz-Temperatur ("189° - ") ignorieren
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


def google_link_aufloesen(link: str) -> str:
    """Google-News-Weiterleitung -> echte Artikel-Adresse (sonst leerer String)."""
    m = re.search(r"/articles/([^/?#]+)", link)
    if not m:
        return ""
    art_id = m.group(1)
    seite = laden(f"https://news.google.com/rss/articles/{art_id}")[0].decode("utf-8", "replace")
    sg = re.search(r'data-n-a-sg="([^"]+)"', seite)
    ts = re.search(r'data-n-a-ts="([^"]+)"', seite)
    if not (sg and ts):
        return ""
    anfrage = ["Fbv4je", '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,'
               'null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"%s",%s,"%s"]' % (art_id, ts.group(1), sg.group(1))]
    daten = ("f.req=" + urllib.parse.quote(json.dumps([[anfrage]]))).encode()
    req = urllib.request.Request("https://news.google.com/_/DotsSplashUi/data/batchexecute", data=daten,
                                 headers={"User-Agent": UA,
                                          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEKUNDEN) as r:
        antwort = r.read().decode("utf-8", "replace")
    teil = json.loads(antwort.split("\n\n", 1)[1])[:-2]
    url = json.loads(teil[0][2])[1]
    return url if isinstance(url, str) and url.startswith("http") else ""


def anreichern(ausgabe):
    """Holt für Meldungen ohne Foto/Text das Vorschaubild (og:image) und die Kurzbeschreibung."""
    if not FOTOS_SUCHEN:
        return
    offen = [a for _, liste in ausgabe for a in liste
             if (not a["bild"] or not a["teaser"]) and a["link"].startswith("http")]
    # 1) Google-News-Weiterleitungen nacheinander auflösen (Google bremst parallele Anfragen)
    google = [a for a in offen if "news.google.com" in a["link"]]
    ok, leer, erster_fehler = 0, 0, ""
    for i, a in enumerate(google):
        for versuch in (1, 2):
            try:
                echt = google_link_aufloesen(a["link"])
                if echt:
                    a["link"] = echt      # Schlagzeile führt jetzt direkt zum Artikel
                    ok += 1
                else:
                    leer += 1
                break
            except Exception as ex:
                erster_fehler = erster_fehler or f"{type(ex).__name__}: {ex}"[:160]
                time.sleep(4 * versuch)
        time.sleep(0.8)
    if google:
        print(f"  Google-News-Links aufgelöst: {ok}/{len(google)}, ohne Ergebnis: {leer}" + (f" (erster Fehler: {erster_fehler})" if erster_fehler else ""))

    # 2) Artikelseiten parallel nach Foto & Anreißer fragen
    def hole(a):
        if "news.google.com" in a["link"]:
            return a, "", ""
        daten, _, ziel = laden(a["link"], 400_000)
        if "news.google.com" in urllib.parse.urlparse(ziel).netloc:
            return a, "", ""          # Google-News-Weiterleitung ohne echte Artikelseite
        seite = daten.decode("utf-8", errors="replace")
        bild = meta_wert(seite, "og:image", "og:image:url", "twitter:image")
        text = meta_wert(seite, "og:description", "description", "twitter:description")
        return a, urllib.parse.urljoin(ziel, bild) if bild else "", saeubern(text)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
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

DEMO_FARBEN = {"werkstatt": ("#8b5cf6", "#ec4899"), "balkon": ("#eab308", "#f97316"), "gs": ("#a90432", "#fdb912"), "claude": ("#c15f3c", "#f0a37f"),
               "smarthome": ("#0b6e99", "#4fd1c5"), "tv": ("#1a1a2e", "#e94560"), "sport": ("#d0021b", "#5a0010"), "digital": ("#111", "#555"),
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
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700'
         '&family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono&display=swap" rel="stylesheet">')


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
#  KI-WERKSTATT (Inhalte aus werkstatt.py)
# ════════════════════════════════════════════════════════════════════

try:
    import werkstatt
except ImportError:          # Zeitung läuft auch ohne Werkstatt-Datei
    werkstatt = None


def werkstatt_heute():
    if not werkstatt:
        return None, None, None
    return werkstatt.heute(dt.date.today().toordinal())


def rel_zeit(d) -> str:
    if not d:
        return ""
    minuten = int((dt.datetime.now(dt.timezone.utc) - d).total_seconds() // 60)
    if minuten < 60:
        return f"vor {max(minuten, 1)} Min."
    if minuten < 24 * 60:
        return f"vor {minuten // 60} Std."
    return d.astimezone().strftime("%d.%m., %H:%M")


# ════════════════════════════════════════════════════════════════════
#  WEBSEITE – moderner Look (hell/dunkel automatisch)
# ════════════════════════════════════════════════════════════════════

CSS = """
:root{--bg:#f4f5f8;--fl:#ffffff;--fl2:#eef0f5;--tx:#0f172a;--tx2:#475569;--tx3:#94a3b8;--rand:rgba(15,23,42,.08);
 --schatten:0 1px 2px rgba(15,23,42,.06),0 8px 24px rgba(15,23,42,.06);--akzent:#8b5cf6;--r:18px}
@media(prefers-color-scheme:dark){:root{--bg:#0b0d12;--fl:#151821;--fl2:#1c2030;--tx:#f1f5f9;--tx2:#a5b0c2;--tx3:#64748b;
 --rand:rgba(255,255,255,.07);--schatten:0 1px 2px rgba(0,0,0,.4),0 10px 30px rgba(0,0,0,.25)}}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth;scroll-padding-top:120px}
body{background:var(--bg);color:var(--tx);font:15px/1.5 Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.wrap{max-width:1200px;margin:0 auto;padding:0 20px}
h1,h2,h3,.brand{font-family:"Space Grotesk",Inter,system-ui,sans-serif;letter-spacing:-.02em}
/* Kopf */
.top{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 82%,transparent);backdrop-filter:blur(14px);
 -webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--rand)}
.topin{display:flex;align-items:center;gap:16px;height:60px}
.brand{font-size:22px;font-weight:700;display:flex;gap:2px;align-items:baseline}
.brand .b2{font-weight:400;background:linear-gradient(90deg,#8b5cf6,#ec4899,#f59e0b);-webkit-background-clip:text;background-clip:text;color:transparent}
.topmeta{color:var(--tx2);font-size:13px;display:flex;gap:8px;align-items:center;flex:1}
.topmeta .dot{width:4px;height:4px;border-radius:50%;background:var(--tx3)}
.btn{background:var(--tx);color:var(--bg);font-weight:600;font-size:13px;padding:8px 14px;border-radius:999px;white-space:nowrap}
.btn:hover{opacity:.85}
.chips{display:flex;gap:8px;overflow-x:auto;padding-top:2px;padding-bottom:12px;scrollbar-width:none}
.chips::-webkit-scrollbar{display:none}
.chips a{flex:0 0 auto;font-size:13px;font-weight:500;padding:6px 12px;border-radius:999px;background:var(--fl);border:1px solid var(--rand);color:var(--tx2)}
.chips a:hover{color:var(--tx);border-color:var(--c,var(--akzent))}
main{padding:24px 0 40px}
/* Aufmacher */
.hero{display:grid;grid-template-columns:1.65fr 1fr;gap:20px;margin-bottom:36px}
.herocard{position:relative;min-height:440px;border-radius:24px;overflow:hidden;background:#1e293b center/cover;display:flex;align-items:flex-end;box-shadow:var(--schatten)}
.herocard::before{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 30%,rgba(0,0,0,.82) 100%)}
.herotext{position:relative;padding:28px;color:#fff}
.herotext h1{font-size:clamp(26px,3.4vw,40px);line-height:1.1;margin:12px 0 10px}
.herotext p{color:rgba(255,255,255,.85);max-width:680px;font-size:15px}
.herotext .zeit{color:rgba(255,255,255,.7);font-size:12.5px;margin-top:10px}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;padding:4px 10px;border-radius:999px;background:var(--c,var(--akzent));color:#fff}
.neu{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.04em;padding:2px 7px;border-radius:999px;background:color-mix(in srgb,var(--c,var(--akzent)) 15%,transparent);color:var(--c,var(--akzent))}
.toplist{background:var(--fl);border-radius:24px;padding:18px;box-shadow:var(--schatten);border:1px solid var(--rand);display:flex;flex-direction:column;gap:4px}
.toplist h2{font-size:15px;color:var(--tx2);font-weight:600;margin:2px 4px 8px}
.mini{display:flex;gap:12px;padding:8px;border-radius:14px;align-items:center}
.mini:hover{background:var(--fl2)}
.mini .th{flex:0 0 76px;height:58px;border-radius:12px;background:var(--fl2) center/cover}
.mini b{display:block;font-size:14px;line-height:1.3;font-weight:600}
.mini .kat{font-size:11.5px;font-weight:600;color:var(--c)}
/* Werkstatt */
.werkstatt{margin-bottom:40px}
.eyebrow{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--c,var(--akzent))}
.whead{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:14px}
.whead h2{font-size:28px;line-height:1.15;margin-top:4px}
.wgrid{display:grid;grid-template-columns:1.5fr 1fr;gap:20px}
.wcard{background:var(--fl);border-radius:var(--r);padding:22px;border:1px solid var(--rand);box-shadow:var(--schatten);position:relative}
.wcard.haupt{border:1px solid transparent;background:linear-gradient(var(--fl),var(--fl)) padding-box,linear-gradient(135deg,#8b5cf6,#ec4899,#f59e0b) border-box}
.wcard h3{font-size:21px;line-height:1.25;margin:10px 0 8px}
.wcard p{color:var(--tx2)}
.badges{display:flex;flex-wrap:wrap;gap:6px}
.badge{font-size:12px;font-weight:600;padding:3px 9px;border-radius:999px;background:var(--fl2);color:var(--tx2)}
.badge.lv{background:color-mix(in srgb,#8b5cf6 16%,transparent);color:#8b5cf6}
ol.schritte{list-style:none;counter-reset:s;margin:16px 0;display:flex;flex-direction:column;gap:10px}
ol.schritte li{counter-increment:s;display:flex;gap:12px;font-size:14.5px}
ol.schritte li::before{content:counter(s);flex:0 0 26px;height:26px;border-radius:50%;background:linear-gradient(135deg,#8b5cf6,#ec4899);
 color:#fff;font-weight:700;font-size:13px;display:flex;align-items:center;justify-content:center}
.prompt{background:#0f172a;color:#e2e8f0;border-radius:14px;overflow:hidden;margin-top:6px}
.prompt .ph{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;font-size:12px;color:#94a3b8;border-bottom:1px solid rgba(255,255,255,.08)}
.prompt pre{white-space:pre-wrap;font:13px/1.55 "JetBrains Mono",ui-monospace,Consolas,monospace;padding:12px 14px}
.kopieren{font:600 12px Inter,sans-serif;border:0;border-radius:8px;padding:5px 10px;background:#8b5cf6;color:#fff;cursor:pointer}
.kopieren.ok{background:#16a34a}
.doku{display:inline-block;margin-top:14px;font-weight:600;font-size:13.5px;color:#8b5cf6}
.wside{display:flex;flex-direction:column;gap:20px}
.wcard.tipp{background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff;border:0}
.wcard.tipp p,.wcard.tipp .eyebrow{color:rgba(255,255,255,.92)}
.werkzeug{font-size:12.5px;color:var(--tx3);margin:8px 0 10px}
/* Rubriken */
.sec{margin-bottom:40px}
.shead{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.sicon{width:36px;height:36px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:19px;
 background:color-mix(in srgb,var(--c) 16%,transparent)}
.shead h2{font-size:22px}
.shead .anz{margin-left:auto;font-size:12.5px;color:var(--tx3)}
.shead .linie{flex:1;height:1px;background:var(--rand)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px}
.card{background:var(--fl);border-radius:var(--r);overflow:hidden;border:1px solid var(--rand);box-shadow:var(--schatten);display:flex;flex-direction:column;
 transition:transform .15s ease,box-shadow .15s ease}
.card:hover{transform:translateY(-3px);box-shadow:0 14px 34px rgba(15,23,42,.14)}
.card .img{aspect-ratio:16/9;background:var(--fl2) center/cover}
.card .cb{padding:14px 16px 16px;display:flex;flex-direction:column;gap:6px;flex:1}
.card .ct{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:12px;color:var(--c);font-weight:600}
.card h3{font-size:16.5px;line-height:1.3}
.card p{font-size:13.5px;color:var(--tx2);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card .zeit{margin-top:auto;font-size:12px;color:var(--tx3)}
.card.gross{grid-column:span 2;flex-direction:row}
.card.gross .img{flex:0 0 55%;aspect-ratio:auto;min-height:250px}
.card.gross h3{font-size:22px}
.card.gross p{-webkit-line-clamp:5}
.spruch{margin:0 0 40px;padding:18px 22px;border-radius:var(--r);background:var(--fl);border:1px solid var(--rand);font-size:16px;font-weight:500}
.spruch small{display:block;font-size:11.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--tx3);margin-bottom:4px}
.leer{color:var(--tx3);font-size:14px}
footer{color:var(--tx3);font-size:12.5px;padding:28px 0 40px;border-top:1px solid var(--rand)}
footer details{margin-top:6px}
@media(max-width:600px){.topmeta{display:none}.brand{flex:1;font-size:20px}.topin{height:56px}}
@media(max-width:860px){.hero,.wgrid{grid-template-columns:1fr}.herocard{min-height:360px}.card.gross{grid-column:auto;flex-direction:column}
 .card.gross .img{aspect-ratio:16/9;min-height:0}.topmeta span:not(:first-child){display:none}.whead h2{font-size:23px}}
"""

JS = """
document.querySelectorAll('.kopieren').forEach(b=>b.addEventListener('click',async()=>{
 const t=b.closest('.prompt').querySelector('pre').innerText;
 try{await navigator.clipboard.writeText(t);b.textContent='Kopiert ✓';b.classList.add('ok');}
 catch(e){const r=document.createRange();r.selectNodeContents(b.closest('.prompt').querySelector('pre'));
  const s=getSelection();s.removeAllRanges();s.addRange(r);b.textContent='Markiert – jetzt kopieren';}
 setTimeout(()=>{b.textContent='Kopieren';b.classList.remove('ok')},2500);}));
"""


def farbe(r) -> str:
    return AKZENT.get(r["id"], "#8b5cf6")


def prompt_box(text: str, titel: str = "Prompt für Claude Code") -> str:
    return (f'<div class="prompt"><div class="ph"><span>{e(titel)}</span>'
            f'<button class="kopieren" type="button">Kopieren</button></div><pre>{e(text)}</pre></div>')


def karte(a, r, gross=False) -> str:
    bild = f'<div class="img" style="background-image:url(\'{e(a["bild"])}\')"></div>' if a["bild"] else ""
    neu = '<span class="neu">NEU</span>' if a.get("neu") else ""
    return (f'<a class="card{" gross" if gross and a["bild"] else ""}" href="{e(a["link"])}" target="_blank" rel="noopener">{bild}'
            f'<div class="cb"><div class="ct"><span>{e(a.get("quelle") or r["titel"])}</span>{neu}</div>'
            f'<h3>{e(a["titel"])}</h3><p>{e(kuerzen(a["teaser"], 260 if gross else 170))}</p>'
            f'<div class="zeit">{e(rel_zeit(a.get("datum")))}</div></div></a>')


def werkstatt_html(r_werk, news) -> str:
    ws, auto, tipp = werkstatt_heute()
    if not ws:
        return ""
    schritte = "".join(f"<li><span>{e(s)}</span></li>" for s in ws["schritte"])
    teile = [f"""<section class="werkstatt" id="r-werkstatt" style="--c:#8b5cf6">
<div class="whead"><div><span class="eyebrow">🛠️ KI-Werkstatt · Workshop des Tages</span><h2>{e(ws['titel'])}</h2></div></div>
<div class="wgrid"><article class="wcard haupt">
<div class="badges"><span class="badge lv">{e(ws['level'])}</span><span class="badge">⏱ {e(ws['dauer'])}</span><span class="badge">✳️ {e(ws['feature'])}</span></div>
<h3>Das baust du heute</h3><p>{e(ws['ziel'])}</p>
<ol class="schritte">{schritte}</ol>
{prompt_box(ws['prompt'])}
<a class="doku" href="{e(ws['link'])}" target="_blank" rel="noopener">Mehr dazu in der Anleitung →</a></article>
<div class="wside"><article class="wcard" style="--c:#0891b2"><span class="eyebrow">⚡ Automatisierung des Tages</span>
<h3>{e(auto['titel'])}</h3><p>{e(auto['idee'])}</p><div class="werkzeug">Werkzeuge: {e(auto['werkzeuge'])}</div>
{prompt_box(auto['prompt'], 'Prompt zum Loslegen')}</article>
<article class="wcard tipp"><span class="eyebrow">💡 Profi-Tipp</span><h3>{e(tipp[0])}</h3><p>{e(tipp[1])}</p></article></div></div>"""]
    if news:
        teile.append(f'<div class="shead" style="margin-top:24px;--c:#8b5cf6"><span class="sicon">📚</span><h2>Neu: Anleitungen & Ideen aus dem Netz</h2>'
                     f'<span class="linie"></span></div><div class="grid">'
                     + "".join(karte(a, r_werk) for a in news) + "</div>")
    teile.append("</section>")
    return "\n".join(teile)


def html_bauen(ausgabe, fehler, demo=False, pdf_name="") -> str:
    heute = dt.datetime.now()
    nach_id = {r["id"]: (r, l[:WEB_PRO_RESSORT]) for r, l in ausgabe}
    reihenfolge = [i for i in WEB_REIHENFOLGE if i in nach_id] + [i for i in nach_id if i not in WEB_REIHENFOLGE]
    alle = [(r, a) for r, l in nach_id.values() for a in l]
    auf_r, auf = aufmacher_finden([(r, l) for r, l in nach_id.values() if r["id"] != "werkstatt"])
    top4 = sorted([(r, a) for r, a in alle if a is not auf and r["id"] != "werkstatt"],
                  key=lambda x: x[1]["punkte"] + (2 if x[1]["bild"] else 0), reverse=True)
    gesehen, top = set(), []
    for r, a in top4:                      # Top-Liste aus verschiedenen Rubriken
        if r["id"] not in gesehen:
            gesehen.add(r["id"]); top.append((r, a))
        if len(top) == 5:
            break
    benutzt = {id(a) for _, a in top} | ({id(auf)} if auf else set())

    chips = "".join(f'<a href="#r-{i}" style="--c:{farbe(nach_id[i][0])}">{ICONS.get(i, "•")} {e(nach_id[i][0]["titel"])}</a>'
                    for i in reihenfolge)
    pdf = f'<a class="btn" href="{e(pdf_name)}">📰 PDF-Ausgabe</a>' if pdf_name else ""
    neu = sum(1 for _, a in alle if a.get("neu"))
    s = [f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark">
<title>{e(ZEITUNG_NAME)} – {e(datum_heute())}</title>{FONTS}<style>{CSS}</style></head><body>
<header class="top"><div class="wrap topin"><a class="brand" href="#"><span>{e(ZEITUNG_NAME.split('-')[0])}</span><span class="b2">{e('-'.join(ZEITUNG_NAME.split('-')[1:]))}</span></a>
<div class="topmeta"><span>{e(datum_heute())}</span><span class="dot"></span><span>{len(alle)} Meldungen</span><span class="dot"></span><span>{neu} neu{" · DEMO" if demo else ""}</span></div>{pdf}</div>
<nav class="chips wrap">{chips}</nav></header><main class="wrap">"""]

    if auf:
        bild = f' style="background-image:url(\'{e(auf["bild"])}\')"' if auf["bild"] else \
            f' style="background:linear-gradient(135deg,{farbe(auf_r)},#0f172a)"'
        s.append(f"""<section class="hero"><a class="herocard" href="{e(auf['link'])}" target="_blank" rel="noopener"{bild}>
<div class="herotext"><span class="pill" style="--c:{farbe(auf_r)}">{ICONS.get(auf_r['id'], '')} {e(auf_r['titel'])}</span>
<h1>{e(auf['titel'])}</h1><p>{e(kuerzen(auf['teaser'], 240))}</p><div class="zeit">{e(auf.get('quelle', ''))} · {e(rel_zeit(auf.get('datum')))}</div></div></a>
<div class="toplist"><h2>Top-Meldungen</h2>""")
        for r, a in top:
            th = f'<div class="th" style="background-image:url(\'{e(a["bild"])}\')"></div>' if a["bild"] else \
                f'<div class="th" style="background:linear-gradient(135deg,{farbe(r)},#0f172a)"></div>'
            s.append(f'<a class="mini" href="{e(a["link"])}" target="_blank" rel="noopener" style="--c:{farbe(r)}">{th}'
                     f'<div><span class="kat">{ICONS.get(r["id"], "")} {e(r["titel"])}</span><b>{e(a["titel"])}</b></div></a>')
        s.append("</div></section>")

    for rid in reihenfolge:
        r, liste = nach_id[rid]
        if rid == "werkstatt":
            s.append(werkstatt_html(r, liste[:6]))
            continue
        liste = [a for a in liste if id(a) not in benutzt] or liste
        s.append(f'<section class="sec" id="r-{rid}" style="--c:{farbe(r)}"><div class="shead"><span class="sicon">{ICONS.get(rid, "•")}</span>'
                 f'<h2>{e(r["titel"])}</h2><span class="linie"></span><span class="anz">{len(liste)} Meldungen</span></div>')
        if not liste:
            s.append('<p class="leer">Heute nichts Neues in dieser Rubrik.</p></section>')
            continue
        erste = max(liste[:3], key=lambda a: a["punkte"] + (4 if a["bild"] else 0))
        rest = [a for a in liste if a is not erste]
        s.append('<div class="grid">' + karte(erste, r, gross=True) + "".join(karte(a, r) for a in rest) + "</div></section>")
        if rid == reihenfolge[min(3, len(reihenfolge) - 1)]:
            s.append(f'<div class="spruch"><small>Spruch des Tages</small>{e(SPRUECHE[heute.toordinal() % len(SPRUECHE)])}</div>')

    fehl = ""
    if fehler:
        fehl = "<details><summary>{} Quelle(n) heute nicht erreichbar</summary><ul>{}</ul></details>".format(
            len(fehler), "".join(f"<li>{e(x)}</li>" for x in fehler))
    s.append(f"""</main><footer><div class="wrap">{e(ZEITUNG_NAME)} · erstellt {heute.strftime('%d.%m.%Y, %H:%M Uhr')} aus RSS-Feeds.
Alle Meldungen führen zur Originalquelle.{fehl}</div></footer><script>{JS}</script></body></html>""")
    return "\n".join(s)


# ════════════════════════════════════════════════════════════════════
#  PDF-ZEITUNG – modernes Magazin-Layout (wird mit Chrome/Edge zu PDF)
# ════════════════════════════════════════════════════════════════════

DRUCK_CSS = """
@page{size:A4;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
html,body{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:Inter,"Segoe UI",Arial,sans-serif;color:#0f172a;background:#fff;font-size:9pt}
a{color:inherit;text-decoration:none}
.H{font-family:"Space Grotesk",Inter,Arial,sans-serif;font-weight:700;letter-spacing:-.02em;line-height:1.08}
.seite{width:210mm;height:297mm;padding:10mm 11mm 8mm;display:flex;flex-direction:column;overflow:hidden;
 page-break-after:always;break-after:page;position:relative}
.seite:last-child{page-break-after:auto;break-after:auto}
.dach{font-weight:700;color:var(--k,#8b5cf6);font-size:7.5pt;letter-spacing:.06em;text-transform:uppercase}
.neu{display:inline-block;background:var(--k,#8b5cf6);color:#fff;padding:.2mm 1.6mm;border-radius:3mm;margin-right:1.5mm;font-size:6.5pt;letter-spacing:.04em}
.meta{font-size:6.8pt;color:#94a3b8;margin-top:1.4mm}
.foto{background:#e2e8f0 center/cover no-repeat;position:relative;border-radius:3mm;overflow:hidden}
.foto.leer{background:linear-gradient(135deg,var(--a),var(--b));display:flex;align-items:center;justify-content:center}
.foto.leer .wort{color:#fff;opacity:.55;font-size:20pt}
/* Titelseite */
.tkopf{display:flex;align-items:flex-end;justify-content:space-between;padding-bottom:3mm}
.marke{font-size:34pt;line-height:.9}
.marke .b2{font-weight:400;background:linear-gradient(90deg,#8b5cf6,#ec4899,#f59e0b);-webkit-background-clip:text;background-clip:text;color:transparent}
.tinfo{text-align:right;font-size:8.5pt;color:#475569;line-height:1.5}
.tinfo b{color:#0f172a;font-size:10pt}
.balken{height:1.2mm;border-radius:1mm;background:linear-gradient(90deg,#8b5cf6,#ec4899,#f59e0b);margin-bottom:5mm}
.tauf .foto{height:80mm;border-radius:4mm}
.tauf .pillbox{position:absolute;left:5mm;top:5mm}
.pill{display:inline-block;background:var(--k,#8b5cf6);color:#fff;font-weight:700;font-size:8pt;padding:1mm 3mm;border-radius:4mm}
.tauf h1{margin:4mm 0 2mm}
.tteaser{font-size:10pt;line-height:1.45;color:#334155}
.tdrei{display:grid;grid-template-columns:repeat(3,1fr);gap:5mm;margin-top:5mm;padding-top:4mm;border-top:.3mm solid #e2e8f0;flex:1;min-height:0;overflow:hidden}
.tdrei article .foto{height:27mm;margin-bottom:2mm}
.tdrei h3{font-size:11.5pt;margin:.8mm 0 1.2mm}
.tdrei p{font-size:8pt;line-height:1.4;color:#475569}
.tfuss{display:grid;grid-template-columns:1.15fr 1fr;gap:5mm;margin-top:3mm}
.wteaser{border-radius:3.5mm;padding:4mm;color:#fff;background:linear-gradient(135deg,#8b5cf6,#ec4899)}
.wteaser .klein{font-size:7pt;font-weight:700;letter-spacing:.1em;text-transform:uppercase;opacity:.9}
.wteaser .H{font-size:12pt;margin:1.5mm 0}
.wteaser p{font-size:8pt;opacity:.92}
.index{background:#f1f5f9;border-radius:3.5mm;padding:3.5mm 4mm}
.index b{display:block;font-size:7pt;letter-spacing:.1em;text-transform:uppercase;color:#64748b;margin-bottom:1.5mm}
.index div{display:flex;justify-content:space-between;gap:3mm;padding:.7mm 0;font-size:8.2pt;border-bottom:.2mm solid #e2e8f0}
.index div:last-child{border:0}
.index i{font-style:normal;font-weight:700;color:#8b5cf6}
.spruchzeile{font-size:7.5pt;color:#64748b;font-style:italic;margin-top:.8mm}
/* Innenseiten */
.ikopf{display:flex;justify-content:space-between;align-items:center;font-size:7.5pt;color:#64748b;padding-bottom:2.5mm;
 border-bottom:.3mm solid #e2e8f0;margin-bottom:5mm}
.ikopf .H{font-size:10pt;color:#0f172a}
.ikopf .nr{font-weight:700;color:#0f172a;background:#f1f5f9;border-radius:3mm;padding:.6mm 2.5mm}
.block{display:flex;flex-direction:column;min-height:0;overflow:hidden;flex:1}
.block + .block{border-top:.3mm solid #e2e8f0;padding-top:4mm;margin-top:4mm}
.bkopf{display:flex;align-items:center;gap:2.5mm;margin-bottom:3.5mm}
.bkopf .strich{width:1.6mm;height:7mm;border-radius:1mm;background:var(--k)}
.bkopf b{font-size:18pt}
.bkopf span{font-size:7.5pt;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-left:auto}
.btop{position:relative;margin-bottom:4mm}
.voll .btop .foto{height:100mm;border-radius:4mm}
.voll .btop .ueber{position:absolute;left:0;right:0;bottom:0;padding:16mm 6mm 5mm;color:#fff;
 background:linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.78))}
.voll .btop .ueber .dach{color:#fff;opacity:.9}
.voll .btop .bteaser{font-size:9.5pt;line-height:1.45;color:#334155;margin-top:3mm}
.halb .btop,.drittel .btop{display:grid;grid-template-columns:1.05fr 1fr;gap:5mm}
.halb .btop .foto{height:54mm}
.drittel .btop .foto{height:36mm}
.halb .btop h2{margin:.8mm 0 2mm}.drittel .btop h2{margin:.6mm 0 1.4mm}
.halb .btop .bteaser{font-size:8.6pt;line-height:1.42;color:#475569}
.drittel .btop .bteaser{font-size:8pt;line-height:1.38;color:#475569}
.drittel .bkopf{margin-bottom:2.5mm}.drittel .bkopf b{font-size:14pt}
.spalten{flex:1;min-height:0;column-gap:6mm;column-fill:balance;column-count:3}
.drittel .spalten{column-count:2}
.spalten article{break-inside:avoid;margin-bottom:3.5mm}
.spalten article .foto{height:24mm;margin:.5mm 0 2mm}
.spalten h4{font-size:10pt;margin:.6mm 0 1.2mm}
.spalten p{font-size:7.8pt;line-height:1.4;color:#475569}
.leerbox{color:#94a3b8;font-size:9pt;padding:4mm 0}
.impressum{font-size:6.5pt;color:#94a3b8;border-top:.3mm solid #e2e8f0;padding-top:1.5mm;margin-top:3mm}
/* Werkstatt-Seite */
.wkopf{border-radius:5mm;padding:6mm;color:#fff;background:linear-gradient(135deg,#6d28d9,#db2777 60%,#f59e0b)}
.wkopf .klein{font-size:7.5pt;font-weight:700;letter-spacing:.12em;text-transform:uppercase;opacity:.9}
.wkopf h1{font-size:21pt;margin:2mm 0 2mm}
.wkopf p{font-size:9.5pt;opacity:.95;max-width:165mm}
.badges{display:flex;gap:2mm;margin-top:3mm}
.badge{background:rgba(255,255,255,.18);border-radius:3mm;padding:.8mm 2.5mm;font-size:7.5pt;font-weight:600}
.wbody{display:grid;grid-template-columns:1.25fr 1fr;gap:6mm;margin-top:5mm}
.wbody h3{font-size:12pt;margin-bottom:2.5mm}
.schritte{list-style:none;counter-reset:s;display:flex;flex-direction:column;gap:2.4mm}
.schritte li{counter-increment:s;display:flex;gap:2.5mm;font-size:8.6pt;line-height:1.42}
.schritte li::before{content:counter(s);flex:0 0 5.2mm;height:5.2mm;border-radius:50%;background:#8b5cf6;color:#fff;font-weight:700;
 font-size:7.5pt;display:flex;align-items:center;justify-content:center}
.prompt{background:#0f172a;color:#e2e8f0;border-radius:3mm;padding:3mm 3.5mm;font:7.8pt/1.5 "JetBrains Mono",Consolas,monospace;white-space:pre-wrap}
.prompt .pk{display:block;font:700 6.5pt Inter,Arial,sans-serif;letter-spacing:.1em;text-transform:uppercase;color:#a78bfa;margin-bottom:1.5mm}
.kasten{border-radius:3.5mm;padding:4mm;background:#f1f5f9;margin-bottom:4mm}
.kasten .klein{font-size:7pt;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#0891b2}
.kasten h4{font-size:11pt;margin:1.2mm 0 1.5mm}
.kasten p{font-size:8.2pt;line-height:1.42;color:#475569;margin-bottom:2mm}
.kasten.tipp{background:linear-gradient(135deg,#8b5cf6,#ec4899);color:#fff}
.kasten.tipp .klein,.kasten.tipp p{color:rgba(255,255,255,.92)}
.wnews{margin-top:5mm;padding-top:4mm;border-top:.3mm solid #e2e8f0;flex:1;min-height:0;overflow:hidden;display:flex;flex-direction:column}
"""

AKZENT = {"gs": "#a90432", "national": "#0ea5e9", "bundesliga": "#e11d48", "europa": "#6366f1", "boxen": "#f97316",
          "welt": "#2563eb", "werkstatt": "#8b5cf6", "claude": "#d97757", "ki": "#14b8a6", "smarthome": "#0891b2",
          "tv": "#db2777", "balkon": "#eab308", "forschung": "#059669", "technik": "#64748b", "visionen": "#7c3aed"}
ICONS = {"gs": "🦁", "national": "🌍", "bundesliga": "⚽", "europa": "🏆", "boxen": "🥊", "welt": "🌐",
         "werkstatt": "🛠️", "claude": "✳️", "ki": "🤖", "smarthome": "🏠", "balkon": "☀️", "tv": "📽️", "forschung": "🧬",
         "technik": "⚙️", "visionen": "🚀"}


def bild_einbetten(ausgabe):
    """Lädt Fotos herunter und bettet sie ins Druck-HTML ein (PDF wird dadurch eigenständig)."""
    offen = [a for _, l in ausgabe for a in l if a["bild"].startswith("http")]

    def hole(a):
        daten, typ, _ = laden(a["bild"], 4_000_000)
        typ = typ.split(";")[0].strip()
        if not typ.startswith("image/") or len(daten) >= 4_000_000:
            raise ValueError("kein Bild")
        try:   # mit Pillow (optional) verkleinern -> PDF bleibt handlich
            import io
            from PIL import Image
            bild = Image.open(io.BytesIO(daten)).convert("RGB")
            bild.thumbnail((1000, 1000))
            puffer = io.BytesIO()
            bild.save(puffer, "JPEG", quality=72, optimize=True)
            daten, typ = puffer.getvalue(), "image/jpeg"
        except Exception:
            pass
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
    k = farbe(r)
    return (f'<div class="{klasse} leer" style="--a:{k};--b:#0f172a">{extra}'
            f'<span class="wort H">{e(r["titel"])}</span></div>')


def hat_foto(a) -> bool:
    return bool(a.get("bild_druck") or a["bild"].startswith("data:"))


def groesse(titel: str, basis: float) -> str:
    n = len(titel)
    faktor = 1.0 if n <= 45 else .86 if n <= 70 else .74 if n <= 100 else .64
    return f"font-size:{basis * faktor:.1f}pt"


def werkstatt_seite(seitennr, kopf, r_werk, news) -> str:
    ws, auto, tipp = werkstatt_heute()
    if not ws:
        return ""
    schritte = "".join(f"<li><span>{e(x)}</span></li>" for x in ws["schritte"])
    s = [f"""<div class="seite">{kopf}<section class="wkopf"><div class="klein">KI-Werkstatt · Workshop des Tages</div>
<h1 class="H">{e(ws['titel'])}</h1><p>{e(ws['ziel'])}</p>
<div class="badges"><span class="badge">{e(ws['level'])}</span><span class="badge">Dauer: {e(ws['dauer'])}</span><span class="badge">{e(ws['feature'])}</span></div></section>
<div class="wbody"><div><h3 class="H">So geht's</h3><ol class="schritte">{schritte}</ol>
<div class="prompt" style="margin-top:4mm"><span class="pk">Prompt für Claude Code – abtippen oder von der Webseite kopieren</span>{e(ws['prompt'])}</div></div>
<div><div class="kasten"><div class="klein">Automatisierung des Tages</div><h4 class="H">{e(auto['titel'])}</h4>
<p>{e(auto['idee'])}</p><p style="font-size:7.5pt;color:#64748b">Werkzeuge: {e(auto['werkzeuge'])}</p>
<div class="prompt"><span class="pk">Prompt</span>{e(kuerzen(auto['prompt'], 260))}</div></div>
<div class="kasten tipp"><div class="klein">Profi-Tipp</div><h4 class="H">{e(tipp[0])}</h4><p>{e(tipp[1])}</p></div></div></div>"""]
    if news:
        s.append('<section class="wnews block" style="--k:#8b5cf6"><div class="bkopf"><span class="strich"></span>'
                 '<b class="H" style="font-size:13pt">Neu: Anleitungen & Ideen aus dem Netz</b></div><div class="spalten">')
        for a in news[:6]:
            s.append(f"""<article><div class="dach">{neu_tag(a)}{e(a.get('quelle') or '')}</div>
<h4 class="H" style="{groesse(a['titel'], 10)}"><a href="{e(a['link'])}">{e(a['titel'])}</a></h4>
<p>{e(kuerzen(a['teaser'], 120))}</p></article>""")
        s.append("</div></section>")
    s.append("</div>")
    return "\n".join(s)


def druck_bauen(ausgabe, demo=False) -> str:
    heute = dt.datetime.now()
    r_nach_id = {r["id"]: (r, l) for r, l in ausgabe}
    auf_r, auf = aufmacher_finden([(r, l) for r, l in ausgabe if r["id"] != "werkstatt"])
    benutzt = {id(auf)} if auf else set()
    spruch = SPRUECHE[heute.toordinal() % len(SPRUECHE)]
    nr = heute.timetuple().tm_yday
    teil1, teil2 = ZEITUNG_NAME.split("-")[0], "-".join(ZEITUNG_NAME.split("-")[1:])

    s = [f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><title>{e(ZEITUNG_NAME)} – {e(datum_heute())}</title>
{FONTS}<style>{DRUCK_CSS}</style></head><body>"""]

    # ── Titelseite ──
    s.append(f"""<div class="seite"><header class="tkopf"><div class="marke H">{e(teil1)}<span class="b2">{e(teil2)}</span></div>
<div class="tinfo"><b>{e(datum_heute())}</b><br>Ausgabe Nr. {nr} · {"DEMO" if demo else e(UNTERTITEL)}
<div class="spruchzeile">„{e(spruch)}“</div></div></header><div class="balken"></div>""")
    if auf:
        k = farbe(auf_r)
        s.append(f"""<section class="tauf" style="--k:{k}">{foto(auf, auf_r, extra=f'<span class="pillbox"><span class="pill">{e(auf_r["titel"])}</span></span>')}
<h1 class="H" style="{groesse(auf['titel'], 27)}"><a href="{e(auf['link'])}">{e(auf['titel'])}</a></h1>
<p class="tteaser">{e(kuerzen(auf['teaser'], 300))}</p>{meta(auf)}</section>""")

    kandidaten = []
    for r, l in ausgabe:
        if r["id"] == "werkstatt" or (auf_r and r["id"] == auf_r["id"]):
            continue
        beste = [a for a in l if a is not auf]
        if beste:
            kandidaten.append((r, max(beste[:3], key=lambda x: x["punkte"] + (3 if x["bild"] else 0))))
    kandidaten.sort(key=lambda x: x[1]["punkte"] + (3 if x[1]["bild"] else 0), reverse=True)
    s.append('<section class="tdrei">')
    for r, a in kandidaten[:3]:
        benutzt.add(id(a))
        s.append(f"""<article style="--k:{farbe(r)}">{foto(a, r)}<div class="dach">{neu_tag(a)}{e(r['titel'])}</div>
<h3 class="H" style="{groesse(a['titel'], 11.5)}"><a href="{e(a['link'])}">{e(a['titel'])}</a></h3>
<p>{e(kuerzen(a['teaser'], 150))}</p>{meta(a)}</article>""")
    s.append("</section>")

    def seiten_name(ids):
        if ids == ["werkstatt"]:
            return "KI-Werkstatt: Workshop des Tages"
        return " · ".join(r_nach_id[i][0]["titel"] for i in ids if i in r_nach_id)

    index = "".join(f'<div><span>{e(seiten_name(ids))}</span><i>{n}</i></div>' for n, ids in enumerate(PDF_SEITEN, start=2))
    ws, _, _ = werkstatt_heute()
    wteaser = (f'<div class="wteaser"><div class="klein">Heute in der KI-Werkstatt · Seite '
               f'{next((n for n, ids in enumerate(PDF_SEITEN, start=2) if ids == ["werkstatt"]), 2)}</div>'
               f'<div class="H">{e(ws["titel"])}</div><p>{e(ws["level"])} · {e(ws["dauer"])} · mit fertigem Prompt für Claude Code</p></div>'
               if ws else '<div></div>')
    s.append(f'<footer class="tfuss">{wteaser}<div class="index"><b>In dieser Ausgabe</b>{index}</div></footer></div>')

    # ── Innenseiten ──
    for seitennr, ids in enumerate(PDF_SEITEN, start=2):
        kopf = (f'<header class="ikopf"><span class="H">{e(teil1)}<span style="font-weight:400">{e(teil2)}</span></span>'
                f'<span>{e(datum_heute())}</span><span class="nr">Seite {seitennr}</span></header>')
        if ids == ["werkstatt"]:
            r_w, news = r_nach_id.get("werkstatt", (None, []))
            s.append(werkstatt_seite(seitennr, kopf, r_w, news))
            continue
        art = {1: "voll", 2: "halb"}.get(len(ids), "drittel")
        s.append(f'<div class="seite">{kopf}')
        for rid in ids:
            if rid not in r_nach_id:
                continue
            r, liste = r_nach_id[rid]
            liste = [a for a in liste if id(a) not in benutzt] or liste
            k = farbe(r)
            s.append(f'<section class="block {art}" style="--k:{k}"><div class="bkopf"><span class="strich"></span>'
                     f'<b class="H">{e(r["titel"])}</b><span>{len(liste)} Meldungen</span></div>')
            if not liste:
                s.append('<p class="leerbox">Heute keine Meldungen in dieser Rubrik.</p></section>')
                continue
            top = max(liste[:3], key=lambda a: a["punkte"] + (4 if a["bild"] else 0))
            rest = [a for a in liste if a is not top][: {"voll": 7, "halb": 3, "drittel": 2}[art]]
            if art == "voll":
                ueber = (f'<div class="ueber"><div class="dach">{neu_tag(top)}{e(top.get("quelle") or r["titel"])}</div>'
                         f'<h2 class="H" style="{groesse(top["titel"], 22)}"><a href="{e(top["link"])}">{e(top["titel"])}</a></h2></div>')
                s.append(f'<article class="btop">{foto(top, r, extra=ueber)}'
                         f'<p class="bteaser">{e(kuerzen(top["teaser"], 300))}</p>{meta(top)}</article>')
            else:
                gr = 16 if art == "halb" else 12.5
                s.append(f"""<article class="btop">{foto(top, r)}<div><div class="dach">{neu_tag(top)}{e(top.get('quelle') or r['titel'])}</div>
<h2 class="H" style="{groesse(top['titel'], gr)}"><a href="{e(top['link'])}">{e(top['titel'])}</a></h2>
<p class="bteaser">{e(kuerzen(top['teaser'], 260 if art == 'halb' else 170))}</p>{meta(top)}</div></article>""")
            s.append('<div class="spalten">')
            for i, a in enumerate(rest):
                bild = foto(a, r) if hat_foto(a) and (art == "voll" or (art == "halb" and i == 0)) else ""
                s.append(f"""<article><div class="dach">{neu_tag(a)}{e(a.get('quelle') or r['titel'])}</div>{bild}
<h4 class="H" style="{groesse(a['titel'], 10)}"><a href="{e(a['link'])}">{e(a['titel'])}</a></h4>
<p>{e(kuerzen(a['teaser'], {"voll": 210, "halb": 150, "drittel": 110}[art]))}</p>{meta(a)}</article>""")
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
