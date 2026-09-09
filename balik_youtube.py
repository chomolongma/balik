import urllib.request, urllib.parse, re, os, json, datetime
import xml.etree.ElementTree as ET
from balik_sinyal import TURLER

KANAL_IDLER = {
    "cagdasozsari":     "UCz968bOakubDKVLpNcC4xzw",
    "tintinfishing4958":"UC3YMwAafjdx92cxxaVHsrQg",
    "BalikveKeyif":     "UCSMdoOc_zMKad4bkOMMKukA",
    "Balikfirarda":     "UCmkQ5lOOnxKUVQjK_JQI0bA",
}
ATOM = "{http://www.w3.org/2005/Atom}"
API_KEY = os.environ.get("YT_API_KEY", "")

def sayfa_getir(url):
    istek = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(istek) as c:
        return c.read().decode("utf-8", errors="ignore")

def yas_hesapla(tarih_metni, simdi):
    tarih = datetime.datetime.fromisoformat(tarih_metni.replace("Z", "+00:00"))
    return (simdi - tarih).days

def api_ile(kanal, kid, simdi):
    """Resmi YouTube Data API — bulutta bu çalışır."""
    url = ("https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode({
        "key": API_KEY, "channelId": kid, "part": "snippet",
        "order": "date", "maxResults": 5, "type": "video"}))
    veri = json.loads(sayfa_getir(url))
    sonuc = []
    for item in veri.get("items", []):
        baslik = item["snippet"]["title"]
        yas = yas_hesapla(item["snippet"]["publishedAt"], simdi)
        gecen = [t for t in TURLER if re.search(t, baslik, re.IGNORECASE)]
        sonuc.append((yas, kanal, gecen, baslik))
    return sonuc

def rss_ile(kanal, kid, simdi):
    """RSS — Mac'te çalışır, bulutta YouTube engelleyebilir."""
    xml = sayfa_getir(f"https://www.youtube.com/feeds/videos.xml?channel_id={kid}")
    kok = ET.fromstring(xml)
    sonuc = []
    for giris in kok.iter(ATOM + "entry"):
        baslik = giris.findtext(ATOM + "title") or ""
        tarih_m = giris.findtext(ATOM + "published") or ""
        try:
            yas = yas_hesapla(tarih_m, simdi)
        except ValueError:
            continue
        gecen = [t for t in TURLER if re.search(t, baslik, re.IGNORECASE)]
        sonuc.append((yas, kanal, gecen, baslik))
    return sonuc

def videolari_getir(gun_siniri=14, en_fazla=8):
    simdi = datetime.datetime.now(datetime.timezone.utc)
    bulgular = []
    for kanal, kid in KANAL_IDLER.items():
        try:
            if API_KEY:
                kanal_videolari = api_ile(kanal, kid, simdi)
            else:
                kanal_videolari = rss_ile(kanal, kid, simdi)
        except Exception as hata:
            print(f"UYARI @{kanal}: {type(hata).__name__}: {hata}")
            continue
        yeniler = [v for v in kanal_videolari if v[0] <= gun_siniri]
        if not yeniler and kanal_videolari:
            yeniler = [min(kanal_videolari)]
        bulgular.extend(yeniler)
    bulgular.sort()
    return bulgular[:en_fazla]

if __name__ == "__main__":
    for yas, kanal, turler, baslik in videolari_getir():
        etiket = f" [{'/'.join(turler)}]" if turler else ""
        print(f"[{yas}g] @{kanal}{etiket}: {baslik[:60]}")
