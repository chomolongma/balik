import urllib.request, urllib.parse, re, datetime
import xml.etree.ElementTree as ET

ARAMALAR = ["Antalya balık", "Finike balık", "Antalya palamut", "Antalya olta"]
TURLER = ["palamut", "akya", "istavrit", "lambuka", "sinarit", "lahos",
          "mercan", "kalamar", "kalmar", "orfoz", "çipura", "levrek", "hamsi"]

def rss_getir(sorgu):
    url = ("https://news.google.com/rss/search?q=" +
           urllib.parse.quote(sorgu) + "&hl=tr&gl=TR&ceid=TR:tr")
    istek = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(istek) as c:
        return ET.parse(c).getroot()

def sinyalleri_getir(gun_siniri=14, en_fazla=5):
    bulgular = []
    gorulen = set()
    simdi = datetime.datetime.now(datetime.timezone.utc)
    for sorgu in ARAMALAR:
        try:
            kok = rss_getir(sorgu)
        except Exception:
            continue  # bir arama çökerse diğerleri devam etsin
        for madde in kok.iter("item"):
            baslik = madde.findtext("title") or ""
            tarih_metni = madde.findtext("pubDate") or ""
            if baslik in gorulen:
                continue
            gorulen.add(baslik)
            try:
                tarih = datetime.datetime.strptime(tarih_metni, "%a, %d %b %Y %H:%M:%S %Z")
                tarih = tarih.replace(tzinfo=datetime.timezone.utc)
                yas = (simdi - tarih).days
            except ValueError:
                yas = 99
            if yas > gun_siniri:
                continue
            gecen = [t for t in TURLER if re.search(t, baslik, re.IGNORECASE)]
            if gecen:
                bulgular.append((yas, gecen, baslik))
    bulgular.sort()
    return bulgular[:en_fazla]

if __name__ == "__main__":
    for yas, turler, baslik in sinyalleri_getir():
        print(f"[{yas}g] {'/'.join(turler)}: {baslik[:70]}")