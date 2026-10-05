import requests
import os
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ============ AMBIL DATA HARGA ============
def ambil_harga(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
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

# ============ AMBIL DATA OHLC ============
def ambil_ohlc(symbol, interval="1h", range_="1mo"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range_}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        result = data["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        highs = quote["high"]
        lows = quote["low"]
        closes = quote["close"]
        data_bersih = []
        for i in range(len(highs)):
            if highs[i] is not None and lows[i] is not None and closes[i] is not None:
                data_bersih.append({
                    "high": highs[i],
                    "low": lows[i],
                    "close": closes[i]
                })
        return data_bersih
    except Exception as e:
        print(f"Error ambil OHLC {symbol}: {e}")
    return []

# ============ DETEKSI SWING HIGH/LOW ============
def deteksi_swing(data, kiri=2, kanan=2):
    swing_highs = []
    swing_lows = []
    
    for i in range(kiri, len(data) - kanan):
        is_swing_high = True
        for j in range(1, kiri + 1):
            if data[i]["high"] <= data[i - j]["high"]:
                is_swing_high = False
                break
        for j in range(1, kanan + 1):
            if data[i]["high"] <= data[i + j]["high"]:
                is_swing_high = False
                break
        if is_swing_high:
            swing_highs.append({"index": i, "harga": data[i]["high"]})
        
        is_swing_low = True
        for j in range(1, kiri + 1):
            if data[i]["low"] >= data[i - j]["low"]:
                is_swing_low = False
                break
        for j in range(1, kanan + 1):
            if data[i]["low"] >= data[i + j]["low"]:
                is_swing_low = False
                break
        if is_swing_low:
            swing_lows.append({"index": i, "harga": data[i]["low"]})
    
    return swing_highs, swing_lows

# ============ ANALISIS TREND ============
def analisis_trend(swing_highs, swing_lows):
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "DATA KURANG", "Butuh minimal 2 swing high & 2 swing low"
    
    sh_terakhir = swing_highs[-1]["harga"]
    sh_sebelum = swing_highs[-2]["harga"]
    sl_terakhir = swing_lows[-1]["harga"]
    sl_sebelum = swing_lows[-2]["harga"]
    
    if sh_terakhir > sh_sebelum:
        struktur_high = "HH (Higher High)"
        bias_high = "bullish"
    else:
        struktur_high = "LH (Lower High)"
        bias_high = "bearish"
    
    if sl_terakhir > sl_sebelum:
        struktur_low = "HL (Higher Low)"
        bias_low = "bullish"
    else:
        struktur_low = "LL (Lower Low)"
        bias_low = "bearish"
    
    if bias_high == "bullish" and bias_low == "bullish":
        trend = "BULLISH"
    elif bias_high == "bearish" and bias_low == "bearish":
        trend = "BEARISH"
    else:
        trend = "RANGING"
    
    keterangan = f"High: {struktur_high}\nLow: {struktur_low}"
    return trend, keterangan

# ============ DETEKSI BOS & MSS ============
def deteksi_bos_mss(data, swing_highs, swing_lows, trend):
    if len(swing_highs) < 1 or len(swing_lows) < 1:
        return None, None
    
    harga_terakhir = data[-1]["close"]
    sh_terakhir = swing_highs[-1]["harga"]
    sl_terakhir = swing_lows[-1]["harga"]
    
    bos = None
    mss = None
    
    # Cek BOS Bullish (harga break swing high terakhir)
    if harga_terakhir > sh_terakhir:
        if trend == "BULLISH":
            bos = f"BOS BULLISH (break ${round(sh_terakhir, 2)})"
        elif trend == "BEARISH":
            mss = f"MSS BULLISH (break ${round(sh_terakhir, 2)}) - sinyal reversal"
    
    # Cek BOS Bearish (harga break swing low terakhir)
    if harga_terakhir < sl_terakhir:
        if trend == "BEARISH":
            bos = f"BOS BEARISH (break ${round(sl_terakhir, 2)})"
        elif trend == "BULLISH":
            mss = f"MSS BEARISH (break ${round(sl_terakhir, 2)}) - sinyal reversal"
    
    return bos, mss

# ============ MAIN ============
print("Ambil data Gold...")
gold, gold_chg = ambil_harga("GC=F")

print("Ambil data DXY...")
dxy, dxy_chg = ambil_harga("DX-Y.NYB")

print("Ambil data US 10Y...")
yield10, yield_chg = ambil_harga("^TNX")

print("Ambil data OHLC Gold (H1)...")
ohlc_gold = ambil_ohlc("GC=F", interval="1h", range_="1mo")
print(f"Total candle: {len(ohlc_gold)}")

# Deteksi swing
swing_highs, swing_lows = deteksi_swing(ohlc_gold, kiri=2, kanan=2)
print(f"Swing High: {len(swing_highs)}, Swing Low: {len(swing_lows)}")

# Analisis trend
trend, keterangan = analisis_trend(swing_highs, swing_lows)
print(f"Trend: {trend}")

# Deteksi BOS & MSS
bos, mss = deteksi_bos_mss(ohlc_gold, swing_highs, swing_lows, trend)
print(f"BOS: {bos}")
print(f"MSS: {mss}")

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
    pesan = pesan + f"Perubahan: {round(yield_chg, 3)}%\n\n"

# Bagian Analisis Teknikal
pesan = pesan + "---\n\n"
pesan = pesan + "📈 *ANALISIS TEKNIKAL (H1)*\n\n"
pesan = pesan + f"🎯 *TREND: {trend}*\n\n"

if len(swing_highs) >= 2 and len(swing_lows) >= 2:
    pesan = pesan + "📊 *SWING TERAKHIR:*\n"
    pesan = pesan + f"• Swing High: ${round(swing_highs[-1]['harga'], 2)}\n"
    pesan = pesan + f"• Swing Low: ${round(swing_lows[-1]['harga'], 2)}\n\n"
    
    pesan = pesan + "📈 *MARKET STRUCTURE:*\n"
    pesan = pesan + keterangan + "\n\n"

if bos:
    pesan = pesan + f"🔔 *{bos}*\n\n"

if mss:
    pesan = pesan + f"🚨 *{mss}*\n\n"

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
