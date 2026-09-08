import json, urllib.request, datetime, webbrowser, os
from balik_sinyal import sinyalleri_getir
from balik_youtube import videolari_getir

LAT, LON = 36.30, 30.15  # Finike

# Instagram hesapları: sağdaki adları gerçekleriyle değiştirin
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
             "&daily=wind_speed_10m_max,surface_pressure_mean,weather_code&timezone=auto")
deniz = getir(f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}"
              "&daily=wave_height_max&current=sea_surface_temperature&timezone=auto")

su = deniz["current"]["sea_surface_temperature"]

def ay_gunu(t):
    return ((t - datetime.date(2000, 1, 6)).days) % 29.53

def ay_bonus(t):
    g = ay_gunu(t)
    if g < 2 or g > 27.5:   return 1.0, "🌑"
    if 12.8 < g < 16.8:     return 1.0, "🌕"
    return 0.0, ""

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

kartlar = []
for i, tarih in enumerate(hava["daily"]["time"]):
    ruzgar = hava["daily"]["wind_speed_10m_max"][i] / 1.852
    dalga = deniz["daily"]["wave_height_max"][i]
    kod = hava["daily"]["weather_code"][i]
    t = datetime.date.fromisoformat(tarih)

    skor = 10.0
    if ruzgar > 10: skor -= (ruzgar - 10) * 0.6
    skor -= dalga * 3

    basinc = ""
    if i > 0 and basinclar[i] is not None and basinclar[i-1] is not None:
        if basinclar[i] < basinclar[i-1] - 1:
            skor += 0.5; basinc = "▼ basınç düşüyor"
        elif basinclar[i] > basinclar[i-1] + 1:
            basinc = "▲ basınç yükseliyor"

    bonus, ay = ay_bonus(t)
    skor += bonus
    skor = max(0, min(10, round(skor, 1)))

    if skor >= 7:   renk, karar = "#16a34a", "⚓ Çıkılır"
    elif skor >= 4: renk, karar = "#d97706", "~ İdare eder"
    else:           renk, karar = "#dc2626", "✗ Olmaz"

    kartlar.append(f"""
    <div class="kart" style="border-top:6px solid {renk}">
      <div class="gun">{gunler[t.weekday()]} <span>{t.day:02d}.{t.month:02d}</span> {ay}</div>
      <div class="ikon">{HAVA_IKON.get(kod, "🌊")}</div>
      <div class="skor" style="color:{renk}">{skor}</div>
      <div class="karar" style="color:{renk}">{karar}</div>
      <div class="detay">💨 {ruzgar:.1f} kn<br>🌊 {dalga:.1f} m</div>
      <div class="basinc">{basinc}</div>
    </div>""")

# --- Instagram şeridi ---
ig_linkler = []
ig_urller = []
for isim, hesap in INSTAGRAM.items():
    if "KULLANICI_ADI" in hesap:
        continue  # henüz doldurulmamış
    url = f"https://www.instagram.com/{hesap}/"
    ig_urller.append(url)
    ig_linkler.append(f'<a class="ig" href="{url}" target="_blank">📷 {isim}</a>')

ig_html = ""
if ig_linkler:
    js_liste = ",".join(f"'{u}'" for u in ig_urller)
    ig_html = (f'<div class="igbar">{"".join(ig_linkler)}'
               f'<button class="ig igbtn" onclick="[{js_liste}].forEach(u=>window.open(u))">'
               f'⚡ Hepsini aç</button></div>')

# --- YouTube balıkçı kanalları ---
yt_html = ""
for yas, kanal, turler, baslik in videolari_getir():
    ne_zaman = "bugün" if yas == 0 else ("dün" if yas == 1 else f"{yas} gün önce")
    etiket = f'<b>{"/".join(turler)}</b> ' if turler else ""
    yt_html += (f'<li>{etiket}<span class="zaman">@{kanal}, {ne_zaman}</span>'
                f' — {baslik[:80]}</li>')
if not yt_html:
    yt_html = "<li>Son 14 günde video yok.</li>"

# --- Basın sinyalleri ---
sinyal_html = ""
for yas, turler, baslik in sinyalleri_getir():
    ne_zaman = "bugün" if yas == 0 else ("dün" if yas == 1 else f"{yas} gün önce")
    sinyal_html += (f'<li><b>{"/".join(turler)}</b> '
                    f'<span class="zaman">({ne_zaman})</span> — {baslik[:80]}</li>')
if not sinyal_html:
    sinyal_html = "<li>Son 14 günde basın sinyali yok.</li>"

bugun = datetime.date.today()
html = f"""<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">
<title>Balık</title><style>
  body {{ font-family:-apple-system,sans-serif; background:#0b1f33; color:#e8eef4;
         margin:0; padding:24px; }}
  h1 {{ margin:0 0 4px; font-size:26px; }}
  .alt {{ color:#8fb3cc; margin-bottom:20px; }}
  .ozet {{ background:#12324f; border-radius:12px; padding:14px 18px;
           display:inline-block; margin-bottom:20px; line-height:1.7; }}  
@media (max-width: 600px) {{
    body {{ padding:12px; }}
    h1 {{ font-size:20px; }}
    .ozet {{ display:block; font-size:14px; }}
    .kartlar {{ display:grid; grid-template-columns:1fr 1fr; }}
    .kart {{ width:auto; }}
    ul {{ padding-left:18px; font-size:14px; }}
  }}
  .kartlar {{ display:flex; gap:12px; flex-wrap:wrap; }}
  .kart {{ background:#ffffff; color:#1e293b; border-radius:12px; padding:12px;
           width:120px; text-align:center; }}
  .gun {{ font-weight:700; }} .gun span {{ color:#64748b; font-weight:400; font-size:12px; }}
  .ikon {{ font-size:30px; margin:6px 0; }}
  .skor {{ font-size:30px; font-weight:800; }}
  .karar {{ font-size:13px; font-weight:600; margin-bottom:6px; }}
  .detay {{ font-size:13px; color:#475569; line-height:1.5; }}
  .basinc {{ font-size:11px; color:#64748b; min-height:14px; }}
  h2 {{ margin-top:28px; font-size:18px; }}
  ul {{ line-height:1.9; }} .zaman {{ color:#8fb3cc; }}
  .igbar {{ margin:18px 0 4px; display:flex; gap:10px; flex-wrap:wrap; }}
  .ig {{ background:#12324f; color:#e8eef4; text-decoration:none; padding:8px 14px;
         border-radius:20px; font-size:14px; border:1px solid #1e4a70; }}
  .ig:hover {{ background:#1e4a70; }}
  .igbtn {{ cursor:pointer; font-family:inherit; }}
</style></head><body>
<h1>🐟 Balık</h1>
<div class="alt">{bugun.strftime("%d.%m.%Y")} itibarıyla 7 günlük görünüm</div>
<div class="ozet">🌡 Deniz suyu: <b>{su} °C</b><br>🐟 Bu ay beklenen: <b>{TURLER[bugun.month]}</b></div>
<div class="kartlar">{"".join(kartlar)}</div>
{ig_html}
<h2>🎣 Balıkçı kanalları</h2><ul>{yt_html}</ul>
<h2>📰 Basın sinyalleri</h2><ul>{sinyal_html}</ul>
</body></html>"""

yol = os.environ.get("CIKTI", os.path.expanduser("~/balik_raporu.html"))
with open(yol, "w", encoding="utf-8") as f:
    f.write(html)
if not os.environ.get("GITHUB_ACTIONS"):
    webbrowser.open("file://" + yol)
