# 🗞️ MORGEN-KNALLER

Deine persönliche Tageszeitung im Boulevard-Look. Ein Python-Skript holt morgens RSS-Feeds zu deinen Themen, sortiert sie, wirft Doppelte raus, markiert Neues, sucht passende Fotos und baut daraus:

- eine **Webseite** (`index.html`) zum Lesen am Handy
- eine **PDF-Zeitung** (`zeitung.pdf`) mit Titelseite, Aufmacher-Foto und eigenen Seiten pro Rubrik

| Seite | Inhalt |
|---|---|
| 1 | Titelseite im Boulevard-Stil: Aufmacher mit Artikel, drei Top-Meldungen, Werkstatt-Hinweis, Inhaltsverzeichnis |
| 2 | **KI-Werkstatt:** Workshop des Tages, Automatisierung des Tages, Profi-Tipp, neue Anleitungen |
| 3 | Galatasaray |
| 4 | Bundesliga |
| 5 | Europas Top-Klubs · Nationalmannschaften · Boxen |
| 6 | Die Welt heute |
| 7 | Neues rund um Claude · Neues von der KI |
| 8 | Smart Home & Tuya · Smart-Home-Ideen aus der Community · Beamer & TV |
| 9 | **Solar:** Rechenbeispiele mit und ohne Speicher für Ebersbach/Göppingen, Solar-Tipp, Angebote, Meldungen aus der Region |
| 10 | Forschung & Gentherapie · Technik & Erfindungen · Visionen |

### Artikel schreibt Claude – alles auf Deutsch

Claude schreibt aus jeder Meldung einen eigenen deutschen Artikel. Englische und türkische Meldungen werden dabei übersetzt, auf der Webseite genauso wie im PDF. Die Originaltexte werden nur gelesen und nie abgedruckt. Dafür brauchst du **einen** der zwei Wege, jeweils als Secret unter **Settings → Secrets and variables → Actions → New repository secret**:

| Weg | Secret-Name | Kosten |
|---|---|---|
| **Über dein Claude-Abo** (Pro/Max …) | `CLAUDE_CODE_OAUTH_TOKEN` | läuft über dein Abo-Kontingent |
| Über die API | `ANTHROPIC_API_KEY` | Abrechnung pro Nutzung auf platform.claude.com |

So bekommst du das Abo-Token: Auf deinem PC Claude Code installieren, dann `claude setup-token` ausführen. Im Browser bestätigen, den angezeigten Token (beginnt mit `sk-ant-oat01-`) kopieren und als Secret `CLAUDE_CODE_OAUTH_TOKEN` eintragen. Das Token gilt etwa ein Jahr.

Ohne Secret funktioniert alles weiter, aber dann bleiben fremdsprachige Meldungen im Original. Fertige Artikel werden zwischengespeichert und nicht doppelt erzeugt.

### Blättern, öffnen, herunterladen

`lesen.html` zeigt die Zeitung zum Umblättern: wischen, tippen oder Pfeiltasten, am PC als Doppelseite. Dazu gibt es Zoom, eine Seitenübersicht, „PDF öffnen“ und „Download“.

### Region

Die Solar-Meldungen „aus deiner Nähe“ kommen aus den Orten in `REGION`, Wetter und Solar-Ertrag aus `WOHNORT` (beides oben in `zeitung.py`).

## Lokal starten

Es reicht Python 3.8 oder neuer, du musst nichts installieren.

```bash
python3 zeitung.py --oeffnen        # Webseite bauen und öffnen
python3 zeitung.py --pdf --oeffnen  # zusätzlich PDF-Zeitung bauen und öffnen
python3 zeitung.py --demo --pdf     # nur das Layout mit Platzhaltern ansehen
python3 zeitung.py --ausgabe ordner # in einen bestimmten Ordner schreiben
```

Das Ergebnis liegt in `ausgaben/`. In `index.html` und `zeitung.pdf` steht immer die neueste Ausgabe, daneben liegen die Ausgaben mit Datum.

Für das PDF braucht das Skript Chrome, Chromium oder Edge. Ist `pillow` installiert (`pip install pillow`), werden die Fotos verkleinert und das PDF bleibt klein. Wird der Browser nicht gefunden, gib den Pfad über die Umgebungsvariable `CHROME` an.

## Jeden Morgen automatisch

**Variante A: GitHub Pages (ohne eigenen Rechner)**
Der Workflow `.github/workflows/zeitung.yml` baut die Zeitung jeden Morgen und stellt sie online.
Einmalig einrichten: **Settings → Pages → Source: „GitHub Actions“**. Danach unter **Actions → Morgen-Zeitung → Run workflow** einmal von Hand starten.
Die Zeitung ist dann unter `https://postmen1971.github.io/zeitung/` erreichbar, das PDF unter `…/zeitung/zeitung.pdf`. Beides lässt sich am iPhone als Lesezeichen auf den Home-Bildschirm legen.

**Variante B: Raspberry Pi / Linux** (`crontab -e`)
```
30 6 * * *  cd ~/zeitung && python3 zeitung.py --pdf --ausgabe /var/www/html
```

**Variante C: Windows**
Lege in der Aufgabenplanung eine tägliche Aufgabe an. Programm: `python`, Argument: `zeitung.py --pdf --oeffnen`, Starten in: Ordner des Repos.

## Anpassen

Alles steht ganz oben in `zeitung.py` unter **EINSTELLUNGEN**:

| Einstellung | Wofür |
|---|---|
| `ZEITUNG_NAME`, `UNTERTITEL` | Name und Untertitel im Zeitungskopf |
| `RESSORTS` | Rubriken, Feeds und Stichwörter. `gnews("Suchbegriff", "de"/"tr"/"en")` macht aus jeder Google-News-Suche einen Feed |
| `FAVORITEN` | Lieblingswörter mit Bonuspunkten. Die Meldung mit den meisten Punkten wird der Aufmacher |
| `SPERRLISTE` | Wörter, bei denen eine Meldung ausgeblendet wird |
| `MAX_PRO_RESSORT`, `MAX_ALTER_STUNDEN` | wie viele Meldungen pro Rubrik und wie alt sie höchstens sein dürfen |
| `PDF_SEITEN` | welche Rubriken auf welcher PDF-Seite stehen |
| `FOTOS_SUCHEN` | fehlende Fotos von der Artikelseite holen |

Alle Meldungen verlinken auf die Originalquelle.
