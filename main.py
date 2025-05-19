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

# التوكن والقناة الحقيقية
BOT_TOKEN = "7883771248:AAFfwmcF3hcHz17_IG0KfyOCSGLjMBzyg8E"
CHANNEL_ID = "@hashimali1986"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"خطأ في إرسال الرسالة: {e}")

assets = {
    "ذهب": {"symbol": "GC=F", "target": 20},
    "بيتكوين": {"symbol": "BTC-USD", "target": 2000},
    "SPX": {"symbol": "^GSPC", "target": 50},
    "NDX": {"symbol": "^NDX", "target": 300}
}

active_trades = {}
last_summary_time = time.time()

def fetch_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=10d&interval=1h"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()

        if "chart" not in data or "error" in data["chart"] and data["chart"]["error"]:
            return None

        timestamps = data["chart"]["result"][0]["timestamp"]
        prices = data["chart"]["result"][0]["indicators"]["quote"][0]
        df = pd.DataFrame(prices)
        df["Date"] = pd.to_datetime(timestamps, unit="s")
        df.set_index("Date", inplace=True)
        return df.dropna().tail(1000)

    except Exception as e:
        print(f"fetch_data error for {symbol}: {e}")
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
    try:
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
            active_trades[name] = {"type": signal, "entry": entry, "target": goal}
            msg = (
                f"#{name}\n"
                f"إشارة: {signal.upper()}\n"
                f"الدخول: {entry:.2f} → الهدف: {goal:.2f}\n"
                f"RSI: {last['RSI']:.2f}, EMA9: {last['EMA9']:.2f}, EMA21: {last['EMA21']:.2f}\n"
                f"الدعم: {last['Support']:.2f}, المقاومة: {last['Resistance']:.2f}\n"
                f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            msg = (
                f"#{name}\n"
                f"لا توجد توصية: الشروط الفنية غير متحققة.\n"
                f"الإغلاق: {price:.2f}, RSI: {last['RSI']:.2f}, EMA9: {last['EMA9']:.2f}, EMA21: {last['EMA21']:.2f}"
            )
        send_telegram_message(msg)

    except Exception as e:
        print(f"check_signal error for {name}: {e}")
        send_telegram_message(f"#{name} | تعذر تحليل البيانات.")

def monitor_trades():
    for name, trade in list(active_trades.items()):
        try:
            df = fetch_data(assets[name]["symbol"])
            if df is not None:
                current_price = df["Close"].iloc[-1]
                if trade["type"] == "buy" and current_price >= trade["target"]:
                    send_telegram_message(f"#{name} تحقق الهدف: BUY عند {trade['target']:.2f}")
                    del active_trades[name]
                elif trade["type"] == "sell" and current_price <= trade["target"]:
                    send_telegram_message(f"#{name} تحقق الهدف: SELL عند {trade['target']:.2f}")
                    del active_trades[name]
        except Exception as e:
            print(f"monitor_trades error for {name}: {e}")

def summarize():
    global last_summary_time
    try:
        if time.time() - last_summary_time >= 86400:
            summary = f"ملخص يومي: تم تنفيذ {len(active_trades)} توصيات نشطة اليوم."
            send_telegram_message(summary)
            last_summary_time = time.time()
    except Exception as e:
        print(f"summarize error: {e}")

def main_loop():
    while True:
        for name, info in assets.items():
            try:
                df = fetch_data(info["symbol"])
                if df is None or df.empty:
                    send_telegram_message(f"#{name} | تعذر جلب البيانات.")
                    continue
                df = calculate_indicators(df)
                check_signal(df, name, info["target"])
            except Exception as e:
                print(f"main_loop error on {name}: {e}")
        monitor_trades()
        summarize()
        time.sleep(3600)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل المحلل الذكي بنجاح وجاهز لإرسال التوصيات كل ساعة.")
    main_loop()
