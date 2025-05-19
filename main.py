import requests
import pandas as pd
import time
from datetime import datetime, timedelta
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

# إعداد التوكن والقناة
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
    "ذهب": {"symbol": "GC=F", "target": 20},
    "بيتكوين": {"symbol": "BTC-USD", "target": 2000},
    "SPX": {"symbol": "^GSPC", "target": 50},
    "NDX": {"symbol": "^NDX", "target": 300}
}

def fetch_hourly_data(symbol):
    """جلب بيانات الساعة الحالية والسابقة"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=2d&interval=1h"
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
            "Close": prices["close"],
            "Date": pd.to_datetime(timestamps, unit="s")
        })
        return df.dropna().tail(2)  # آخر ساعتين
    except Exception as e:
        print(f"fetch_hourly_data error: {e}")
        return None

def predict_next_candle(df):
    """توقع اتجاه الشمعة القادمة باستخدام EMA9/EMA21"""
    if len(df) < 2:
        return "غير متوفر"
    
    # حساب المؤشرات
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    
    # تحليل الاتجاه
    last_ema9 = df["EMA9"].iloc[-1]
    last_ema21 = df["EMA21"].iloc[-1]
    
    if last_ema9 > last_ema21:
        return "صاعدة ↑"
    else:
        return "هابطة ↓"

def send_hourly_update():
    """إرسال تحديثات الأسعار كل ساعة مع التوقع"""
    messages = []
    for name, info in assets.items():
        df = fetch_hourly_data(info["symbol"])
        if df is not None and len(df) >= 2:
            current_price = df["Close"].iloc[-1]
            prediction = predict_next_candle(df)
            messages.append(
                f"#{name}\n"
                f"السعر الحالي: {current_price:.2f}\n"
                f"التوقع للساعة القادمة: {prediction}\n"
                "―――――――――――――――――――"
            )
    
    if messages:
        header = "🕒 **تحديث الساعة**\n" + datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC") + "\n\n"
        send_telegram_message(header + "\n".join(messages))

def main_loop():
    keep_alive()
    send_telegram_message("✅ تم تشغيل النظام مع التحديثات الساعية!")
    
    last_hour = -1
    while True:
        now = datetime.utcnow()
        if now.minute == 0 and now.hour != last_hour:  # عند بداية كل ساعة
            send_hourly_update()
            last_hour = now.hour
            time.sleep(60)  # منع التكرار
        time.sleep(30)  # تحقق كل 30 ثانية

if __name__ == "__main__":
    main_loop()
