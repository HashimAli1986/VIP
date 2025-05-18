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

# إعداد التوكن والقناة
BOT_TOKEN = "7883771248:AAFfwmcF3hcHz17_IG0KfyOCSGLjMBzyg8E"
CHANNEL_ID = "@hashimali1986"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text}
    requests.post(url, data=data)

assets = {
    "ذهب": {"symbol": "GC=F", "target": 20},
    "بيتكوين": {"symbol": "BTC-USD", "target": 2000},
    "SPX": {"symbol": "^GSPC", "target": 50},
    "NDX": {"symbol": "^NDX", "target": 300}
}

active_trades = {}
last_summary_time = time.time()

def fetch_data(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=60d&interval=1h"
    try:
        response = requests.get(url)
        data = response.json()

        # التحقق من وجود النتائج
        if not data.get("chart") or not data["chart"].get("result"):
            print(f"{symbol} | لا يوجد نتائج في البيانات.")
            return None

        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp")
        indicators = result.get("indicators", {})
        quote = indicators.get("quote", [{}])[0]

        # التحقق من توفر الأعمدة
        required_keys = ["open", "high", "low", "close"]
        for key in required_keys:
            if key not in quote:
                print(f"{symbol} | البيانات ناقصة: {key} غير موجود.")
                return None

        df = pd.DataFrame({
            "Open": quote["open"],
            "High": quote["high"],
            "Low": quote["low"],
            "Close": quote["close"]
        })

        df["Date"] = pd.to_datetime(timestamps, unit="s")
        df.set_index("Date", inplace=True)
        return df.tail(1000)

    except Exception as e:
        print(f"{symbol} | خطأ أثناء جلب البيانات: {e}")
        return None

        timestamps = data["chart"]["result"][0]["timestamp"]
        prices = data["chart"]["result"][0]["indicators"]["quote"][0]
        df = pd.DataFrame(prices)
        df["Date"] = pd.to_datetime(timestamps, unit="s")
        df.set_index("Date", inplace=True)
        return df.dropna().tail(1000)

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

def check_signal(df, name, target):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = last["Close"]
    signal = None

    if prev["EMA9"] < prev["EMA21"] and last["EMA9"] > last["EMA21"] and last["RSI"] < 30:
        signal = "buy"
    elif prev["EMA9"] > prev["EMA21"] and last["EMA9"] < last["EMA21"] and last["RSI"] > 70:
        signal = "sell"

    if signal:
        entry = price
        goal = entry + target if signal == "buy" else entry - target
        active_trades[name] = {
            "type": signal,
            "entry": entry,
            "target": goal
        }
        msg = (
            f"#{name}\n"
            f"إشارة: {signal.upper()}\n"
            f"الدخول: {entry:.2f} → الهدف: {goal:.2f}\n"
            f"RSI: {last['RSI']:.2f}, EMA9: {last['EMA9']:.2f}, EMA21: {last['EMA21']:.2f}\n"
            f"الدعم: {last['Support']:.2f}, المقاومة: {last['Resistance']:.2f}\n"
            f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        send_telegram_message(msg)
    else:
        msg = (
            f"#{name}\n"
            f"لا توجد توصية: الشروط الفنية غير متحققة.\n"
            f"الإغلاق: {price:.2f}, RSI: {last['RSI']:.2f}, EMA9: {last['EMA9']:.2f}, EMA21: {last['EMA21']:.2f}"
        )
        send_telegram_message(msg)

def monitor_trades():
    for name, trade in list(active_trades.items()):
        df = fetch_data(assets[name]["symbol"])
        if df is not None:
            current_price = df["Close"].iloc[-1]
            if trade["type"] == "buy" and current_price >= trade["target"]:
                send_telegram_message(f"#{name} تحقق الهدف: BUY عند {trade['target']:.2f}")
                del active_trades[name]
            elif trade["type"] == "sell" and current_price <= trade["target"]:
                send_telegram_message(f"#{name} تحقق الهدف: SELL عند {trade['target']:.2f}")
                del active_trades[name]

def summarize():
    global last_summary_time
    if time.time() - last_summary_time >= 86400:
        summary = f"ملخص يومي: تم تنفيذ {len(active_trades)} توصيات نشطة اليوم."
        send_telegram_message(summary)
        last_summary_time = time.time()

def main_loop():
    while True:
        for name, info in assets.items():
            df = fetch_data(info["symbol"])
            if df is None or df.empty:
                send_telegram_message(f"#{name} | تعذر جلب البيانات.")
                continue
            df = calculate_indicators(df)
            check_signal(df, name, info["target"])
        monitor_trades()
        summarize()
        time.sleep(3600)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل المحلل الذكي بنجاح وجاهز لإرسال التوصيات.")
    main_loop()
