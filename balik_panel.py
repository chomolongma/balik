import json, urllib.request, datetime, webbrowser, os
from balik_sinyal import sinyalleri_getir
from balik_youtube import videolari_getir

LAT, LON = 36.30, 30.15  # Finike

INSTAGRAM = {
    "Çağdaş Özsarı":  "cagdasozsari",
    "Tintin Fishing": "tintin.fishing",
    "Balık ve Keyif": "balikvekeyif",
    "Balık Firarda":  "balik_firarda",
}

def getir(url):
    with urllib.request.urlopen(url) as c:
        return json.load(c)

hava = getir(f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}"
             "&daily=wind_speed_10m_max,surface_pressure_mean,weather_code,sunrise,sunset"
             "&timezone=auto")
deniz = getir(f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}"
              "&daily=wave_height_max&current=sea_surface_temperature&timezone=auto")

su = deniz["current"]["sea_surface_temperature"]

def ay_gunu(t):
    return ((t - datetime.date(2000, 1, 6)).days) % 29.53

def ay_evre(t):
    g = ay_gunu(t)
    if g < 2 or g > 27.5:   return 1.0, "🌑", "Yeni ay"
    if 12.8 < g < 16.8:     return 1.0, "🌕", "Dolunay"
    if g < 12.8:            return 0.0, "🌓", "İlk yarı"
    return 0.0, "🌗", "Son yarı"

def s2str(saat):
    """Ondalık saati '06:40' biçimine çevir."""
    saat %= 24
    h = int(saat)
    m = int(round((saat - h) * 60))
    if m == 60: h, m = (h + 1) % 24, 0
    return f"{h:02d}:{m:02d}"

def solunar_pencereler(t):
    """Majör (2 saat) ve minör (1 saat) pencereleri saat aralığı olarak döndür."""
    yas = ay_gunu(t)
    transit = (12.0 + yas * 0.813) % 24
    dip = (transit + 12) % 24
    majorler = [((m - 1) % 24, (m + 1) % 24) for m in (transit, dip)]
    minorler = [((m - 0.5) % 24, (m + 0.5) % 24)
                for m in ((transit - 6.2) % 24, (transit + 6.2) % 24)]
    return majorler, minorler

HAVA_IKON = {0:"☀️",1:"🌤",2:"⛅",3:"☁️",45:"🌫",48:"🌫",51:"🌦",53:"🌦",55:"🌧",
             61:"🌧",63:"🌧",65:"🌧",80:"🌦",81:"🌧",82:"⛈",95:"⛈",96:"⛈",99:"⛈"}

TURLER = {
    1:"lahos, sinarit, mercan", 2:"lahos, sinarit, mercan", 3:"sinarit, mercan, kupes",
    4:"sinarit, akya, mercan", 5:"akya, sinarit, lambuka öncesi", 6:"akya, iskorpit, mercan",
    7:"lambuka, akya, mercan", 8:"lambuka, akya, sinarit", 9:"lambuka, palamut geçişi, akya",
    10:"palamut, akya, sinarit", 11:"akya, sinarit, lahos", 12:"lahos, sinarit, mercan",
}

gunler = ["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"]
basinclar = hava["daily"]["surface_pressure_mean"]

def gun_hesapla(i, tarih):
    ruzgar = hava["daily"]["wind_speed_10m_max"][i] / 1.852
    dalga = deniz["daily"]["wave_height_max"][i]
    kod = hava["daily"]["weather_code"][i]
    t = datetime.date.fromisoformat(tarih)

    skor = 10.0
    if ruzgar > 10: skor -= (ruzgar - 10) * 0.6
    skor -= dalga * 3

    basinc_yon = ""
    basinc_bonus = False
    if i > 0 and basinclar[i] is not None and basinclar[i-1] is not None:
        fark = basinclar[i] - basinclar[i-1]
        if fark < -3:
            skor += 1.0; basinc_yon = "▼"; basinc_bonus = True
        elif fark < -1:
            skor += 0.5; basinc_yon = "▼"; basinc_bonus = True
        elif fark > 1:
            basinc_yon = "▲"

    bonus, ay_ikon, ay_ad = ay_evre(t)
    skor += bonus
    skor = max(0, min(10, round(skor, 1)))

    if skor >= 7:   renk, karar = "#16a34a", "ÇIKILIR"
    elif skor >= 4: renk, karar = "#d97706", "İDARE EDER"
    else:           renk, karar = "#dc2626", "OLMAZ"

    dogus = hava["daily"]["sunrise"][i][-5:]
    batis = hava["daily"]["sunset"][i][-5:]

    return dict(t=t, ruzgar=ruzgar, dalga=dalga, ikon=HAVA_IKON.get(kod, "🌊"),
                skor=skor, renk=renk, karar=karar,
                basinc=basinc_yon, basinc_bonus=basinc_bonus,
                ay_ikon=ay_ikon, ay_ad=ay_ad, dogus=dogus, batis=batis)

tum_gunler = [gun_hesapla(i, tarih) for i, tarih in enumerate(hava["daily"]["time"])]
bugun_v = tum_gunler[0]
sonraki = tum_gunler[1:]

# --- Haftanın günü ---
en_iyi = max(tum_gunler, key=lambda g: g["skor"])
en_iyi_ad = "BUGÜN" if en_iyi is bugun_v else f"{gunler[en_iyi['t'].weekday()]} {en_iyi['t'].day:02d}.{en_iyi['t'].month:02d}"

# --- Bugünün saat çizelgesi (solunar + altın saatler) ---
majorler, minorler = solunar_pencereler(bugun_v["t"])

def saat_cevir(hhmm):
    h, m = hhmm.split(":")
    return int(h) + int(m) / 60

GW, GH, GS = 680, 118, 26
def x_koy(saat): return GS + saat / 24 * (GW - 2 * GS)

def bant(a, b, renk, y, yuk):
    parcalar = []
    for (p, q) in ([(a, b)] if a <= b else [(a, 24), (0, b)]):
        x1, x2 = x_koy(p), x_koy(q)
        parcalar.append(f'<rect x="{x1:.0f}" y="{y}" width="{max(x2-x1,2):.0f}" '
                        f'height="{yuk}" rx="5" fill="{renk}"/>')
    return "".join(parcalar)

cizelge = ""
for (a, b) in majorler:
    cizelge += bant(a, b, "#16a34a", 34, 34)
for (a, b) in minorler:
    cizelge += bant(a, b, "#2563eb", 42, 18)
for saat in range(0, 25, 3):
    x = x_koy(saat)
    cizelge += (f'<line x1="{x:.0f}" y1="72" x2="{x:.0f}" y2="78" stroke="#334155"/>'
                f'<text x="{x:.0f}" y="94" text-anchor="middle" fill="#7d8b96" font-size="12">{saat:02d}</text>')
cizelge += f'<line x1="{GS}" y1="72" x2="{GW-GS}" y2="72" stroke="#334155" stroke-width="2"/>'
for ikon, hhmm in (("🌅", bugun_v["dogus"]), ("🌇", bugun_v["batis"])):
    x = x_koy(saat_cevir(hhmm))
    cizelge += (f'<text x="{x:.0f}" y="24" text-anchor="middle" font-size="16">{ikon}</text>'
                f'<line x1="{x:.0f}" y1="28" x2="{x:.0f}" y2="72" stroke="#7d8b96" stroke-dasharray="3,3"/>')
saat_grafik = f'<svg viewBox="0 0 {GW} {GH}" style="width:100%;height:auto">{cizelge}</svg>'

maj_metin = " & ".join(f"{s2str(a)}–{s2str(b)}" for a, b in majorler)
mnr_metin = " & ".join(f"{s2str(a)}–{s2str(b)}" for a, b in minorler)

# --- Haftalık grafik ---
W, H, SOL, UST = 680, 150, 30, 16
adim = (W - 2*SOL) / (len(tum_gunler) - 1)
noktalar, etiketler = [], []
for i, g in enumerate(tum_gunler):
    x = SOL + i * adim
    y = UST + (10 - g["skor"]) / 10 * (H - UST - 34)
    noktalar.append(f"{x:.0f},{y:.0f}")
    gad = "Bugün" if i == 0 else gunler[g["t"].weekday()]
    etiketler.append(
        f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5" fill="{g["renk"]}"/>'
        f'<text x="{x:.0f}" y="{y-10:.0f}" text-anchor="middle" fill="{g["renk"]}" '
        f'font-size="13" font-weight="700">{g["skor"]}</text>'
        f'<text x="{x:.0f}" y="{H-6}" text-anchor="middle" fill="#7d8b96" font-size="12">{gad}</text>')
grafik = (f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto">'
          f'<polyline points="{" ".join(noktalar)}" fill="none" stroke="#334155" stroke-width="2"/>'
          + "".join(etiketler) + '</svg>')

# --- Sonraki günler şeridi ---
serit = ""
for g in sonraki:
    yildiz = "⭐ " if g is en_iyi else ""
    serit += f"""
    <div class="skart" style="border-top:5px solid {g['renk']}">
      <div class="skart-gun">{yildiz}{gunler[g['t'].weekday()]} <span>{g['t'].day:02d}.{g['t'].month:02d}</span></div>
      <div class="skart-ikon">{g['ikon']}</div>
      <div class="skart-skor" style="color:{g['renk']}">{g['skor']}</div>
      <div class="skart-detay">💨{g['ruzgar']:.0f}kn 🌊{g['dalga']:.1f}m</div>
      {"<div class='rozet'>🎣 basınç avantajı</div>" if g['basinc_bonus'] else ""}
    </div>"""

# --- Instagram şeridi ---
ig_linkler, ig_urller = [], []
for isim, hesap in INSTAGRAM.items():
    url = f"https://www.instagram.com/{hesap}/"
    ig_urller.append(url)
    ig_linkler.append(f'<a class="ig" href="{url}" target="_blank">📷 {isim}</a>')
js_liste = ",".join(f"'{u}'" for u in ig_urller)
ig_html = (f'<div class="igbar">{"".join(ig_linkler)}'
           f'<button class="ig igbtn" onclick="[{js_liste}].forEach(u=>window.open(u))">'
           f'⚡ Hepsini aç</button></div>')

# --- YouTube ---
yt_html = ""
for yas, kanal, turler, baslik in videolari_getir():
    ne_zaman = "bugün" if yas == 0 else ("dün" if yas == 1 else f"{yas} gün önce")
    etiket = f'<span class="tur">{"/".join(turler)}</span> ' if turler else ""
    yt_html += (f'<div class="sinyal">{etiket}<b>@{kanal}</b> '
                f'<span class="zaman">{ne_zaman}</span><br>{baslik[:90]}</div>')
if not yt_html:
    yt_html = '<div class="sinyal">Son 14 günde video yok.</div>'

# --- Basın ---
sinyal_html = ""
for yas, turler, baslik in sinyalleri_getir():
    ne_zaman = "bugün" if yas == 0 else ("dün" if yas == 1 else f"{yas} gün önce")
    sinyal_html += (f'<div class="sinyal"><span class="tur">{"/".join(turler)}</span> '
                    f'<span class="zaman">{ne_zaman}</span><br>{baslik[:90]}</div>')
if not sinyal_html:
    sinyal_html = '<div class="sinyal">Son 14 günde basın sinyali yok.</div>'

bugun = datetime.date.today()
html = f"""<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Balık</title><style>
  * {{ box-sizing:border-box; }}
  body {{ font-family:-apple-system,sans-serif; background:#000; color:#f2f5f7;
         margin:0; padding:14px; max-width:760px; margin-left:auto; margin-right:auto; }}
  .tarih {{ color:#7d8b96; font-size:14px; margin:2px 0 12px; }}

  .hero {{ border-radius:24px; padding:26px 20px 22px; text-align:center;
           color:#fff; margin-bottom:14px; }}
  .hero-gun {{ font-size:16px; font-weight:600; opacity:.9; letter-spacing:1px; }}
  .hero-skor {{ font-size:104px; font-weight:900; line-height:1; margin:6px 0; }}
  .hero-karar {{ font-size:30px; font-weight:800; letter-spacing:2px; }}
  .hero-ikon {{ font-size:44px; margin-top:6px; }}

  .kutular {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:10px; }}
  .kutu {{ background:#14181d; border-radius:18px; padding:14px; text-align:center; }}
  .kutu-ikon {{ font-size:30px; }}
  .kutu-deger {{ font-size:26px; font-weight:800; margin-top:2px; }}
  .kutu-ad {{ font-size:12px; color:#7d8b96; margin-top:2px; }}

  .saatler {{ background:#14181d; border-radius:18px; padding:12px 16px;
              margin-top:8px; line-height:1.8; }}

  h2 {{ font-size:17px; margin:20px 0 10px; color:#aebac4; }}
  .grafik {{ background:#0c0f12; border-radius:18px; padding:10px 6px 4px; }}
  .serit {{ display:flex; gap:10px; overflow-x:auto; padding-bottom:6px;
            -webkit-overflow-scrolling:touch; }}
  .serit {{ scrollbar-width:none; }}
  .serit::-webkit-scrollbar {{ display:none; }}
  .skart {{ background:#14181d; border-radius:16px; padding:12px; min-width:112px;
            text-align:center; flex-shrink:0; }}
  .skart-gun {{ font-weight:700; font-size:14px; }}
  .skart-gun span {{ color:#7d8b96; font-weight:400; font-size:11px; }}
  .skart-ikon {{ font-size:26px; margin:4px 0; }}
  .skart-skor {{ font-size:26px; font-weight:800; }}
  .skart-detay {{ font-size:12px; color:#7d8b96; margin-top:4px; }}

  .igbar {{ display:flex; gap:8px; overflow-x:auto; padding-bottom:6px;
            scrollbar-width:none; }}
  .igbar::-webkit-scrollbar {{ display:none; }}
  .ig {{ background:#14181d; color:#f2f5f7; text-decoration:none; padding:10px 14px;
         border-radius:22px; font-size:14px; white-space:nowrap; flex-shrink:0;
         border:1px solid #232a31; }}
  .igbtn {{ cursor:pointer; font-family:inherit; }}

  .sinyal {{ background:#101418; border-radius:14px; padding:12px 14px;
             margin-bottom:8px; font-size:15px; line-height:1.5; }}
  .tur {{ background:#1d4ed8; color:#fff; border-radius:8px; padding:1px 8px;
          font-size:12px; font-weight:700; }}
  .zaman {{ color:#7d8b96; font-size:13px; }}
  .rozet {{ display:inline-block; background:#0e2a1a; color:#4ade80; border-radius:8px;
            padding:2px 8px; font-size:11px; font-weight:700; margin-top:6px; }}
  .rozet-hero {{ background:rgba(0,0,0,.25); color:#fff; font-size:14px;
                 padding:6px 12px; border-radius:12px; margin-top:10px; }}
</style></head><body>
<div class="tarih">🐟 Balık — Finike · {bugun.strftime("%d.%m.%Y")} · ⭐ Haftanın günü: {en_iyi_ad}</div>

<div class="hero" style="background:{bugun_v['renk']}">
  <div class="hero-gun">BUGÜN · {gunler[bugun_v['t'].weekday()].upper()}</div>
  <div class="hero-skor">{bugun_v['skor']}</div>
  <div class="hero-karar">{'⚓ ' if bugun_v['skor']>=7 else ''}{bugun_v['karar']}</div>
  <div class="hero-ikon">{bugun_v['ikon']}</div>
  {"<div class='rozet rozet-hero'>🎣 basınç avantajı — balık beslenmede</div>" if bugun_v['basinc_bonus'] else ""}
</div>

<div class="kutular">
  <div class="kutu"><div class="kutu-ikon">💨</div>
    <div class="kutu-deger">{bugun_v['ruzgar']:.1f} kn</div>
    <div class="kutu-ad">Rüzgar {bugun_v['basinc']}</div></div>
  <div class="kutu"><div class="kutu-ikon">🌊</div>
    <div class="kutu-deger">{bugun_v['dalga']:.1f} m</div>
    <div class="kutu-ad">Dalga</div></div>
  <div class="kutu"><div class="kutu-ikon">🌡</div>
    <div class="kutu-deger">{su} °C</div>
    <div class="kutu-ad">Deniz suyu</div></div>
  <div class="kutu"><div class="kutu-ikon">{bugun_v['ay_ikon']}</div>
    <div class="kutu-deger" style="font-size:18px">{bugun_v['ay_ad']}</div>
    <div class="kutu-ad">Ay</div></div>
</div>

<h2>⏰ Bugünün saatleri</h2>
<div class="grafik">{saat_grafik}</div>
<div class="saatler" style="font-size:13px">
  <span style="color:#4ade80">■</span> Majör {maj_metin} ·
  <span style="color:#60a5fa">■</span> Minör {mnr_metin} ·
  🌅 {bugun_v['dogus']} · 🌇 {bugun_v['batis']}
</div>

<div class="sinyal" style="background:#14181d; margin-top:10px">🐟 <b>Bu ay beklenen:</b> {TURLER[bugun.month]}</div>

<h2>📈 Haftanın seyri</h2>
<div class="grafik">{grafik}</div>

<h2>📅 Sonraki günler</h2>
<div class="serit">{serit}</div>

<h2>📷 Taze kaynaklar</h2>
{ig_html}

<h2>🎣 Balıkçı kanalları</h2>
{yt_html}

<h2>📰 Basın sinyalleri</h2>
{sinyal_html}
</body></html>"""

yol = os.environ.get("CIKTI", os.path.expanduser("~/balik_raporu.html"))
with open(yol, "w", encoding="utf-8") as f:
    f.write(html)
if not os.environ.get("GITHUB_ACTIONS"):
    webbrowser.open("file://" + yol)
