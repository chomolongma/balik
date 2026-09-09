import json, urllib.request, datetime, webbrowser, os, math
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
    saat %= 24
    h = int(saat)
    m = int(round((saat - h) * 60))
    if m == 60: h, m = (h + 1) % 24, 0
    return f"{h:02d}:{m:02d}"

def solunar_pencereler(t):
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

en_iyi = max(tum_gunler, key=lambda g: g["skor"])
en_iyi_ad = "BUGÜN" if en_iyi is bugun_v else f"{gunler[en_iyi['t'].weekday()]} {en_iyi['t'].day:02d}.{en_iyi['t'].month:02d}"

# ================= SAAT DALGASI =================
def pencere_merkez(a, b):
    return (a + ((b - a) % 24) / 2) % 24

def dairesel_fark(s, c):
    f = abs(s - c) % 24
    return min(f, 24 - f)

def saat_cevir(hhmm):
    h, m = hhmm.split(":")
    return int(h) + int(m) / 60

def dalga_ciz(g, gorunur, mobil=False):
    if mobil:
        GW, GH, GS = 390, 168, 16
        TABAN, TAVAN = 112, 34
        f_tepe, f_dip, f_eksen, f_gunes = 15, 14, 12, 13
        eksen_adim = 6
    else:
        GW, GH, GS = 680, 150, 26
        TABAN, TAVAN = 104, 30
        f_tepe, f_dip, f_eksen, f_gunes = 13, 13, 12, 12
        eksen_adim = 3

    def x_koy(saat): return GS + saat / 24 * (GW - 2 * GS)
    def y_koy(a): return TABAN - a * (TABAN - TAVAN)

    majorler, minorler = solunar_pencereler(g["t"])
    major_m = [pencere_merkez(a, b) for a, b in majorler]
    minor_m = [pencere_merkez(a, b) for a, b in minorler]

    def aktivite(s):
        a = 0.0
        for c in major_m:
            a += 1.0 * math.exp(-(dairesel_fark(s, c) ** 2) / (2 * 1.3 ** 2))
        for c in minor_m:
            a += 0.5 * math.exp(-(dairesel_fark(s, c) ** 2) / (2 * 0.9 ** 2))
        return min(a, 1.0)

    dogus_s, batis_s = saat_cevir(g["dogus"]), saat_cevir(g["batis"])

    nokta_list = []
    s = 0.0
    while s <= 24.001:
        nokta_list.append(f"{x_koy(s):.1f},{y_koy(aktivite(s)):.1f}")
        s += 1 / 6
    yol = (f"M {x_koy(0):.1f},{TABAN} L " + " L ".join(nokta_list)
           + f" L {x_koy(24):.1f},{TABAN} Z")

    gid = g["t"].isoformat()
    on_ek = "m-" if mobil else ""
    sky_id = f"sky-{on_ek}{gid}"
    verim_id = f"verim-{on_ek}{gid}"

    # Gökyüzü: gece koyu, gündüz açık, tan geçişleri yumuşak
    c = (f'<defs><linearGradient id="{sky_id}" x1="0" x2="1" y1="0" y2="0">'
         f'<stop offset="0%" stop-color="#0a1020"/>'
         f'<stop offset="{dogus_s/24*100-2:.1f}%" stop-color="#0a1020"/>'
         f'<stop offset="{dogus_s/24*100+2:.1f}%" stop-color="#2b3a52"/>'
         f'<stop offset="{batis_s/24*100-2:.1f}%" stop-color="#2b3a52"/>'
         f'<stop offset="{batis_s/24*100+2:.1f}%" stop-color="#0a1020"/>'
         f'<stop offset="100%" stop-color="#0a1020"/></linearGradient>'
         # Verim: tepe yeşil, orta sarı, dip kızıl
         f'<linearGradient id="{verim_id}" x1="0" x2="0" y1="0" y2="1">'
         f'<stop offset="0%" stop-color="#22c55e" stop-opacity="0.85"/>'
         f'<stop offset="45%" stop-color="#eab308" stop-opacity="0.55"/>'
         f'<stop offset="100%" stop-color="#7f1d1d" stop-opacity="0.45"/>'
         f'</linearGradient></defs>'
         f'<rect x="{GS}" y="{TAVAN-6}" width="{GW-2*GS}" height="{TABAN-TAVAN+6}" '
         f'fill="url(#{sky_id})" rx="8"/>'
         f'<path d="{yol}" fill="url(#{verim_id})"/>'
         f'<path d="{yol}" fill="none" stroke="#4ade80" stroke-width="2.5"/>')

    # Tepe etiketleri (majör)
    for m in major_m:
        x, y = x_koy(m), y_koy(aktivite(m))
        c += (f'<text x="{x:.0f}" y="{y-8:.0f}" text-anchor="middle" fill="#4ade80" '
              f'font-size="{f_tepe}" font-weight="800">🐟 {s2str(m)}</text>')
    # Kabartı etiketleri (minör)
    for m in minor_m:
        x, y = x_koy(m), y_koy(aktivite(m))
        c += (f'<text x="{x:.0f}" y="{y-6:.0f}" text-anchor="middle" fill="#60a5fa" '
              f'font-size="{f_tepe}" font-weight="700">{s2str(m)}</text>')
    # Dip etiketleri: grafiğin iç tabanında, tepe fontuyla aynı boy/renk
    tum_vakitler = sorted(major_m + minor_m)
    for i2 in range(len(tum_vakitler)):
        a2 = tum_vakitler[i2]
        b2 = tum_vakitler[(i2 + 1) % len(tum_vakitler)]
        orta = (a2 + ((b2 - a2) % 24) / 2) % 24
        x = x_koy(orta)
        c += (f'<text x="{x:.0f}" y="{TABAN+40}" text-anchor="middle" fill="#4ade80" '
              f'font-size="{f_dip}" font-weight="800">{s2str(orta)}</text>')
    # Saat ekseni
    for saat in range(0, 25, eksen_adim):
        x = x_koy(saat)
        c += (f'<line x1="{x:.0f}" y1="{TABAN}" x2="{x:.0f}" y2="{TABAN+6}" stroke="#334155"/>'
              f'<text x="{x:.0f}" y="{TABAN+22}" text-anchor="middle" fill="#7d8b96" '
              f'font-size="{f_eksen}">{saat:02d}</text>')
    c += f'<line x1="{GS}" y1="{TABAN}" x2="{GW-GS}" y2="{TABAN}" stroke="#334155" stroke-width="2"/>'
    # Doğuş/batış saatleri (turuncu)
    for hhmm, sx in ((g["dogus"], dogus_s), (g["batis"], batis_s)):
        c += (f'<text x="{x_koy(sx):.0f}" y="{TAVAN-12}" text-anchor="middle" '
              f'fill="#f59e0b" font-size="{f_gunes}" font-weight="700">{hhmm}</text>')
    # ŞİMDİ çizgisi (sadece bugün; JS canlı taşır)
    if gorunur:
        simdi_id = "simdi-m" if mobil else "simdi"
        c += (f'<g id="{simdi_id}"><line x1="0" y1="{TAVAN-16}" x2="0" y2="{TABAN}" '
              f'stroke="#ef4444" stroke-width="3"/>'
              f'<text x="0" y="{TAVAN-22}" text-anchor="middle" fill="#ef4444" '
              f'font-size="12" font-weight="800">ŞİMDİ</text></g>')

    snf = "dalga-m" if mobil else "dalga-d"
    snf2 = " secili" if gorunur else ""
    return (f'<div class="dalga {snf}{snf2}" id="dalga-{on_ek}{gid}">'
            f'<svg viewBox="0 0 {GW} {GH+34}" style="width:100%;height:auto">{c}</svg></div>')

dalgalar = "".join(dalga_ciz(g, i == 0) for i, g in enumerate(tum_gunler))
dalgalar += "".join(dalga_ciz(g, i == 0, mobil=True) for i, g in enumerate(tum_gunler))

# ================= HAFTALIK GRAFİK =================
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
        f'<text x="{x:.0f}" y="{H-6}" text-anchor="middle" fill="#475569" font-size="12">{gad}</text>')
grafik = (f'<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto">'
          f'<polyline points="{" ".join(noktalar)}" fill="none" stroke="#334155" stroke-width="2"/>'
          + "".join(etiketler) + '</svg>')

# ================= SONRAKİ GÜNLER =================
serit = ""
for g in tum_gunler:
    bugun_mu = g is bugun_v
    yildiz = "⭐ " if g is en_iyi else ""
    serit += f"""
    <div class="skart" data-gun="{g['t'].isoformat()}" data-ad="{gunler[g['t'].weekday()]} {g['t'].day:02d}.{g['t'].month:02d}" onclick="dalgaSec(this)" style="border-top:5px solid {g['renk']}; cursor:pointer">
      <div class="skart-gun">{yildiz}{gunler[g['t'].weekday()]} <span>{g['t'].day:02d}.{g['t'].month:02d}</span></div>
      <div class="skart-ikon">{g['ikon']}</div>
      <div class="skart-skor" style="color:{g['renk']}">{g['skor']}</div>
      <div class="skart-detay">💨{g['ruzgar']:.0f}kn 🌊{g['dalga']:.1f}m</div>
      {"<div class='rozet'>🎣 basınç avantajı</div>" if g['basinc_bonus'] else ""}
    </div>"""

# ================= INSTAGRAM =================
ig_linkler, ig_urller = [], []
for isim, hesap in INSTAGRAM.items():
    url = f"https://www.instagram.com/{hesap}/"
    ig_urller.append(url)
    ig_linkler.append(f'<a class="ig" href="{url}" target="_blank">📷 {isim}</a>')
js_liste = ",".join(f"'{u}'" for u in ig_urller)
ig_html = (f'<div class="igbar">{"".join(ig_linkler)}'
           f'<button class="ig igbtn" onclick="[{js_liste}].forEach(u=>window.open(u))">'
           f'⚡ Hepsini aç</button></div>')

# ================= YOUTUBE =================
yt_html = ""
for yas, kanal, turler, baslik in videolari_getir():
    ne_zaman = "bugün" if yas == 0 else ("dün" if yas == 1 else f"{yas} gün önce")
    etiket = f'<span class="tur">{"/".join(turler)}</span> ' if turler else ""
    yt_html += (f'<div class="sinyal">{etiket}<b>@{kanal}</b> '
                f'<span class="zaman">{ne_zaman}</span><br>{baslik[:90]}</div>')
if not yt_html:
    yt_html = '<div class="sinyal">Son 14 günde video yok.</div>'

# ================= BASIN =================
sinyal_html = ""
for yas, turler, baslik in sinyalleri_getir():
    ne_zaman = "bugün" if yas == 0 else ("dün" if yas == 1 else f"{yas} gün önce")
    sinyal_html += (f'<div class="sinyal"><span class="tur">{"/".join(turler)}</span> '
                    f'<span class="zaman">{ne_zaman}</span><br>{baslik[:90]}</div>')
if not sinyal_html:
    sinyal_html = '<div class="sinyal">Son 14 günde basın sinyali yok.</div>'

# ================= SAYFA =================
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

  h2 {{ font-size:17px; margin:20px 0 10px; color:#aebac4; }}
  .grafik {{ background:#0c0f12; border-radius:18px; padding:10px 6px 4px; }}

  .dalga {{ display:none; }}
  .dalga-d.secili {{ display:block; }}
  @media (max-width: 600px) {{
    .dalga-d.secili {{ display:none; }}
    .dalga-m.secili {{ display:block; }}
  }}

  .serit {{ display:flex; gap:10px; overflow-x:auto; padding-bottom:6px;
            -webkit-overflow-scrolling:touch; scrollbar-width:none; }}
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

<h2>📅 Sonraki günler</h2>
<div class="serit">{serit}</div>

<h2>⏰ Saatler — <span id="dalga-baslik">bugün</span></h2>
<div class="grafik">{dalgalar}</div>

<h2>📈 Haftanın seyri</h2>
<div class="grafik">{grafik}</div>

<div class="sinyal" style="background:#14181d">🐟 <b>Bu ay beklenen:</b> {TURLER[bugun.month]}</div>

<h2>📷 Taze kaynaklar</h2>
{ig_html}

<h2>🎣 Balıkçı kanalları</h2>
{yt_html}

<h2>📰 Basın sinyalleri</h2>
{sinyal_html}

<script>
function dalgaSec(kart) {{
  document.querySelectorAll('.dalga').forEach(function(d) {{ d.classList.remove('secili'); }});
  var g = kart.dataset.gun;
  document.getElementById('dalga-' + g).classList.add('secili');
  document.getElementById('dalga-m-' + g).classList.add('secili');
  document.getElementById('dalga-baslik').textContent = kart.dataset.ad;
  document.querySelectorAll('.skart').forEach(function(k) {{ k.style.outline = ''; }});
  kart.style.outline = '2px solid #4ade80';
}}
function simdiGuncelle() {{
  var d = new Date();
  var s = d.getHours() + d.getMinutes() / 60;
  var gd = document.getElementById('simdi');
  var gm = document.getElementById('simdi-m');
  if (gd) gd.setAttribute('transform', 'translate(' + (26 + s / 24 * (680 - 52)) + ',0)');
  if (gm) gm.setAttribute('transform', 'translate(' + (16 + s / 24 * (390 - 32)) + ',0)');
}}
simdiGuncelle();
setInterval(simdiGuncelle, 60000);
</script>
</body></html>"""

yol = os.environ.get("CIKTI", os.path.expanduser("~/balik_raporu.html"))
with open(yol, "w", encoding="utf-8") as f:
    f.write(html)
if not os.environ.get("GITHUB_ACTIONS"):
    webbrowser.open("file://" + yol)
