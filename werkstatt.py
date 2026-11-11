# -*- coding: utf-8 -*-
"""
KI-WERKSTATT – Inhalte für die tägliche Rubrik in MORGEN-KNALLER.

Jeden Tag wird automatisch ein anderer Workshop, eine andere Automatisierungs-Idee
und ein anderer Profi-Tipp gezeigt. Eigene Einträge einfach unten ergänzen.

Grundlage: offizielle Claude-Code-Dokumentation (code.claude.com/docs).
"""

DOKU = "https://code.claude.com/docs/en/quickstart"

# ──────────────────────────────────────────────────────────────────────
#  WORKSHOPS – kleine Projekte, die man als Einsteiger mit Claude Code baut
# ──────────────────────────────────────────────────────────────────────
WORKSHOPS = [
    {"titel": "Start: Claude Code installieren und das erste Projekt anlegen",
     "level": "Einsteiger", "dauer": "15 Min", "feature": "Installation & erste Sitzung",
     "ziel": "Claude Code läuft auf deinem PC und hat dir seine erste Datei geschrieben.",
     "schritte": [
         "Windows: PowerShell öffnen und  irm https://claude.ai/install.ps1 | iex  eingeben (Mac/Linux: curl -fsSL https://claude.ai/install.sh | bash).",
         "Neues PowerShell-Fenster öffnen und mit  claude --version  prüfen, ob alles geklappt hat.",
         "Einen leeren Ordner anlegen, z. B. C:\\Projekte\\test, hineinwechseln (cd) und  claude  starten. Beim ersten Mal meldest du dich im Browser an.",
         "Den Prompt unten eingeben und zuschauen, wie Claude die Datei anlegt. Mit /help siehst du alle Befehle.",
     ],
     "prompt": "Erstelle mir eine einfache HTML-Seite index.html mit einer Begrüßung, dem heutigen Datum und einem Knopf, der einen zufälligen Motivationsspruch anzeigt. Erkläre mir danach in 3 Sätzen, was du gemacht hast.",
     "link": "https://code.claude.com/docs/en/quickstart"},

    {"titel": "CLAUDE.md: Claude dauerhaft erklären, wie du arbeitest",
     "level": "Einsteiger", "dauer": "10 Min", "feature": "CLAUDE.md & /init",
     "ziel": "Claude kennt bei jedem Start deine Regeln (Sprache, Stil, Ordner) und du musst sie nicht ständig wiederholen.",
     "schritte": [
         "In deinem Projektordner  claude  starten.",
         "/init eingeben – Claude schaut sich das Projekt an und schreibt eine erste CLAUDE.md.",
         "Die Datei öffnen und eigene Regeln ergänzen, z. B. „Antworte immer auf Deutsch“ oder „Kommentare im Code bitte einfach halten“.",
         "Faustregel aus der Doku: CLAUDE.md kurz halten (unter 200 Zeilen). Was Claude zweimal falsch macht, gehört hinein.",
     ],
     "prompt": "Ergänze meine CLAUDE.md um diese Regeln: Antworte auf Deutsch. Erkläre Änderungen kurz und für Einsteiger verständlich. Frag nach, bevor du Dateien löschst. Teste HTML-Seiten, indem du sie auf Fehler prüfst.",
     "link": "https://code.claude.com/docs/en/memory"},

    {"titel": "Tuya-Steckdose per Python-Skript schalten",
     "level": "Einsteiger+", "dauer": "45 Min", "feature": "Python-Skript mit Claude",
     "ziel": "Ein kleines Skript schaltet deine Smart-Life/Tuya-Steckdose im Heimnetz ein und aus – ohne App.",
     "schritte": [
         "Ordner  tuya-test  anlegen und dort  claude  starten.",
         "Claude bitten, die Python-Bibliothek tinytuya zu installieren und den Einrichtungs-Assistenten zu erklären (der holt die nötigen Geräteschlüssel).",
         "Den Prompt unten nutzen. Gerätenamen und IP-Adresse aus der Smart-Life-App/dem Router eintragen.",
         "Testen: Skript starten, Steckdose klickt. Danach kannst du es z. B. per Zeitplan automatisch laufen lassen.",
     ],
     "prompt": "Ich habe eine Tuya/Smart-Life-Steckdose. Schreibe mir ein Python-Skript mit tinytuya, das die Steckdose per Kommandozeile ein- und ausschaltet (python steckdose.py an / aus) und den aktuellen Zustand anzeigt. Erkläre mir Schritt für Schritt, wie ich die Geräte-ID und den Local Key bekomme.",
     "link": "https://github.com/jasonacox/tinytuya"},

    {"titel": "Eigenes Smart-Home-Dashboard als Webseite",
     "level": "Fortgeschritten", "dauer": "1–2 Std", "feature": "Mehrere Dateien, Plan-Modus",
     "ziel": "Eine Seite im Heimnetz zeigt deine Geräte als große Kacheln zum Antippen – perfekt fürs Tablet an der Wand.",
     "schritte": [
         "Im Projektordner  claude  starten und mit Shift+Tab in den Planungsmodus wechseln: Claude plant zuerst, ohne gleich Dateien zu ändern.",
         "Den Prompt eingeben und den Plan in Ruhe lesen. Passt er, Shift+Tab drücken und umsetzen lassen.",
         "Lokal starten (Claude sagt dir den Befehl) und am Handy über die IP-Adresse des PCs/Raspberry Pi öffnen.",
     ],
     "prompt": "Plane und baue ein Smart-Home-Dashboard: ein kleiner Python-Webserver (Flask) mit tinytuya im Hintergrund, eine moderne HTML-Seite mit großen Kacheln (Name, Symbol, an/aus), dunkles Design, für Handy und Tablet optimiert. Geräte sollen in einer config.json stehen. Zeig mir zuerst den Plan.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Downloads-Ordner automatisch aufräumen",
     "level": "Einsteiger", "dauer": "20 Min", "feature": "Skript + Windows-Aufgabenplanung",
     "ziel": "Jeden Abend sortiert ein Skript Bilder, PDFs, Videos und Installer in eigene Unterordner.",
     "schritte": [
         "Ordner  aufraeumen  anlegen, dort  claude  starten und den Prompt eingeben.",
         "Erst mit einem Testordner probieren (Claude kann dir einen mit Beispieldateien anlegen).",
         "Claude bitten, den Eintrag für die Windows-Aufgabenplanung zu erstellen – dann läuft es jeden Tag von allein.",
     ],
     "prompt": "Schreibe ein Python-Skript, das meinen Downloads-Ordner aufräumt: Bilder nach Bilder/, PDFs nach Dokumente/, Videos nach Videos/, .exe/.msi nach Installer/, alles älter als 60 Tage nach Archiv/JJJJ-MM/. Es soll nichts löschen, ein Protokoll schreiben und einen Testmodus (--nur-anzeigen) haben. Erstelle danach eine .bat-Datei und erkläre, wie ich sie täglich mit der Aufgabenplanung starte.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Handyfotos nach Datum sortieren und umbenennen",
     "level": "Einsteiger", "dauer": "20 Min", "feature": "Dateien in Massen bearbeiten",
     "ziel": "Tausende Fotos heißen danach  2026-11-11_14-32_Urlaub.jpg  und liegen in Jahres-/Monatsordnern.",
     "schritte": [
         "Eine KOPIE deines Fotoordners anlegen (immer erst an einer Kopie üben!).",
         "In dem Ordner  claude  starten und den Prompt eingeben.",
         "Claude zeigt zuerst eine Vorschau der neuen Namen. Erst wenn sie stimmt, „ja, umbenennen“ sagen.",
     ],
     "prompt": "Sortiere die Fotos in diesem Ordner: Lies das Aufnahmedatum aus den EXIF-Daten (sonst Dateidatum), benenne sie um in JJJJ-MM-TT_HH-MM.jpg und verschiebe sie in Ordner JJJJ/MM. Doppelte Fotos erkennen und in einen Ordner Duplikate/ legen. Zeig mir zuerst eine Vorschau der ersten 20 Änderungen.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Claude im Skript: Berichte mit  claude -p  automatisch schreiben",
     "level": "Fortgeschritten", "dauer": "30 Min", "feature": "Einmal-Befehl  claude -p",
     "ziel": "Claude arbeitet ohne Chatfenster: Ein Befehl liest eine Datei, schreibt eine Zusammenfassung und beendet sich.",
     "schritte": [
         "Im Terminal ausprobieren:  claude -p \"Fasse die Datei notizen.txt in 5 Stichpunkten zusammen\"",
         "Die Ausgabe in eine Datei umleiten:  ... > zusammenfassung.md",
         "Den Befehl in ein Skript packen und per Aufgabenplanung/cron täglich laufen lassen – z. B. für Protokolle, Notizen oder Feeds.",
     ],
     "prompt": "Schreibe mir eine PowerShell-Datei, die jeden Abend alle .txt-Dateien aus meinem Ordner Notizen sammelt, sie mit claude -p zu einer kurzen Tageszusammenfassung auf Deutsch verarbeitet und als Notizen/Zusammenfassung_DATUM.md speichert. Erkläre, wie ich sie in der Aufgabenplanung eintrage.",
     "link": "https://code.claude.com/docs/en/cli-reference"},

    {"titel": "Eigener Skill: dein Lieblings-Ablauf als /Befehl",
     "level": "Fortgeschritten", "dauer": "20 Min", "feature": "Skills",
     "ziel": "Statt jedes Mal denselben langen Prompt zu tippen, startest du ihn mit z. B.  /wochenbericht.",
     "schritte": [
         "Laut Doku gilt: Wenn du denselben Prompt immer wieder tippst, mach einen Skill daraus.",
         "Claude bitten, den Skill anzulegen (Prompt unten). Er landet als SKILL.md im Ordner .claude/skills/.",
         "Claude Code neu starten, / tippen – dein Befehl erscheint in der Liste.",
     ],
     "prompt": "Lege mir einen Claude-Code-Skill namens wochenbericht an. Er soll: alle Dateien ansehen, die ich diese Woche in diesem Projekt geändert habe, eine kurze Zusammenfassung auf Deutsch schreiben (Was ist neu? Was ist offen?) und sie als berichte/woche_DATUM.md speichern.",
     "link": "https://code.claude.com/docs/en/skills"},

    {"titel": "Hook: Benachrichtigung, wenn Claude fertig ist",
     "level": "Fortgeschritten", "dauer": "15 Min", "feature": "Hooks",
     "ziel": "Du musst nicht neben dem PC sitzen: Ist Claude fertig oder braucht eine Antwort, kommt ein Signal.",
     "schritte": [
         "Hooks sind laut Doku für Dinge gedacht, die JEDES Mal gleich passieren sollen – ohne dass Claude nachdenken muss.",
         "Claude den Prompt unten geben. Es richtet den Hook in den Einstellungen ein.",
         "Testen: eine längere Aufgabe starten, weggehen, auf das Signal warten.",
     ],
     "prompt": "Richte mir einen Claude-Code-Hook ein, der unter Windows einen Ton abspielt und eine Desktop-Benachrichtigung zeigt, sobald du fertig bist oder auf meine Eingabe wartest. Erkläre mir, in welcher Datei der Hook steht und wie ich ihn wieder abschalte.",
     "link": "https://code.claude.com/docs/en/hooks-guide"},

    {"titel": "Preiswächter: Bescheid sagen, wenn der Beamer günstiger wird",
     "level": "Einsteiger+", "dauer": "40 Min", "feature": "Web-Abfrage + Zeitplan",
     "ziel": "Ein Skript prüft täglich den Preis eines Produkts und schickt dir eine Nachricht, wenn er unter deinen Wunschpreis fällt.",
     "schritte": [
         "Ordner  preiswaechter  anlegen,  claude  starten, Prompt eingeben.",
         "Produkt-Links und Wunschpreise in eine Liste eintragen.",
         "Benachrichtigung wählen: E-Mail oder Telegram-Bot (Claude erklärt beides).",
         "Mit Aufgabenplanung/cron 1× täglich starten.",
     ],
     "prompt": "Baue einen Preiswächter in Python: Produkte stehen in produkte.json (Name, URL, Wunschpreis). Das Skript liest den aktuellen Preis von der Seite, speichert den Verlauf in einer CSV und schickt mir eine Telegram-Nachricht, wenn der Preis unter den Wunschpreis fällt. Erkläre mir, wie ich einen Telegram-Bot anlege.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Telegram-Bot: Galatasaray-News aufs Handy",
     "level": "Einsteiger+", "dauer": "45 Min", "feature": "Bot + Feeds",
     "ziel": "Jeden Morgen schickt dir dein eigener Bot die wichtigsten Galatasaray-Schlagzeilen.",
     "schritte": [
         "Bei Telegram mit @BotFather einen Bot anlegen und den Token notieren.",
         "Ordner  gs-bot  anlegen,  claude  starten, Prompt eingeben.",
         "Den Bot einmal manuell starten, dann per Zeitplan (z. B. 7 Uhr).",
     ],
     "prompt": "Schreibe einen Telegram-Bot in Python, der die RSS-Feeds https://www.fotomac.com.tr/rss/galatasaray.xml und https://www.aspor.com.tr/rss/galatasaray.xml liest und mir die 5 neuesten Schlagzeilen mit Link schickt. Schon gesendete Meldungen sollen nicht doppelt kommen. Token in einer .env-Datei.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Home-Assistant-Automationen schreiben lassen",
     "level": "Einsteiger", "dauer": "15 Min", "feature": "Konfiguration erklären & erzeugen",
     "ziel": "Statt YAML zu lernen beschreibst du, was passieren soll – Claude schreibt die Automation.",
     "schritte": [
         "In deinem Home-Assistant-Konfigordner (oder einer Kopie davon)  claude  starten.",
         "Den Prompt anpassen: Geräte so benennen, wie sie in Home Assistant heißen.",
         "Claude prüft die Datei auf Fehler. Danach in Home Assistant „Automationen neu laden“.",
     ],
     "prompt": "Schreibe mir Home-Assistant-Automationen in automations.yaml: 1) Wohnzimmerlicht 15 Minuten nach Sonnenuntergang an, 2) alle Steckdosen um 1 Uhr nachts aus, außer dem Router, 3) Benachrichtigung aufs Handy, wenn die Waschmaschinen-Steckdose länger als 5 Minuten unter 5 Watt liegt (= Wäsche fertig). Erkläre jede Automation kurz.",
     "link": "https://www.home-assistant.io/docs/automation/"},

    {"titel": "Unbekannten Code verstehen, bevor du ihn änderst",
     "level": "Einsteiger", "dauer": "10 Min", "feature": "Projekt erkunden",
     "ziel": "Du lädst ein Projekt von GitHub und Claude erklärt dir in einfachen Worten, wie es funktioniert.",
     "schritte": [
         "Projekt herunterladen (z. B. deine Zeitung: github.com/Postmen1971/zeitung) und im Ordner  claude  starten.",
         "Doku-Tipp: Lass Claude erst erkunden, bevor es etwas ändert.",
         "Fragen stellen wie: „Wo wird das PDF gebaut?“ oder „Wie füge ich eine neue Rubrik hinzu?“",
     ],
     "prompt": "Was macht dieses Projekt? Erkläre mir die Ordnerstruktur und die wichtigsten Dateien so, als wäre ich Einsteiger. Zeig mir danach, an welcher Stelle ich eine neue Rubrik hinzufügen würde – aber ändere noch nichts.",
     "link": "https://code.claude.com/docs/en/quickstart"},

    {"titel": "Fehler finden: Fehlermeldung rein, Lösung raus",
     "level": "Einsteiger", "dauer": "10 Min", "feature": "Debugging",
     "ziel": "Wenn ein Skript abstürzt, findet Claude die Ursache und erklärt sie dir.",
     "schritte": [
         "Die komplette Fehlermeldung kopieren (nicht nur die letzte Zeile).",
         "Doku-Tipp: konkret sein. Statt „repariere den Fehler“ lieber beschreiben, was passiert und was du erwartet hast.",
         "Claude den Fehler beheben lassen, danach erneut testen.",
     ],
     "prompt": "Wenn ich python zeitung.py --pdf starte, erscheint dieser Fehler: [FEHLERMELDUNG EINFÜGEN]. Erwartet hätte ich, dass ein PDF im Ordner ausgaben entsteht. Finde die Ursache, erkläre sie mir in 2 Sätzen und behebe sie.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Haushaltsbuch als App für Handy und PC",
     "level": "Einsteiger", "dauer": "30 Min", "feature": "Web-App in einer Datei",
     "ziel": "Eine einzige HTML-Datei, in die du Ausgaben einträgst – mit Monatsübersicht und Diagramm.",
     "schritte": [
         "Ordner anlegen,  claude  starten, Prompt eingeben.",
         "Die Datei im Browser öffnen und testen.",
         "Wünsche nachschieben: „Füge Kategorien hinzu“, „Mach das Diagramm bunter“, „Export als CSV“.",
     ],
     "prompt": "Baue eine Haushaltsbuch-App als einzelne HTML-Datei: Ausgaben mit Datum, Betrag, Kategorie und Notiz erfassen, Speicherung im Browser, Monatsübersicht mit Summe pro Kategorie, ein Balkendiagramm und CSV-Export. Modernes, dunkles Design, gut am Handy bedienbar.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Lernspiel für Kinder: Einmaleins-Rakete",
     "level": "Einsteiger", "dauer": "30 Min", "feature": "Spiel in HTML",
     "ziel": "Ein buntes Mathe-Spiel für die Grundschule, das im Browser läuft.",
     "schritte": [
         "Ordner anlegen,  claude  starten, Prompt eingeben.",
         "Mit den Kindern testen und ihre Wünsche als nächsten Prompt formulieren.",
         "Tipp: Mehrere kleine Wünsche nacheinander funktionieren besser als ein riesiger Prompt.",
     ],
     "prompt": "Baue ein Einmaleins-Spiel für Grundschulkinder als einzelne HTML-Datei: Eine Rakete fliegt bei jeder richtigen Antwort höher, bei 10 richtigen landet sie auf dem Mond (Animation + Jubel). Auswahl der Reihen 1–10, große Knöpfe, freundliche Farben, Punktestand und Highscore.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Excel-Arbeit automatisieren: CSV rein, fertiger Bericht raus",
     "level": "Einsteiger+", "dauer": "30 Min", "feature": "Daten verarbeiten",
     "ziel": "Ein Skript macht aus einer Export-Datei automatisch eine formatierte Excel-Auswertung.",
     "schritte": [
         "Eine Beispiel-CSV (ohne vertrauliche Daten!) in einen Ordner legen.",
         "claude  starten und die Spalten kurz beschreiben.",
         "Prompt eingeben, Ergebnis öffnen, nachbessern lassen.",
     ],
     "prompt": "In diesem Ordner liegt daten.csv. Schreibe ein Python-Skript, das daraus eine Excel-Datei mit drei Blättern macht: Rohdaten, Zusammenfassung pro Tag (Summe, Durchschnitt, Maximum) und ein Diagramm. Kopfzeilen fett, Spaltenbreiten passend. Erkläre mir, wie ich es nächstes Mal mit einer neuen CSV starte.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Raspberry Pi einrichten lassen: Schritt-für-Schritt-Plan",
     "level": "Einsteiger+", "dauer": "1 Std", "feature": "Claude als Einrichtungshelfer",
     "ziel": "Claude erstellt dir eine Checkliste und Skripte für Pi-hole, Home Assistant oder deine Zeitung auf dem Pi.",
     "schritte": [
         "Auf dem Pi (per SSH) Claude Code installieren:  curl -fsSL https://claude.ai/install.sh | bash",
         "Im Home-Ordner  claude  starten und den Prompt eingeben.",
         "Jeden Befehl, den Claude ausführen will, bestätigst du selbst – so lernst du nebenbei Linux.",
     ],
     "prompt": "Ich bin Linux-Einsteiger. Richte auf diesem Raspberry Pi meine Zeitung ein: Repository github.com/Postmen1971/zeitung klonen, Chromium für das PDF installieren, einen cron-Eintrag für 6:30 Uhr anlegen und einen kleinen Webserver, damit ich die Zeitung im Heimnetz am Handy öffnen kann. Erkläre jeden Befehl, bevor du ihn ausführst.",
     "link": "https://code.claude.com/docs/en/setup"},

    {"titel": "Deine Zeitung erweitern: neue Rubrik in 5 Minuten",
     "level": "Einsteiger", "dauer": "10 Min", "feature": "Bestehendes Projekt ändern",
     "ziel": "Du fügst MORGEN-KNALLER selbst eine neue Rubrik hinzu – z. B. Formel 1, Rezepte oder Angebote.",
     "schritte": [
         "Projekt klonen:  git clone https://github.com/Postmen1971/zeitung  und hineinwechseln.",
         "claude  starten, Prompt eingeben (Thema anpassen).",
         "Mit  python zeitung.py --pdf --oeffnen  testen, dann mit „committe und pushe die Änderung“ hochladen.",
     ],
     "prompt": "Füge dieser Zeitung eine neue Rubrik „Formel 1“ hinzu: passende RSS-Feeds suchen (deutsch), eigene Farbe, auf der Webseite nach der Bundesliga und im PDF auf der Seite mit Europas Top-Klubs. Teste es mit --demo --pdf und zeig mir, was du geändert hast.",
     "link": "https://code.claude.com/docs/en/quickstart"},

    {"titel": "Git ohne Angst: Änderungen speichern und zurückholen",
     "level": "Einsteiger", "dauer": "15 Min", "feature": "Git im Gespräch",
     "ziel": "Du sicherst jeden Zwischenstand und kannst Fehler jederzeit rückgängig machen.",
     "schritte": [
         "Im Projekt  claude  starten.",
         "Fragen wie „Welche Dateien habe ich geändert?“ oder „Committe meine Änderungen mit einer guten Beschreibung“.",
         "Wenn etwas kaputt ist: „Zeig mir die letzten 5 Commits“ und „Hol die Version von gestern zurück“.",
     ],
     "prompt": "Erkläre mir Git anhand dieses Projekts in einfachen Worten: Was ist ein Commit, ein Branch, ein Push? Lege dann einen neuen Branch „experiment“ an, damit ich gefahrlos ausprobieren kann, und zeig mir, wie ich zurück zum Hauptstand komme.",
     "link": "https://code.claude.com/docs/en/quickstart"},

    {"titel": "MCP: Claude mit anderen Diensten verbinden",
     "level": "Fortgeschritten", "dauer": "20 Min", "feature": "MCP-Server",
     "ziel": "Claude kann direkt auf einen Dienst zugreifen (z. B. GitHub, eine Datenbank oder den Browser), statt dass du Daten hin- und herkopierst.",
     "schritte": [
         "Doku-Faustregel: Wenn du ständig Daten aus einem Browser-Tab kopierst, den Claude nicht sieht, verbinde das System per MCP.",
         "In Claude Code fragen, welche MCP-Server es für deinen Dienst gibt und wie man sie einrichtet.",
         "Mit /mcp prüfst du, ob die Verbindung steht.",
     ],
     "prompt": "Ich möchte, dass du direkt auf meine GitHub-Repositories zugreifen kannst. Erkläre mir, welcher MCP-Server dafür geeignet ist, richte ihn für dieses Projekt ein und zeig mir mit /mcp, dass die Verbindung funktioniert.",
     "link": "https://code.claude.com/docs/en/mcp"},

    # ── Projekte rund um Tuya & Solar ──
    {"titel": "Balkonkraftwerk-Ertrag mit einer Tuya-Steckdose messen",
     "level": "Einsteiger+", "dauer": "45 Min", "feature": "Python-Skript + Diagramm",
     "ziel": "Eine Tuya-Steckdose mit Strommessung zwischen Balkonkraftwerk und Hausnetz zeigt dir täglich, wie viel Sonne du geerntet hast.",
     "schritte": [
         "Eine Tuya/Smart-Life-Steckdose MIT Leistungsmessung besorgen und das Balkonkraftwerk darüber anschließen (Herstellerangaben zur Belastbarkeit beachten).",
         "Ordner  solar-log  anlegen,  claude  starten, Prompt eingeben.",
         "Skript alle 5 Minuten per Aufgabenplanung/cron laufen lassen – am Abend zeigt die HTML-Seite dein Tagesdiagramm.",
     ],
     "prompt": "Schreibe ein Python-Skript mit tinytuya, das alle 5 Minuten die aktuelle Leistung (Watt) meiner Tuya-Steckdose am Balkonkraftwerk ausliest und in solar.csv speichert. Baue dazu eine HTML-Seite mit einem Tages- und Monatsdiagramm, den erzeugten kWh und der Ersparnis bei 0,35 €/kWh. Erkläre, wie ich es automatisch starte.",
     "link": "https://github.com/jasonacox/tinytuya"},

    {"titel": "Solar-Prognose: Wann lohnt sich heute die Waschmaschine?",
     "level": "Einsteiger+", "dauer": "40 Min", "feature": "Wetter-API + Telegram",
     "ziel": "Jeden Morgen bekommst du eine Nachricht: „Heute 11–15 Uhr viel Sonne – Waschmaschine und Spülmaschine dann starten.“",
     "schritte": [
         "Ordner  solarprognose  anlegen,  claude  starten.",
         "Den Prompt eingeben – die kostenlose Wetter-Schnittstelle Open-Meteo braucht keinen Schlüssel.",
         "Bot-Token bei Telegram (@BotFather) holen, Skript täglich um 7 Uhr starten.",
     ],
     "prompt": "Schreibe ein Python-Skript, das über die kostenlose Open-Meteo-API die stündliche Sonneneinstrahlung für Waiblingen holt, für mein 800-W-Balkonkraftwerk (Südbalkon) die erwartete Leistung pro Stunde grob schätzt und mir per Telegram die 3 besten Stunden für Waschmaschine/Spülmaschine schickt. Erkläre die Schätzung in einfachen Worten.",
     "link": "https://open-meteo.com/"},

    {"titel": "Überschuss nutzen: Steckdose schaltet bei Sonnenstrom",
     "level": "Fortgeschritten", "dauer": "1 Std", "feature": "Automatisierung mit Regeln",
     "ziel": "Liefert das Balkonkraftwerk mehr als dein Haus gerade braucht, schaltet eine Tuya-Steckdose z. B. das E-Bike- oder Akku-Ladegerät ein.",
     "schritte": [
         "Du brauchst eine Messung am Balkonkraftwerk (Tuya-Steckdose) und – ideal – einen Lesekopf am Stromzähler.",
         "Claude mit dem Prompt eine Regel bauen lassen: einschalten ab X Watt Überschuss, ausschalten bei Wolken (mit Verzögerung, damit es nicht ständig klickt).",
         "Erst mit einer Lampe testen, dann mit dem Ladegerät.",
     ],
     "prompt": "Baue mir eine Home-Assistant-Automation (oder ein Python-Skript mit tinytuya): Wenn mein Balkonkraftwerk 10 Minuten lang mehr als 300 W liefert, schalte die Steckdose „Ladegerät“ ein; fällt die Leistung 10 Minuten unter 150 W, wieder aus. Höchstens 4 Schaltungen pro Stunde. Erkläre jede Zeile.",
     "link": "https://www.home-assistant.io/docs/automation/"},

    {"titel": "Zählerstand per Handyfoto: Claude liest ab",
     "level": "Einsteiger", "dauer": "15 Min", "feature": "Bilder verstehen",
     "ziel": "Du fotografierst einmal pro Woche den Stromzähler – Claude liest den Stand ab und führt deine Verbrauchstabelle.",
     "schritte": [
         "Fotos der Zähler in einen Ordner  zaehler  legen (Dateiname egal).",
         "claude  im Ordner starten – Claude Code kann Bilder ansehen.",
         "Prompt eingeben. Jede Woche einfach neues Foto dazulegen und „aktualisiere die Tabelle“ sagen.",
     ],
     "prompt": "In diesem Ordner liegen Fotos meines Stromzählers. Lies aus jedem Foto Datum (aus den Dateiinfos) und Zählerstand ab, trage alles in verbrauch.csv ein, berechne den Verbrauch pro Woche und erstelle eine HTML-Seite mit Diagramm. Wenn du einen Wert nicht sicher lesen kannst, frag mich.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Alle Tuya-Geräte auf einen Blick: Geräteliste & Backup",
     "level": "Einsteiger", "dauer": "20 Min", "feature": "Daten aufbereiten",
     "ziel": "Eine übersichtliche Seite mit allen Smart-Life-Geräten: Name, Raum, IP-Adresse, Typ – praktisch bei Router-Wechsel oder Problemen.",
     "schritte": [
         "Mit dem tinytuya-Assistenten deine Geräteliste (devices.json) erzeugen lassen.",
         "Im selben Ordner  claude  starten und den Prompt eingeben.",
         "Die Seite ausdrucken oder als PDF speichern – dein Smart-Home-Notfallzettel.",
     ],
     "prompt": "Lies die devices.json von tinytuya und baue daraus eine übersichtliche HTML-Seite: Tabelle mit Name, Gerätetyp, IP, Geräte-ID (Local Key nur verdeckt mit Klick zum Anzeigen), gruppiert nach Raum, mit Suchfeld. Dazu ein Skript, das täglich prüft, welche Geräte nicht erreichbar sind.",
     "link": "https://github.com/jasonacox/tinytuya"},

    {"titel": "Urlaubsmodus: Anwesenheit mit Licht simulieren",
     "level": "Einsteiger+", "dauer": "30 Min", "feature": "Zufalls-Zeitplan",
     "ziel": "Während du weg bist, gehen Lampen abends zu wechselnden Zeiten an und aus – wie wenn jemand zu Hause wäre.",
     "schritte": [
         "Ordner anlegen,  claude  starten, Prompt eingeben (Lampennamen anpassen).",
         "Einmal mit „Testlauf in 5 Minuten“ ausprobieren.",
         "Vor dem Urlaub einschalten, danach wieder aus – oder per Home Assistant mit Schalter.",
     ],
     "prompt": "Schreibe ein Python-Skript mit tinytuya für meinen Urlaub: Zwischen Sonnenuntergang und 23:30 Uhr sollen die Lampen Wohnzimmer, Küche und Flur zufällig, aber realistisch an- und ausgehen (nie alle gleichzeitig, jeden Abend anders). Mit Schalter --start und --stop und Protokolldatei.",
     "link": "https://github.com/jasonacox/tinytuya"},

    # ── Mehr Claude-Projekte für jeden Tag ──
    {"titel": "Stromrechnung & Verträge verstehen und vergleichen",
     "level": "Einsteiger", "dauer": "15 Min", "feature": "Dokumente auswerten",
     "ziel": "Claude liest deine Strom- oder Handyrechnung (PDF) und erklärt in einfachen Worten, was du zahlst und wo du sparen kannst.",
     "schritte": [
         "Rechnung als PDF in einen Ordner legen (persönliche Daten wie Kontonummer vorher schwärzen).",
         "claude  starten und Prompt eingeben.",
         "Nachfragen: „Wann kann ich kündigen?“ oder „Rechne mir 3.000 kWh mit 32 Cent aus.“",
     ],
     "prompt": "Lies die Stromrechnung in diesem Ordner und erkläre mir: Arbeitspreis, Grundpreis, Abschlag, Verbrauch im Vergleich zum Vorjahr, Kündigungsfrist. Rechne aus, was ich mit einem 800-W-Balkonkraftwerk bei geschätzt 500 kWh Eigenverbrauch pro Jahr sparen würde. Fasse alles in 5 Stichpunkten zusammen.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Familien-Wochenplaner als Handy-App",
     "level": "Einsteiger", "dauer": "40 Min", "feature": "Web-App + Speicher",
     "ziel": "Termine, Einkaufsliste und Essensplan der Familie in einer App, die auf jedem Handy im Browser läuft.",
     "schritte": [
         "Ordner anlegen,  claude  starten, Prompt eingeben.",
         "Ausprobieren, Wünsche nachschieben („Farben pro Person“, „Wochenansicht“).",
         "Online stellen: Claude erklärt dir GitHub Pages – genau wie bei deiner Zeitung.",
     ],
     "prompt": "Baue einen Familien-Wochenplaner als einzelne HTML-Datei: Wochenansicht mit Terminen pro Person (eigene Farben), gemeinsame Einkaufsliste zum Abhaken, Essensplan für 7 Tage. Speicherung im Browser, Export/Import als Datei, großes, kinderfreundliches Design, für Handy optimiert.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Eigene Chrome-Erweiterung: Preise in Euro pro kWh",
     "level": "Fortgeschritten", "dauer": "45 Min", "feature": "Browser-Erweiterung",
     "ziel": "Beim Surfen auf Shop-Seiten zeigt dir eine kleine Erweiterung bei Balkonkraftwerken automatisch „Preis pro Wp“ an.",
     "schritte": [
         "Ordner  erweiterung  anlegen,  claude  starten, Prompt eingeben.",
         "In Chrome chrome://extensions öffnen, Entwicklermodus an, „Entpackte Erweiterung laden“ und den Ordner wählen.",
         "Auf einer Shop-Seite testen und Claude Fehler beheben lassen.",
     ],
     "prompt": "Baue eine Chrome-Erweiterung (Manifest V3): Auf Produktseiten erkennt sie Preis und Modulleistung (Wp) eines Balkonkraftwerks im Seitentext und blendet oben rechts ein kleines Feld „x,xx € pro Wp“ ein. Nur lokal, keine Daten senden. Erkläre mir die Installation.",
     "link": "https://code.claude.com/docs/en/common-workflows"},

    {"titel": "Vorlesen lassen: Zeitung als Podcast für die Fahrt",
     "level": "Fortgeschritten", "dauer": "45 Min", "feature": "claude -p + Sprachausgabe",
     "ziel": "Jeden Morgen wird aus deiner MORGEN-KNALLER-Zeitung eine 5-Minuten-Audiodatei für das Auto.",
     "schritte": [
         "Repository deiner Zeitung klonen und  claude  starten.",
         "Prompt eingeben – Claude baut einen zusätzlichen Schritt in den GitHub-Workflow.",
         "Die MP3 erscheint neben dem PDF auf deiner Seite.",
     ],
     "prompt": "Erweitere diese Zeitung: Nach dem Bauen sollen die 8 wichtigsten Meldungen zu einem gesprochenen 5-Minuten-Nachrichtentext zusammengefasst und mit einer kostenlosen Text-zu-Sprache-Bibliothek als nachrichten.mp3 gespeichert werden. Auf der Webseite ein Abspielknopf. Teste lokal mit --demo.",
     "link": "https://code.claude.com/docs/en/cli-reference"},
]


# ──────────────────────────────────────────────────────────────────────
#  AUTOMATISIERUNGS-IDEEN – kurz, mit Prompt zum Loslegen
# ──────────────────────────────────────────────────────────────────────
AUTOMATISIERUNGEN = [
    {"titel": "Wäsche fertig? Nachricht aufs Handy",
     "idee": "Eine Tuya-Steckdose mit Strommessung erkennt, wann die Waschmaschine fertig ist (Verbrauch fällt) und schickt eine Push-Nachricht.",
     "werkzeuge": "Home Assistant oder tinytuya + Telegram",
     "prompt": "Schreibe ein Python-Skript, das alle 60 Sekunden den Verbrauch meiner Tuya-Steckdose liest (tinytuya) und mir eine Telegram-Nachricht schickt, wenn er nach einem Waschgang 5 Minuten lang unter 5 Watt liegt."},
    {"titel": "Standby-Killer um Mitternacht",
     "idee": "Fernseher, Beamer, Konsole und Soundbar hängen an Smart-Steckdosen – nachts gehen sie automatisch aus und sparen Strom.",
     "werkzeuge": "Smart-Life-App (Szenen) oder Home Assistant",
     "prompt": "Erstelle mir eine Home-Assistant-Automation, die um 0:30 Uhr die Steckdosen „TV“, „Beamer“ und „Konsole“ ausschaltet – aber nur, wenn der Fernseher seit 20 Minuten weniger als 15 Watt verbraucht."},
    {"titel": "Kinoabend mit einem Knopf",
     "idee": "Ein Tipp: Licht dimmt auf 20 %, Beamer und Soundbar gehen an, Rollladen runter.",
     "werkzeuge": "Home Assistant Szene + Tuya-Geräte",
     "prompt": "Schreibe eine Home-Assistant-Szene „Kinoabend“ und ein Skript, das sie per Knopf auf meinem Dashboard startet: Wohnzimmerlicht 20 %, Steckdosen Beamer und Soundbar an, nach 2 Stunden ohne Bewegung alles wieder aus."},
    {"titel": "Morgen-Briefing vorlesen lassen",
     "idee": "Dein Rechner erstellt morgens aus Wetter, Terminen und den Zeitungs-Schlagzeilen ein kurzes Briefing als Audiodatei.",
     "werkzeuge": "Python + claude -p + Text-zu-Sprache",
     "prompt": "Baue ein Skript, das die 5 wichtigsten Schlagzeilen aus postmen1971.github.io/zeitung holt, mit claude -p ein 1-Minuten-Briefing auf Deutsch schreibt und es mit einer Text-zu-Sprache-Bibliothek als MP3 speichert."},
    {"titel": "Rechnungen automatisch einsortieren",
     "idee": "PDF-Rechnungen aus dem Download-Ordner werden erkannt, nach Firma und Datum umbenannt und in Jahresordner verschoben.",
     "werkzeuge": "Python (PDF lesen) + Aufgabenplanung",
     "prompt": "Schreibe ein Skript, das PDFs in Downloads öffnet, Rechnungsdatum, Firma und Betrag erkennt, die Datei in JJJJ-MM-TT_Firma_Betrag.pdf umbenennt, nach Rechnungen/JJJJ verschiebt und alles in rechnungen.csv einträgt."},
    {"titel": "Website-Wächter",
     "idee": "Eine Seite (z. B. Ticket-Verkauf, Termin-Buchung, Vereins-News) wird regelmäßig geprüft – ändert sich etwas, kommt eine Nachricht.",
     "werkzeuge": "Python + cron/Aufgabenplanung + Telegram",
     "prompt": "Schreibe ein Skript, das alle 30 Minuten eine Webseite lädt, nur den Bereich mit einer bestimmten Überschrift vergleicht und mir per Telegram den neuen Text schickt, wenn er sich geändert hat."},
    {"titel": "Backup auf USB-Stick beim Einstecken",
     "idee": "Sobald dein Backup-Stick steckt, werden Dokumente und Fotos gesichert – nur neue und geänderte Dateien.",
     "werkzeuge": "PowerShell/robocopy + Aufgabenplanung",
     "prompt": "Erstelle mir ein PowerShell-Skript mit robocopy, das Dokumente und Bilder auf das Laufwerk mit dem Namen BACKUP spiegelt, ein Protokoll schreibt und mich am Ende mit einer Meldung informiert. Erkläre, wie es automatisch startet, wenn der Stick eingesteckt wird."},
    {"titel": "Fire-TV-Senderliste täglich prüfen",
     "idee": "Ein Skript testet jeden Morgen, welche Streams deiner M3U-Liste erreichbar sind, und baut eine bereinigte Liste.",
     "werkzeuge": "Python + GitHub Actions",
     "prompt": "Schreibe ein Python-Skript, das eine M3U-Liste einliest, jeden Stream kurz anfragt (Timeout 5 s), tote Sender aussortiert und eine neue M3U-Datei plus Bericht schreibt. Richte es als täglichen GitHub-Actions-Workflow ein."},
    {"titel": "Termine aus E-Mails in den Kalender",
     "idee": "Bestätigungsmails (Arzt, Werkstatt, Elternabend) werden erkannt und als Kalendertermin vorgeschlagen.",
     "werkzeuge": "Claude mit Gmail-/Kalender-Verbindung",
     "prompt": "Durchsuche meine E-Mails der letzten 7 Tage nach Terminbestätigungen und schlage mir für jede einen Kalendereintrag vor (Titel, Datum, Uhrzeit, Ort). Trage erst ein, wenn ich bestätige."},
    {"titel": "Wöchentlicher Smart-Home-Bericht",
     "idee": "Jeden Sonntag eine Übersicht: Stromverbrauch pro Steckdose, Geräte die offline waren, Auffälligkeiten.",
     "werkzeuge": "Home Assistant Verlauf + claude -p",
     "prompt": "Schreibe ein Skript, das aus Home Assistant den Stromverbrauch aller Steckdosen der letzten Woche holt, die Top-3-Verbraucher und Auffälligkeiten findet und mit claude -p einen kurzen Bericht auf Deutsch erstellt."},

    # ── Tuya-Ideen, wie sie Privatleute im Alltag nutzen ──
    {"titel": "Kaffeemaschine vorheizen per Wecker",
     "idee": "Die Siebträger- oder Filtermaschine hängt an einer Tuya-Steckdose und geht 15 Minuten vor dem Handywecker an – an Wochenenden später.",
     "werkzeuge": "Smart-Life-Zeitplan oder Home Assistant mit Handy-Wecker",
     "prompt": "Erstelle eine Home-Assistant-Automation: Die Steckdose „Kaffeemaschine“ schaltet 15 Minuten vor meinem nächsten Handy-Wecker ein und nach 45 Minuten automatisch aus. Am Wochenende nur, wenn der Wecker vor 10 Uhr klingelt."},
    {"titel": "Gefrierschrank-Wächter",
     "idee": "Ein günstiger Tuya-Temperatursensor im Gefrierschrank meldet, wenn es wärmer als −12 °C wird oder die Tür offen stand.",
     "werkzeuge": "Tuya-Zigbee-Temperatursensor + Smart-Life-Benachrichtigung",
     "prompt": "Erkläre mir Schritt für Schritt, wie ich in der Smart-Life-App eine Automation anlege, die mir eine Nachricht schickt, wenn mein Tuya-Temperatursensor im Gefrierschrank 10 Minuten lang über −12 °C misst. Und wie ich das zusätzlich in Home Assistant mit einem Verlaufsdiagramm sehe."},
    {"titel": "Lüften-Erinnerung gegen Schimmel",
     "idee": "Tuya-Hygrometer in Bad und Schlafzimmer: Steigt die Luftfeuchte über 65 %, blinkt eine Lampe kurz oder das Handy erinnert ans Lüften.",
     "werkzeuge": "Tuya-Temperatur/Feuchte-Sensor + Smart-Life-Szene",
     "prompt": "Baue eine Home-Assistant-Automation: Wenn die Luftfeuchte im Bad 15 Minuten über 65 % liegt, schick mir eine Nachricht „Bitte lüften“ und lass die Flurlampe zweimal kurz blinken – höchstens einmal pro Stunde, nachts nicht."},
    {"titel": "Briefkasten-Melder",
     "idee": "Ein Tuya-Tür/Fenster-Kontakt an der Briefkastenklappe meldet: „Post ist da!“ – mit Sperre, damit nicht jede Werbung dreimal piept.",
     "werkzeuge": "Tuya-Zigbee-Türkontakt + Smart-Life",
     "prompt": "Erstelle eine Automation für meinen Tuya-Türkontakt am Briefkasten: Beim Öffnen eine Handy-Nachricht „Post ist da“, danach 2 Stunden keine weitere Meldung. Zusätzlich ein Zähler, wie oft diese Woche Post kam."},
    {"titel": "Kinder-Gute-Nacht-Licht",
     "idee": "Um 19:30 dimmt das Kinderzimmerlicht langsam auf warmes Orange, um 20:15 aus – das Nachtlicht bleibt an. Klappt mit fast jeder Tuya-Lampe.",
     "werkzeuge": "Tuya-RGB-Lampe + Smart-Life-Szene",
     "prompt": "Schreibe mir eine Home-Assistant-Automation „Gute Nacht Kinderzimmer“: 19:30 Uhr Licht in 15 Minuten von 70 % Warmweiß auf 20 % Orange dimmen, 20:15 Uhr aus, Nachtlicht-Steckdose an. Am Freitag und Samstag 1 Stunde später."},
    {"titel": "Heizkörper runter, wenn das Fenster offen ist",
     "idee": "Tuya-Heizkörperthermostat plus Fensterkontakt: Fenster auf → Heizung aus, Fenster zu → zurück auf die alte Temperatur.",
     "werkzeuge": "Tuya-Zigbee-Thermostat + Fensterkontakt",
     "prompt": "Erstelle eine Home-Assistant-Automation: Wenn der Fensterkontakt im Schlafzimmer länger als 1 Minute offen ist, setze das Tuya-Thermostat auf 7 °C und merke dir die alte Temperatur; wird das Fenster geschlossen, stelle die alte Temperatur wieder her."},
    {"titel": "Balkonkraftwerk-Tagesbericht aufs Handy",
     "idee": "Jeden Abend um 21 Uhr: „Heute 3,1 kWh Sonnenstrom – gespart: ca. 1,09 €. Monat bisher: 41 kWh.“",
     "werkzeuge": "Tuya-Messsteckdose + Python oder Home Assistant",
     "prompt": "Baue mir ein Skript, das jeden Abend die heute erzeugte Energie meines Balkonkraftwerks aus der Tuya-Messsteckdose liest und mir per Telegram eine Nachricht mit kWh, Ersparnis (0,35 €/kWh), Monatssumme und dem besten Tag des Monats schickt."},
]


# ──────────────────────────────────────────────────────────────────────
#  PROFI-TIPPS – kurz und aus der offiziellen Doku
# ──────────────────────────────────────────────────────────────────────
TIPPS = [
    ("Sei konkret", "Statt „repariere den Fehler“ besser: „Repariere den Login-Fehler, bei dem nach falschem Passwort eine leere Seite kommt.“ Je genauer, desto besser das Ergebnis."),
    ("Große Aufgaben in Schritte teilen", "Nummeriere deine Wünsche: 1. Datenbank anlegen, 2. Schnittstelle bauen, 3. Webseite dazu. Claude arbeitet sie der Reihe nach ab."),
    ("Erst erkunden, dann ändern", "Lass Claude zuerst das Projekt analysieren („analysiere die Ordnerstruktur“), bevor es Code schreibt. Das spart Fehlversuche."),
    ("Shift+Tab wechselt den Modus", "Mit Shift+Tab schaltest du um, wie selbstständig Claude arbeitet – z. B. erst planen lassen, dann umsetzen."),
    ("/clear für ein neues Thema", "Neues Thema? /clear leert das Gespräch. Claude ist dann wieder „frisch“ und verwechselt nichts mit der alten Aufgabe."),
    ("Weitermachen, wo du aufgehört hast", "claude -c setzt das letzte Gespräch im Ordner fort, claude -r lässt dich ein älteres auswählen."),
    ("Was zweimal schiefgeht, gehört in CLAUDE.md", "Macht Claude denselben Fehler zum zweiten Mal, schreib die Regel in die CLAUDE.md – dann gilt sie für jede Sitzung."),
    ("Wiederkehrende Prompts werden Skills", "Tippst du denselben Start-Prompt immer wieder, speichere ihn als Skill. Dann reicht /name."),
    ("Regeln, die IMMER gelten müssen: Hooks", "Eine Bitte in CLAUDE.md ist ein Wunsch, ein Hook ist eine Garantie – z. B. „nie die Datei .env bearbeiten“."),
    ("/ zeigt alles, was geht", "Tippe nur /, um alle Befehle und Skills zu sehen. Mit ↑ holst du frühere Eingaben zurück, Tab ergänzt Befehle."),
    ("Claude fragen, wie Claude funktioniert", "Du kannst direkt fragen: „Wie lege ich einen eigenen Skill an?“ oder „Was kann Claude Code?“ – es erklärt sich selbst."),
    ("Ohne Terminal geht's auch", "Claude Code gibt es auch als Desktop-App, im Browser unter claude.ai/code und in VS Code – praktisch für den Einstieg."),
    ("Kostenloser Kurs", "Auf academy.claude.com gibt es den Kurs „Claude Code 101“ – kostenlos und im eigenen Tempo."),
    ("Wie mit einem Kollegen reden", "Beschreib, was du erreichen willst und warum. Claude findet den Weg oft besser, wenn es das Ziel kennt."),
]


def heute(tag_nr: int):
    """Wählt für den Tag (z. B. Tag im Jahr) Workshop, Automatisierung und Tipp aus."""
    return (WORKSHOPS[tag_nr % len(WORKSHOPS)],
            AUTOMATISIERUNGEN[tag_nr % len(AUTOMATISIERUNGEN)],
            TIPPS[tag_nr % len(TIPPS)])


# ──────────────────────────────────────────────────────────────────────
#  SOLAR-ECKE – Balkonkraftwerk-Tipps und Ersparnis
#  (Regeln Stand 2026: 800 VA Wechselrichter, bis 2.000 Wp Module,
#   Eintrag im Marktstammdatenregister binnen eines Monats)
# ──────────────────────────────────────────────────────────────────────
SOLAR_TIPPS = [
    ("Die Regeln in einem Satz", "Bis 800 Watt Wechselrichter und bis 2.000 Wp Modulleistung gelten die einfachen Regeln: keine Anmeldung beim Netzbetreiber, aber Eintrag im Marktstammdatenregister innerhalb eines Monats."),
    ("Ausrichtung schlägt Größe", "Ein leicht schräg aufgestelltes Modul nach Süden bringt deutlich mehr als ein senkrechtes am Geländer. Wer nur senkrecht kann: lieber ein Modul mehr nehmen."),
    ("Ost + West statt nur Süd", "Je ein Modul nach Osten und Westen liefert morgens und abends Strom – genau dann, wenn viele zu Hause sind. Das erhöht den Eigenverbrauch."),
    ("Grundlast ist dein Freund", "Kühlschrank, Router, Gefrierschrank und Standby laufen den ganzen Tag. Diese Grundlast „frisst“ den Sonnenstrom am zuverlässigsten – miss sie mit einer Tuya-Steckdose."),
    ("Große Verbraucher mittags", "Waschmaschine, Spülmaschine und Trockner möglichst zwischen 11 und 15 Uhr starten – viele Geräte haben eine Startzeitvorwahl."),
    ("Speicher: erst rechnen, dann kaufen", "Ein Speicher lohnt sich vor allem, wenn mittags niemand zu Hause ist. Wichtig: Er muss im Marktstammdatenregister gesondert angemeldet werden."),
    ("Verschattung kostet viel", "Schon ein Schatten auf einem Teil des Moduls kann die Leistung stark senken. Prüfe vor dem Kauf zu verschiedenen Uhrzeiten, wann Sonne auf den Balkon fällt."),
    ("Vermieter fragen – aber mit Rückenwind", "Ein pauschales Verbot ist in der Regel nicht mehr möglich. Vermieter und Eigentümergemeinschaft dürfen aber bei Art und Befestigung mitreden – sauber planen und anfragen."),
    ("Ertrag selbst ausrechnen", "Der kostenlose PVGIS-Rechner der EU zeigt für deine Adresse, Neigung und Ausrichtung den erwarteten Jahresertrag – genauer als jede Faustregel."),
    ("Im Winter tief stellen", "Im Winter steht die Sonne flach. Wer die Neigung verstellen kann, holt mit steilerem Winkel (60–70°) mehr heraus."),
    ("Messen motiviert", "Eine Messsteckdose oder die App des Wechselrichters zeigt dir täglich, was du erzeugst. Wer sieht, wann Strom da ist, verbraucht ihn auch eher selbst."),
    ("Angebote richtig vergleichen", "Vergleiche den Preis pro Wp (Euro geteilt durch Modulleistung) und prüfe: Wechselrichter mit 800 W? Halterung dabei? Stecker und Kabellänge passend für deinen Balkon?"),
]

# Grobe Schätzung für den Raum Stuttgart/Rems-Murr: ca. 1.000 kWh pro kWp und Jahr bei optimaler Südausrichtung.
# Faktoren für typische Balkon-Montagen (Schätzwerte). Genauer: PVGIS-Rechner.
ERTRAG_PRO_KWP = 1000
AUSRICHTUNGEN = {"Süd, schräg (ca. 30°)": 1.0, "Süd, senkrecht am Geländer": 0.7,
                 "Ost oder West, schräg": 0.8, "Ost oder West, senkrecht": 0.55}


def ersparnis(wp: float, ausrichtung: str, eigenverbrauch: float = 0.6, preis: float = 0.35, kosten: float = 0.0):
    """Jahresertrag (kWh), selbst genutzte kWh, Ersparnis (€/Jahr) und Amortisation (Jahre)."""
    kwh = wp / 1000 * ERTRAG_PRO_KWP * AUSRICHTUNGEN.get(ausrichtung, 0.8)
    kwh = min(kwh, 800 / 1000 * 1300)        # 800-W-Wechselrichter begrenzt grob den Jahresertrag
    selbst = kwh * eigenverbrauch
    euro = selbst * preis
    return round(kwh), round(selbst), round(euro), (round(kosten / euro, 1) if kosten and euro else None)


def solar_heute(tag_nr: int):
    return SOLAR_TIPPS[tag_nr % len(SOLAR_TIPPS)]
