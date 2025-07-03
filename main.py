import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "تحليل مؤشر S&P 500 والشركات الكبرى يعمل بنجاح"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

BOT_TOKEN = "7883771248:AAFfwmcF3hcHz17_IG0KfyOCSGLjMBzyg8E"
CHANNEL_ID = "@hashimali1986"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

companies = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "GOOGL": "Alphabet A", "GOOG": "Alphabet C",
    "AMZN": "Amazon", "META": "Meta Platforms", "BRK.B": "Berkshire Hathaway", "TSLA": "Tesla", "LLY": "Eli Lilly",
    "V": "Visa", "JNJ": "Johnson & Johnson", "UNH": "UnitedHealth", "JPM": "JPMorgan Chase", "XOM": "Exxon Mobil",
    "PG": "Procter & Gamble", "MA": "Mastercard", "AVGO": "Broadcom", "HD": "Home Depot", "COST": "Costco",
    "MRK": "Merck", "PEP": "PepsiCo", "ABBV": "AbbVie", "WMT": "Walmart", "KO": "Coca-Cola",
    "MSTR": "MicroStrategy", "APP": "AppLovin", "SMCI": "Super Micro Computer", "GS": "Goldman Sachs",
    "MU": "Micron Technology", "COIN": "Coinbase", "CRWD": "CrowdStrike", "AMD": "Advanced Micro Devices"
}

def fetch_data(symbol, interval):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval={interval}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]

        if not all(key in quotes for key in ["close", "open", "high", "low"]):
            return None

        df = pd.DataFrame({
            "Close": quotes["close"],
            "Open": quotes["open"],
            "High": quotes["high"],
            "Low": quotes["low"]
        })

        df["Date"] = pd.to_datetime(timestamps, unit="s")
        df.set_index("Date", inplace=True)
        return df.dropna()
    except Exception as e:
        print(f"fetch_data error ({symbol}): {e}")
        return None

def calculate_indicators(df):
    # حساب المتوسطات المتحركة الأسية
    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    
    # حساب RSI
    delta = df["Close"].diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # حساب MACD وخط الإشارة
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    
    return df

def is_strong_breakout(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    rsi = last["RSI"]
    macd_cross = last["MACD"] > last["Signal"] and prev["MACD"] < prev["Signal"]
    macd_negative_cross = last["MACD"] < last["Signal"] and prev["MACD"] > prev["Signal"]
    up_breakout = last["Close"] > prev["High"] and rsi < 70 and macd_cross
    down_breakout = last["Close"] < prev["Low"] and rsi > 30 and macd_negative_cross
    return up_breakout, down_breakout

def interpret_trend(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    rsi = last["RSI"]
    macd_cross = last["MACD"] > last["Signal"] and prev["MACD"] < prev["Signal"]
    ema_cross = last["EMA9"] > last["EMA21"] > last["EMA50"]
    macd_negative_cross = last["MACD"] < last["Signal"] and prev["MACD"] > prev["Signal"]
    
    if macd_cross and ema_cross and rsi < 70:
        return "صاعدة قوية"
    elif macd_negative_cross and last["EMA9"] < last["EMA21"] and rsi > 60:
        return "هابطة قوية"
    elif last["MACD"] > last["Signal"] and rsi < 60:
        return "صاعدة"
    elif last["MACD"] < last["Signal"] and rsi > 40:
        return "هابطة"
    else:
        return "جانبية"

def analyze_and_send():
    msg = f"📊 تحديث التحليل الفني – {datetime.utcnow().strftime('%H:%M')} UTC\n\n"
    
    assets = {
        "MSTR": "MicroStrategy", "APP": "AppLovin", "AVGO": "Broadcom", "SMCI": "Super Micro Computer",
        "GS": "Goldman Sachs", "MU": "Micron Technology", "META": "Meta Platforms", "AAPL": "Apple",
        "COIN": "Coinbase", "TSLA": "Tesla", "LLY": "Eli Lilly", "CRWD": "CrowdStrike", "MSFT": "Microsoft",
        "AMD": "Advanced Micro Devices", "NVDA": "NVIDIA", "GOOGL": "Alphabet (Class A)", "GOOG": "Alphabet (Class C)",
        "AMZN": "Amazon", "BRK.B": "Berkshire Hathaway", "V": "Visa", "JNJ": "Johnson & Johnson",
        "UNH": "UnitedHealth", "JPM": "JPMorgan Chase", "XOM": "Exxon Mobil", "PG": "Procter & Gamble",
        "MA": "Mastercard", "HD": "Home Depot", "COST": "Costco", "MRK": "Merck", "PEP": "PepsiCo",
        "ABBV": "AbbVie", "WMT": "Walmart", "KO": "Coca-Cola"
    }

    for symbol, name in assets.items():
        df_1h = fetch_data(symbol, "1h")
        df_1d = fetch_data(symbol, "1d")

        if df_1h is None or df_1d is None:
            msg += f"{name}: ⚠️ تعذر جلب البيانات.\n\n"
            continue

        df_1h = calculate_indicators(df_1h)
        df_1d = calculate_indicators(df_1d)

        dir_1h = interpret_trend(df_1h)
        dir_1d = interpret_trend(df_1d)
        price = df_1h["Close"].iloc[-1]
        
        # تحليل RSI و MACD
        rsi_1h = df_1h["RSI"].iloc[-1]
        rsi_1d = df_1d["RSI"].iloc[-1]
        macd_1h = df_1h["MACD"].iloc[-1]
        macd_1d = df_1d["MACD"].iloc[-1]
        
        # إضافة تحليل المؤشرات
        rsi_analysis = ""
        if rsi_1h > 70:
            rsi_analysis += "RSI الساعة: تشبع بيعي ⚠️"
        elif rsi_1h < 30:
            rsi_analysis += "RSI الساعة: تشبع شرائي ✅"
            
        if rsi_1d > 70:
            rsi_analysis += " | RSI اليومي: تشبع بيعي ⚠️"
        elif rsi_1d < 30:
            rsi_analysis += " | RSI اليومي: تشبع شرائي ✅"
            
        macd_analysis = ""
        if macd_1h > df_1h["Signal"].iloc[-1]:
            macd_analysis += "MACD الساعة: إيجابي 📈"
        else:
            macd_analysis += "MACD الساعة: سلبي 📉"
            
        if macd_1d > df_1d["Signal"].iloc[-1]:
            macd_analysis += " | MACD اليومي: إيجابي 📈"
        else:
            macd_analysis += " | MACD اليومي: سلبي 📉"

        msg += (
            f"📈 {name} – السعر: {price:.2f}\n"
            f"فريم الساعة: {dir_1h}\n"
            f"فريم اليومي: {dir_1d}\n"
            f"{rsi_analysis}\n"
            f"{macd_analysis}\n\n"
        )

    send_telegram_message(msg.strip())

def hourly_loop():
    last_sent = -1
    while True:
        now = datetime.utcnow()
        if now.hour != last_sent and now.minute >= 0:
            last_sent = now.hour
            try:
                analyze_and_send()
            except Exception as e:
                print(f"Error in analysis: {e}")
                send_telegram_message(f"⚠️ حدث خطأ في التحليل: {str(e)[:100]}")
        time.sleep(60)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل تحليل مؤشر S&P 500 والشركات الكبرى مع مؤشرات RSI و MACD.")
    Thread(target=hourly_loop).start()
