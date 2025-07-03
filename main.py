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
    # تحليل S&P 500
    df_hour = fetch_data("^GSPC", "1h")
    df_day = fetch_data("^GSPC", "1d")
    if df_hour is None or df_day is None:
        send_telegram_message("⚠️ تعذر جلب بيانات S&P 500.")
        return

    df_hour = calculate_indicators(df_hour)
    df_day = calculate_indicators(df_day)
    dir_1h = interpret_trend(df_hour)
    dir_1d = interpret_trend(df_day)
    final = (
        "صاعدة قوية" if dir_1h == "صاعدة" and dir_1d == "صاعدة"
        else "هابطة قوية" if dir_1h == "هابطة" and dir_1d == "هابطة"
        else "تذبذب أو غير مؤكد"
    )
    price = df_hour["Close"].iloc[-1]
    msg = f"📊 تحليل مؤشر S&P 500 – {datetime.utcnow().strftime('%H:%M')} UTC\n" \
          f"السعر الحالي: {price:.2f}\n" \
          f"فريم الساعة: {dir_1h}\n" \
          f"فريم اليومي: {dir_1d}\n" \
          f"الاتجاه العام: {final}\n\n"

    # تحليل كل الشركات
    msg += "📈 تحليل الشركات الكبرى:\n\n"
    for symbol, name in companies.items():
        df = fetch_data(symbol, "1d")
        if df is None or len(df) < 20:
            msg += f"{name} ({symbol}): تعذر في البيانات\n"
            continue
        df = calculate_indicators(df)
        direction = interpret_trend(df)
        price = df["Close"].iloc[-1]
        msg += f"{name} ({symbol}): {direction} – السعر: {price:.2f}\n"

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
