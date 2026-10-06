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

# Daftar pair yang dipantau
PAIRS = {
    "GOLD": {"symbol": "GC=F", "emoji": "🥇", "nama": "Gold (XAUUSD)"},
    "EURUSD": {"symbol": "EURUSD=X", "emoji": "💶", "nama": "EURUSD"},
    "BTC": {"symbol": "BTC-USD", "emoji": "₿", "nama": "Bitcoin"},
    "OIL": {"symbol": "CL=F", "emoji": "🛢️", "nama": "Crude Oil"}
}

RSS_BERITA = [
    "https://www.fxstreet.com/rss/news",
    "https://www.kitco.com/rss/KitcoNews.xml",
    "https://www.investing.com/rss/news_285.rss"
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
        return "RANGING"
    if sh[-1]["harga"] > sh[-2]["harga"]:
        bh = "bullish"
    else:
        bh = "bearish"
    if sl[-1]["harga"] > sl[-2]["harga"]:
        bl = "bullish"
    else:
        bl = "bearish"
    if bh == "bullish" and bl == "bullish":
        return "BULLISH"
    elif bh == "bearish" and bl == "bearish":
        return "BEARISH"
    return "RANGING"

def probabilitas_sederhana(data):
    """Probabilitas berdasarkan trend + swing"""
    sh, sl = deteksi_swing(data)
    trend = analisis_trend(sh, sl)
    
    if trend == "BULLISH":
        return 65, 35, trend
    elif trend == "BEARISH":
        return 35, 65, trend
    else:
        return 50, 50, trend

def hitung_korelasi(data1, data2):
    """Hitung korelasi sederhana antara 2 data"""
    if len(data1) < 10 or len(data2) < 10:
        return None
    
    n = min(len(data1), len(data2), 30)
    closes1 = [d["close"] for d in data1[-n:]]
    closes2 = [d["close"] for d in data2[-n:]]
    
    # Hitung perubahan
    chg1 = [closes1[i] - closes1[i-1] for i in range(1, len(closes1))]
    chg2 = [closes2[i] - closes2[i-1] for i in range(1, len(closes2))]
    
    # Korelasi sederhana
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

# Data DXY & Yield (untuk risk sentiment)
dxy, dxy_chg = ambil_harga("DX-Y.NYB")
yield10, yield_chg = ambil_harga("^TNX")

# Analisis tiap pair
hasil_pairs = {}
data_pairs = {}

for kode, info in PAIRS.items():
    print(f"Analisis {kode}...")
    harga, chg = ambil_harga(info["symbol"])
    data_h1 = ambil_ohlc(info["symbol"], interval="1h", range_="1mo")
    data_h4 = gabung_h4(data_h1)
    data_d1 = ambil_ohlc(info["symbol"], interval="1d", range_="6mo")
    
    if data_h4:
        prob_bull, prob_bear, trend = probabilitas_sederhana(data_h4)
    else:
        prob_bull, prob_bear, trend = 50, 50, "RANGING"
    
    hasil_pairs[kode] = {
        "harga": harga,
        "chg": chg,
        "prob_bull": prob_bull,
        "prob_bear": prob_bear,
        "trend": trend,
        "emoji": info["emoji"],
        "nama": info["nama"]
    }
    data_pairs[kode] = data_d1

# Hitung korelasi
korelasi_gold_dxy = None
korelasi_gold_oil = None
korelasi_gold_btc = None

if data_pairs.get("GOLD") and dxy:
    dxy_data = ambil_ohlc("DX-Y.NYB", interval="1d", range_="6mo")
    if dxy_data:
        korelasi_gold_dxy = hitung_korelasi(data_pairs["GOLD"], dxy_data)

if data_pairs.get("GOLD") and data_pairs.get("OIL"):
    korelasi_gold_oil = hitung_korelasi(data_pairs["GOLD"], data_pairs["OIL"])

if data_pairs.get("GOLD") and data_pairs.get("BTC"):
    korelasi_gold_btc = hitung_korelasi(data_pairs["GOLD"], data_pairs["BTC"])

print("Ambil berita...")
berita_list = ambil_berita_gold()

# ============ SUSUN PESAN ============
tanggal = datetime.now().strftime("%d %B %Y")
pesan = "📊 *MULTI-PAIR ANALYSIS*\n"
pesan += f"📅 {tanggal}\n\n"

# Data market
if dxy:
    pesan += f"💵 *DXY*: {round(dxy, 2)} ({round(dxy_chg, 2)}%)\n"
if yield10:
    pesan += f"📈 *US 10Y*: {round(yield10, 3)}% ({round(yield_chg, 3)}%)\n"

pesan += "\n---\n\n"
pesan += "🎯 *ANALISIS PAIRS*\n\n"

for kode, h in hasil_pairs.items():
    pesan += f"{h['emoji']} *{h['nama']}*\n"
    if h["harga"]:
        pesan += f"💰 Harga: {round(h['harga'], 2)} ({round(h['chg'], 2)}%)\n"
    pesan += f"🎯 Bias: {h['trend']} ({h['prob_bull']}%/{h['prob_bear']}%)\n\n"

pesan += "---\n\n"
pesan += "📊 *KORELASI GOLD:*\n\n"

if korelasi_gold_dxy is not None:
    pesan += f"• Gold vs DXY: {korelasi_gold_dxy}\n"
if korelasi_gold_oil is not None:
    pesan += f"• Gold vs Oil: {korelasi_gold_oil}\n"
if korelasi_gold_btc is not None:
    pesan += f"• Gold vs BTC: {korelasi_gold_btc}\n"

pesan += "\n"

if berita_list:
    pesan += "---\n\n"
    pesan += "📰 *BERITA:*\n\n"
    for b in berita_list[:3]:
        pesan += f"{b['sentimen']}\n{b['judul'][:80]}...\n\n"

pesan += "⚠️ _Disclaimer: Bukan jaminan profit. DYOR._"

# ============ KIRIM ============
# Kirim chart Gold
if data_pairs.get("GOLD"):
    print("Bikin chart Gold...")
    chart_path = bikin_chart(data_pairs["GOLD"], "chart_gold.png", "Gold (XAUUSD) D1")
    if chart_path:
        kirim_foto_telegram(chart_path, caption="📈 Chart Gold D1")

url_tg = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
r = requests.post(url_tg, data={"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"})
print("Terkirim!" if r.status_code == 200 else f"Gagal: {r.json()}")
print("Selesai!")
