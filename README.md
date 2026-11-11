# 🗞️ MORGEN-KNALLER

Deine persönliche Tageszeitung im Boulevard-Look. Ein Python-Skript holt morgens RSS-Feeds zu deinen Themen, sortiert sie, wirft Doppelte raus, markiert Neues und baut daraus eine HTML-Zeitung.

**Rubriken:** Galatasaray · Fußball · Boxen · Neues von der KI · Die Welt heute · Forschung & Gentherapie · Technik & Erfindungen · Visionen

## Lokal starten

Es reicht Python 3.8 oder neuer, du musst nichts installieren.

```bash
python3 zeitung.py --oeffnen        # Zeitung bauen und im Browser öffnen
python3 zeitung.py --demo           # nur das Layout mit Platzhaltern ansehen
python3 zeitung.py --ausgabe ordner # in einen bestimmten Ordner schreiben
```

Das Ergebnis liegt in `ausgaben/zeitung_JJJJ-MM-TT.html` und `ausgaben/index.html`. In `index.html` steht immer die neueste Ausgabe.

## Jeden Morgen automatisch

**Variante A: GitHub Pages (ohne eigenen Rechner)**
Der Workflow `.github/workflows/zeitung.yml` baut die Zeitung jeden Morgen und stellt sie online.
Einmalig einrichten: **Settings → Pages → Source: „GitHub Actions“**. Danach unter **Actions → Morgen-Zeitung → Run workflow** einmal von Hand starten.
Die Zeitung ist dann unter `https://postmen1971.github.io/zeitung/` erreichbar und lässt sich auch am iPhone als Lesezeichen auf den Home-Bildschirm legen.

**Variante B: Raspberry Pi / Linux** (`crontab -e`)
```
30 6 * * *  cd ~/zeitung && python3 zeitung.py --ausgabe /var/www/html
```

**Variante C: Windows**
Lege in der Aufgabenplanung eine tägliche Aufgabe an. Programm: `python`, Argument: `zeitung.py --oeffnen`, Starten in: Ordner des Repos.

## Anpassen

Alles steht ganz oben in `zeitung.py` unter **EINSTELLUNGEN**:

| Einstellung | Wofür |
|---|---|
| `ZEITUNG_NAME`, `UNTERTITEL` | Name und Untertitel im Zeitungskopf |
| `RESSORTS` | Rubriken, Feeds und Stichwörter. `gnews("Suchbegriff", "de"/"tr"/"en")` macht aus jeder Google-News-Suche einen Feed |
| `FAVORITEN` | Lieblingswörter mit Bonuspunkten. Die Meldung mit den meisten Punkten wird der Aufmacher |
| `SPERRLISTE` | Wörter, bei denen eine Meldung ausgeblendet wird |
| `MAX_PRO_RESSORT`, `MAX_ALTER_STUNDEN` | wie viele Meldungen pro Rubrik und wie alt sie höchstens sein dürfen |

Alle Meldungen verlinken auf die Originalquelle.
