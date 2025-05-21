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

# استخدام رموز العقود الآجلة
assets = {
    "ذهب": {"symbol": "GC=F"},
    "بيتكوين": {"symbol": "BTC-USD"},
    "SPX": {"symbol": "ES=F"},   # Futures for S&P 500
    "NDX": {"symbol": "NQ=F"}    # Futures for Nasdaq
}

def fetch_intraday_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1m"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
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
        return df.dropna().tail(100)
    except Exception as e:
        print(f"fetch_intraday_data error ({symbol}): {e}")
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

def analyze_next_hour_direction(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    direction = "صاعدة" if last["Close"] > last["Open"] else "هابطة"
    ema_cross = "صعود" if prev["EMA9"] < prev["EMA21"] and last["EMA9"] > last["EMA21"] else "هبوط" if prev["EMA9"] > prev["EMA21"] and last["EMA9"] < last["EMA21"] else "جانبي"
    rsi_zone = "تشبع بيع" if last["RSI"] < 30 else "تشبع شراء" if last["RSI"] > 70 else "محايد"
    return last["Close"], direction, ema_cross, rsi_zone, last["RSI"], last["Support"], last["Resistance"]

def generate_full_report(name, price, direction, ema_cross, rsi_value, rsi_zone, support, resistance):
    summary = (
        f"{name}:\n"
        f"السعر الحالي: {price:.2f}\n"
        f"الاتجاه المتوقع: {direction}\n"
        f"تقاطع EMA: {ema_cross}\n"
        f"RSI: {rsi_value:.2f} ({rsi_zone})\n"
        f"الدعم: {support:.2f} | المقاومة: {resistance:.2f}"
    )

    if name == "ذهب":
        if direction == "صاعدة" and ema_cross == "صعود":
            recommendation = f"التوصية: شراء | الدخول: {price:.0f}-{price+3:.0f} | الهدف: {price+15:.0f} | الوقف: {price-10:.0f} | القوة: قوية"
        else:
            recommendation = f"التوصية: بيع | الدخول: {price-2:.0f}-{price+1:.0f} | الهدف: {price-20:.0f} | الوقف: {price+10:.0f} | القوة: متوسطة"
    elif name == "بيتكوين":
        recommendation = f"التوصية: بيع | الدخول: {price-100:.0f}-{price+100:.0f} | الهدف: {price-2000:.0f} | الوقف: {price+1000:.0f} | القوة: متوسطة إلى قوية"
    elif name == "SPX":
        recommendation = f"التوصية: بيع | الدخول: {price:.0f}-{price+10:.0f} | الهدف: {price-40:.0f} | الوقف: {price+30:.0f} | القوة: قوية"
    elif name == "NDX":
        recommendation = f"التوصية: بيع | الدخول: {price:.0f}-{price+20:.0f} | الهدف: {price-150:.0f} | الوقف: {price+100:.0f} | القوة: قوية جدًا"
    else:
        recommendation = "التوصية: غير متوفرة"

    return f"{summary}\n{recommendation}\n"

def hourly_price_update():
    last_sent_hour = -1
    while True:
        now = datetime.utcnow()
        if now.hour != last_sent_hour and now.minute >= 0:
            last_sent_hour = now.hour
            try:
                msg = f"تحديث الساعة {now.strftime('%H:%M')} UTC\n"
                for name, info in assets.items():
                    df = fetch_intraday_data(info["symbol"])
                    if df is None or df.empty or len(df) < 50:
                        msg += f"\n{name}: البيانات غير متوفرة.\n"
                    else:
                        df = calculate_indicators(df)
                        price, direction, ema_cross, rsi_zone, rsi_value, support, resistance = analyze_next_hour_direction(df)
                        report = generate_full_report(name, price, direction, ema_cross, rsi_value, rsi_zone, support, resistance)
                        msg += f"\n{report}"
                send_telegram_message(msg)
            except Exception as e:
                send_telegram_message(f"⚠️ خطأ في التحديث: {e}")
        time.sleep(30)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل المحلل الذكي بنجاح باستخدام بيانات العقود الآجلة والمؤشرات اللحظية.")
    Thread(target=hourly_price_update).start()
