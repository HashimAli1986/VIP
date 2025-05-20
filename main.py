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
    "MSTR": {"symbol": "MSTR"},
    "APP": {"symbol": "APP"},
    "AVGO": {"symbol": "AVGO"},
    "SMCI": {"symbol": "SMCI"},
    "GS": {"symbol": "GS"},
    "MU": {"symbol": "MU"},
    "META": {"symbol": "META"},
    "APPL": {"symbol": "APPL"},
    "COIN": {"symbol": "COIN"},
    "TSLA": {"symbol": "TSLA"},
    "LLY": {"symbol": "LLY"},
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
            print(f"لا توجد بيانات لـ {symbol}")
            return None
            
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        prices = result["indicators"]["quote"][0]
        
        if not all(k in prices for k in ["open", "high", "low", "close"]):
            print(f"بيانات غير مكتملة لـ {symbol}")
            return None
            
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

def analyze_next_hour_direction(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    direction = "صاعدة" if last["Close"] > last["Open"] else "هابطة"
    ema_cross = "صعود" if prev["EMA9"] < prev["EMA21"] and last["EMA9"] > last["EMA21"] else "هبوط" if prev["EMA9"] > prev["EMA21"] and last["EMA9"] < last["EMA21"] else "جانبي"
    rsi_zone = "تشبع بيع" if last["RSI"] < 30 else "تشبع شراء" if last["RSI"] > 70 else "محايد"

    summary = (
        f"الاتجاه المتوقع: {direction}\n"
        f"تقاطع EMA: {ema_cross}\n"
        f"RSI: {last['RSI']:.2f} ({rsi_zone})\n"
        f"الدعم: {last['Support']:.2f} | المقاومة: {last['Resistance']:.2f}"
    )
    return last["Close"], summary

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
                    if df is None:
                        msg += f"\n{name}: البيانات غير متوفرة (فشل جلب البيانات من المصدر).\n"
                    elif df.empty:
                        msg += f"\n{name}: البيانات غير متوفرة (البيانات فاضية).\n"
                    elif len(df) < 1000:
                        msg += f"\n{name}: البيانات غير كافية (< 1000 شمعة).\n"
                    else:
                        df = calculate_indicators(df)
                        price, direction_info = analyze_next_hour_direction(df)
                        msg += f"\n{name}:\nالسعر الحالي: {price:.2f}\n{direction_info}\n"
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
