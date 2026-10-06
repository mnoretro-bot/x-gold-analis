import requests
import feedparser
import os
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_KEY = os.environ.get("GROQ_API_KEY")

RSS_BERITA = [
    "https://www.fxstreet.com/rss/news",
    "https://www.kitco.com/rss/KitcoNews.xml",
    "https://www.investing.com/rss/news_285.rss"
]

def analisis_berita_ai(judul_berita):
    """Analisis berita pakai Groq AI"""
    if not GROQ_KEY:
        return "⚪ Netral"
    
    prompt = f"""Analisis sentimen berita ini untuk GOLD (XAUUSD).
Jawab HANYA dengan 1 kata: BULLISH, BEARISH, atau NETRAL.

Berita: {judul_berita}

Jawaban:"""
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": "Bearer " + GROQ_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        r = requests.post(url, headers=headers, json=data, timeout=15)
        hasil = r.json()
        if "choices" in hasil:
            jawaban = hasil["choices"][0]["message"]["content"].strip().upper()
            if "BULLISH" in jawaban:
                return "🟢 Bullish"
            elif "BEARISH" in jawaban:
                return "🔴 Bearish"
            else:
                return "⚪ Netral"
    except:
        pass
    return "⚪ Netral"

def ambil_berita_gold():
    """Ambil berita gold + sentiment AI"""
    berita_list = []
    for url in RSS_BERITA:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                judul = entry.title
                sentimen = analisis_berita_ai(judul)
                berita_list.append({
                    "judul": judul,
                    "sentimen": sentimen
                })
        except:
            pass
    return berita_list[:5]

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

def analisis_trend(sh, sl):
    if len(sh) < 2 or len(sl) < 2:
        return "RANGING", "Data kurang"
    if sh[-1]["harga"] > sh[-2]["harga"]:
        bh = "bullish"
    else:
        bh = "bearish"
    if sl[-1]["harga"] > sl[-2]["harga"]:
        bl = "bullish"
    else:
        bl = "bearish"
    if bh == "bullish" and bl == "bullish":
        return "BULLISH", "HH + HL"
    elif bh == "bearish" and bl == "bearish":
        return "BEARISH", "LH + LL"
    return "RANGING", "Mixed"

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

def deteksi_fvg(data):
    bull, bear = [], []
    for i in range(1, len(data) - 1):
        if data[i+1]["low"] > data[i-1]["high"]:
            bull.append({"atas": data[i+1]["low"], "bawah": data[i-1]["high"]})
        if data[i+1]["high"] < data[i-1]["low"]:
            bear.append({"atas": data[i-1]["low"], "bawah": data[i+1]["high"]})
    return bull, bear

def probabilitas_tf(data, nama_tf):
    sh, sl = deteksi_swing(data)
    trend, ket = analisis_trend(sh, sl)
    
    bobot = {"bullish": 0, "bearish": 0, "netral": 0}
    
    if trend == "BULLISH":
        bobot["bullish"] += 50
    elif trend == "BEARISH":
        bobot["bearish"] += 50
    else:
        bobot["netral"] += 50
    
    bos, mss = deteksi_bos_mss(data, sh, sl, trend)
    if bos:
        if "Bullish" in bos:
            bobot["bullish"] += 30
        else:
            bobot["bearish"] += 30
    if mss:
        if "Bullish" in mss:
            bobot["bullish"] += 30
        else:
            bobot["bearish"] += 30
    
    bull_ob, bear_ob = deteksi_ob(data)
    if bull_ob and not bear_ob:
        bobot["bullish"] += 15
    elif bear_ob and not bull_ob:
        bobot["bearish"] += 15
    else:
        bobot["netral"] += 15
    
    bull_fvg, bear_fvg = deteksi_fvg(data)
    if bull_fvg and not bear_fvg:
        bobot["bullish"] += 5
    elif bear_fvg and not bull_fvg:
        bobot["bearish"] += 5
    else:
        bobot["netral"] += 5
    
    netral_setengah = bobot["netral"] / 2
    skor_bull = bobot["bullish"] + netral_setengah
    skor_bear = bobot["bearish"] + netral_setengah
    total = skor_bull + skor_bear
    
    if total == 0:
        return 50, 50, trend, ket
    
    prob_bull = round((skor_bull / total) * 100)
    prob_bear = 100 - prob_bull
    
    if prob_bull < 10:
        prob_bull = 10
        prob_bear = 90
    elif prob_bear < 10:
        prob_bear = 10
        prob_bull = 90
    
    return prob_bull, prob_bear, trend, ket

def hitung_risk_sentiment(dxy_chg, yield_chg):
    skor = 0
    if dxy_chg is not None:
        skor += dxy_chg * 10
    if yield_chg is not None:
        skor += yield_chg * 5
    
    if skor > 5:
        return "RISK-OFF", "DXY & Yield naik -> bullish gold"
    elif skor < -5:
        return "RISK-ON", "DXY & Yield turun -> bearish gold"
    else:
        return "NETRAL", "Sentimen campur"

def hitung_saran_trading(prob_bull, prob_bear, harga_sekarang, bull_ob, bear_ob):
    if prob_bull >= 60:
        bias = "BUY"
        if bull_ob:
            entry = bull_ob[-1]["atas"]
            sl = bull_ob[-1]["bawah"] - 5
        else:
            entry = harga_sekarang
            sl = harga_sekarang - 20
        tp1 = entry + 20
        tp2 = entry + 40
    elif prob_bear >= 60:
        bias = "SELL"
        if bear_ob:
            entry = bear_ob[-1]["bawah"]
            sl = bear_ob[-1]["atas"] + 5
        else:
            entry = harga_sekarang
            sl = harga_sekarang + 20
        tp1 = entry - 20
        tp2 = entry - 40
    else:
        return None
    
    rr = abs(tp1 - entry) / abs(sl - entry) if abs(sl - entry) > 0 else 0
    
    return {
        "bias": bias, "entry": round(entry, 2), "sl": round(sl, 2),
        "tp1": round(tp1, 2), "tp2": round(tp2, 2), "rr": round(rr, 2)
    }

def backtest(data, prob_bull, prob_bear):
    """Backtest sederhana: hitung win rate 30 hari terakhir"""
    if len(data) < 30:
        return None
    
    menang = 0
    total = 0
    benar_bull = 0
    
    if prob_bull >= 60:
        bias = "BULLISH"
        benar_bull = 1
    elif prob_bear >= 60:
        bias = "BEARISH"
        benar_bull = 0
    else:
        return None
    
    for i in range(1, min(30, len(data))):
        perubahan = data[-i]["close"] - data[-i-1]["close"]
        if bias == "BULLISH" and perubahan > 0:
            menang += 1
        elif bias == "BEARISH" and perubahan < 0:
            menang += 1
        total += 1
    
    if total == 0:
        return None
    
    win_rate = round((menang / total) * 100)
    return win_rate

# ============ MAIN ============
print("Ambil data...")
gold, gold_chg = ambil_harga("GC=F")
dxy, dxy_chg = ambil_harga("DX-Y.NYB")
yield10, yield_chg = ambil_harga("^TNX")

data_h1 = ambil_ohlc("GC=F", interval="1h", range_="1mo")
data_h4 = gabung_h4(data_h1)
data_m15 = ambil_ohlc("GC=F", interval="15m", range_="7d")
data_d1 = ambil_ohlc("GC=F", interval="1d", range_="6mo")

print("Ambil berita + AI...")
berita_list = ambil_berita_gold()
print(f"Berita: {len(berita_list)}")

prob_d1_bull, prob_d1_bear, trend_d1, _ = probabilitas_tf(data_d1, "D1")
prob_h4_bull, prob_h4_bear, trend_h4, _ = probabilitas_tf(data_h4, "H4")
prob_h1_bull, prob_h1_bear, trend_h1, _ = probabilitas_tf(data_h1, "H1")
prob_m15_bull, prob_m15_bear, trend_m15, _ = probabilitas_tf(data_m15, "M15")

prob_bull_total = round(prob_d1_bull*0.30 + prob_h4_bull*0.30 + prob_h1_bull*0.25 + prob_m15_bull*0.15)
prob_bear_total = 100 - prob_bull_total

risk_sent, risk_ket = hitung_risk_sentiment(dxy_chg, yield_chg)
bull_ob_h4, bear_ob_h4 = deteksi_ob(data_h4)
saran = hitung_saran_trading(prob_bull_total, prob_bear_total, gold, bull_ob_h4, bear_ob_h4)
win_rate = backtest(data_d1, prob_bull_total, prob_bear_total)

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
pesan += "🎯 *MULTI-TIMEFRAME*\n\n"
pesan += f"📆 D1: {prob_d1_bull}%/{prob_d1_bear}% ({trend_d1})\n"
pesan += f"🗓️ H4: {prob_h4_bull}%/{prob_h4_bear}% ({trend_h4})\n"
pesan += f"📅 H1: {prob_h1_bull}%/{prob_h1_bear}% ({trend_h1})\n"
pesan += f"⏰ M15: {prob_m15_bull}%/{prob_m15_bear}% ({trend_m15})\n\n"

pesan += "---\n\n"
pesan += "💡 *KESIMPULAN:*\n"
pesan += f"📈 Bullish: *{prob_bull_total}%*\n"
pesan += f"📉 Bearish: *{prob_bear_total}%*\n\n"

if prob_bull_total >= 65:
    pesan += "🎯 Bias: *STRONG BULLISH*\n\n"
elif prob_bull_total >= 55:
    pesan += "🎯 Bias: *BULLISH*\n\n"
elif prob_bear_total >= 65:
    pesan += "🎯 Bias: *STRONG BEARISH*\n\n"
elif prob_bear_total >= 55:
    pesan += "🎯 Bias: *BEARISH*\n\n"
else:
    pesan += "🎯 Bias: *NETRAL*\n\n"

if win_rate is not None:
    pesan += f"📊 *Backtest 30 hari:* Win rate {win_rate}%\n\n"

pesan += "---\n\n"
pesan += "🌍 *RISK SENTIMENT:*\n"
pesan += f"🎯 {risk_sent}\n"
pesan += f"📝 {risk_ket}\n\n"

if saran:
    pesan += "---\n\n"
    pesan += "💰 *SARAN TRADING:*\n\n"
    pesan += f"🎯 Bias: *{saran['bias']}*\n"
    pesan += f"📍 Entry: ${saran['entry']}\n"
    pesan += f"🛑 SL: ${saran['sl']}\n"
    pesan += f"🎯 TP1: ${saran['tp1']}\n"
    pesan += f"🎯 TP2: ${saran['tp2']}\n"
    pesan += f"📊 RR: 1:{saran['rr']}\n\n"

if berita_list:
    pesan += "---\n\n"
    pesan += "📰 *BERITA GOLD (AI Analysis):*\n\n"
    for b in berita_list:
        pesan += f"{b['sentimen']}\n{b['judul'][:80]}...\n\n"

pesan += "⚠️ _Disclaimer: Bukan jaminan profit. DYOR._"

# ============ KIRIM ============
url_tg = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
r = requests.post(url_tg, data={"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"})
print("Terkirim!" if r.status_code == 200 else f"Gagal: {r.json()}")
print("Selesai!")
