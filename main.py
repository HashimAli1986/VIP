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
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    df["MACD"] = df["Close"].ewm(span=12).mean() - df["Close"].ewm(span=26).mean()
    df["Signal"] = df["MACD"].ewm(span=9).mean()
    return df

def interpret_trend(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    rsi = last["RSI"]
    macd_cross = last["MACD"] > last["Signal"] and prev["MACD"] < prev["Signal"]
    ema_cross = last["EMA9"] > last["EMA21"] > last["EMA50"]
    if macd_cross and ema_cross and rsi < 70:
        return "صاعدة"
    elif last["MACD"] < last["Signal"] and last["EMA9"] < last["EMA21"] and rsi > 60:
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

        msg += (
            f"{name} – {datetime.utcnow().strftime('%H:%M')} UTC\n"
            f"السعر الحالي: {price:.2f}\n"
            f"فريم الساعة: {dir_1h}\n"
            f"فريم اليومي: {dir_1d}\n"
            f"الاتجاه العام: "
            f"{'صاعدة قوية' if dir_1h == 'صاعدة' and dir_1d == 'صاعدة' else 'هابطة قوية' if dir_1h == 'هابطة' and dir_1d == 'هابطة' else 'تذبذب أو غير مؤكد'}\n\n"
        )

    send_telegram_message(msg.strip())

def hourly_loop():
    last_sent = -1
    while True:
        now = datetime.utcnow()
        if now.hour != last_sent and now.minute >= 0:
            last_sent = now.hour
            analyze_and_send()
        time.sleep(60)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل تحليل مؤشر S&P 500 والشركات الكبرى.")
    Thread(target=hourly_loop).start()
