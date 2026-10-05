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
        opens = quote["open"]
        data_bersih = []
        for i in range(len(highs)):
            if highs[i] and lows[i] and closes[i] and opens[i]:
                data_bersih.append({
                    "open": opens[i],
                    "high": highs[i],
                    "low": lows[i],
                    "close": closes[i]
                })
        return data_bersih
    except Exception as e:
        print(f"Error ambil OHLC {symbol}: {e}")
    return []

# ============ DETEKSI SWING ============
def deteksi_swing(data, kiri=2, kanan=2):
    swing_highs = []
    swing_lows = []
    for i in range(kiri, len(data) - kanan):
        is_sh = True
        for j in range(1, kiri + 1):
            if data[i]["high"] <= data[i - j]["high"]:
                is_sh = False
                break
        for j in range(1, kanan + 1):
            if data[i]["high"] <= data[i + j]["high"]:
                is_sh = False
                break
        if is_sh:
            swing_highs.append({"index": i, "harga": data[i]["high"]})
        
        is_sl = True
        for j in range(1, kiri + 1):
            if data[i]["low"] >= data[i - j]["low"]:
                is_sl = False
                break
        for j in range(1, kanan + 1):
            if data[i]["low"] >= data[i + j]["low"]:
                is_sl = False
                break
        if is_sl:
            swing_lows.append({"index": i, "harga": data[i]["low"]})
    return swing_highs, swing_lows

# ============ ANALISIS TREND ============
def analisis_trend(swing_highs, swing_lows):
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return "DATA KURANG", "Butuh minimal 2 swing"
    
    sh_last = swing_highs[-1]["harga"]
    sh_prev = swing_highs[-2]["harga"]
    sl_last = swing_lows[-1]["harga"]
    sl_prev = swing_lows[-2]["harga"]
    
    if sh_last > sh_prev:
        struktur_high = "HH"
        bias_h = "bullish"
    else:
        struktur_high = "LH"
        bias_h = "bearish"
    
    if sl_last > sl_prev:
        struktur_low = "HL"
        bias_l = "bullish"
    else:
        struktur_low = "LL"
        bias_l = "bearish"
    
    if bias_h == "bullish" and bias_l == "bullish":
        trend = "BULLISH"
    elif bias_h == "bearish" and bias_l == "bearish":
        trend = "BEARISH"
    else:
        trend = "RANGING"
    
    ket = f"High: {struktur_high}, Low: {struktur_low}"
    return trend, ket

# ============ DETEKSI BOS & MSS ============
def deteksi_bos_mss(data, swing_highs, swing_lows, trend):
    if not swing_highs or not swing_lows:
        return None, None
    harga = data[-1]["close"]
    sh = swing_highs[-1]["harga"]
    sl = swing_lows[-1]["harga"]
    bos = None
    mss = None
    if harga > sh:
        if trend == "BULLISH":
            bos = f"BOS Bullish (break ${round(sh, 2)})"
        elif trend == "BEARISH":
            mss = f"MSS Bullish (break ${round(sh, 2)})"
    if harga < sl:
        if trend == "BEARISH":
            bos = f"BOS Bearish (break ${round(sl, 2)})"
        elif trend == "BULLISH":
            mss = f"MSS Bearish (break ${round(sl, 2)})"
    return bos, mss

# ============ DETEKSI ORDER BLOCKS ============
def deteksi_ob(data):
    bullish_ob = []
    bearish_ob = []
    
    for i in range(1, len(data) - 1):
        # Bullish OB: candle bearish, candle berikutnya bullish kencang
        if data[i]["close"] < data[i]["open"]:  # bearish
            body_next = data[i+1]["close"] - data[i+1]["open"]
            body_curr = data[i]["open"] - data[i]["close"]
            if body_next > body_curr * 1.5 and data[i+1]["close"] > data[i]["high"]:
                bullish_ob.append({
                    "atas": data[i]["high"],
                    "bawah": data[i]["low"]
                })
        
        # Bearish OB: candle bullish, candle berikutnya bearish kencang
        if data[i]["close"] > data[i]["open"]:  # bullish
            body_next = data[i+1]["open"] - data[i+1]["close"]
            body_curr = data[i]["close"] - data[i]["open"]
            if body_next > body_curr * 1.5 and data[i+1]["close"] < data[i]["low"]:
                bearish_ob.append({
                    "atas": data[i]["high"],
                    "bawah": data[i]["low"]
                })
    
    return bullish_ob, bearish_ob

# ============ DETEKSI FVG ============
def deteksi_fvg(data):
    bullish_fvg = []
    bearish_fvg = []
    
    for i in range(1, len(data) - 1):
        # Bullish FVG: low candle i+1 > high candle i-1
        if data[i+1]["low"] > data[i-1]["high"]:
            bullish_fvg.append({
                "atas": data[i+1]["low"],
                "bawah": data[i-1]["high"]
            })
        
        # Bearish FVG: high candle i+1 < low candle i-1
        if data[i+1]["high"] < data[i-1]["low"]:
            bearish_fvg.append({
                "atas": data[i-1]["low"],
                "bawah": data[i+1]["high"]
            })
    
    return bullish_fvg, bearish_fvg

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

swing_highs, swing_lows = deteksi_swing(ohlc_gold, kiri=2, kanan=2)
trend, ket = analisis_trend(swing_highs, swing_lows)
bos, mss = deteksi_bos_mss(ohlc_gold, swing_highs, swing_lows, trend)
bull_ob, bear_ob = deteksi_ob(ohlc_gold)
bull_fvg, bear_fvg = deteksi_fvg(ohlc_gold)

print(f"Trend: {trend}")
print(f"Bullish OB: {len(bull_ob)}, Bearish OB: {len(bear_ob)}")
print(f"Bullish FVG: {len(bull_fvg)}, Bearish FVG: {len(bear_fvg)}")

# ============ SUSUN PESAN ============
tanggal = datetime.now().strftime("%d %B %Y")
pesan = "📊 *DATA MARKET GOLD*\n"
pesan = pesan + "📅 " + tanggal + "\n\n"

if gold:
    pesan += f"🥇 *GOLD*: ${round(gold, 2)} ({round(gold_chg, 2)}%)\n"
if dxy:
    pesan += f"💵 *DXY*: {round(dxy, 2)} ({round(dxy_chg, 2)}%)\n"
if yield10:
    pesan += f"📈 *US 10Y*: {round(yield10, 3)}% ({round(yield_chg, 3)}%)\n"

pesan += "\n---\n\n"
pesan += "📈 *ANALISIS TEKNIKAL (H1)*\n\n"
pesan += f"🎯 *TREND: {trend}*\n\n"

if len(swing_highs) >= 2 and len(swing_lows) >= 2:
    pesan += f"📊 *Swing High:* ${round(swing_highs[-1]['harga'], 2)}\n"
    pesan += f"📊 *Swing Low:* ${round(swing_lows[-1]['harga'], 2)}\n\n"
    pesan += f"📈 *Struktur:* {ket}\n\n"

if bos:
    pesan += f"🔔 *{bos}*\n\n"
if mss:
    pesan += f"🚨 *{mss}*\n\n"

# Order Blocks terakhir
if bull_ob:
    ob = bull_ob[-1]
    pesan += f"📦 *Bullish OB:* ${round(ob['bawah'], 2)} - ${round(ob['atas'], 2)}\n"
if bear_ob:
    ob = bear_ob[-1]
    pesan += f"📦 *Bearish OB:* ${round(ob['bawah'], 2)} - ${round(ob['atas'], 2)}\n"
pesan += "\n"

# FVG terakhir
if bull_fvg:
    fvg = bull_fvg[-1]
    pesan += f"📊 *Bullish FVG:* ${round(fvg['bawah'], 2)} - ${round(fvg['atas'], 2)}\n"
if bear_fvg:
    fvg = bear_fvg[-1]
    pesan += f"📊 *Bearish FVG:* ${round(fvg['bawah'], 2)} - ${round(fvg['atas'], 2)}\n"

# ============ KIRIM TELEGRAM ============
url_tg = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
r = requests.post(url_tg, data={
    "chat_id": CHAT_ID,
    "text": pesan,
    "parse_mode": "Markdown"
})

print("Terkirim!" if r.status_code == 200 else f"Gagal: {r.json()}")
print("Selesai!")
