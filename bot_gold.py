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
    "GOLD": {"symbol": "GC=F", "emoji": "🥇", "nama": "Gold (XAUUSD)", "sector": "Commodities"},
    "EURUSD": {"symbol": "EURUSD=X", "emoji": "💶", "nama": "EURUSD", "sector": "Forex"},
    "BTC": {"symbol": "BTC-USD", "emoji": "₿", "nama": "Bitcoin", "sector": "Crypto"},
    "OIL": {"symbol": "CL=F", "emoji": "🛢️", "nama": "Crude Oil", "sector": "Commodities"},
    "SILVER": {"symbol": "SI=F", "emoji": "🥈", "nama": "Silver", "sector": "Commodities"},
    "SP500": {"symbol": "^GSPC", "emoji": "📈", "nama": "S&P 500", "sector": "Indices"},
    "USDJPY": {"symbol": "JPY=X", "emoji": "💴", "nama": "USDJPY", "sector": "Forex"},
    "GBPUSD": {"symbol": "GBPUSD=X", "emoji": "💷", "nama": "GBPUSD", "sector": "Forex"}
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

def analisis_multi_tf_pair(symbol):
    data_h1 = ambil_ohlc(symbol, "1h", "1mo")
    data_h4 = gabung_h4(data_h1)
    data_d1 = ambil_ohlc(symbol, "1d", "6mo")
    data_m15 = ambil_ohlc(symbol, "15m", "7d")
    
    hasil = {}
    
    if data_d1:
        pb, pbe, tr, _, _, _ = probabilitas_tf(data_d1, "D1")
        hasil["D1"] = {"bull": pb, "bear": pbe, "trend": tr}
    else:
        hasil["D1"] = {"bull": 50, "bear": 50, "trend": "N/A"}
    
    if data_h4:
        pb, pbe, tr, _, _, _ = probabilitas_tf(data_h4, "H4")
        hasil["H4"] = {"bull": pb, "bear": pbe, "trend": tr}
    else:
        hasil["H4"] = {"bull": 50, "bear": 50, "trend": "N/A"}
    
    if data_h1:
        pb, pbe, tr, _, _, _ = probabilitas_tf(data_h1, "H1")
        hasil["H1"] = {"bull": pb, "bear": pbe, "trend": tr}
    else:
        hasil["H1"] = {"bull": 50, "bear": 50, "trend": "N/A"}
    
    if data_m15:
        pb, pbe, tr, _, _, _ = probabilitas_tf(data_m15, "M15")
        hasil["M15"] = {"bull": pb, "bear": pbe, "trend": tr}
    else:
        hasil["M15"] = {"bull": 50, "bear": 50, "trend": "N/A"}
    
    bull_gabung = round(
        hasil["D1"]["bull"] * 0.30 +
        hasil["H4"]["bull"] * 0.30 +
        hasil["H1"]["bull"] * 0.25 +
        hasil["M15"]["bull"] * 0.15
    )
    bear_gabung = 100 - bull_gabung
    
    hasil["GABUNGAN"] = {"bull": bull_gabung, "bear": bear_gabung}
    return hasil

# ============ MAIN ============
print("Ambil data multi-pair...")
dxy, dxy_chg = ambil_harga("DX-Y.NYB")
yield10, yield_chg = ambil_harga("^TNX")

hasil_pairs = {}
data_pairs = {}
mtf_results = {}

for kode, info in PAIRS.items():
    print(f"Analisis {kode}...")
    harga, chg = ambil_harga(info["symbol"])
    data_d1 = ambil_ohlc(info["symbol"], interval="1d", range_="6mo")
    
    mtf = analisis_multi_tf_pair(info["symbol"])
    mtf_results[kode] = mtf
    
    hasil_pairs[kode] = {
        "harga": harga, "chg": chg,
        "prob_bull": mtf["GABUNGAN"]["bull"],
        "prob_bear": mtf["GABUNGAN"]["bear"],
        "trend": mtf["H4"]["trend"],
        "emoji": info["emoji"], "nama": info["nama"],
        "sector": info["sector"]
    }
    data_pairs[kode] = data_d1

print("Ambil berita...")
berita_list = ambil_berita_gold()
print("Ambil kalender...")
kalender = ambil_kalender_ekonomi()

# Korelasi
korelasi_list = []
kode_list = list(PAIRS.keys())
for i in range(len(kode_list)):
    for j in range(i+1, len(kode_list)):
        k1 = kode_list[i]
        k2 = kode_list[j]
        if data_pairs.get(k1) and data_pairs.get(k2):
            kor = hitung_korelasi(data_pairs[k1], data_pairs[k2])
            if kor is not None:
                korelasi_list.append((k1, k2, kor))

korelasi_list.sort(key=lambda x: abs(x[2]), reverse=True)

# Sector
sector_hasil = {}
for kode, h in hasil_pairs.items():
    sector = h["sector"]
    if sector not in sector_hasil:
        sector_hasil[sector] = []
    sector_hasil[sector].append(h)

# Ranking untuk Top 3
ranking = []
for kode, h in hasil_pairs.items():
    kekuatan = max(h["prob_bull"], h["prob_bear"])
    bias = "BUY" if h["prob_bull"] > h["prob_bear"] else "SELL"
    ranking.append({
        "kode": kode, "nama": h["nama"], "emoji": h["emoji"],
        "bias": bias, "prob": kekuatan, "symbol": PAIRS[kode]["symbol"]
    })

ranking.sort(key=lambda x: x["prob"], reverse=True)
top3 = ranking[:3]

# ============ ALERT ============
alert_korelasi = None
for k1, k2, kor in korelasi_list:
    if kor >= 0.9:
        alert_korelasi = f"⚡ *ALERT KORELASI TINGGI!*\n\n{PAIRS[k1]['emoji']} {PAIRS[k1]['nama']} vs {PAIRS[k2]['emoji']} {PAIRS[k2]['nama']}\nKorelasi: *{kor}*"
        break
    elif kor <= -0.9:
        alert_korelasi = f"⚡ *ALERT KORELASI NEGATIF!*\n\n{PAIRS[k1]['emoji']} {PAIRS[k1]['nama']} vs {PAIRS[k2]['emoji']} {PAIRS[k2]['nama']}\nKorelasi: *{kor}*"
        break

alert_khusus = None
for kode, h in hasil_pairs.items():
    if h["prob_bull"] >= 80:
        alert_khusus = f"🚨🚨🚨 *ALERT SINYAL KUAT* 🚨🚨🚨\n\n{h['emoji']} {h['nama']}: *STRONG BULLISH {h['prob_bull']}%!*"
        break
    elif h["prob_bear"] >= 80:
        alert_khusus = f"🚨🚨🚨 *ALERT SINYAL KUAT* 🚨🚨🚨\n\n{h['emoji']} {h['nama']}: *STRONG BEARISH {h['prob_bear']}%!*"
        break

# ============ SUSUN PESAN ============
tanggal = datetime.now().strftime("%d %B %Y")
pesan = "📊 *MULTI-PAIR + MULTI-TIMEFRAME*\n"
pesan += f"📅 {tanggal}\n\n"

if dxy:
    pesan += f"💵 *DXY*: {round(dxy, 2)} ({round(dxy_chg, 2)}%)\n"
if yield10:
    pesan += f"📈 *US 10Y*: {round(yield10, 3)}% ({round(yield_chg, 3)}%)\n"

pesan += "\n---\n\n"
pesan += "🎯 *ANALISIS MULTI-TIMEFRAME*\n\n"

for kode, h in hasil_pairs.items():
    mtf = mtf_results[kode]
    pesan += f"{h['emoji']} *{h['nama']}*\n"
    if h["harga"]:
        pesan += f"💰 {round(h['harga'], 2)} ({round(h['chg'], 2)}%)\n"
    pesan += f"📆 D1: {mtf['D1']['bull']}/{mtf['D1']['bear']} ({mtf['D1']['trend']})\n"
    pesan += f"🗓️ H4: {mtf['H4']['bull']}/{mtf['H4']['bear']} ({mtf['H4']['trend']})\n"
    pesan += f"📅 H1: {mtf['H1']['bull']}/{mtf['H1']['bear']} ({mtf['H1']['trend']})\n"
    pesan += f"⏰ M15: {mtf['M15']['bull']}/{mtf['M15']['bear']} ({mtf['M15']['trend']})\n"
    pesan += f"🎯 *Gabungan: {mtf['GABUNGAN']['bull']}%/{mtf['GABUNGAN']['bear']}%*\n\n"

pesan += "---\n\n"
pesan += "🏭 *SECTOR ANALYSIS:*\n\n"
for sector, pairs in sector_hasil.items():
    pesan += f"*{sector}:*\n"
    for h in pairs:
        bias = "BUY" if h["prob_bull"] > h["prob_bear"] else "SELL"
        kekuatan = max(h["prob_bull"], h["prob_bear"])
        pesan += f"  {h['emoji']} {h['nama']}: {bias} ({kekuatan}%)\n"
    pesan += "\n"

pesan += "---\n\n"
pesan += "📊 *KORELASI MATRIX (Top 5):*\n\n"
for k1, k2, kor in korelasi_list[:5]:
    emoji1 = PAIRS[k1]["emoji"]
    emoji2 = PAIRS[k2]["emoji"]
    if kor > 0.7:
        label = "🟢 Kuat+"
    elif kor > 0.3:
        label = "🟡 Sedang+"
    elif kor < -0.7:
        label = "🔴 Kuat-"
    elif kor < -0.3:
        label = "🟠 Sedang-"
    else:
        label = "⚪ Lemah"
    pesan += f"• {emoji1} vs {emoji2}: {kor} {label}\n"

pesan += "\n---\n\n"
pesan += "🌍 *RISK SENTIMENT:*\n"
risk_sent, risk_ket = hitung_risk_sentiment(dxy_chg, yield_chg)
pesan += f"🎯 {risk_sent}\n"
pesan += f"📝 {risk_ket}\n\n"

if berita_list:
    pesan += "---\n\n"
    pesan += "📰 *BERITA:*\n\n"
    for b in berita_list[:3]:
        pesan += f"{b['sentimen']}\n{b['judul'][:80]}...\n\n"

pesan += "⚠️ _Disclaimer: Bukan jaminan profit. DYOR._"

# ============ KIRIM ============
if alert_korelasi:
    url_alert = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
    requests.post(url_alert, data={"chat_id": CHAT_ID, "text": alert_korelasi, "parse_mode": "Markdown"})

if alert_khusus:
    url_alert = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
    requests.post(url_alert, data={"chat_id": CHAT_ID, "text": alert_khusus, "parse_mode": "Markdown"})

# Multi-Asset Chart (Top 3)
print("Bikin chart Top 3...")
for i, r in enumerate(top3, 1):
    data_chart = ambil_ohlc(r["symbol"], "1d", "6mo")
    if data_chart:
        chart_file = f"chart_{r['kode'].lower()}.png"
        chart_path = bikin_chart(data_chart, chart_file, f"{r['nama']} D1")
        if chart_path:
            kirim_foto_telegram(chart_path, caption=f"{r['emoji']} Chart {r['nama']}")

url_tg = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"

max_len = 4000
potongan = []
while len(pesan) > max_len:
    idx = pesan.rfind("\n", 0, max_len)
    if idx == -1:
        idx = max_len
    potongan.append(pesan[:idx])
    pesan = pesan[idx:].lstrip()
potongan.append(pesan)

for i, bagian in enumerate(potongan):
    r = requests.post(url_tg, data={"chat_id": CHAT_ID, "text": bagian, "parse_mode": "Markdown"})
    print(f"Bagian {i+1} terkirim!" if r.status_code == 200 else f"Bagian {i+1} gagal")

# ============ TRADING JOURNAL ============
print("Bikin trading journal...")

journal = "📓 *TRADING JOURNAL*\n"
journal += f"📅 {tanggal}\n\n"

journal += "🎯 *SINYAL HARI INI:*\n"
for r in ranking:
    m = mtf_results[r["kode"]]
    journal += f"• {r['emoji']} {r['nama']}: *{r['bias']}* ({r['prob']}%)\n"
    journal += f"  D1: {m['D1']['bull']}/{m['D1']['bear']} | H4: {m['H4']['bull']}/{m['H4']['bear']} | H1: {m['H1']['bull']}/{m['H1']['bear']} | M15: {m['M15']['bull']}/{m['M15']['bear']}\n"

journal += "\n⭐ *TOP 3 SETUP:*\n"
for i, r in enumerate(top3, 1):
    journal += f"{i}. {r['emoji']} {r['nama']} — *{r['bias']}* ({r['prob']}%)\n"

journal += "\n💡 *REKOMENDASI:*\n"
if top3:
    terbaik = top3[0]
    journal += f"Fokus ke {terbaik['emoji']} {terbaik['nama']} — sinyal paling kuat ({terbaik['prob']}%).\n"
    
    if terbaik['prob'] >= 80:
        journal += "🔥 Sinyal SANGAT KUAT — bisa entry langsung.\n"
    elif terbaik['prob'] >= 65:
        journal += "✅ Sinyal kuat — tunggu konfirmasi M15.\n"
    else:
        journal += "⚠️ Sinyal sedang — tunggu setup lebih jelas.\n"

journal += "\n⚠️ _Bukan jaminan profit. DYOR._"

r_journal = requests.post(url_tg, data={
    "chat_id": CHAT_ID, "text": journal, "parse_mode": "Markdown"
})
print("Journal terkirim!" if r_journal.status_code == 200 else f"Journal gagal")

print("Selesai!")
