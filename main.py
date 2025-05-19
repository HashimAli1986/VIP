import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread
import yfinance as yf

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
        df = yf.download(symbol, period="3y", interval="1d", progress=False)
        return df.tail(1000)
    except Exception as e:
        print(f"fetch_data error: {e}")
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

    ema9_prev = prev["EMA9"].item() if hasattr(prev["EMA9"], "item") else prev["EMA9"]
    ema21_prev = prev["EMA21"].item() if hasattr(prev["EMA21"], "item") else prev["EMA21"]
    ema9_last = last["EMA9"].item() if hasattr(last["EMA9"], "item") else last["EMA9"]
    ema21_last = last["EMA21"].item() if hasattr(last["EMA21"], "item") else last["EMA21"]
    rsi_value = last["RSI"].item() if hasattr(last["RSI"], "item") else last["RSI"]
    support = last["Support"].item() if hasattr(last["Support"], "item") else last["Support"]
    resistance = last["Resistance"].item() if hasattr(last["Resistance"], "item") else last["Resistance"]

    ema_cross = "صعود" if ema9_prev < ema21_prev and ema9_last > ema21_last else "هبوط" if ema9_prev > ema21_prev and ema9_last < ema21_last else "جانبي"
    rsi_zone = "تشبع بيع" if rsi_value < 30 else "تشبع شراء" if rsi_value > 70 else "محايد"

    summary = (
        f"الاتجاه المتوقع: {direction}\n"
        f"تقاطع EMA: {ema_cross}\n"
        f"RSI: {rsi_value:.2f} ({rsi_zone})\n"
        f"الدعم: {support:.2f} | المقاومة: {resistance:.2f}"
    )
    return float(last["Close"]), summary

def hourly_price_update():
    last_sent_hour = -1
    while True:
        now = datetime.utcnow()
        if now.hour != last_sent_hour and now.minute >= 0:
            last_sent_hour = now.hour
            try:
                print(f"تشغيل التحديث الساعة {now.strftime('%H:%M')} UTC")
                msg = f"تحديث الساعة {now.strftime('%H:%M')} UTC\n"
                for name, info in assets.items():
                    df = fetch_daily_data(info["symbol"])
                    if df is not None and len(df) >= 1000:
                        df = calculate_indicators(df)
                        price, direction_info = analyze_next_hour_direction(df)
                        msg += f"\n{name}:\nالسعر الحالي: {price:.2f}\n{direction_info}\n"
                    else:
                        msg += f"\n{name}: البيانات غير متوفرة.\n"
                send_telegram_message(msg)
            except Exception as e:
                error_msg = f"Error in hourly update: {e}"
                print(error_msg)
                send_telegram_message(f"تنبيه: {error_msg}")
        time.sleep(30)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل المحلل الذكي بنجاح: إرسال كل ساعة + تحليل 1000 شمعة يومية.")
    Thread(target=hourly_price_update).start()
