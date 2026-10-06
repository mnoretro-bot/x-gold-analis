import requests
import os
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ============ AMBIL HARGA ============
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
            return closes[-1], ((closes[-1] - closes[-2]) / closes[-2]) * 100
    except Exception as e:
        print(f"Error: {e}")
    return None, None

# ============ AMBIL OHLC ============
def ambil_ohlc(symbol, interval="1h", range_="1mo"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range_}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        result = data["chart"]["result"][0]
        q = result["indicators"]["quote"][0]
        out = []
        for i in range(len(q["high"])):
            if q["high"][i] and q["low"][i] and q["close"][i] and q["open"][i]:
                out.append({
                    "open": q["open"][i], "high": q["high"][i],
                    "low": q["low"][i], "close": q["close"][i]
                })
        return out
    except:
        return []

# ============ GABUNG CANDLE H1 -> H4 ============
def gabung_h4(data_h1):
    h4 = []
    for i in range(0, len(data_h1) - 3, 4):
        candle = data_h1[i:i+4]
        h4.append({
            "open": candle[0]["open"],
            "high": max(c["high"] for c in candle),
            "low": min(c["low"] for c in candle),
            "close": candle[-1]["close"]
        })
    return h4

# ============ SWING ============
def deteksi_swing(data, kiri=2, kanan=2):
    sh, sl = [], []
    for i in range(kiri, len(data) - kanan):
        is_sh = all(data[i]["high"] > data[i-j]["high"] for j in range(1, kiri+1)) and \
                all(data[i]["high"] > data[i+j]["high"] for j in range(1, kanan+1))
        if is_sh:
            sh.append({"index": i, "harga": data[i]["high"]})
        is_sl = all(data[i]["low"] < data[i-j]["low"] for j in range(1, kiri+1)) and \
                all(data[i]["low"] < data[i+j]["low"] for j in range(1, kanan+1))
        if is_sl:
            sl.append({"index": i, "harga": data[i]["low"]})
    return sh, sl

# ============ TREND ============
def analisis_trend(sh, sl):
    if len(sh) < 2 or len(sl) < 2:
        return "RANGING", "Data kurang", 0
    if sh[-1]["harga"] > sh[-2]["harga"]:
        bh = "bullish"
    else:
        bh = "bearish"
    if sl[-1]["harga"] > sl[-2]["harga"]:
        bl = "bullish"
    else:
        bl = "bearish"
    if bh == "bullish" and bl == "bullish":
        return "BULLISH", "HH + HL", 1
    elif bh == "bearish" and bl == "bearish":
        return "BEARISH", "LH + LL", -1
    return "RANGING", "Mixed", 0

# ============ BOS & MSS ============
def deteksi_bos_mss(data, sh, sl, trend):
    if not sh or not sl:
        return None, None
    harga = data[-1]["close"]
    bos, mss = None, None
    if harga > sh[-1]["harga"]:
        if trend == "BULLISH":
            bos = f"BOS Bullish (${round(sh[-1]['harga'], 2)})"
        elif trend == "BEARISH":
            mss = f"MSS Bullish (${round(sh[-1]['harga'], 2)})"
    if harga < sl[-1]["harga"]:
        if trend == "BEARISH":
            bos = f"BOS Bearish (${round(sl[-1]['harga'], 2)})"
        elif trend == "BULLISH":
            mss = f"MSS Bearish (${round(sl[-1]['harga'], 2)})"
    return bos, mss

# ============ ORDER BLOCK ============
def deteksi_ob(data):
    bull, bear = [], []
    for i in range(1, len(data) - 1):
        if data[i]["close"] < data[i]["open"]:
            bn = data[i+1]["close"] - data[i+1]["open"]
            bc = data[i]["open"] - data[i]["close"]
            if bn > bc * 1.5 and data[i+1]["close"] > data[i]["high"]:
                bull.append({"atas": data[i]["high"], "bawah": data[i]["low"]})
        if data[i]["close"] > data[i]["open"]:
            bn = data[i+1]["open"] - data[i+1]["close"]
            bc = data[i]["close"] - data[i]["open"]
            if bn > bc * 1.5 and data[i+1]["close"] < data[i]["low"]:
                bear.append({"atas": data[i]["high"], "bawah": data[i]["low"]})
    return bull, bear

# ============ FVG ============
def deteksi_fvg(data):
    bull, bear = [], []
    for i in range(1, len(data) - 1):
        if data[i+1]["low"] > data[i-1]["high"]:
            bull.append({"atas": data[i+1]["low"], "bawah": data[i-1]["high"]})
        if data[i+1]["high"] < data[i-1]["low"]:
            bear.append({"atas": data[i-1]["low"], "bawah": data[i+1]["high"]})
    return bull, bear

# ============ PROBABILITAS PER TIMEFRAME ============
def probabilitas_tf(data, nama_tf):
    sh, sl = deteksi_swing(data)
    trend, ket, skor_trend = analisis_trend(sh, sl)
    
    bobot = {"bullish": 0, "bearish": 0, "netral": 0}
    
    # Trend (bobot 100)
    if trend == "BULLISH":
        bobot["bullish"] += 100
    elif trend == "BEARISH":
        bobot["bearish"] += 100
    else:
        bobot["netral"] += 100
    
    # Cek BOS/MSS di timeframe ini
    bos, mss = deteksi_bos_mss(data, sh, sl, trend)
    if bos:
        if "Bullish" in bos:
            bobot["bullish"] += 50
        else:
            bobot["bearish"] += 50
    if mss:
        if "Bullish" in mss:
            bobot["bullish"] += 50
        else:
            bobot["bearish"] += 50
    
    netral_setengah = bobot["netral"] / 2
    skor_bull = bobot["bullish"] + netral_setengah
    skor_bear = bobot["bearish"] + netral_setengah
    total = skor_bull + skor_bear
    
    if total == 0:
        return 50, 50, trend, ket, bos, mss
    prob_bull = round((skor_bull / total) * 100)
    prob_bear = 100 - prob_bull
    return prob_bull, prob_bear, trend, ket, bos, mss

# ============ MAIN ============
print("Ambil data...")
gold, gold_chg = ambil_harga("GC=F")
dxy, dxy_chg = ambil_harga("DX-Y.NYB")
yield10, yield_chg = ambil_harga("^TNX")

print("Ambil data H1...")
data_h1 = ambil_ohlc("GC=F", interval="1h", range_="1mo")
print(f"H1 candles: {len(data_h1)}")

print("Gabung H1 jadi H4...")
data_h4 = gabung_h4(data_h1)
print(f"H4 candles: {len(data_h4)}")

print("Ambil data M15...")
data_m15 = ambil_ohlc("GC=F", interval="15m", range_="7d")
print(f"M15 candles: {len(data_m15)}")

# Hitung probabilitas per timeframe
prob_h4_bull, prob_h4_bear, trend_h4, ket_h4, bos_h4, mss_h4 = probabilitas_tf(data_h4, "H4")
prob_h1_bull, prob_h1_bear, trend_h1, ket_h1, bos_h1, mss_h1 = probabilitas_tf(data_h1, "H1")
prob_m15_bull, prob_m15_bear, trend_m15, ket_m15, bos_m15, mss_m15 = probabilitas_tf(data_m15, "M15")

# Probabilitas gabungan (bobot: H4 40%, H1 35%, M15 25%)
prob_bull_total = round(prob_h4_bull * 0.4 + prob_h1_bull * 0.35 + prob_m15_bull * 0.25)
prob_bear_total = 100 - prob_bull_total

# ============ SUSUN PESAN ============
tanggal = datetime.now().strftime("%d %B %Y")
pesan = "📊 *DATA MARKET GOLD*\n"
pesan += f"📅 {tanggal}\n\n"

if gold:
    pesan += f"🥇 *GOLD*: ${round(gold, 2)} ({round(gold_chg, 2)}%)\n"
if dxy:
    pesan += f"💵 *DXY*: {round(dxy, 2)} ({round(dxy_chg, 2)}%)\n"
if yield10:
    pesan += f"📈 *US 10Y*: {round(yield10, 3)}% ({round(yield_chg, 3)}%)\n"

pesan += "\n---\n\n"
pesan += "🎯 *PROBABILITAS MULTI-TIMEFRAME*\n\n"

pesan += f"🗓️ *H4 (Mingguan):*\n"
pesan += f"  📈 Bullish: {prob_h4_bull}%\n"
pesan += f"  📉 Bearish: {prob_h4_bear}%\n"
pesan += f"  Trend: {trend_h4}\n\n"

pesan += f"📅 *H1 (Harian):*\n"
pesan += f"  📈 Bullish: {prob_h1_bull}%\n"
pesan += f"  📉 Bearish: {prob_h1_bear}%\n"
pesan += f"  Trend: {trend_h1}\n\n"

pesan += f"⏰ *M15 (Jangka Pendek):*\n"
pesan += f"  📈 Bullish: {prob_m15_bull}%\n"
pesan += f"  📉 Bearish: {prob_m15_bear}%\n"
pesan += f"  Trend: {trend_m15}\n\n"

pesan += "---\n\n"
pesan += "💡 *KESIMPULAN GABUNGAN:*\n\n"
pesan += f"📈 Bullish: *{prob_bull_total}%*\n"
pesan += f"📉 Bearish: *{prob_bear_total}%*\n\n"

# Interpretasi
if prob_bull_total >= 65:
    pesan += "🎯 Bias: *STRONG BULLISH*\n"
elif prob_bull_total >= 55:
    pesan += "🎯 Bias: *BULLISH*\n"
elif prob_bear_total >= 65:
    pesan += "🎯 Bias: *STRONG BEARISH*\n"
elif prob_bear_total >= 55:
    pesan += "🎯 Bias: *BEARISH*\n"
else:
    pesan += "🎯 Bias: *NETRAL / RANGING*\n"

# ============ KIRIM ============
url_tg = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
r = requests.post(url_tg, data={"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"})
print("Terkirim!" if r.status_code == 200 else f"Gagal: {r.json()}")
print("Selesai!")
