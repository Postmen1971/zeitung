import sys, re, urllib.request, concurrent.futures
sys.path.insert(0, ".")
import zeitung as z
KANDIDATEN = """
gs|https://www.fotomac.com.tr/rss/galatasaray.xml
gs|https://www.aspor.com.tr/rss/galatasaray.xml
gs|https://www.fanatik.com.tr/rss/galatasaray
gs|https://www.ntvspor.net/rss/kategori/galatasaray
gs|https://www.ntv.com.tr/spor.rss
gs|https://www.sabah.com.tr/rss/spor.xml
gs|https://www.haberturk.com/rss/spor.xml
gs|https://www.cnnturk.com/feed/rss/spor/news
gs|https://www.milliyet.com.tr/rss/rssnew/sporrss.xml
gs|https://www.hurriyet.com.tr/rss/spor
gs|https://www.trtspor.com.tr/rss/futbol.rss
fb|https://newsfeed.kicker.de/news/fussball
fb|https://www.sportschau.de/fussball/index~rss2.xml
fb|https://www.sport1.de/news.rss
fb|https://www.transfermarkt.de/rss/news
fb|https://www.spox.com/pub/rss/sport-fussball.xml
box|https://www.boxingnews24.com/feed/
box|https://www.badlefthook.com/rss/index.xml
box|https://www.ringtv.com/feed/
box|https://www.boxingscene.com/rss.xml
box|https://www.ran.de/sports/boxen/rss
ki|https://the-decoder.de/feed/
ki|https://t3n.de/tag/kuenstliche-intelligenz/rss.xml
ki|https://www.heise.de/rss/heise-atom.xml
fo|https://www.scinexx.de/feed/
fo|https://medicalxpress.com/rss-feed/genetics-news/
fo|https://www.aerzteblatt.de/rss/news.asp
fo|https://www.spektrum.de/alias/rss/spektrum-de-rss-feed/996406
fo|https://www.deutschlandfunk.de/forschung-aktuell-100.rss
te|https://rss.golem.de/rss.php?feed=RSS2.0
te|https://t3n.de/rss.xml
te|https://www.chip.de/rss/rss_topnews.xml
te|https://www.ingenieur.de/feed/
te|https://www.trendsderzukunft.de/feed/
te|https://newatlas.com/index.rss
vi|https://www.futurezone.de/feed/
vi|https://www.raumfahrer.net/feed/
vi|https://www.spektrum.de/alias/rss/astronomie/1011330
we|https://www.tagesschau.de/xml/rss2/
we|https://rss.dw.com/rdf/rss-de-all
""".split()

def test(zeile):
    rid, url = zeile.split("|", 1)
    try:
        liste = z.feed_lesen(z.laden(url)[0], url)
    except Exception as ex:
        return f"FEHLER {rid:3} {url}  {type(ex).__name__}: {str(ex)[:60]}"
    n = len(liste); b = sum(1 for a in liste if a["bild"])
    og = ""
    if n and b == 0:
        try:
            seite = z.laden(liste[0]["link"], 400_000)[0].decode("utf-8", "replace")
            og = " og:image=" + ("JA" if z.meta_wert(seite, "og:image") else "nein")
        except Exception as ex:
            og = f" og:FEHLER {type(ex).__name__}"
    bsp = liste[0]["titel"][:60] if n else ""
    return f"OK     {rid:3} {url}  items={n} bilder={b}{og} | {bsp}"

with concurrent.futures.ThreadPoolExecutor(8) as p:
    for r in p.map(test, KANDIDATEN):
        print(r)

# Google-News-Diagnose
g = z.feed_lesen(z.laden(z.gnews("Galatasaray"))[0], "news.google.com")
link = g[0]["link"]; print("\nGN link:", link[:100])
for pfad in ("https://news.google.com/rss/articles/", "https://news.google.com/articles/"):
    aid = re.search(r"/articles/([^/?#]+)", link).group(1)
    try:
        d, typ, ziel = z.laden(pfad + aid, 600_000)
        t = d.decode("utf-8", "replace")
        tt = re.search(r"<title>(.*?)</title>", t, re.S)
        print(pfad, "len", len(d), "ziel", ziel[:80], "sg" , "data-n-a-sg" in t, "title", tt.group(1)[:60] if tt else "-")
    except Exception as ex:
        print(pfad, "FEHLER", ex)
for i, a in enumerate(g[:12]):
    try:
        print(i, (z.google_link_aufloesen(a["link"]) or "LEER")[:90])
    except Exception as ex:
        print(i, "EXC", type(ex).__name__, str(ex)[:100])
    import time; time.sleep(1.5)
