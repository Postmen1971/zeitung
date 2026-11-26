# -*- coding: utf-8 -*-
"""
NINJA CREAMi SCOOP & SWIRL – Inhalte für die Rubrik in MORGEN-KNALLER.

Gerät: Ninja CREAMi Scoop & Swirl / Swirl by CREAMi 13-in-1 (NC701EU / NC702EU), 480-ml-Becher.
Jeden Tag ein anderes Rezept (Schwerpunkt Softeis) und ein anderer Tipp.
Alle Rezepte sind für EINEN 480-ml-Becher gedacht – nie über die Fülllinie füllen.
Eigene Rezepte einfach unten in REZEPTE ergänzen.
"""

# Programme laut Hersteller: 6 Softeis-Programme, 6 klassische Scoop-Programme und Mix-In
PROGRAMME_SOFTEIS = [
    ("Ice Cream", "klassisches, luftiges Softeis aus Milch/Sahne"),
    ("Light Ice Cream", "für fett- und zuckerarme Grundmassen (z. B. mit Erythrit)"),
    ("Frozen Yoghurt", "Joghurt-Softeis, schön frisch und leicht säuerlich"),
    ("Fruiti", "Frucht-Softeis aus Obst, z. B. Mango oder Ananas aus der Dose"),
    ("Soft Serve Gelato", "dichter und cremiger, ideal für Nuss- und Schokosorten"),
    ("CreamiFit", "für Protein-Eis mit wenig Kalorien"),
]
PROGRAMME_SCOOP = "Kugeleis (Scoop): u. a. Eiscreme, Sorbet, Gelato und Milchshake – dazu Mix-In zum Unterrühren von Stückchen"

KURZANLEITUNG = [
    "Grundmasse anrühren, bis sich Zucker bzw. Pulver ganz gelöst hat (notfalls kurz pürieren).",
    "In den Swirl-Becher füllen – Boden/Düse muss geschlossen sein – und höchstens bis zur Fülllinie.",
    "Deckel drauf und mindestens 24 Stunden gerade stehend einfrieren. Auch wenn der Becher früher hart wirkt: erst nach 24 Stunden ist er kalt genug.",
    "Deckel abnehmen, Becher in die Außenschüssel setzen und einsetzen, wie es die Schnellstart-Anleitung zeigt.",
    "Fürs Softeis eines der 6 Softeis-Programme wählen, für Kugeleis ein Scoop-Programm.",
    "Softeis: Ausgabeaufsatz laut Anleitung anbringen, Waffel oder Becher unter die Öffnung halten und am Hebel zapfen – der Hebel hat 3 Geschwindigkeiten.",
    "Ein Becher reicht für bis zu 4 Waffeln. Alle abnehmbaren Teile sind spülmaschinenfest.",
]

TIPPS = [
    ("24 Stunden sind Pflicht", "Die Grundmasse muss richtig durchgefroren sein. Nach einer Nacht ist der Becher oft schon hart, innen aber noch nicht kalt genug – dann wird das Softeis körnig."),
    ("Flach einfrieren", "Den Becher gerade ins Gefrierfach stellen. Schräg gefrorene Masse bildet einen Buckel, an dem das Messer hängen bleibt."),
    ("Zu kalt? Kurz warten", "Kommt der Becher aus einem sehr kalten Gefrierschrank, ruckelt die Maschine stark. Dann den Becher 5–10 Minuten auf der Arbeitsfläche stehen lassen und erst dann starten."),
    ("Etwas süßer anrühren", "Kälte schwächt den Geschmack. Die Grundmasse darf im flüssigen Zustand ruhig etwas zu süß schmecken – gefroren passt es dann genau."),
    ("Zucker und Fett machen cremig", "Wer Zucker und Sahne stark reduziert, sollte das Light- oder CreamiFit-Programm nehmen. Mit dem normalen Ice-Cream-Programm wird fettarme Masse sonst krümelig."),
    ("Der Frischkäse-Trick", "Ein Esslöffel zimmerwarmer Frischkäse (oder 1 EL Instant-Vanillepudding-Pulver) macht Softeis glatter und stabiler – so machen es auch viele Ninja-Rezepte."),
    ("Krümelig geworden?", "Einen Schuss Milch dazugeben und die Masse noch einmal mit dem gleichen Programm durchlaufen lassen. Meist wird sie dann schön cremig."),
    ("Stückchen gehören obendrauf", "Kekse, Nüsse oder Schokostückchen fürs Softeis lieber als Topping nehmen – in der Masse können sie die Ausgabeöffnung verstopfen. Fürs Kugeleis gibt es das Mix-In-Programm."),
    ("Mehrere Becher vorbereiten", "Am besten immer 2–3 Becher mit verschiedenen Sorten im Gefrierfach haben. Dann ist jederzeit Softeis da, ohne 24 Stunden zu warten."),
    ("Reste richtig aufheben", "Übriges Eis glatt streichen, Deckel drauf und wieder einfrieren. Vor dem nächsten Mal einfach noch einmal das Programm laufen lassen."),
    ("Obst aus der Dose", "Ananas, Mango oder Pfirsich aus der Dose samt Saft bis zur Fülllinie einfüllen, einfrieren, Fruiti-Programm – fertig ist das Frucht-Softeis ohne Zucker extra."),
    ("Gekauftes Eis wird Softeis", "Keine Zeit? Gekauftes Eis in den Becher geben, glatt streichen, kurz durchfrieren und mit einem Softeis-Programm verarbeiten."),
    ("Nicht über die Fülllinie", "Zu volle Becher können die Maschine blockieren und laufen beim Zapfen über. Die Linie am Becher ist die Obergrenze."),
    ("Protein-Eis gelingt mit Fett", "Bei CreamiFit-Rezepten hilft ein Esslöffel Joghurt oder Frischkäse. Nur Proteinpulver und Wasser wird schnell eisig."),
    ("Sauber halten", "Becher, Deckel, Messer und Ausgabeteile direkt nach dem Zapfen abspülen – getrocknetes Softeis in der Düse geht schwer ab."),
]

# Rezepte: (Name, Programm, Saison, Zutaten, Zubereitung, Topping-Idee)
# Saison: "" = immer, "winter" = Nov–Feb, "sommer" = Mai–Sep
REZEPTE = [
    ("Klassisches Vanille-Softeis", "Softeis: Ice Cream", "",
     ["250 ml Vollmilch", "150 ml Sahne", "60 g Zucker", "1 TL Vanilleextrakt", "1 EL Frischkäse (zimmerwarm)"],
     "Frischkäse mit Zucker glatt rühren, Milch, Sahne und Vanille unterrühren, bis der Zucker gelöst ist.",
     "bunte Streusel oder Schokosauce"),
    ("Schoko-Softeis", "Softeis: Ice Cream", "",
     ["300 ml Vollmilch", "120 ml Sahne", "70 g Zucker", "2 EL Backkakao", "1 Prise Salz"],
     "Kakao mit Zucker und Salz mischen, dann nach und nach Milch und Sahne einrühren, bis nichts mehr klumpt.",
     "Schokoraspel"),
    ("Erdbeer-Frozen-Joghurt", "Softeis: Frozen Yoghurt", "sommer",
     ["300 g griechischer Joghurt", "150 g Erdbeeren (frisch oder TK, püriert)", "60 g Zucker oder Honig"],
     "Erdbeeren mit Zucker pürieren und mit dem Joghurt glatt rühren.",
     "frische Erdbeerstücke"),
    ("Mango-Softeis ohne Zucker", "Softeis: Fruiti", "",
     ["1 Dose Mango in Saft (Fruchtstücke und Saft bis zur Fülllinie)"],
     "Mango mit Saft in den Becher geben, bei Bedarf kurz pürieren.",
     "Kokosraspel"),
    ("Ananas-Softeis wie im Freizeitpark", "Softeis: Fruiti", "",
     ["1 Dose Ananas in Saft (Stücke und Saft bis zur Fülllinie)", "2 EL Kokosmilch"],
     "Ananas samt Saft und Kokosmilch in den Becher geben und kurz durchpürieren.",
     "eine Cocktailkirsche"),
    ("Bananen-Softeis", "Softeis: Fruiti", "",
     ["3 sehr reife Bananen", "100 ml Milch", "1 TL Honig"],
     "Bananen mit Milch und Honig fein pürieren.",
     "gehackte Walnüsse"),
    ("Pistazien-Gelato-Softeis", "Softeis: Soft Serve Gelato", "",
     ["300 ml Vollmilch", "100 ml Sahne", "60 g Pistaziencreme", "40 g Zucker"],
     "Pistaziencreme mit Zucker und etwas Milch glatt rühren, Rest der Milch und Sahne dazugeben.",
     "gehackte Pistazien"),
    ("Sahlep-Softeis (türkische Art)", "Softeis: Soft Serve Gelato", "winter",
     ["400 ml Vollmilch", "100 ml Sahne", "2 EL Instant-Sahlep-Pulver", "40 g Zucker", "nach Wunsch 1 Messerspitze gemahlener Mastix"],
     "Sahlep-Pulver mit Zucker in die kalte Milch rühren, Sahne dazu, gut verquirlen bis alles gelöst ist.",
     "Zimt und gehackte Pistazien"),
    ("Vanille-Protein-Softeis", "Softeis: CreamiFit", "",
     ["400 ml fettarme Milch", "30 g Vanille-Proteinpulver", "1 EL Joghurt", "Süße nach Geschmack (z. B. Erythrit)"],
     "Proteinpulver mit etwas Milch klümpchenfrei anrühren, Rest der Milch und Joghurt dazugeben.",
     "ein paar Beeren"),
    ("Schoko-Banane-Protein", "Softeis: CreamiFit", "",
     ["1 reife Banane", "300 ml fettarme Milch", "30 g Schoko-Proteinpulver"],
     "Alles zusammen fein pürieren.",
     "Bananenscheiben"),
    ("Zitronen-Joghurt light", "Softeis: Light Ice Cream", "sommer",
     ["300 ml fettarme Milch", "150 g Naturjoghurt", "40 g Erythrit oder Zucker", "Abrieb und Saft von ½ Zitrone"],
     "Erythrit in der Milch auflösen, Joghurt, Zitronenabrieb und Saft einrühren.",
     "Zitronenmelisse"),
    ("Kaffee-Softeis", "Softeis: Ice Cream", "",
     ["200 ml kalter starker Kaffee", "200 ml Vollmilch", "80 ml Sahne", "60 g Zucker"],
     "Zucker im noch warmen Kaffee auflösen, abkühlen lassen, dann Milch und Sahne dazu.",
     "Kakaopulver"),
    ("Kokos-Softeis (vegan)", "Softeis: Ice Cream", "",
     ["400 ml Kokosmilch (vollfett)", "60 g Zucker", "1 Prise Salz"],
     "Kokosmilch kurz erwärmen, Zucker und Salz darin auflösen, abkühlen lassen.",
     "geröstete Kokoschips"),
    ("Haselnuss-Nougat-Softeis", "Softeis: Soft Serve Gelato", "",
     ["350 ml Vollmilch", "100 ml Sahne", "3 EL Nuss-Nougat-Creme", "30 g Zucker"],
     "Nougatcreme mit Zucker und etwas warmer Milch glatt rühren, restliche Milch und Sahne dazugeben.",
     "gehackte Haselnüsse"),
    ("Himbeer-Frozen-Joghurt", "Softeis: Frozen Yoghurt", "",
     ["300 g Naturjoghurt (3,5 %)", "150 g Himbeeren (TK geht gut)", "60 g Zucker"],
     "Himbeeren mit Zucker pürieren, nach Wunsch durch ein Sieb streichen, mit Joghurt verrühren.",
     "weiße Schokolade"),
    ("Salted-Caramel-Softeis", "Softeis: Ice Cream", "",
     ["250 ml Vollmilch", "150 ml Sahne", "4 EL Karamellsauce", "20 g Zucker", "½ TL Salz"],
     "Karamellsauce mit Zucker, Salz und etwas Milch glatt rühren, dann Rest der Milch und Sahne dazu.",
     "Karamellsauce und ein paar Salzbrezeln"),
    ("Spekulatius-Softeis", "Softeis: Ice Cream", "winter",
     ["250 ml Vollmilch", "150 ml Sahne", "50 g Zucker", "1 TL Spekulatiusgewürz", "1 EL Frischkäse"],
     "Frischkäse mit Zucker und Gewürz glatt rühren, Milch und Sahne unterrühren.",
     "zerbröselte Spekulatius obendrauf (nicht in die Masse – verstopft sonst die Düse)"),
    ("Bratapfel-Softeis", "Softeis: Ice Cream", "winter",
     ["200 g Apfelmus", "200 ml Vollmilch", "80 ml Sahne", "40 g brauner Zucker", "1 TL Zimt"],
     "Alles gründlich verrühren, bis der Zucker gelöst ist.",
     "Zimt und gehackte Mandeln"),
    ("Lebkuchen-Schoko-Softeis", "Softeis: Soft Serve Gelato", "winter",
     ["300 ml Vollmilch", "120 ml Sahne", "60 g Zucker", "2 EL Kakao", "1 TL Lebkuchengewürz"],
     "Kakao, Zucker und Gewürz mischen, nach und nach Milch und Sahne einrühren.",
     "Orangenabrieb"),
    ("Heidelbeer-Joghurt-Softeis", "Softeis: Frozen Yoghurt", "sommer",
     ["300 g griechischer Joghurt", "150 g Heidelbeeren", "50 g Honig"],
     "Heidelbeeren mit Honig pürieren und mit dem Joghurt glatt rühren.",
     "ganze Heidelbeeren"),
    ("Pfirsich-Softeis", "Softeis: Fruiti", "sommer",
     ["1 Dose Pfirsiche in Saft (Stücke und Saft bis zur Fülllinie)"],
     "Pfirsiche mit Saft in den Becher geben und kurz pürieren.",
     "Amarettini-Brösel"),
    ("Kinder-Liebling: Cookies-Softeis", "Softeis: Ice Cream", "",
     ["250 ml Vollmilch", "150 ml Sahne", "60 g Zucker", "1 TL Vanilleextrakt", "1 EL Instant-Vanillepudding-Pulver"],
     "Puddingpulver mit Zucker mischen, Milch, Sahne und Vanille einrühren, bis alles gelöst ist.",
     "zerbröselte Schoko-Cookies obendrauf"),
]


def _saison_passt(saison: str, monat: int) -> bool:
    if saison == "winter":
        return monat in (11, 12, 1, 2)
    if saison == "sommer":
        return monat in (5, 6, 7, 8, 9)
    return True


def heute(tag_nr: int, monat: int):
    """Rezept des Tages, drei weitere Ideen und Tipp des Tages – passend zur Jahreszeit."""
    passend = [r for r in REZEPTE if _saison_passt(r[2], monat)]
    rezept = passend[tag_nr % len(passend)]
    weitere = []
    for i in range(1, len(passend)):
        r = passend[(tag_nr + i * 3) % len(passend)]
        if r is not rezept and r not in weitere:
            weitere.append(r)
        if len(weitere) == 3:
            break
    return rezept, weitere, TIPPS[tag_nr % len(TIPPS)]


# Fotos von Wikimedia Commons (freie Lizenzen, Urheber wird angezeigt). Dateiname auf commons.wikimedia.org
BILDER = {
    "Klassisches Vanille-Softeis": "Vanilla ice cream cone.JPG",
    "Schoko-Softeis": "2018-06-09 18 06 38 A chocolate soft-serve ice cream cone at the Dairy Lou Recreation Center in the Franklin Farm section of Oak Hill, Fairfax County, Virginia.jpg",
    "Erdbeer-Frozen-Joghurt": "Strawberry Frozen Yogurt (2552806737).jpg",
    "Mango-Softeis ohne Zucker": "Mangos - single and halved.jpg",
    "Ananas-Softeis wie im Freizeitpark": "Pineapple Dole Whip.jpg",
    "Bananen-Softeis": "Vegan ice cream, banana nice cream.jpg",
    "Pistazien-Gelato-Softeis": "Pistachio ice cream.jpg",
    "Sahlep-Softeis (türkische Art)": "Maraş dondurma.jpg",
    "Vanille-Protein-Softeis": "Dairy Queen Soft Serve Vanilla Cone (17400892134).jpg",
    "Schoko-Banane-Protein": "Chocolate Banana Ice Cream Recipe By Sonia Goyal.jpg",
    "Zitronen-Joghurt light": "Lemon ice cream in Rome.jpg",
    "Kaffee-Softeis": "Coffee ice-cream at siri mane.jpg",
    "Kokos-Softeis (vegan)": "Coconut ice cream - Bangkok - 2017-05-03 (001).jpg",
    "Haselnuss-Nougat-Softeis": "Nutella gelato.jpg",
    "Himbeer-Frozen-Joghurt": "Berry Frozen Yogurt (4723048814).jpg",
    "Salted-Caramel-Softeis": "Salted caramel ice cream (26314112816).jpg",
    "Spekulatius-Softeis": "Spekulatius four pieces of.jpg",
    "Bratapfel-Softeis": "AppleCinnamonIceCream.jpg",
    "Lebkuchen-Schoko-Softeis": "Lebkuchen-pile.jpg",
    "Heidelbeer-Joghurt-Softeis": "Blueberry frozen yoghurt (4937999312).jpg",
    "Pfirsich-Softeis": "Mitchell's Peach Ice Cream (19156805683).jpg",
    "Kinder-Liebling: Cookies-Softeis": "Udders Cookies and Cream Ice Cream (cropped).jpg",
}
TITELBILD = "Liat Portal for Foodie Disorder - Chocolate and vanilla soft serve ice cream cone.jpg"
