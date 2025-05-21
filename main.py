import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "المحلل الذكي يعمل بنجاح"

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

assets = {
    "ذهب": {"symbol": "GC=F"},
    "بيتكوين": {"symbol": "BTC-USD"},
    "SPX": {"symbol": "^GSPC"},
    "NDX": {"symbol": "^NDX"}
}

def fetch_daily_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()

        if not data["chart"]["result"]:
            return None

        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        prices = result["indicators"]["quote"][0]

        df = pd.DataFrame({
            "Open": prices["open"],
            "High": prices["high"],
            "Low": prices["low"],
            "Close": prices["close"]
        })
        df["Date"] = pd.to_datetime(timestamps, unit="s")
        df.set_index("Date", inplace=True)
        return df.dropna().iloc[-1000:]
    except Exception as e:
        print(f"fetch_data error ({symbol}): {e}")
        return None

def calculate_indicators(df):
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    df["Support"] = df["Low"].rolling(50).min()
    df["Resistance"] = df["High"].rolling(50).max()
    return df

def analyze_asset(name, df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = last["Close"]
    direction = "صاعدة" if last["Close"] > last["Open"] else "هابطة"
    ema_cross = "صعود" if prev["EMA9"] < prev["EMA21"] and last["EMA9"] > last["EMA21"] else "هبوط" if prev["EMA9"] > prev["EMA21"] and last["EMA9"] < last["EMA21"] else "جانبي"
    rsi_value = last["RSI"]
    rsi_zone = "تشبع بيع" if rsi_value < 30 else "تشبع شراء" if rsi_value > 70 else "محايد"
    support = last["Support"]
    resistance = last["Resistance"]

    # توليد التوصية حسب الأصل
    recommendation = ""
    if name == "ذهب" and direction == "صاعدة":
        recommendation = f"التوصية: شراء | الدخول: {price:.0f}-{price+3:.0f} | الهدف: {price+15:.0f} | الوقف: {price-10:.0f} | القوة: قوية"
    elif name == "بيتكوين" and rsi_value > 70:
        recommendation = f"التوصية: بيع | الدخول: {price-100:.0f}-{price+100:.0f} | الهدف: {price-2000:.0f} | الوقف: {price+1000:.0f} | القوة: متوسطة إلى قوية"
    elif name == "SPX" and rsi_value > 80:
        recommendation = f"التوصية: بيع | الدخول: {price:.0f}-{price+10:.0f} | الهدف: {price-40:.0f} | الوقف: {price+30:.0f} | القوة: قوية"
    elif name == "NDX" and rsi_value > 80:
        recommendation = f"التوصية: بيع | الدخول: {price:.0f}-{price+20:.0f} | الهدف: {price-150:.0f} | الوقف: {price+100:.0f} | القوة: قوية جدًا"

    summary = (
        f"{name}:\n"
        f"السعر الحالي: {price:.2f}\n"
        f"الاتجاه المتوقع: {direction}\n"
        f"تقاطع EMA: {ema_cross}\n"
        f"RSI: {rsi_value:.2f} ({rsi_zone})\n"
        f"الدعم: {support:.2f} | المقاومة: {resistance:.2f}\n"
        f"{recommendation if recommendation else ''}"
    )
    return summary

def hourly_price_update():
    last_sent_hour = -1
    while True:
        now = datetime.utcnow()
        if now.hour != last_sent_hour and now.minute >= 0:
            last_sent_hour = now.hour
            try:
                msg = f"تحديث الساعة {now.strftime('%H:%M')} UTC\n\n"
                for name, info in assets.items():
                    df = fetch_daily_data(info["symbol"])
                    if df is not None and len(df) >= 1000:
                        df = calculate_indicators(df)
                        msg += analyze_asset(name, df) + "\n\n"
                    else:
                        msg += f"{name}: البيانات غير متوفرة.\n\n"
                send_telegram_message(msg.strip())
            except Exception as e:
                send_telegram_message(f"⚠️ خطأ: {str(e)}")
        time.sleep(30)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل المحلل الذكي بنجاح: توصيات فنية + تحليل شموع + تحديث كل ساعة.")
    Thread(target=hourly_price_update).start()hourly_price_update).start()y_price_update).start()
