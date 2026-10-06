import requests
import feedparser
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime

TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_KEY = os.environ.get("GROQ_API_KEY")

PAIRS = {
    "GOLD": {"symbol": "GC=F", "emoji": "🥇", "nama": "Gold (XAUUSD)"},
    "EURUSD": {"symbol": "EURUSD=X", "emoji": "💶", "nama": "EURUSD"},
    "BTC": {"symbol": "BTC-USD", "emoji": "₿", "nama": "Bitcoin"},
    "OIL": {"symbol": "CL=F", "emoji": "🛢️", "nama": "Crude Oil"},
    "SILVER": {"symbol": "SI=F", "emoji": "🥈", "nama": "Silver"},
    "SP500": {"symbol": "^GSPC", "emoji": "📈", "nama": "S&P 500"},
    "USDJPY": {"symbol": "JPY=X", "emoji": "💴", "nama": "USDJPY"},
    "GBPUSD": {"symbol": "GBPUSD=X", "emoji": "💷", "nama": "GBPUSD"}
}

RSS_BERITA = [
    "https://www.fxstreet.com/rss/news",
    "https://www.kitco.com/rss/KitcoNews.xml",
    "https://www.investing.com/rss/news_285.rss"
]

RSS_KALENDER = [
    "https://www.forexfactory.com/rss.php?section=calendar",
    "https://www.investing.com/rss/news_11.rss"
]

def analisis_berita_ai(judul_berita):
    if not GROQ_KEY:
        return "⚪ Netral"
    prompt = f"""Analisis sentimen berita ini untuk GOLD (XAUUSD).
Jawab HANYA dengan 1 kata: BULLISH, BEARISH, atau NETRAL.

Berita: {judul_berita}

Jawaban:"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": "Bearer " + GROQ_KEY, "Content-Type": "application/json"}
    data = {"model": "openai/gpt-oss-20b", "messages": [{"role": "user", "content": prompt}]}
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
    berita_list = []
    for url in RSS_BERITA:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                judul = entry.title
                sentimen = analisis_berita_ai(judul)
                berita_list.append({"judul": judul, "sentimen": sentimen})
        except:
            pass
    return berita_list[:5]

def ambil_kalender_ekonomi():
    events = []
    for url in RSS_KALENDER:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:3]:
                events.append(entry.title)
        except:
            pass
    return events[:5]

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
        print(f"Error {symbol}: {e}")
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
        return 50, 50, trend, ket, bos, mss
    prob_bull = round((skor_bull / total) * 100)
    prob_bear = 100 - prob_bull
    if prob_bull < 10:
        prob_bull = 10
        prob_bear = 90
    elif prob_bear < 10:
        prob_bear = 10
        prob_bull = 90
    return prob_bull, prob_bear, trend, ket, bos, mss

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
    return {"bias": bias, "entry": round(entry, 2), "sl": round(sl, 2),
            "tp1": round(tp1, 2), "tp2": round(tp2, 2), "rr": round(rr, 2)}

def backtest(data, prob_bull, prob_bear):
    if len(data) < 30:
        return None
    menang = 0
    total = 0
    if prob_bull >= 60:
        bias = "BULLISH"
    elif prob_bear >= 60:
        bias = "BEARISH"
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
    return round((menang / total) * 100)

def hitung_korelasi(data1, data2):
    if len(data1) < 10 or len(data2) < 10:
        return None
    n = min(len(data1), len(data2), 30)
    closes1 = [d["close"] for d in data1[-n:]]
    closes2 = [d["close"] for d in data2[-n:]]
    chg1 = [closes1[i] - closes1[i-1] for i in range(1, len(closes1))]
    chg2 = [closes2[i] - closes2[i-1] for i in range(1, len(closes2))]
    n = len(chg1)
    if n < 5:
        return None
    mean1 = sum(chg1) / n
    mean2 = sum(chg2) / n
    num = sum((chg1[i] - mean1) * (chg2[i] - mean2) for i in range(n))
    den1 = sum((chg1[i] - mean1) ** 2 for i in range(n)) ** 0.5
    den2 = sum((chg2[i] - mean2) ** 2 for i in range(n)) ** 0.5
    if den1 == 0 or den2 == 0:
        return None
    return round(num / (den1 * den2), 2)

def bikin_chart(data, nama_file, judul="Chart"):
    if len(data) < 10:
        return None
    try:
        closes = [d["close"] for d in data[-50:]]
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(closes, label="Close", color="blue", linewidth=1.5)
        ax.set_title(judul)
        ax.set_ylabel("Harga")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(nama_file, dpi=70)
        plt.close()
        return nama_file
    except Exception as e:
        print(f"Error chart: {e}")
        return None

def kirim_foto_telegram(path_foto, caption=""):
    url = "https://api.telegram.org/bot" + TOKEN + "/sendPhoto"
    try:
        with open(path_foto, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": CHAT_ID, "caption": caption}
            r = requests.post(url, files=files, data=data, timeout=30)
            return r.status_code == 200
    except:
        return False

# ============ MAIN ============
print("Ambil data multi-pair...")
dxy, dxy_chg = ambil_harga("DX-Y.NYB")
yield10, yield_chg = ambil_harga("^TNX")

hasil_pairs = {}
data_pairs = {}

for kode, info in PAIRS.items():
    print(f"Analisis {kode}...")
    harga, chg = ambil_harga(info["symbol"])
    data_h1 = ambil_ohlc(info["symbol"], interval="1h", range_="1mo")
    data_h4 = gabung_h4(data_h1)
    data_d1 = ambil_ohlc(info["symbol"], interval="1d", range_="6mo")
    
    if data_h4:
        prob_bull, prob_bear, trend, _, bos, mss = probabilitas_tf(data_h4, "H4")
    else:
        prob_bull, prob_bear, trend, bos, mss = 50, 50, "RANGING", None, None
    
    hasil_pairs[kode] = {
        "harga": harga, "chg": chg,
        "prob_bull": prob_bull, "prob_bear": prob_bear,
        "trend": trend, "emoji": info["emoji"], "nama": info["nama"],
        "bos": bos, "mss": mss
    }
    data_pairs[kode] = data_d1

print("Ambil berita...")
berita_list = ambil_berita_gold()
print("Ambil kalender...")
kalender = ambil_kalender_ekonomi()

# Korelasi
korelasi_gold_dxy = None
korelasi_gold_oil = None
korelasi_gold_btc = None

if data_pairs.get("GOLD"):
    dxy_data = ambil_ohlc("DX-Y.NYB", interval="1d", range_="6mo")
    if dxy_data:
        korelasi_gold_dxy = hitung_korelasi(data_pairs["GOLD"], dxy_data)
if data_pairs.get("GOLD") and data_pairs.get("OIL"):
    korelasi_gold_oil = hitung_korelasi(data_pairs["GOLD"], data_pairs["OIL"])
if data_pairs.get("GOLD") and data_pairs.get("BTC"):
    korelasi_gold_btc = hitung_korelasi(data_pairs["GOLD"], data_pairs["BTC"])

# ============ CEK ALERT ============
alert_khusus = None
alert_rr = None

# Alert probabilitas > 80%
for kode, h in hasil_pairs.items():
    if h["prob_bull"] >= 80:
        alert_khusus = f"🚨🚨🚨 *ALERT SINYAL KUAT* 🚨🚨🚨\n\n{h['emoji']} {h['nama']}: *STRONG BULLISH {h['prob_bull']}%!*"
        break
    elif h["prob_bear"] >= 80:
        alert_khusus = f"🚨🚨🚨 *ALERT SINYAL KUAT* 🚨🚨🚨\n\n{h['emoji']} {h['nama']}: *STRONG BEARISH {h['prob_bear']}%!*"
        break

# Alert BOS/MSS Gold
if not alert_khusus and hasil_pairs.get("GOLD"):
    g = hasil_pairs["GOLD"]
    if g.get("bos"):
        alert_khusus = f"🔔 *ALERT BOS GOLD:*\n{g['bos']}"
    elif g.get("mss"):
        alert_khusus = f"🚨 *ALERT MSS GOLD:*\n{g['mss']}"

# Alert RR > 1:3 untuk Gold
if hasil_pairs.get("GOLD") and hasil_pairs["GOLD"]["harga"]:
    g = hasil_pairs["GOLD"]
    bull_ob_h4, bear_ob_h4 = deteksi_ob(gabung_h4(ambil_ohlc("GC=F", "1h", "1mo")))
    saran = hitung_saran_trading(g["prob_bull"], g["prob_bear"], g["harga"], bull_ob_h4, bear_ob_h4)
    if saran and saran["rr"] >= 3:
        alert_rr = f"🔥🔥 *SETUP BAGUS!* 🔥🔥\n\n🥇 GOLD: *{saran['bias']}*\n📍 Entry: ${saran['entry']}\n🛑 SL: ${saran['sl']}\n🎯 TP1: ${saran['tp1']}\n📊 RR: 1:{saran['rr']}\n🎯 Probabilitas: {g['prob_bear'] if saran['bias']=='SELL' else g['prob_bull']}%"

# ============ SUSUN PESAN ============
tanggal = datetime.now().strftime("%d %B %Y")
pesan = "📊 *MULTI-PAIR ANALYSIS*\n"
pesan += f"📅 {tanggal}\n\n"

if dxy:
    pesan += f"💵 *DXY*: {round(dxy, 2)} ({round(dxy_chg, 2)}%)\n"
if yield10:
    pesan += f"📈 *US 10Y*: {round(yield10, 3)}% ({round(yield_chg, 3)}%)\n"

pesan += "\n---\n\n"
pesan += "🎯 *ANALISIS PAIRS*\n\n"

for kode, h in hasil_pairs.items():
    pesan += f"{h['emoji']} *{h['nama']}*\n"
    if h["harga"]:
        pesan += f"💰 {round(h['harga'], 2)} ({round(h['chg'], 2)}%)\n"
    pesan += f"🎯 {h['trend']} ({h['prob_bull']}%/{h['prob_bear']}%)\n"
    if h.get("bos"):
        pesan += f"🔔 {h['bos']}\n"
    if h.get("mss"):
        pesan += f"🚨 {h['mss']}\n"
    pesan += "\n"

pesan += "---\n\n"
pesan += "📊 *KORELASI GOLD:*\n\n"
if korelasi_gold_dxy is not None:
    pesan += f"• Gold vs DXY: {korelasi_gold_dxy}\n"
if korelasi_gold_oil is not None:
    pesan += f"• Gold vs Oil: {korelasi_gold_oil}\n"
if korelasi_gold_btc is not None:
    pesan += f"• Gold vs BTC: {korelasi_gold_btc}\n"

pesan += "\n---\n\n"
pesan += "🌍 *RISK SENTIMENT:*\n"
risk_sent, risk_ket = hitung_risk_sentiment(dxy_chg, yield_chg)
pesan += f"🎯 {risk_sent}\n"
pesan += f"📝 {risk_ket}\n\n"

if kalender:
    pesan += "---\n\n"
    pesan += "📅 *KALENDER EKONOMI:*\n\n"
    for e in kalender:
        pesan += f"• {e[:80]}\n"
    pesan += "\n"

if berita_list:
    pesan += "---\n\n"
    pesan += "📰 *BERITA:*\n\n"
    for b in berita_list[:3]:
        pesan += f"{b['sentimen']}\n{b['judul'][:80]}...\n\n"

pesan += "⚠️ _Disclaimer: Bukan jaminan profit. DYOR._"

# ============ KIRIM ============
# Kirim alert terpisah
if alert_khusus:
    url_alert = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
    r_alert = requests.post(url_alert, data={
        "chat_id": CHAT_ID, "text": alert_khusus, "parse_mode": "Markdown"
    })
    print("Alert terkirim!" if r_alert.status_code == 200 else f"Alert gagal")

if alert_rr:
    url_alert = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
    r_alert = requests.post(url_alert, data={
        "chat_id": CHAT_ID, "text": alert_rr, "parse_mode": "Markdown"
    })
    print("Alert RR terkirim!" if r_alert.status_code == 200 else f"Alert RR gagal")

# Kirim chart
if data_pairs.get("GOLD"):
    chart_path = bikin_chart(data_pairs["GOLD"], "chart_gold.png", "Gold (XAUUSD) D1")
    if chart_path:
        kirim_foto_telegram(chart_path, caption="📈 Chart Gold D1")

# Kirim pesan utama
url_tg = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
r = requests.post(url_tg, data={"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"})
print("Terkirim!" if r.status_code == 200 else f"Gagal: {r.json()}")
print("Selesai!")
