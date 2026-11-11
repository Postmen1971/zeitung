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
REGION = ["Ebersbach", "Göppingen", "Uhingen", "Reichenbach an der Fils", "Plochingen", "Esslingen"]   # "aus deiner Nähe"
WOHNORT = {"name": "Ebersbach an der Fils", "lat": 48.716, "lon": 9.524}   # für den Wetter- und Solar-Kasten
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
    "ebersbach": 8, "göppingen": 7, "uhingen": 6, "fils": 4, "plochingen": 4, "esslingen": 3, "stuttgart": 2,
    "ersparnis": 3, "sparen": 2, "förder": 3,
    "balkonkraftwerk": 4, "angebot": 2, "deal": 2, "rabatt": 2, "tiefstpreis": 3, "bestpreis": 3,
    "beamer": 4, "projektor": 3, "oled": 2, "fernseher": 2, "4k": 1,
    "roboter": 2, "erfindung": 3, "fusion": 2, "raumfahrt": 2, "quanten": 2,
}

# Meldungen mit diesen Wörtern werden ausgeblendet
SPERRLISTE = ["horoskop", "gewinnspiel", "anzeige", "sponsored", "rabattcode", "live hören", "quoten", "tipp, prognose", "wettbasis"]


def gnews(suche: str, sprache: str = "de", tage: int = 2) -> str:
    """Google-News-Suche als RSS (Standard: letzte 2 Tage)."""
    q = urllib.parse.quote(f"{suche} when:{tage}d")
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
    {"id": "smartideen", "dach": "SMART HOME", "titel": "Smart-Home-Ideen aus der Community", "stil": "smarthome",
     "stichwoerter": ["tuya", "smart life", "home assistant", "automation", "smart home", "smarthome", "zigbee",
                      "sensor", "dashboard", "idee", "project", "setup", "diy"],
     "max_alter": 24 * 14,     # Ideen dürfen bis zu 2 Wochen alt sein
     "feeds": [F("https://hackaday.com/category/home-hacks/feed/"),
               F("https://smarthomescene.com/feed/"),
               F("https://dev.to/feed/tag/homeassistant"), F("https://dev.to/feed/tag/smarthome"),
               F("https://dev.to/feed/tag/iot", True),
               F(gnews("Tuya Ideen Automation", tage=14)), F(gnews("Smart Home DIY Projekt", tage=14)),
               F(gnews("Home Assistant Automation Beispiele", tage=14)),
               F(gnews("Tuya automation ideas", "en", tage=14), True),
               F(gnews("Smart Life App Szenen Tipps", tage=14))]},
    {"id": "solar", "dach": "SOLAR", "titel": "Solar aus Göppingen & Umgebung", "stil": "balkon",
     "stichwoerter": ["balkonkraftwerk", "steckersolar", "solar", "photovoltaik", "pv-anlage", "pv ", "energie"],
     "max_alter": 24 * 21,     # regionale Solar-Meldungen sind selten – 3 Wochen zurück
     "feeds": [F(gnews("Balkonkraftwerk Göppingen OR Ebersbach OR Uhingen", tage=21)),
               F(gnews("Photovoltaik Landkreis Göppingen", tage=21)), F(gnews("Solar Göppingen", tage=21)),
               F(gnews("Stadtwerke Göppingen Solar OR Photovoltaik", tage=30)),
               F(gnews("Energieagentur Landkreis Göppingen", tage=30)),
               F(gnews("Balkonkraftwerk Esslingen OR Plochingen OR Filstal", tage=21)),
               F(gnews("Balkonkraftwerk Baden-Württemberg", tage=7)),
               F(gnews("Balkonkraftwerk Erfahrung Ersparnis")), F(gnews("Balkonkraftwerk Tipps Ertrag")),
               F(gnews("Balkonkraftwerk Speicher lohnt sich"))]},
    {"id": "balkon", "dach": "SOLAR", "titel": "Balkonkraftwerk-Angebote", "stil": "balkon",
     "stichwoerter": ["balkonkraftwerk", "balkon-kraftwerk", "steckersolar", "stecker-solar", "mini-pv",
                      "mini-solar", "solarmodul", "solaranlage für den balkon", "balkonsolar", "pv-speicher",
                      "anker solix", "ecoflow", "zendure", "growatt", "hoymiles", "deye", "wechselrichter"],
     "feeds": [F(gnews("Balkonkraftwerk Angebot Göppingen OR Esslingen OR Stuttgart", tage=14)),
               F(gnews("Balkonkraftwerk Angebot")), F(gnews("Balkonkraftwerk Deal Preis")),
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
           "reddit.com/r/ClaudeCode": "r/ClaudeCode", "r/homeassistant": "r/homeassistant",
           "hackaday": "Hackaday", "smarthomescene": "SmartHomeScene", "mydealz": "mydealz", "anthropics/claude-code": "Claude Code (GitHub)"}

# Reihenfolge der Rubriken auf der Webseite
WEB_REIHENFOLGE = ["werkstatt", "claude", "ki", "gs", "bundesliga", "europa", "national", "boxen", "welt",
                   "smarthome", "smartideen", "solar", "balkon", "tv", "forschung", "technik", "visionen"]

# Aufbau der PDF-Zeitung: Seite 1 = Titelseite, danach je Seite eine oder zwei Rubriken
PDF_SEITEN = [["werkstatt"], ["gs"], ["bundesliga"], ["europa", "national", "boxen"], ["welt"], ["claude", "ki"],
              ["smarthome", "smartideen", "tv"], ["solar", "balkon"], ["forschung", "technik", "visionen"]]

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
                if a["datum"] and (jetzt - a["datum"]).total_seconds() > r.get("max_alter", MAX_ALTER_STUNDEN) * 3600:
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
#  ARTIKEL – Claude schreibt aus jeder Meldung einen eigenen Zeitungsartikel
# ════════════════════════════════════════════════════════════════════
# Braucht einen API-Schlüssel von https://platform.claude.com (Umgebungsvariable
# ANTHROPIC_API_KEY, bei GitHub als "Secret"). Ohne Schlüssel druckt die Zeitung
# die Anreißer der Quellen. Die Originaltexte werden nur gelesen, nie abgedruckt.

KI_MODELL = os.environ.get("KI_MODELL", "claude-haiku-5-5")
ARTIKEL_PRO_RESSORT = 6            # so viele Meldungen pro Rubrik bekommen einen Artikel
ARTIKEL_CACHE = BASIS / "artikel_cache.json"

ARTIKEL_ANWEISUNG = """Du bist Redakteur einer deutschen Boulevardzeitung. Schreibe aus der folgenden Meldung einen
eigenständigen Zeitungsartikel auf Deutsch.

Regeln:
- Ausschließlich in eigenen Worten. Übernimm keine Sätze aus der Quelle; höchstens ein kurzes Zitat (unter 15 Wörtern) in Anführungszeichen.
- Nur Fakten aus der Quelle. Nichts erfinden, keine Zahlen, Namen oder Zitate ergänzen. Fehlen Infos, schreib kürzer.
- Ton: lebendig und packend wie Boulevard, aber korrekt und fair. Keine Beleidigungen, keine Übertreibung von Tatsachen.
- Ist die Quelle türkisch oder englisch: auf Deutsch übersetzen und erklären, was für deutsche Leser unklar sein könnte.
- Länge des Artikeltextes: etwa {woerter} Wörter in 2–3 Absätzen.

Antworte NUR mit JSON in dieser Form:
{{"dachzeile": "max. 4 Wörter", "schlagzeile": "max. 9 Wörter, knackig", "vorspann": "1 Satz, max. 25 Wörter", "text": "Absätze getrennt durch \\n\\n"}}

Rubrik: {rubrik}
Original-Schlagzeile: {titel}
Quelle: {quelle}
Kurzbeschreibung: {teaser}

Text der Originalseite (nur zum Lesen):
{seite}"""


def artikeltext_holen(url: str) -> str:
    """Liest den Fließtext einer Artikelseite (nur als Grundlage für Claude)."""
    if not url.startswith("http") or "news.google.com" in url:
        return ""
    daten = laden(url, 900_000)[0].decode("utf-8", "replace")
    daten = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header|aside|form)[^>]*>.*?</\1>", " ", daten)
    m = re.search(r"(?is)<article[^>]*>(.*?)</article>", daten)
    bereich = m.group(1) if m and len(m.group(1)) > 1500 else daten
    absaetze = [saeubern(p) for p in re.findall(r"(?is)<p[^>]*>(.*?)</p>", bereich)]
    absaetze = [p for p in absaetze if len(p) > 60 and "cookie" not in p.lower()]
    return "\n".join(absaetze)[:7000]


def cache_laden() -> dict:
    try:
        return json.loads(ARTIKEL_CACHE.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def claude_fragen(prompt: str, schluessel: str) -> str:
    daten = json.dumps({"model": KI_MODELL, "max_tokens": 900,
                        "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=daten, headers={
        "x-api-key": schluessel, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        antwort = json.loads(r.read().decode())
    return "".join(b.get("text", "") for b in antwort.get("content", []) if b.get("type") == "text")


def artikel_schreiben(ausgabe):
    """Ergänzt a['ki'] = {dachzeile, schlagzeile, vorspann, text} für die wichtigsten Meldungen."""
    schluessel = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not schluessel:
        print("  Artikel: kein ANTHROPIC_API_KEY – die Zeitung nutzt die Anreißer der Quellen.")
        return
    cache = cache_laden()
    jobs = []
    for r, liste in ausgabe:
        for i, a in enumerate(liste[:ARTIKEL_PRO_RESSORT]):
            woerter = 170 if i == 0 else 90
            jobs.append((r, a, woerter))

    fehler, neu = [], 0

    def schreibe(job):
        r, a, woerter = job
        k = hashlib.sha1(f"{a['link']}|{woerter}".encode()).hexdigest()[:20]
        if k in cache:
            return a, cache[k], k, False
        try:
            seite = artikeltext_holen(a["link"])
        except Exception:
            seite = ""
        if len(seite) < 300:
            woerter = min(woerter, 60)          # wenig Material -> kurzer Artikel
        prompt = ARTIKEL_ANWEISUNG.format(woerter=woerter, rubrik=r["titel"], titel=a["titel"],
                                          quelle=a.get("quelle", ""), teaser=a["teaser"] or "-",
                                          seite=seite or "(nicht verfügbar – nur Schlagzeile und Kurzbeschreibung nutzen)")
        text = claude_fragen(prompt, schluessel)
        m = re.search(r"\{.*\}", text, re.S)
        ki = json.loads(m.group(0))
        if not ki.get("text"):
            raise ValueError("leer")
        return a, ki, k, True

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for fut in concurrent.futures.as_completed([pool.submit(schreibe, j) for j in jobs]):
            try:
                a, ki, k, frisch = fut.result()
                a["ki"] = ki
                cache[k] = ki
                neu += frisch
            except Exception as ex:
                fehler.append(f"{type(ex).__name__}: {str(ex)[:120]}")
    # Cache klein halten
    if len(cache) > 1500:
        cache = dict(list(cache.items())[-1500:])
    try:
        ARTIKEL_CACHE.write_text(json.dumps(cache, ensure_ascii=False), "utf-8")
    except OSError:
        pass
    fertig = sum(1 for _, l in ausgabe for a in l if a.get("ki"))
    print(f"  Artikel: {fertig} fertig ({neu} neu geschrieben)" + (f", {len(fehler)} Fehler, z. B. {fehler[0]}" if fehler else ""))


def schlagzeile(a) -> str:
    return (a.get("ki") or {}).get("schlagzeile") or a["titel"]


def dachzeile(a, r) -> str:
    return (a.get("ki") or {}).get("dachzeile") or r["titel"]


def vorspann(a) -> str:
    return (a.get("ki") or {}).get("vorspann") or ""


def artikel_absaetze(a, max_woerter: int):
    """Absätze des Artikels (KI-Text oder Anreißer), auf max_woerter gekürzt."""
    text = (a.get("ki") or {}).get("text") or a["teaser"] or ""
    absaetze, zaehler = [], 0
    for p in [x.strip() for x in text.split("\n") if x.strip()]:
        w = p.split()
        if zaehler + len(w) > max_woerter:
            rest = max_woerter - zaehler
            if rest > 12 or (not absaetze and rest > 0):
                absaetze.append(" ".join(w[:rest]) + " …")
            break
        absaetze.append(p)
        zaehler += len(w)
    return absaetze



# ════════════════════════════════════════════════════════════════════
#  WETTER & SOLAR-ERTRAG FÜR DEN WOHNORT (Open-Meteo, kostenlos, ohne Schlüssel)
# ════════════════════════════════════════════════════════════════════

WETTER_TEXT = {0: "sonnig", 1: "heiter", 2: "wolkig", 3: "bedeckt", 45: "Nebel", 48: "Nebel", 51: "Niesel", 53: "Niesel",
               55: "Niesel", 61: "Regen", 63: "Regen", 65: "starker Regen", 66: "Eisregen", 67: "Eisregen", 71: "Schnee",
               73: "Schnee", 75: "viel Schnee", 77: "Schnee", 80: "Schauer", 81: "Schauer", 82: "Starkregen",
               85: "Schneeschauer", 86: "Schneeschauer", 95: "Gewitter", 96: "Gewitter", 99: "Gewitter"}
BALKON_KWP, BALKON_FAKTOR = 0.8, 0.75 * 0.7      # 800 Wp, Systemverluste, senkrechte Montage (grob)


def wetter_holen():
    url = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&timezone=Europe%2FBerlin&forecast_days=3"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunshine_duration,"
           "shortwave_radiation_sum").format(**WOHNORT)
    d = json.loads(laden(url)[0].decode())["daily"]
    tage = []
    for i in range(len(d["time"])):
        mj = d["shortwave_radiation_sum"][i] or 0
        kwh = mj / 3.6 * BALKON_KWP * BALKON_FAKTOR
        tage.append({"datum": dt.date.fromisoformat(d["time"][i]), "code": d["weather_code"][i],
                     "max": round(d["temperature_2m_max"][i]), "min": round(d["temperature_2m_min"][i]),
                     "regen": d["precipitation_probability_max"][i] or 0,
                     "sonne_h": round((d["sunshine_duration"][i] or 0) / 3600, 1), "solar_kwh": round(kwh, 1)})
    return tage


def wetter_demo():
    heute = dt.date.today()
    return [{"datum": heute + dt.timedelta(days=i), "code": c, "max": t, "min": t - 7, "regen": r, "sonne_h": h, "solar_kwh": k}
            for i, (c, t, r, h, k) in enumerate([(1, 12, 10, 6.5, 1.9), (3, 9, 40, 1.2, 0.6), (61, 7, 80, 0.3, 0.3)])]


def wetter_symbol(code: int, groesse: str = "11mm") -> str:
    """Kleines Wettersymbol als SVG (keine Emoji-Schrift nötig)."""
    sonne = '<circle cx="14" cy="13" r="7" fill="#ffc107"/>'
    wolke = '<path d="M9 26h17a6 6 0 0 0 0-12 8 8 0 0 0-15-2 6 6 0 0 0-2 14z" fill="{f}"/>'
    if code in (0, 1):
        innen = sonne + "".join(f'<line x1="14" y1="13" x2="{14 + 11 * __import__("math").cos(w)}" y2="{13 + 11 * __import__("math").sin(w)}" '
                               f'stroke="#ffc107" stroke-width="2"/>' for w in [i * 0.785 for i in range(8)])
    elif code == 2:
        innen = sonne + wolke.format(f="#cfd8dc")
    elif code in (3, 45, 48):
        innen = wolke.format(f="#90a4ae")
    elif code in (71, 73, 75, 77, 85, 86):
        innen = wolke.format(f="#90a4ae") + "".join(f'<circle cx="{x}" cy="31" r="1.6" fill="#4fc3f7"/>' for x in (12, 18, 24))
    elif code >= 95:
        innen = wolke.format(f="#607d8b") + '<path d="M18 26l-4 7h4l-2 6 7-9h-4l2-4z" fill="#ffc107"/>'
    else:
        innen = wolke.format(f="#90a4ae") + "".join(f'<line x1="{x}" y1="29" x2="{x - 2}" y2="35" stroke="#1e88e5" stroke-width="2"/>' for x in (13, 19, 25))
    return f'<svg viewBox="0 0 36 38" style="width:{groesse};height:{groesse}">{innen}</svg>'


WETTER = []          # wird in main() gefüllt


# Links zu Solar-Angeboten in der Nähe (öffnen jeweils die aktuelle Suche)
def angebote_links():
    ort = urllib.parse.quote_plus
    return [("Balkonkraftwerk kaufen in Göppingen", f"https://www.google.com/search?q={ort('Balkonkraftwerk kaufen Göppingen')}"),
            ("Solar-Fachbetriebe bei Ebersbach (Karte)", f"https://www.google.com/maps/search/{ort('Photovoltaik Fachbetrieb Ebersbach an der Fils')}"),
            ("Baumärkte mit Balkonkraftwerk bei Göppingen", f"https://www.google.com/maps/search/{ort('Baumarkt Göppingen')}"),
            ("Gebrauchte Balkonkraftwerke (Kleinanzeigen)", f"https://www.google.com/search?q={ort('site:kleinanzeigen.de Balkonkraftwerk Göppingen')}"),
            ("Förderung im Kreis Göppingen", f"https://www.google.com/search?q={ort('Förderung Balkonkraftwerk Landkreis Göppingen')}"),
            ("Alle aktuellen Deals (mydealz)", "https://www.mydealz.de/search?q=balkonkraftwerk")]

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


DEMO_TEXT = ("Das ist Blindtext für die Demo-Ausgabe. Im echten Lauf schreibt Claude hier einen eigenen Artikel "
             "aus der Originalmeldung – in eigenen Worten, auf Deutsch und ohne etwas dazuzuerfinden. Türkische und "
             "englische Meldungen werden dabei gleich übersetzt.\n\nSo bekommt jede Meldung einen richtigen Zeitungstext "
             "mit Vorspann, mehreren Absätzen und Quellenangabe. Die Länge passt sich der Stelle in der Zeitung an: "
             "Aufmacher bekommen mehr Text, kleine Meldungen weniger. Wer mehr wissen will, tippt auf die Schlagzeile "
             "und landet beim Originalartikel.\n\nNoch mehr Blindtext, damit man sieht, wie sich lange Artikel in den "
             "Spalten verhalten. Die Zeitung schneidet zu lange Texte sauber ab, damit nichts über den Seitenrand läuft "
             "und jede Seite aufgeräumt aussieht, genau wie eine gedruckte Boulevardzeitung am Kiosk.")


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
                "ki": {"dachzeile": f"{r['titel']} aktuell", "schlagzeile": f"Platzhalter-Schlagzeile Nr. {n + 1} aus {r['titel']}",
                       "vorspann": "Hier steht der fett gedruckte Vorspann: ein Satz, der neugierig macht und das Wichtigste verrät.",
                       "text": DEMO_TEXT},
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
/* Zeitung von heute */
.ausgabe{display:flex;gap:22px;align-items:center;background:var(--fl);border:1px solid var(--rand);border-radius:24px;padding:20px;margin-bottom:36px;box-shadow:var(--schatten)}
.cover{flex:0 0 150px;height:212px;border-radius:8px;background:#fff center/cover;box-shadow:0 10px 30px rgba(0,0,0,.25);transform:rotate(-2deg);transition:transform .2s}
.cover:hover{transform:rotate(0) scale(1.03)}
.ausgabe h2{font-size:24px;margin:6px 0 6px}.ausgabe p{color:var(--tx2);max-width:560px}
.knoepfe{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.btn.rot{background:#d0021b;color:#fff}.btn.hell{background:var(--fl2);color:var(--tx)}
@media(max-width:600px){.ausgabe{flex-direction:column;align-items:flex-start}.cover{flex-basis:auto;width:130px;height:184px}}
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
/* Solar-Rechner */
.rechner .felder{display:grid;grid-template-columns:1fr 1fr;gap:12px 16px;margin:14px 0}
.rechner label{display:flex;flex-direction:column;gap:6px;font-size:13px;color:var(--tx2)}
.rechner label b{color:var(--tx)}
.rechner input[type=range]{accent-color:#f59e0b}
.rechner select,.rechner input[type=number]{font:inherit;padding:8px 10px;border-radius:10px;border:1px solid var(--rand);background:var(--fl2);color:var(--tx)}
.ergebnis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:6px 0 8px}
.ergebnis div{background:var(--fl2);border-radius:12px;padding:10px 12px}
.ergebnis small{display:block;font-size:11.5px;color:var(--tx3)}
.ergebnis b{font-family:"Space Grotesk",Inter,sans-serif;font-size:20px}
.ergebnis .gruen{background:color-mix(in srgb,#16a34a 15%,transparent)}.ergebnis .gruen b{color:#16a34a}
@media(max-width:600px){.rechner .felder,.ergebnis{grid-template-columns:1fr 1fr}}
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


def solar_html(r, liste) -> str:
    tipp = werkstatt.solar_heute(dt.date.today().toordinal()) if werkstatt and hasattr(werkstatt, "solar_heute") else None
    ausr = getattr(werkstatt, "AUSRICHTUNGEN", {"Süd, senkrecht am Geländer": 0.7}) if werkstatt else {"Süd, senkrecht am Geländer": 0.7}
    basis = getattr(werkstatt, "ERTRAG_PRO_KWP", 1000) if werkstatt else 1000
    opts = "".join(f'<option value="{f}"{" selected" if "senkrecht" in n and "Süd" in n else ""}>{e(n)}</option>' for n, f in ausr.items())
    teile = [f"""<section class="sec" id="r-solar" style="--c:{farbe(r)}"><div class="shead"><span class="sicon">🌞</span>
<h2>{e(r['titel'])}</h2><span class="linie"></span><span class="anz">{len(liste)} Meldungen</span></div>
<div class="wgrid" style="margin-bottom:16px"><article class="wcard rechner"><span class="eyebrow" style="--c:#d97706">☀️ Ersparnis-Rechner</span>
<h3>Was bringt dir ein Balkonkraftwerk?</h3>
<div class="felder">
<label>Modulleistung <b><span id="wpw">900</span> Wp</b><input id="wp" type="range" min="300" max="2000" step="50" value="900"></label>
<label>Montage<select id="au">{opts}</select></label>
<label>Eigenverbrauch <b><span id="evw">60</span> %</b><input id="ev" type="range" min="20" max="100" step="5" value="60"></label>
<label>Strompreis (€/kWh)<input id="pr" type="number" min="0.1" max="1" step="0.01" value="0.35"></label>
<label>Kaufpreis (€)<input id="kp" type="number" min="0" step="10" value="450"></label></div>
<div class="ergebnis"><div><small>Ertrag / Jahr</small><b id="r1">–</b></div><div><small>selbst genutzt</small><b id="r2">–</b></div>
<div class="gruen"><small>Ersparnis / Jahr</small><b id="r3">–</b></div><div><small>hat sich bezahlt nach</small><b id="r4">–</b></div></div>
<p class="werkzeug">Grobe Schätzung für den Raum Göppingen (ca. {basis} kWh pro kWp bei optimaler Lage, max. 800-W-Wechselrichter).
Genauer für deine Adresse: <a href="https://re.jrc.ec.europa.eu/pvg_tools/de/" target="_blank" rel="noopener" style="text-decoration:underline">PVGIS-Rechner der EU</a>.</p></article>
<div class="wside">{f'<article class="wcard tipp" style="background:linear-gradient(135deg,#f59e0b,#ea580c)"><span class="eyebrow">🌞 Solar-Tipp des Tages</span><h3>{e(tipp[0])}</h3><p>{e(tipp[1])}</p></article>' if tipp else ''}
<article class="wcard"><span class="eyebrow" style="--c:#d97706">📋 Die Regeln 2026</span><p style="margin-top:8px">Bis <b>800 W</b> Wechselrichter und <b>2.000 Wp</b> Module:
keine Anmeldung beim Netzbetreiber, aber Eintrag im <b>Marktstammdatenregister</b> innerhalb eines Monats. Ein Speicher wird dort gesondert angemeldet.</p></article></div></div>
<script>(function(){{const B={basis},$=i=>document.getElementById(i);function rechne(){{const wp=+$('wp').value,f=+$('au').value,ev=+$('ev').value/100,
pr=+$('pr').value||0,kp=+$('kp').value||0;$('wpw').textContent=wp;$('evw').textContent=Math.round(ev*100);
let kwh=Math.min(wp/1000*B*f,1040);const selbst=kwh*ev,eur=selbst*pr;$('r1').textContent=Math.round(kwh)+' kWh';
$('r2').textContent=Math.round(selbst)+' kWh';$('r3').textContent=Math.round(eur)+' €';$('r4').textContent=eur>0&&kp>0?(kp/eur).toFixed(1).replace('.',',')+' Jahren':'–';}}
['wp','au','ev','pr','kp'].forEach(i=>$(i).addEventListener('input',rechne));rechne();}})();</script>"""]
    if liste:
        erste = max(liste[:3], key=lambda a: a["punkte"] + (4 if a["bild"] else 0))
        teile.append('<div class="grid">' + karte(erste, r, gross=True) + "".join(karte(a, r) for a in liste if a is not erste) + "</div>")
    teile.append("</section>")
    return "\n".join(teile)


def html_bauen(ausgabe, fehler, demo=False, pdf_name="", leser=False, download_name="zeitung.pdf") -> str:
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
    pdf = (f'<a class="btn" href="lesen.html">📰 Zeitung lesen</a>' if leser else
           f'<a class="btn" href="{e(pdf_name)}">📰 PDF-Ausgabe</a>' if pdf_name else "")
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

    if pdf_name:
        cover = ('<a class="cover" href="lesen.html" style="background-image:url(\'seiten/mini-01.jpg\')"></a>' if leser else "")
        s.append(f"""<section class="ausgabe">{cover}<div><span class="eyebrow" style="--c:#d0021b">📰 Die Zeitung von heute</span>
<h2>{e(ZEITUNG_NAME)} vom {e(datum_heute())}</h2><p>{len(PDF_SEITEN) + 1} Seiten im Boulevard-Format mit Artikeln, Fotos und der KI-Werkstatt –
zum Umblättern direkt hier im Browser oder als PDF.</p><div class="knoepfe">
{'<a class="btn rot" href="lesen.html">Jetzt durchblättern</a>' if leser else ''}
<a class="btn hell" href="{e(pdf_name)}" target="_blank" rel="noopener">PDF öffnen</a>
<a class="btn hell" href="{e(pdf_name)}" download="{e(download_name)}">⬇ Herunterladen</a></div></div></section>""")

    for rid in reihenfolge:
        r, liste = nach_id[rid]
        if rid == "werkstatt":
            s.append(werkstatt_html(r, liste[:6]))
            continue
        if rid == "solar":
            s.append(solar_html(r, [a for a in liste if id(a) not in benutzt] or liste))
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


AKZENT = {"gs": "#a90432", "national": "#0ea5e9", "bundesliga": "#e11d48", "europa": "#6366f1", "boxen": "#f97316",
          "welt": "#2563eb", "werkstatt": "#8b5cf6", "claude": "#d97757", "ki": "#14b8a6", "smarthome": "#0891b2",
          "tv": "#db2777", "balkon": "#eab308", "solar": "#f59e0b", "smartideen": "#0d9488", "forschung": "#059669", "technik": "#64748b", "visionen": "#7c3aed"}
ICONS = {"gs": "🦁", "national": "🌍", "bundesliga": "⚽", "europa": "🏆", "boxen": "🥊", "welt": "🌐",
         "werkstatt": "🛠️", "claude": "✳️", "ki": "🤖", "smarthome": "🏠", "smartideen": "💡", "solar": "🌞", "balkon": "🏷️", "tv": "📽️", "forschung": "🧬",
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


# ════════════════════════════════════════════════════════════════════
#  PDF-ZEITUNG – klassischer Boulevard-Look mit Artikeln
# ════════════════════════════════════════════════════════════════════

FONTS_DRUCK = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
               '<link href="https://fonts.googleapis.com/css2?family=Anton&family=Roboto+Condensed:wght@400;700;900'
               '&family=Roboto:wght@400;700&family=PT+Serif:wght@400;700&family=JetBrains+Mono&display=swap" rel="stylesheet">')

DRUCK_CSS = """
@font-face{font-family:"KnallerFett";font-weight:400;src:local("Anton"),local("Impact"),local("DejaVu Sans Condensed Bold"),local("DejaVuSansCondensed-Bold"),local("Arial Black")}
@page{size:A4;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
html,body{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:Roboto,Arial,Helvetica,sans-serif;color:#111;background:#fff;font-size:8.4pt;line-height:1.33;hyphens:auto;-webkit-hyphens:auto}
a{color:inherit;text-decoration:none}
.H{font-family:Anton,KnallerFett,Impact,sans-serif;font-weight:400;text-transform:uppercase;line-height:.95;letter-spacing:.1px;hyphens:manual}
.C{font-family:"Roboto Condensed","Arial Narrow",Arial,sans-serif}
.seite{width:210mm;height:297mm;padding:7mm 8mm 6mm;display:flex;flex-direction:column;overflow:hidden;page-break-after:always;break-after:page;position:relative}
.seite:last-child{page-break-after:auto;break-after:auto}
.dach{font-family:"Roboto Condensed",Arial,sans-serif;font-weight:900;color:#d0021b;text-transform:uppercase;font-size:8.5pt;letter-spacing:.2px;margin-bottom:.8mm}
.neu{background:#d0021b;color:#fff;padding:0 1.2mm;margin-right:1.2mm;font-size:7pt}
/* Schlagzeilen-Varianten */
.hl span{padding:.2mm 1.6mm;box-decoration-break:clone;-webkit-box-decoration-break:clone}
.hl.rot span{background:#d0021b;color:#fff}
.hl.gelb span{background:#ffd400;color:#111}
.hl.schwarz span{background:#111;color:#fff}
.hl.rotschrift{color:#d0021b}
/* Fotos */
figure{position:relative;overflow:hidden;background:#222}
.foto{width:100%;height:100%;background:#333 center/cover no-repeat}
.foto.leer{background:repeating-linear-gradient(-45deg,var(--a) 0 6mm,var(--b) 6mm 12mm);display:flex;align-items:center;justify-content:center}
.foto.leer .wort{color:#fff;font-size:22pt;opacity:.9;transform:rotate(-6deg);text-shadow:.8mm .8mm 0 rgba(0,0,0,.35)}
figcaption{position:absolute;left:0;right:0;bottom:0;background:rgba(0,0,0,.62);color:#fff;font:700 6.4pt "Roboto Condensed",Arial,sans-serif;padding:.8mm 2mm}
.stoerer{position:absolute;top:4mm;right:4mm;width:24mm;height:24mm;border-radius:50%;background:#ffd400;color:#d0021b;
 display:flex;align-items:center;justify-content:center;text-align:center;font-size:12pt;line-height:.95;transform:rotate(-12deg);
 box-shadow:.8mm .8mm 0 rgba(0,0,0,.35);padding:2mm}
/* Artikeltext */
.txt p{margin-bottom:1.4mm}
.txt p.lead{font-weight:700;font-size:9.2pt;line-height:1.3}
.txt p:last-child::after{content:" ■";color:#d0021b;font-size:7pt}
.quelle{font:700 6.6pt "Roboto Condensed",Arial,sans-serif;color:#777;text-transform:uppercase;margin-top:.6mm}
/* Titelseite */
.mast{display:flex;align-items:stretch;gap:4mm;border-bottom:1.6mm solid #111;padding-bottom:2.5mm}
.logo{background:#d0021b;color:#fff;width:46mm;height:30mm;display:flex;flex-direction:column;justify-content:center;align-items:center;
 font-size:23pt;line-height:.92;text-align:center}
.mastmid{flex:1;display:flex;flex-direction:column;justify-content:space-between}
.slogan{font-weight:900;color:#d0021b;font-size:9pt;letter-spacing:.6px}
.anrisse div{font-size:8pt;font-weight:700;padding:.5mm 0;border-bottom:.2mm solid #ddd;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.anrisse b{color:#d0021b;text-transform:uppercase;font-weight:900;margin-right:1.5mm}
.mastinfo{text-align:right;font-size:8pt;line-height:1.4;display:flex;flex-direction:column;justify-content:space-between}
.mastinfo b{font-size:10pt;white-space:nowrap}.preis{font-family:Anton,KnallerFett,Impact,sans-serif;font-size:13pt;color:#d0021b}
.aufm{margin-top:3mm}
.aufm h1{margin:1mm 0 3mm}
.aufmgrid{display:grid;grid-template-columns:1.55fr 1fr;gap:4mm;height:86mm}
.aufmgrid .txt{overflow:hidden;column-count:1}
.reihe{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;border-top:1.2mm solid #111;margin-top:3mm;padding-top:2.5mm;flex:1;min-height:0}
.reihe article{overflow:hidden;display:flex;flex-direction:column}
.reihe figure{height:25mm;margin-bottom:1.5mm;flex:0 0 auto}
.reihe h3{font-size:13pt;margin-bottom:1.2mm}
.reihe .txt{font-size:7.9pt;overflow:hidden;flex:1;min-height:0}
.seitehinweis{margin-top:1mm;flex:0 0 auto;font:900 7pt "Roboto Condensed",Arial,sans-serif;color:#d0021b;text-transform:uppercase}
.tfuss{display:grid;grid-template-columns:1.2fr 1fr;gap:4mm;margin-top:2.5mm;height:33mm}
.wbox{background:#ffd400;padding:2.5mm 3mm;position:relative;overflow:hidden}
.wbox .klein{font:900 7pt "Roboto Condensed",Arial,sans-serif;color:#d0021b;letter-spacing:.4px}
.wbox .H{font-size:14pt;margin:1mm 0}
.wbox p{font-size:7.8pt}
.inhalt{border:.5mm solid #111;padding:1.6mm 2.5mm;font:7.2pt "Roboto Condensed",Arial,sans-serif;overflow:hidden}
.inhalt b{display:block;font-family:Anton,KnallerFett,Impact,sans-serif;font-weight:400;font-size:9pt;margin-bottom:.5mm}
.inhalt div{display:flex;justify-content:space-between;gap:2mm;border-bottom:.2mm dotted #999;padding:.1mm 0;white-space:nowrap;overflow:hidden}
.inhalt div span{overflow:hidden;text-overflow:ellipsis}
.inhalt i{font-style:normal;font-weight:900;color:#d0021b}
/* Innenseiten */
.kopf{display:flex;align-items:center;gap:3mm;border-bottom:1mm solid #111;padding-bottom:1.5mm;margin-bottom:3mm;font:8pt "Roboto Condensed",Arial,sans-serif}
.kopf .rubrik{background:#d0021b;color:#fff;font-size:15pt;padding:.8mm 3mm}
.kopf .kname{font-family:Anton,KnallerFett,Impact,sans-serif;font-size:10pt;color:#d0021b;margin-left:auto}
.kopf .snr{font-size:15pt;background:#111;color:#fff;padding:.6mm 2.5mm}
.block{display:flex;flex-direction:column;min-height:0;overflow:hidden}
.block + .block{border-top:1.2mm solid #111;padding-top:2.5mm;margin-top:2.5mm}
.label{display:flex;align-items:center;gap:2mm;margin-bottom:1.6mm}
.label b{font-family:Anton,KnallerFett,Impact,sans-serif;font-weight:400;font-size:11pt;color:#fff;background:var(--k);padding:.4mm 2.5mm;text-transform:uppercase}
.label span{flex:1;height:.6mm;background:var(--k)}
.haupt h2{margin-bottom:2mm}
.voll{flex:1}
.voll .hauptgrid{display:grid;grid-template-columns:1.25fr 1fr;gap:4mm;height:88mm}
.voll .hauptgrid .txt{overflow:hidden}
.vier{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:3mm 5mm;margin-top:3mm;border-top:.4mm solid #111;padding-top:2.5mm;flex:1;min-height:0}
.vier article{overflow:hidden;display:grid;grid-template-columns:36mm 1fr;gap:3mm;border-bottom:.3mm solid #ccc;padding-bottom:2mm}
.vier article.ohne{grid-template-columns:1fr}
.vier figure{height:30mm}
.vier h3{font-size:12.5pt;margin-bottom:1mm}
.vier .txt{font-size:8pt;overflow:hidden}
.halb{flex:1}
.halb .hauptgrid{display:grid;grid-template-columns:1fr 1fr;gap:4mm;height:56mm}
.halb .txt{overflow:hidden}
.zwei{display:grid;grid-template-columns:1fr 1fr;gap:5mm;margin-top:3.5mm;flex:1;min-height:0;border-top:.3mm solid #999;padding-top:2mm}
.zwei article{overflow:hidden}
.zwei h3{font-size:11pt;margin-bottom:1mm}
.zwei .txt{font-size:7.9pt}
.drittel{flex:1}
.drittel .hauptgrid{display:grid;grid-template-columns:62mm 1fr;gap:4mm;flex:1;min-height:0}
.drittel figure{height:100%}
.drittel .txt{overflow:hidden;font-size:8pt}
.drittel h2{margin-bottom:1.5mm}
.drittel .nebenbei{font-size:7.6pt;border-top:.3mm dotted #999;margin-top:1.5mm;padding-top:1mm}
.drittel .nebenbei b{font-family:"Roboto Condensed",Arial,sans-serif;font-weight:900}
.leerbox{color:#888;font-style:italic;padding:3mm 0}
.impressum{font:6.4pt "Roboto Condensed",Arial,sans-serif;color:#777;border-top:.3mm solid #999;padding-top:1mm;margin-top:2mm}
/* Werkstatt-Seite */
.wtitel{margin:1mm 0 3mm}
.wgrid{display:grid;grid-template-columns:1.25fr 1fr;gap:5mm}
.ziel{font-weight:700;font-size:10pt;line-height:1.3;margin-bottom:3mm}
.badges{display:flex;gap:1.5mm;margin-bottom:3mm}
.badge{background:#111;color:#fff;font:700 7.5pt "Roboto Condensed",Arial,sans-serif;padding:.6mm 2mm}
.badge.g{background:#ffd400;color:#111}
.schritte{list-style:none;counter-reset:s;display:flex;flex-direction:column;gap:2mm;margin-bottom:3mm}
.schritte li{counter-increment:s;display:flex;gap:2.5mm;font-size:8.8pt;line-height:1.35}
.schritte li::before{content:counter(s);flex:0 0 6mm;height:6mm;background:#d0021b;color:#fff;font-family:Anton,KnallerFett,Impact,sans-serif;
 font-size:10pt;display:flex;align-items:center;justify-content:center}
.prompt{background:#111;color:#f5f5f5;padding:3mm;font:7.8pt/1.45 "JetBrains Mono",Consolas,monospace;white-space:pre-wrap;border-left:2mm solid #ffd400}
.prompt .pk{display:block;font:900 7pt "Roboto Condensed",Arial,sans-serif;color:#ffd400;text-transform:uppercase;margin-bottom:1mm}
.kasten{border:.6mm solid #111;margin-bottom:3mm}
.kasten .kk{background:#d0021b;color:#fff;font-family:Anton,KnallerFett,Impact,sans-serif;font-size:11pt;padding:.6mm 2.5mm;text-transform:uppercase}
.kasten .ki{padding:2.5mm}
.kasten h4{font-size:12pt;margin-bottom:1.2mm}
.kasten p{font-size:8.2pt;margin-bottom:1.5mm}
.kasten.gelb{background:#ffd400;border-color:#ffd400}.kasten.gelb .kk{background:#111}
.wnews{border-top:1.2mm solid #111;margin-top:4mm;padding-top:2.5mm;display:grid;grid-template-columns:repeat(3,1fr);gap:4mm;flex:1;min-height:0;overflow:hidden}
.wnews article{overflow:hidden}
.wnews h4{font-size:10.5pt;margin-bottom:1mm}
.wnews .txt{font-size:7.6pt}
/* Solar-Seite */
.sgrid{display:grid;grid-template-columns:1.15fr 1fr;gap:5mm;margin-top:2mm}
.halbspalte .txt{font-size:8.2pt}
.tab{width:100%;border-collapse:collapse;font:7.8pt "Roboto Condensed",Arial,sans-serif}
.tab th{text-align:left;background:#111;color:#fff;padding:.8mm 1.2mm;font-weight:700}
.tab td{padding:.9mm 1.2mm;border-bottom:.2mm solid #ccc}
.tab tr:nth-child(odd) td{background:#fffbe0}
.fussnote{font-size:6.6pt!important;color:#555;margin-top:1.5mm}
.deals{display:grid;grid-template-columns:repeat(3,1fr);gap:2.5mm 4mm}
.deals article{border-left:1.2mm solid #ffd400;padding-left:2mm;overflow:hidden;max-height:24mm}
.deals h4{font-size:9.5pt;margin-bottom:.6mm}
.deals p{font-size:7.4pt}
/* ===== Bild-Look: Serifen-Text, schwarze Schlagzeilen, wenig Farbe ===== */
body{font-family:"PT Serif",Georgia,"Times New Roman",serif;font-size:8pt;line-height:1.3}
.S{font-family:"PT Serif",Georgia,serif;font-weight:700;line-height:1.08;letter-spacing:-.1px}
.G{font-family:Anton,KnallerFett,Impact,sans-serif;font-weight:400;line-height:.9;letter-spacing:-.6px;color:#111;hyphens:manual}
.vier h3.H,.zwei h3.H,.deals h4.H,.wnews h4.H,.reihe h3.H{font-family:"PT Serif",Georgia,serif;font-weight:700;text-transform:none;line-height:1.1}
.kopf{border-bottom:none;padding-bottom:0;margin-bottom:2mm;align-items:flex-end}
.kopf .rubrik{background:none;color:#111;font-size:22pt;padding:0;line-height:.9}
.kopf .kname{font-size:9pt}
.kopf .snr{background:#d0021b}
.kopf + *{border-top:.9mm solid #111;padding-top:2mm}
.label b{background:#d0021b}.label span{background:#111;height:.4mm}
.dach{color:#d0021b}
/* Titelseite */
.tb{padding:6mm 7mm 5mm}
.tb-oben{display:grid;grid-template-columns:42mm 1fr 46mm;gap:3mm;height:46mm}
.tb-datum{font-size:7pt;font-weight:900;letter-spacing:.3px;margin-bottom:.8mm}
.tb-logo .logo{width:42mm;height:33mm;font-size:21pt}
.tb-slogan{font-size:6pt;font-weight:900;color:#d0021b;text-transform:uppercase;margin-top:.8mm;line-height:1.2}
.tb-portraits{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:27mm 1fr;gap:1.5mm}
.tb-portraits figure{height:27mm}
.tb-portraits figcaption{display:none}
.pcap{position:absolute;left:0;bottom:0;right:0;background:rgba(0,0,0,.7);color:#fff;font-size:5.8pt;font-weight:700;padding:.4mm 1mm;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tb-ph{grid-column:1/-1;font-size:13.5pt;overflow:hidden}
.sh{font-size:6.5pt;font-weight:900;color:#d0021b;text-transform:uppercase;white-space:nowrap}
.tb-anz{border:.5mm solid #111;padding:2mm 2.5mm;background:#fff6c9;display:flex;flex-direction:column;gap:1mm;overflow:hidden}
.anzk{font-size:6.5pt;font-weight:900;color:#fff;background:#d0021b;align-self:flex-start;padding:.2mm 1.5mm}
.tb-anz .H{font-size:12.5pt;text-transform:none;line-height:1}
.tb-anz p{font-size:7pt}.anzf{margin-top:auto;font-size:7.5pt;font-weight:900;color:#d0021b}
.tb-dach{margin-top:2.5mm;font-size:8.5pt;font-weight:900;color:#d0021b;text-transform:uppercase}
.tb .G{margin:.5mm 0 2.5mm}
.tb-haupt{display:grid;grid-template-columns:40mm 1fr 47mm;grid-template-rows:minmax(0,1fr);gap:3mm;flex:1;min-height:0;border-top:.9mm solid #111;padding-top:2mm}
.tb-links{border-right:.3mm solid #111;padding-right:2.5mm;overflow:hidden;display:flex;flex-direction:column;font-size:7.3pt;line-height:1.28}
.kn{margin-bottom:1.5mm;hyphens:auto;flex:0 1 auto;overflow:hidden;min-height:0}.kn b{color:#d0021b;font-family:"Roboto Condensed",Arial,sans-serif;font-weight:900}
.kn .kt{font-weight:700}.kn i{font-style:normal;font-family:"Roboto Condensed",Arial,sans-serif;font-weight:900;font-size:6.3pt;color:#d0021b}
.zitat{border-top:.9mm solid #d0021b;padding-top:1mm;margin:1mm 0 2mm;flex:0 0 auto}
.zq{font-family:Anton,KnallerFett,Impact,sans-serif;color:#d0021b;font-size:30pt;line-height:1;height:7mm;overflow:hidden}
.zitat .S{font-size:9.5pt}.zk{font-size:6pt;font-weight:900;margin-top:.8mm}
.kitipp{border:.4mm solid #111;padding:1.5mm;font-size:7pt;flex:0 0 auto}.kitipp .kk{background:#111;color:#fff;font-weight:900;font-size:7pt;
 margin:-1.5mm -1.5mm 1mm;padding:.4mm 1.5mm}.kitipp b{font-size:8pt}
.tb-mitte{display:flex;flex-direction:column;min-height:0;overflow:hidden}
.tb-mitte figure{height:74mm;flex:0 0 auto}
.tb-mitte .vs{font-size:12pt;margin:2mm 0 1.5mm}
.txt2{column-count:2;column-gap:3.5mm;column-rule:.2mm solid #bbb;font-size:7.9pt;overflow:hidden;flex:1;min-height:0}
.txt2 p{margin-bottom:1.2mm}.txt2 .quelle{break-inside:avoid}
.tb-rechts{border-left:.3mm solid #111;padding-left:2.5mm;overflow:hidden;display:flex;flex-direction:column;gap:2mm}
.rotlabel{background:#d0021b;color:#fff;font-size:7pt;font-weight:900;padding:.3mm 1.6mm;text-transform:uppercase}
.serie h3{font-size:13pt;margin:1mm 0 1.5mm}.serie .txt{font-size:7.5pt;margin-top:1.5mm}
.gv{display:grid;grid-template-columns:1fr 1fr;gap:1.5mm}
.gv>div{border:.4mm solid #111;font-size:6.6pt;line-height:1.2;overflow:hidden}
.gv .gk{color:#fff;font-weight:900;font-size:7pt;text-align:center;padding:.4mm 0}
.gv .gw .gk{background:#2e7d32}.gv .vl .gk{background:#c62828}
.gvb{height:16mm;background:#ddd center/cover}.gv p{padding:1mm}
.wetter{border:.4mm solid #111;font-family:"Roboto Condensed",Arial,sans-serif}
.wk{background:#0d47a1;color:#fff;font-weight:900;font-size:7pt;padding:.4mm 1.5mm}
.wt{display:grid;grid-template-columns:15mm 9mm 1fr auto auto;align-items:center;gap:1mm;font-size:7pt;padding:0 1.5mm;border-bottom:.2mm solid #ddd}
.wt b{font-size:10pt}.wt .mn{color:#666}.wt .rg{color:#1e88e5;font-size:6.5pt}
.solarz{font-size:6.8pt;padding:1mm 1.5mm;background:#fff6c9}
.tb-banner{background:#111;color:#fff;display:flex;align-items:center;gap:3mm;padding:2mm 3mm;margin-top:2mm}
.tb-banner .G{color:#fff;font-size:19pt;text-transform:uppercase;flex:1;line-height:.95}
.tb-banner .bd{color:#ffd400;font-weight:900;font-size:7.5pt;text-transform:uppercase}
.tb-banner .bs{background:#ffd400;color:#111;font-weight:900;font-size:8pt;padding:.5mm 2mm;white-space:nowrap}
.tb-inhalt{font-size:6.6pt;margin-top:1.2mm;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.tb-inhalt b{color:#d0021b}
"""


def hl(titel: str, stil: str, basis: float, tag: str = "h2") -> str:
    """Boulevard-Schlagzeile: schwarz, rot/gelb/schwarz hinterlegt oder rote Schrift."""
    gr = groesse(titel, basis)
    if stil in ("rot", "gelb", "schwarz"):
        return f'<{tag} class="H hl {stil}" style="{gr}"><span>{e(titel)}</span></{tag}>'
    return f'<{tag} class="H{" hl rotschrift" if stil == "rotschrift" else ""}" style="{gr}">{e(titel)}</{tag}>'


def text_html(a, woerter: int, lead=True) -> str:
    teile = []
    vs = vorspann(a)
    if lead and vs:
        teile.append(f'<p class="lead">{e(vs)}</p>')
    for p in artikel_absaetze(a, woerter):
        teile.append(f"<p>{e(p)}</p>")
    if not teile:
        teile.append('<p>Mehr dazu in der Originalmeldung.</p>')
    teile.append(f'<div class="quelle">Quelle: {e(a.get("quelle") or "")} · {e(zeit_text(a.get("datum")))}</div>')
    return '<div class="txt">' + "".join(teile) + "</div>"


def bild(a, r, stoerer: str = "") -> str:
    src = a.get("bild_druck") or (a["bild"] if a["bild"].startswith("data:") else "")
    st = f'<div class="stoerer H">{e(stoerer)}</div>' if stoerer else ""
    if src:
        return (f'<figure><div class="foto" style="background-image:url(\'{src}\')"></div>{st}'
                f'<figcaption>Foto: {e(a.get("quelle") or r["titel"])}</figcaption></figure>')
    k = farbe(r)
    return f'<figure><div class="foto leer" style="--a:{k};--b:#111"><span class="wort H">{e(r["dach"])}</span></div>{st}</figure>'


STILE = ["plain", "plain", "rot", "plain", "schwarz"]


def werkstatt_seite(seitennr, kopf, r_werk, news) -> str:
    ws, auto, tipp = werkstatt_heute()
    if not ws:
        return ""
    schritte = "".join(f"<li><span>{e(x)}</span></li>" for x in ws["schritte"])
    s = [f"""<div class="seite">{kopf}<div class="dach">Workshop des Tages · {e(ws['feature'])}</div>
{hl(ws['titel'], 'rot', 26, 'h1').replace('<h1 class="', '<h1 class="wtitel ')}
<div class="wgrid"><div><div class="badges"><span class="badge">{e(ws['level'])}</span><span class="badge g">Dauer: {e(ws['dauer'])}</span></div>
<p class="ziel">{e(ws['ziel'])}</p><ol class="schritte">{schritte}</ol>
<div class="prompt"><span class="pk">Dein Prompt für Claude Code (auf der Webseite zum Kopieren)</span>{e(ws['prompt'])}</div></div>
<div><div class="kasten"><div class="kk">Automatisierung des Tages</div><div class="ki"><h4 class="H">{e(auto['titel'])}</h4>
<p>{e(auto['idee'])}</p><p><b>Werkzeuge:</b> {e(auto['werkzeuge'])}</p>
<div class="prompt" style="border-left-color:#d0021b"><span class="pk">Prompt</span>{e(kuerzen(auto['prompt'], 240))}</div></div></div>
<div class="kasten gelb"><div class="kk">Profi-Tipp</div><div class="ki"><h4 class="H">{e(tipp[0])}</h4><p>{e(tipp[1])}</p></div></div></div></div>"""]
    if news:
        s.append('<section class="wnews">')
        for a in news[:3]:
            s.append(f'<article><div class="dach">{neu_tag(a)}{e(dachzeile(a, r_werk))}</div>'
                     f'<h4 class="H">{e(schlagzeile(a))}</h4>{text_html(a, 130)}</article>')
        s.append("</section>")
    s.append("</div>")
    return "\n".join(s)


SOLAR_BEISPIELE = [("1 Modul · 450 Wp · senkrecht nach Süden", 450, "Süd, senkrecht am Geländer"),
                   ("2 Module · 900 Wp · senkrecht nach Süden", 900, "Süd, senkrecht am Geländer"),
                   ("2 Module · 900 Wp · schräg nach Süden", 900, "Süd, schräg (ca. 30°)"),
                   ("4 Module · 1.800 Wp · Ost/West schräg", 1800, "Ost oder West, schräg")]


def solar_seite(seitennr, kopf, r_solar, solar_news, r_balkon, deals) -> str:
    tipp = werkstatt.solar_heute(dt.date.today().toordinal()) if werkstatt and hasattr(werkstatt, "solar_heute") else None
    s = [f"""<div class="seite">{kopf}<div class="dach">Sonnenstrom vom Balkon · Ideen, Angebote und Meldungen aus {e(REGION[0])} & Umgebung</div>
{hl("Sonne vom Balkon: So viel kannst du sparen", "gelb", 28, "h1")}<div class="sgrid">"""]
    if solar_news:
        a = solar_news[0]
        s.append(f"""<article class="haupt halbspalte"><div class="dach">{neu_tag(a)}{e(dachzeile(a, r_solar))}</div>
{hl(schlagzeile(a), 'plain', 16)}<figure style="height:46mm;margin:1.5mm 0 2mm">{bild(a, r_solar)[8:-9]}</figure>{text_html(a, 110)}</article>""")
    else:
        s.append("<div></div>")
    zeilen = ""
    if werkstatt and hasattr(werkstatt, "ersparnis"):
        for name, wp, ausr in SOLAR_BEISPIELE:
            kwh, selbst, euro, _ = werkstatt.ersparnis(wp, ausr)
            zeilen += f"<tr><td>{e(name)}</td><td>{kwh}</td><td>{selbst}</td><td><b>{euro} €</b></td></tr>"
    s.append(f"""<div>{f'<div class="kasten gelb"><div class="kk">Solar-Tipp des Tages</div><div class="ki"><h4 class="H">{e(tipp[0])}</h4><p>{e(tipp[1])}</p></div></div>' if tipp else ''}
<div class="kasten"><div class="kk">So viel bringt dein Balkonkraftwerk</div><div class="ki"><table class="tab">
<tr><th>Anlage</th><th>kWh/Jahr</th><th>selbst genutzt</th><th>Ersparnis/Jahr</th></tr>{zeilen}</table>
<p class="fussnote">Grobe Schätzung für den Raum Göppingen: ca. 1.000 kWh pro kWp bei optimaler Lage, 60 % Eigenverbrauch,
0,35 €/kWh. Deine Werte: kostenloser PVGIS-Rechner der EU oder der Rechner auf der Webseite.</p></div></div></div></div>""")
    s.append('<div class="label" style="--k:#eab308;margin-top:3mm"><b>Angebote des Tages</b><span></span></div><div class="deals">')
    for a in deals[:6]:
        s.append(f'<article><div class="dach">{neu_tag(a)}{e(a.get("quelle") or "")}</div>'
                 f'<h4 class="H">{e(a["titel"])}</h4><p>{e(" ".join(artikel_absaetze(a, 22)))}</p></article>')
    s.append("</div>")
    if len(solar_news) > 1:
        s.append('<div class="zwei" style="flex:1">')
        for a in solar_news[1:3]:
            s.append(f'<article><div class="dach">{neu_tag(a)}{e(dachzeile(a, r_solar))}</div>'
                     f'{hl(schlagzeile(a), "plain", 11, "h3")}{text_html(a, 60, lead=False)}</article>')
        s.append("</div>")
    s.append("</div>")
    return "\n".join(s)


def druck_bauen(ausgabe, demo=False) -> str:
    heute = dt.datetime.now()
    r_nach_id = {r["id"]: (r, l) for r, l in ausgabe}
    auf_r, auf = aufmacher_finden([(r, l) for r, l in ausgabe if r["id"] != "werkstatt"])
    benutzt = {id(auf)} if auf else set()
    nr = heute.timetuple().tm_yday
    seite_von = {}
    for n, ids in enumerate(PDF_SEITEN, start=2):
        for i in ids:
            seite_von[i] = n

    s = [f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><title>{e(ZEITUNG_NAME)} – {e(datum_heute())}</title>
{FONTS_DRUCK}<style>{DRUCK_CSS}</style></head><body>"""]

    # ── Titelseite – Aufbau wie eine echte Boulevard-Titelseite ──
    GEWINN = ["gewinnt", "sieg", "siegt", "rekord", "durchbruch", "triumph", "meister", "jubel", "rettet", "feiert",
              "kazandı", "galibiyet", "zafer", "bestpreis", "tiefstpreis", "erfolg", "geschafft"]
    VERLUST = ["verliert", "niederlage", "pleite", "rückruf", "streik", "absturz", "kaybetti", "mağlubiyet", "scheitert",
               "entlassen", "insolvenz", "panne", "ausfall", "sperre", "teurer", "warnt", "blamage", "aus für"]
    pool = []
    for r, l in ausgabe:
        if r["id"] == "werkstatt":
            continue
        pool += [(r, a) for a in l[:5] if a is not auf]
    pool.sort(key=lambda x: x[1]["punkte"] + (3 if x[1]["bild"] else 0), reverse=True)

    def nimm(bed, anzahl, rubriken_einmal=True):
        out, rub = [], set()
        for r, a in pool:
            if id(a) in benutzt or not bed(r, a) or (rubriken_einmal and r["id"] in rub):
                continue
            out.append((r, a)); benutzt.add(id(a)); rub.add(r["id"])
            if len(out) == anzahl:
                break
        return out

    def enthaelt(a, woerter):
        t = f" {schlagzeile(a)} {a['titel']} ".lower()
        return any(w in t for w in woerter)

    gewinner = nimm(lambda r, a: enthaelt(a, GEWINN), 1)
    verlierer = nimm(lambda r, a: enthaelt(a, VERLUST), 1)
    oben = nimm(lambda r, a: hat_foto(a), 3)
    rechts = nimm(lambda r, a: hat_foto(a), 1)
    banner = nimm(lambda r, a: True, 1)
    kurz = nimm(lambda r, a: True, 5, rubriken_einmal=False)
    ws, _, tipp = werkstatt_heute()
    seite = lambda r: seite_von.get(r["id"], "")

    def riesen_groesse(t):
        return max(30, min(84, 2650 / max(len(t), 1)))

    logo = "".join(f"<span>{e(w)}</span>" for w in ZEITUNG_NAME.replace("-", " ").split())
    s.append(f"""<div class="seite tb"><div class="tb-oben"><div class="tb-logo"><div class="tb-datum C">{e(datum_heute().upper())}</div>
<div class="logo H">{logo}</div><div class="tb-slogan C">Unabhängig · Persönlich · Nr. {nr} · 0,00 €{" · DEMO" if demo else ""}</div></div>
<div class="tb-portraits">""")
    for r, a in oben:
        s.append(f'<figure>{bild(a, r)[8:-9]}<span class="pcap C">{e(dachzeile(a, r))}</span></figure>')
    if oben:
        r0, a0 = oben[0]
        s.append(f'<div class="tb-ph S">{e(schlagzeile(a0))} <span class="sh C">Seite {seite(r0)}</span></div>')
    s.append("</div>")
    if ws:
        s.append(f"""<div class="tb-anz"><div class="anzk C">KI-WERKSTATT · SEITE {seite_von.get('werkstatt', 2)}</div>
<div class="H">{e(ws['titel'])}</div><p>{e(ws['level'])} · {e(ws['dauer'])} · mit fertigem Prompt für Claude Code</p>
<div class="anzf C">Heute selbst ausprobieren!</div></div>""")
    else:
        s.append("<div></div>")
    s.append("</div>")

    if auf:
        g = schlagzeile(auf)
        s.append(f'<div class="tb-dach C">{neu_tag(auf)}{e(dachzeile(auf, auf_r))}</div>'
                 f'<h1 class="G" style="font-size:{riesen_groesse(g):.0f}pt">{e(g)}</h1>')

    # Hauptzone: Kurzmeldungen | Aufmacher | Serie + Gewinner/Verlierer + Wetter
    s.append('<div class="tb-haupt"><aside class="tb-links">')
    for r, a in kurz:
        s.append(f'<p class="kn"><b>{e(dachzeile(a, r))}</b> – <span class="kt">{e(schlagzeile(a))}.</span> '
                 f'{e(" ".join(artikel_absaetze(a, 11)))} <i>S. {seite(r)}</i></p>')
    s.append(f'<div class="zitat"><div class="zq">“</div><div class="S">{e(SPRUECHE[heute.toordinal() % len(SPRUECHE)])}</div>'
             f'<div class="zk C">SPRUCH DES TAGES</div></div>')
    if tipp:
        s.append(f'<div class="kitipp"><div class="kk C">KI-TIPP</div><b>{e(tipp[0])}</b><p>{e(kuerzen(tipp[1], 110))}</p></div>')
    s.append("</aside>")
    if auf:
        s.append(f"""<section class="tb-mitte">{bild(auf, auf_r)}<div class="vs S">{e(vorspann(auf) or kuerzen(auf['teaser'], 140))}</div>
<div class="txt2">{''.join(f'<p>{e(p)}</p>' for p in artikel_absaetze(auf, 170))}
<div class="quelle">Quelle: {e(auf.get('quelle') or '')} · mehr auf Seite {seite(auf_r)}</div></div></section>""")
    s.append('<aside class="tb-rechts">')
    for r, a in rechts:
        s.append(f"""<div class="serie"><span class="rotlabel C">{e(r['dach'])}</span><h3 class="S">{e(schlagzeile(a))}</h3>
<figure style="height:34mm">{bild(a, r)[8:-9]}</figure><div class="txt">{''.join(f'<p>{e(p)}</p>' for p in artikel_absaetze(a, 45))}</div>
<div class="sh C">Seite {seite(r)}</div></div>""")
    if gewinner or verlierer:
        s.append('<div class="gv">')
        for titel, liste, kl in (("GEWINNER", gewinner, "gw"), ("VERLIERER", verlierer, "vl")):
            if liste:
                r, a = liste[0]
                th = f'<div class="gvb" style="background-image:url(\'{a.get("bild_druck") or a["bild"]}\')"></div>' if hat_foto(a) else ""
                s.append(f'<div class="{kl}"><div class="gk C">{titel}</div>{th}<p><b>{e(schlagzeile(a))}</b></p></div>')
            else:
                s.append("<div></div>")
        s.append("</div>")
    if WETTER:
        tage = ["Heute", "Morgen", "Übermorgen"]
        zeilen = "".join(f'<div class="wt"><span>{tage[i] if i < 3 else w["datum"].strftime("%a")}</span>{wetter_symbol(w["code"], "8mm")}'
                         f'<b>{w["max"]}°</b><span class="mn">{w["min"]}°</span><span class="rg">{w["regen"]} %</span></div>'
                         for i, w in enumerate(WETTER[:3]))
        h0 = WETTER[0]
        s.append(f"""<div class="wetter"><div class="wk C">WETTER {e(WOHNORT['name'].split()[0].upper())}</div>{zeilen}
<div class="solarz C">Heute {e(WETTER_TEXT.get(h0['code'], ''))}, {h0['sonne_h']:.1f} Std. Sonne.<br><b>Dein 800-W-Balkonkraftwerk: ca. {h0['solar_kwh']:.1f} kWh</b>
(≈ {h0['solar_kwh'] * 0.35:.2f} €)</div></div>""")
    s.append("</aside></div>")

    for r, a in banner:
        s.append(f'<div class="tb-banner"><span class="bd C">{e(r["dach"])}</span><span class="G">{e(schlagzeile(a))}</span>'
                 f'<span class="bs C">Seite {seite(r)}</span></div>')

    def seiten_name(ids):
        if ids == ["werkstatt"]:
            return "KI-Werkstatt"
        if ids == ["solar", "balkon"]:
            return "Solar & Angebote"
        return " · ".join(r_nach_id[i][0]["titel"] for i in ids if i in r_nach_id)

    s.append('<div class="tb-inhalt C"><b>HEUTE:</b> ' + " &nbsp;|&nbsp; ".join(
        f'<b>{n}</b> {e(seiten_name(ids))}' for n, ids in enumerate(PDF_SEITEN, start=2)) + "</div></div>")

    # ── Innenseiten ──
    for seitennr, ids in enumerate(PDF_SEITEN, start=2):
        erste = r_nach_id.get(ids[0], (None, None))[0]
        rubrik = "KI-WERKSTATT" if ids == ["werkstatt"] else "SOLAR" if ids == ["solar", "balkon"] else (erste["dach"] if erste else "")
        kopf = (f'<header class="kopf"><span class="rubrik H">{e(rubrik)}</span><span class="kname">{e(ZEITUNG_NAME)}</span>'
                f'<span>{e(datum_heute())}</span><span class="snr H">{seitennr}</span></header>')
        if ids == ["werkstatt"]:
            r_w, news = r_nach_id.get("werkstatt", (None, []))
            s.append(werkstatt_seite(seitennr, kopf, r_w, news))
            continue
        if ids == ["solar", "balkon"]:
            r_s, sn = r_nach_id.get("solar", ({"titel": "Solar", "dach": "SOLAR", "id": "solar"}, []))
            r_b, dl = r_nach_id.get("balkon", ({"titel": "Angebote", "dach": "SOLAR", "id": "balkon"}, []))
            s.append(solar_seite(seitennr, kopf, r_s, sn, r_b, dl))
            continue
        art = {1: "voll", 2: "halb"}.get(len(ids), "drittel")
        s.append(f'<div class="seite">{kopf}')
        for bi, rid in enumerate(ids):
            if rid not in r_nach_id:
                continue
            r, liste = r_nach_id[rid]
            liste = [a for a in liste if id(a) not in benutzt] or liste
            k = farbe(r) if r["id"] == "gs" else "#d0021b"
            label = f'<div class="label"><b>{e(r["titel"])}</b><span></span></div>' if art != "voll" else ""
            s.append(f'<section class="block {art}" style="--k:{k}">{label}')
            if not liste:
                s.append('<p class="leerbox">Heute keine Meldungen in dieser Rubrik.</p></section>')
                continue
            top = max(liste[:3], key=lambda a: a["punkte"] + (4 if a["bild"] else 0))
            rest = [a for a in liste if a is not top]
            stil = STILE[(seitennr + bi) % len(STILE)]
            if art == "voll":
                s.append(f"""<article class="haupt"><div class="dach">{neu_tag(top)}{e(dachzeile(top, r))}</div>
{hl(schlagzeile(top), stil, 34)}<div class="hauptgrid">{bild(top, r, stoerer='NEU!' if top.get('neu') else '')}{text_html(top, 170)}</div></article>
<div class="vier">""")
                for j, a in enumerate(rest[:4]):
                    mit = bool(a.get("bild_druck") or a["bild"].startswith("data:"))
                    s.append(f"""<article class="{'' if mit else 'ohne'}">{bild(a, r) if mit else ''}<div><div class="dach">{neu_tag(a)}{e(dachzeile(a, r))}</div>
{hl(schlagzeile(a), 'plain', 12.5, 'h3')}{text_html(a, 60 if mit else 85, lead=False)}</div></article>""")
                s.append("</div>")
            elif art == "halb":
                s.append(f"""<article class="haupt"><div class="dach">{neu_tag(top)}{e(dachzeile(top, r))}</div>
{hl(schlagzeile(top), stil, 21)}<div class="hauptgrid">{bild(top, r)}{text_html(top, 95)}</div></article><div class="zwei">""")
                for a in rest[:2]:
                    s.append(f'<article><div class="dach">{neu_tag(a)}{e(dachzeile(a, r))}</div>'
                             f'{hl(schlagzeile(a), "plain", 11, "h3")}{text_html(a, 50, lead=False)}</article>')
                s.append("</div>")
            else:
                neben = rest[0] if rest else None
                nb = (f'<div class="nebenbei"><b>{e(schlagzeile(neben))}.</b> {e(" ".join(artikel_absaetze(neben, 28)))}</div>'
                      if neben else "")
                s.append(f"""<article class="haupt" style="display:flex;flex-direction:column;flex:1;min-height:0">
<div class="dach">{neu_tag(top)}{e(dachzeile(top, r))}</div>{hl(schlagzeile(top), stil, 15)}
<div class="hauptgrid">{bild(top, r)}<div style="overflow:hidden">{text_html(top, 70)}{nb}</div></div></article>""")
            s.append("</section>")
        if seitennr == len(PDF_SEITEN) + 1:
            s.append(f'<div class="impressum">{e(ZEITUNG_NAME)} wird automatisch aus RSS-Feeds erstellt '
                     f'({heute.strftime("%d.%m.%Y, %H:%M Uhr")}). Artikel: von Claude (KI) in eigenen Worten aus den genannten Quellen zusammengefasst – '
                     f'Angaben ohne Gewähr, Fotos gehören den Quellen. Nur für den privaten Gebrauch.</div>')
        s.append("</div>")
    s.append("</body></html>")
    return "\n".join(s)


# ════════════════════════════════════════════════════════════════════
#  BLÄTTER-LESER – die PDF-Zeitung im Browser umblättern
# ════════════════════════════════════════════════════════════════════

def seiten_bilder(pdf_datei: Path, ordner: Path, dpi: int = 150):
    """Macht aus jeder PDF-Seite ein JPG (+ Vorschaubild). Nutzt PyMuPDF, sonst pdftoppm."""
    ziel = ordner / "seiten"
    if ziel.exists():
        shutil.rmtree(ziel)
    ziel.mkdir(parents=True)
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_datei))
        for n, seite in enumerate(doc, start=1):
            seite.get_pixmap(dpi=dpi).save(str(ziel / f"seite-{n:02d}.png"))
    except ImportError:
        if not shutil.which("pdftoppm"):
            print("⚠ Für den Blätter-Leser fehlt PyMuPDF (pip install pymupdf) oder pdftoppm.")
            return []
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf_datei), str(ziel / "roh")],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        for f in sorted(ziel.glob("roh-*.png")):
            f.rename(ziel / f"seite-{int(f.stem.split('-')[-1]):02d}.png")
    seiten, minis = [], []
    for f in sorted(ziel.glob("seite-*.png")):
        try:   # als JPG speichern (kleiner) + Vorschaubild
            from PIL import Image
            bild = Image.open(f).convert("RGB")
            gross = f.with_suffix(".jpg")
            bild.save(gross, "JPEG", quality=80, optimize=True)
            mini = f.with_name(f.stem.replace("seite", "mini") + ".jpg")
            bild.thumbnail((240, 340))
            bild.save(mini, "JPEG", quality=70)
            f.unlink()
            seiten.append(f"seiten/{gross.name}")
            minis.append(f"seiten/{mini.name}")
        except Exception:
            seiten.append(f"seiten/{f.name}")
            minis.append(f"seiten/{f.name}")
    return list(zip(seiten, minis))


LESER_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:#1b1d22;color:#fff;font:14px/1.4 Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;overflow:hidden}
a{color:inherit;text-decoration:none}
.leiste{position:fixed;left:0;right:0;top:0;height:54px;display:flex;align-items:center;gap:8px;padding:0 12px;
 background:rgba(20,22,27,.92);backdrop-filter:blur(10px);z-index:10;border-bottom:1px solid rgba(255,255,255,.08)}
.leiste .titel{font-weight:700;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.leiste .titel span{color:#ff4d5e}
.k{display:inline-flex;align-items:center;gap:6px;height:36px;padding:0 12px;border-radius:10px;background:rgba(255,255,255,.08);
 color:#fff;font-weight:600;font-size:13px;border:0;cursor:pointer;white-space:nowrap}
.k:hover{background:rgba(255,255,255,.16)}.k.rot{background:#d0021b}.k.rot:hover{background:#e3122c}
.buehne{position:fixed;top:54px;bottom:92px;left:0;right:0;display:flex;align-items:center;justify-content:center;perspective:2600px}
.buch{position:relative;display:flex}
.buch .s{position:relative;background:#fff center/contain no-repeat;box-shadow:0 20px 60px rgba(0,0,0,.55)}
.buch .s.leer{background:transparent;box-shadow:none}
.buch .s.links::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,0,0,0) 85%,rgba(0,0,0,.18));pointer-events:none}
.buch .s.rechts::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,0,0,.18),rgba(0,0,0,0) 15%);pointer-events:none}
.blatt{position:absolute;top:0;transform-style:preserve-3d;transform-origin:left center;transition:transform .75s cubic-bezier(.45,.05,.3,1);z-index:5}
.blatt .f,.blatt .b{position:absolute;inset:0;background:#fff center/contain no-repeat;backface-visibility:hidden;-webkit-backface-visibility:hidden}
.blatt .b{transform:rotateY(180deg)}
.blatt .f::after,.blatt .b::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(0,0,0,.22),rgba(0,0,0,0) 30%);opacity:.0;transition:opacity .75s}
.blatt.dreht .f::after,.blatt.dreht .b::after{opacity:1}
.pfeil{position:fixed;top:50%;transform:translateY(-50%);width:46px;height:46px;border-radius:50%;border:0;background:rgba(255,255,255,.12);
 color:#fff;font-size:22px;cursor:pointer;z-index:6}
.pfeil:hover{background:rgba(255,255,255,.25)}.pfeil.l{left:12px}.pfeil.r{right:12px}
.pfeil[disabled]{opacity:.2;cursor:default}
.leiste2{position:fixed;left:0;right:0;bottom:0;height:92px;background:rgba(20,22,27,.95);display:flex;align-items:center;gap:8px;
 padding:0 12px;overflow-x:auto;border-top:1px solid rgba(255,255,255,.08);scrollbar-width:thin}
.mini{flex:0 0 auto;width:52px;height:74px;background:#fff center/cover;border-radius:4px;opacity:.55;cursor:pointer;border:2px solid transparent;position:relative}
.mini.an{opacity:1;border-color:#ff4d5e}
.mini span{position:absolute;bottom:-1px;right:2px;font-size:10px;font-weight:700;color:#111;text-shadow:0 0 3px #fff}
.nr{font-variant-numeric:tabular-nums;color:#aab;font-size:13px;white-space:nowrap}
.lupe{position:fixed;inset:0;background:#111;z-index:30;overflow:auto;display:none;-webkit-overflow-scrolling:touch}
.lupe.an{display:block}
.lupe img{display:block;width:100%;max-width:1400px;margin:0 auto 12px}
.lupe .zu{position:fixed;top:12px;right:12px;z-index:31}
.hinweis{position:fixed;bottom:104px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.7);padding:8px 14px;border-radius:999px;font-size:12.5px;white-space:nowrap;
 transition:opacity .6s;pointer-events:none}
@media(max-width:640px){.hinweis{font-size:11px;bottom:90px}.leiste .k .t{display:none}.pfeil{display:none}.leiste2{height:80px}.buehne{bottom:80px}.mini{width:44px;height:62px}}
"""

LESER_JS = r"""
const P = SEITEN, M = MINIS, n = P.length;
const buch = document.querySelector('.buch'), nrEl = document.querySelector('.nr');
const L = document.querySelector('.pfeil.l'), R = document.querySelector('.pfeil.r');
P.forEach(u => { const i = new Image(); i.src = u; });
let doppel = false, v = 0, laeuft = false, W = 0, H = 0;
const ansicht = k => doppel ? (k === 0 ? [null, 0] : [2*k-1, 2*k < n ? 2*k : null]) : [k];
const anzahl = () => doppel ? Math.floor(n/2) + 1 : n;
const bg = (el, s) => { if (s === null || s === undefined) { el.classList.add('leer'); el.style.backgroundImage = 'none'; }
  else { el.classList.remove('leer'); el.style.backgroundImage = `url('${P[s]}')`; } };
function masse(){
  doppel = innerWidth > innerHeight && innerWidth >= 900;
  const b = document.querySelector('.buehne').getBoundingClientRect();
  const maxH = b.height - 24, maxW = (b.width - (innerWidth < 640 ? 16 : 130)) / (doppel ? 2 : 1);
  H = Math.min(maxH, maxW * 297/210); W = H * 210/297;
}
function bauen(){
  masse();
  buch.innerHTML = '';
  (doppel ? ['links','rechts'] : ['einzel']).forEach(c => { const d = document.createElement('div'); d.className = 's ' + c;
    d.style.width = W + 'px'; d.style.height = H + 'px'; buch.appendChild(d); });
  zeigen();
}
function zeigen(){
  const a = ansicht(v), s = buch.querySelectorAll('.s');
  a.forEach((x, i) => bg(s[i], x));
  const seiten = a.filter(x => x !== null);
  nrEl.textContent = `Seite ${seiten.map(x => x+1).join('–')} / ${n}`;
  document.querySelectorAll('.mini').forEach((m, i) => m.classList.toggle('an', seiten.includes(i)));
  const akt = document.querySelector('.mini.an'); if (akt) akt.scrollIntoView({inline:'center', block:'nearest', behavior:'smooth'});
  L.disabled = v === 0; R.disabled = v >= anzahl() - 1;
  history.replaceState(null, '', '#s' + (seiten[0] + 1));
}
function blatt(vorne, hinten, start, ende, fertig){
  const b = document.createElement('div'); b.className = 'blatt';
  b.style.width = W + 'px'; b.style.height = H + 'px'; b.style.left = doppel ? W + 'px' : '0px';
  b.innerHTML = '<div class="f"></div><div class="b"></div>';
  bg(b.querySelector('.f'), vorne); bg(b.querySelector('.b'), hinten);
  if (hinten === null) b.querySelector('.b').style.background = '#f4f1ea';
  b.style.transition = 'none'; b.style.transform = `rotateY(${start}deg)`;
  buch.appendChild(b); b.getBoundingClientRect();
  b.style.transition = ''; b.classList.add('dreht'); b.style.transform = `rotateY(${ende}deg)`;
  let ok = false; const zu = () => { if (ok) return; ok = true; fertig(); b.remove(); laeuft = false; };
  b.addEventListener('transitionend', zu); setTimeout(zu, 900);
}
function vor(){
  if (laeuft || v >= anzahl() - 1) return; laeuft = true;
  const alt = ansicht(v), neu = ansicht(v + 1), s = buch.querySelectorAll('.s');
  if (doppel){ bg(s[1], neu[1]); blatt(alt[1], neu[0], 0, -180, () => { v++; zeigen(); }); }
  else { bg(s[0], neu[0]); blatt(alt[0], null, 0, -180, () => { v++; zeigen(); }); }
}
function zurueck(){
  if (laeuft || v <= 0) return; laeuft = true;
  const alt = ansicht(v), neu = ansicht(v - 1), s = buch.querySelectorAll('.s');
  if (doppel){ bg(s[0], neu[0]); blatt(neu[1], alt[0], -180, 0, () => { v--; zeigen(); }); }
  else { blatt(neu[0], null, -180, 0, () => { v--; zeigen(); }); }
}
function springen(seite){ v = doppel ? Math.floor((seite + 1) / 2) : seite; zeigen(); }
R.onclick = vor; L.onclick = zurueck;
addEventListener('keydown', e => { if (e.key === 'ArrowRight' || e.key === ' ') vor(); if (e.key === 'ArrowLeft') zurueck();
  if (e.key === 'Escape') lupe(false); });
let x0 = null, y0 = null;
buch.addEventListener('touchstart', e => { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, {passive:true});
buch.addEventListener('touchend', e => { if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
  if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) (dx < 0 ? vor : zurueck)(); x0 = null; });
let ct; buch.addEventListener('click', e => { const r = buch.getBoundingClientRect(), rechts = e.clientX - r.left > r.width / 2;
  clearTimeout(ct); ct = setTimeout(() => (rechts ? vor : zurueck)(), 240); });
buch.addEventListener('dblclick', () => { clearTimeout(ct); lupe(true); });
document.querySelectorAll('.mini').forEach((m, i) => m.onclick = () => springen(i));
const LU = document.querySelector('.lupe');
function lupe(an){ if (an){ const a = ansicht(v).filter(x => x !== null);
  LU.querySelector('.bilder').innerHTML = a.map(x => `<img src="${P[x]}" alt="Seite ${x+1}">`).join(''); }
  LU.classList.toggle('an', an); }
document.querySelector('.lupeauf').onclick = () => lupe(true);
LU.querySelector('.zu').onclick = () => lupe(false);
let tw; addEventListener('resize', () => { clearTimeout(tw); tw = setTimeout(() => { const s = ansicht(v).find(x => x !== null) || 0; bauen(); springen(s); }, 150); });
const start = parseInt((location.hash.match(/s(\d+)/) || [])[1] || '1') - 1;
bauen(); if (start > 0) springen(Math.min(start, n - 1));
setTimeout(() => { const h = document.querySelector('.hinweis'); if (h) h.style.opacity = 0; }, 3500);
"""


def lesen_bauen(seiten, pdf_name: str, download_name: str) -> str:
    bilder = [s for s, _ in seiten]
    minis = "".join(f'<div class="mini" style="background-image:url(\'{e(m)}\')" title="Seite {i}"><span>{i}</span></div>'
                    for i, (_, m) in enumerate(seiten, start=1))
    js = LESER_JS.replace("SEITEN", json.dumps(bilder)).replace("MINIS", json.dumps([m for _, m in seiten]))
    return f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(ZEITUNG_NAME)} lesen – {e(datum_heute())}</title><style>{LESER_CSS}</style></head><body>
<div class="leiste"><a class="k" href="index.html" title="Zur Webseite">←<span class="t"> Webseite</span></a>
<div class="titel"><span>{e(ZEITUNG_NAME)}</span> · {e(datum_heute())}</div>
<button class="k lupeauf" title="Vergrößern">🔍<span class="t"> Zoom</span></button>
<a class="k" href="{e(pdf_name)}" target="_blank" rel="noopener" title="PDF im Browser öffnen">📄<span class="t"> PDF öffnen</span></a>
<a class="k rot" href="{e(pdf_name)}" download="{e(download_name)}" title="PDF herunterladen">⬇<span class="t"> Download</span></a></div>
<div class="buehne"><div class="buch"></div></div>
<button class="pfeil l" title="Zurück (←)">‹</button><button class="pfeil r" title="Weiter (→)">›</button>
<div class="leiste2"><span class="nr"></span>{minis}</div>
<div class="hinweis">Wischen oder tippen zum Umblättern · Doppeltipp = Zoom</div>
<div class="lupe"><button class="k rot zu">✕ Schließen</button><div class="bilder"></div></div>
<script>{js}</script></body></html>"""


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

    global WETTER
    try:
        WETTER = wetter_demo() if args.demo else wetter_holen()
    except Exception as ex:
        print(f"  Wetter nicht verfügbar: {type(ex).__name__}")
    if args.demo:
        ausgabe, fehler = demo_sammeln()
    else:
        ausgabe, fehler = zeitung_sammeln()
        anreichern(ausgabe)
        artikel_schreiben(ausgabe)

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
            seiten = seiten_bilder(pdf_tag, ordner)
            if seiten:
                (ordner / "lesen.html").write_text(
                    lesen_bauen(seiten, "zeitung.pdf", f"{ZEITUNG_NAME}_{tag}.pdf"), "utf-8")
                print(f"✔ Blätter-Leser -> {ordner / 'lesen.html'} ({len(seiten)} Seiten)")

    leser_ok = (ordner / "lesen.html").exists() and pdf_ok
    seite = html_bauen(ausgabe, fehler, demo=args.demo, pdf_name="zeitung.pdf" if pdf_ok else "",
                       leser=leser_ok, download_name=f"{ZEITUNG_NAME}_{tag}.pdf")
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
