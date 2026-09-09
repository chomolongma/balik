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
    batis =
