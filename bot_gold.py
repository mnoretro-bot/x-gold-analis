import requests
import os
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ============ AMBIL DATA VIA YAHOO FINANCE API ============
def ambil_harga(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        if len(closes) >= 2:
            harga_sekarang = closes[-1]
            harga_sebelum = closes[-2]
            perubahan = ((harga_sekarang - harga_sebelum) / harga_sebelum) * 100
            return harga_sekarang, perubahan
    except Exception as e:
        print(f"Error ambil {symbol}: {e}")
    return None, None

# Ambil data
print("Ambil data Gold...")
gold, gold_chg = ambil_harga("GC=F")

print("Ambil data DXY...")
dxy, dxy_chg = ambil_harga("DX-Y.NYB")

print("Ambil data US 10Y Yield...")
yield10, yield_chg = ambil_harga("^TNX")

# ============ SUSUN PESAN ============
tanggal = datetime.now().strftime("%d %B %Y")
pesan = "📊 *DATA MARKET GOLD*\n"
pesan = pesan + "📅 " + tanggal + "\n\n"

if gold:
    pesan = pesan + "🥇 *GOLD (XAUUSD)*:\n"
    pesan = pesan + f"Harga: ${round(gold, 2)}\n"
    pesan = pesan + f"Perubahan: {round(gold_chg, 2)}%\n\n"

if dxy:
    pesan = pesan + "💵 *DXY (Dollar Index)*:\n"
    pesan = pesan + f"Nilai: {round(dxy, 2)}\n"
    pesan = pesan + f"Perubahan: {round(dxy_chg, 2)}%\n\n"

if yield10:
    pesan = pesan + "📈 *US 10Y YIELD*:\n"
    pesan = pesan + f"Nilai: {round(yield10, 3)}%\n"
    pesan = pesan + f"Perubahan: {round(yield_chg, 3)}%\n"

# ============ KIRIM TELEGRAM ============
url_tg = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
r = requests.post(url_tg, data={
    "chat_id": CHAT_ID,
    "text": pesan,
    "parse_mode": "Markdown"
})

if r.status_code == 200:
    print("Terkirim!")
else:
    print(f"Gagal: {r.json()}")

print("Selesai!")
