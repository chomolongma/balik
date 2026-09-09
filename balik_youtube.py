import urllib.request, re, datetime
import xml.etree.ElementTree as ET
from balik_sinyal import TURLER

# Kanal ID'leri sabit — teşhis çalışmamızda bulmuştuk, bunlar hiç değişmez
KANAL_IDLER = {
    "cagdasozsari":     "UCz968bOakubDKVLpNcC4xzw",
    "tintinfishing4958":"UC3YMwAafjdx92cxxaVHsrQg",
    "BalikveKeyif":     "UCSMdoOc_zMKad4bkOMMKukA",
    "Balikfirarda":     "UCmkQ5lOOnxKUVQjK_JQI0bA",
}
ATOM = "{http://www.w3.org/2005/Atom}"

def sayfa_getir(url):
    istek = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(istek) as c:
        return c.read().decode("utf-8", errors="ignore")

def videolari_getir(gun_siniri=14, en_fazla=8):
    simdi = datetime.datetime.now(datetime.timezone.utc)
    bulgular = []
    for kanal, kid in KANAL_IDLER.items():
        try:
            xml = sayfa_getir(f"https://www.youtube.com/feeds/videos.xml?channel_id={kid}")
            kok = ET.fromstring(xml)
        except Exception as hata:
            print(f"UYARI @{kanal}: {type(hata).__name__}: {hata}")
            continue
        kanal_videolari = []
        for giris in kok.iter(ATOM + "entry"):
            baslik = giris.findtext(ATOM + "title") or ""
            tarih_m = giris.findtext(ATOM + "published") or ""
            try:
                yas = (simdi - datetime.datetime.fromisoformat(tarih_m)).days
            except ValueError:
                continue
            gecen = [t for t in TURLER if re.search(t, baslik, re.IGNORECASE)]
            kanal_videolari.append((yas, kanal, gecen, baslik))
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
