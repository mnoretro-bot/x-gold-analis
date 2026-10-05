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
        return "RANGING", "Data kurang"
    if sh[-1]["harga"] > sh[-2]["harga"]:
        h = "HH"
        bh = "bullish"
    else:
        h = "LH"
        bh = "bearish"
    if sl[-1]["harga"] > sl[-2]["harga"]:
        l = "HL"
        bl = "bullish"
    else:
        l = "LL"
        bl = "bearish"
    if bh == "bullish" and bl == "bullish":
        return "BULLISH", f"{h} + {l}"
    elif bh == "bearish" and bl == "bearish":
        return "BEARISH", f"{h} + {l}"
    return "RANGING", f"{h} + {l}"

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

# ============ PROBABILITAS ============
def hitung_probabilitas(gold_chg, dxy_chg, yield_chg, trend):
    bobot = {"bullish": 0, "bearish": 0, "netral": 0}
    alasan = []
    
    # Gold trend (bobot 20)
    if gold_chg is not None:
        if gold_chg > 0.1:
            bobot["bullish"] += 20
            alasan.append(f"Gold naik {round(gold_chg, 2)}% -> Bullish (+20)")
        elif gold_chg < -0.1:
            bobot["bearish"] += 20
            alasan.append(f"Gold turun {round(gold_chg, 2)}% -> Bearish (+20)")
        else:
            bobot["netral"] += 20
            alasan.append(f"Gold flat {round(gold_chg, 2)}% -> Netral (+20)")
    
    # DXY (bobot 25) - korelasi negatif
    if dxy_chg is not None:
        if dxy_chg > 0.1:
            bobot["bearish"] += 25
            alasan.append(f"DXY naik {round(dxy_chg, 2)}% -> Bearish gold (+25)")
        elif dxy_chg < -0.1:
            bobot["bullish"] += 25
            alasan.append(f"DXY turun {round(dxy_chg, 2)}% -> Bullish gold (+25)")
        else:
            bobot["netral"] += 25
            alasan.append(f"DXY flat {round(dxy_chg, 2)}% -> Netral (+25)")
    
    # US 10Y (bobot 25) - korelasi negatif
    if yield_chg is not None:
        if yield_chg > 0.5:
            bobot["bearish"] += 25
            alasan.append(f"US 10Y naik {round(yield_chg, 2)}% -> Bearish gold (+25)")
        elif yield_chg < -0.5:
            bobot["bullish"] += 25
            alasan.append(f"US 10Y turun {round(yield_chg, 2)}% -> Bullish gold (+25)")
        else:
            bobot["netral"] += 25
            alasan.append(f"US 10Y flat {round(yield_chg, 2)}% -> Netral (+25)")
    
    # Trend (bobot 30)
    if trend == "BULLISH":
        bobot["bullish"] += 30
        alasan.append("Trend teknikal BULLISH (+30)")
    elif trend == "BEARISH":
        bobot["bearish"] += 30
        alasan.append("Trend teknikal BEARISH (+30)")
    else:
        bobot["netral"] += 30
        alasan.append("Trend teknikal RANGING (+30 netral)")
    
    prob_bull = round(bobot["bullish"])
    prob_bear = round(bobot["bearish"])
    prob_netral = round(bobot["netral"])
    
    # Kalau bull & bear dua-duanya 0, kasih 50/50
    if prob_bull == 0 and prob_bear == 0:
        prob_bull = 50
        prob_bear = 50
    
    return prob_bull, prob_bear, alasan

# ============ MAIN ============
print("Ambil data...")
gold, gold_chg = ambil_harga("GC=F")
dxy, dxy_chg = ambil_harga("DX-Y.NYB")
yield10, yield_chg = ambil_harga("^TNX")
ohlc_gold = ambil_ohlc("GC=F", interval="1h", range_="1mo")

sh, sl = deteksi_swing(ohlc_gold)
trend, ket = analisis_trend(sh, sl)
bos, mss = deteksi_bos_mss(ohlc_gold, sh, sl, trend)
bull_ob, bear_ob = deteksi_ob(ohlc_gold)
bull_fvg, bear_fvg = deteksi_fvg(ohlc_gold)

prob_bull, prob_bear, alasan_prob = hitung_probabilitas(gold_chg, dxy_chg, yield_chg, trend)

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
pesan += "🎯 *PROBABILITAS GOLD*\n\n"
pesan += f"📈 Bullish: *{prob_bull}%*\n"
pesan += f"📉 Bearish: *{prob_bear}%*\n\n"

pesan += "📊 *ALASAN:*\n"
for a in alasan_prob:
    pesan += f"• {a}\n"

pesan += "\n---\n\n"
pesan += "📈 *ANALISIS TEKNIKAL (H1)*\n\n"
pesan += f"🎯 *TREND: {trend}*\n\n"

if len(sh) >= 2 and len(sl) >= 2:
    pesan += f"📊 Swing High: ${round(sh[-1]['harga'], 2)}\n"
    pesan += f"📊 Swing Low: ${round(sl[-1]['harga'], 2)}\n\n"
    pesan += f"📈 Struktur: {ket}\n\n"

if bos:
    pesan += f"🔔 *{bos}*\n\n"
if mss:
    pesan += f"🚨 *{mss}*\n\n"

if bull_ob:
    ob = bull_ob[-1]
    pesan += f"📦 Bullish OB: ${round(ob['bawah'], 2)} - ${round(ob['atas'], 2)}\n"
if bear_ob:
    ob = bear_ob[-1]
    pesan += f"📦 Bearish OB: ${round(ob['bawah'], 2)} - ${round(ob['atas'], 2)}\n"

if bull_fvg:
    fvg = bull_fvg[-1]
    pesan += f"📊 Bullish FVG: ${round(fvg['bawah'], 2)} - ${round(fvg['atas'], 2)}\n"
if bear_fvg:
    fvg = bear_fvg[-1]
    pesan += f"📊 Bearish FVG: ${round(fvg['bawah'], 2)} - ${round(fvg['atas'], 2)}\n"

# ============ KIRIM ============
url_tg = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
r = requests.post(url_tg, data={"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"})
print("Terkirim!" if r.status_code == 200 else f"Gagal: {r.json()}")
print("Selesai!")
