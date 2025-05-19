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

active_trades = {}
trade_start_times = {}
last_summary_time = time.time()

def fetch_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=180d&interval=4h"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        timestamps = data["chart"]["result"][0]["timestamp"]
        prices = data["chart"]["result"][0]["indicators"]["quote"][0]
        df = pd.DataFrame(prices)
        df["Date"] = pd.to_datetime(timestamps, unit="s")
        df.set_index("Date", inplace=True)
        return df.dropna().tail(1000)
    except Exception as e:
        print(f"fetch_data error: {e}")
        return None

def get_upcoming_news():
    try:
        url = "https://site.api.efxdata.com/calendar?days=1"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            news = r.json()
            now = datetime.utcnow()
            for item in news.get("data", []):
                event_time = datetime.strptime(item["datetime"], "%Y-%m-%dT%H:%M:%SZ")
                if 0 <= (event_time - now).total_seconds() <= 3600 and item["impact"] in ["High", "Medium"]:
                    return f"تنبيه: خبر اقتصادي قريب - {item['title']} الساعة {event_time.strftime('%H:%M')} UTC"
        return ""
    except:
        return ""

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

def analyze_candle(df):
    last = df.iloc[-1]
    return "صاعدة" if last["Close"] > last["Open"] else "هابطة"

def check_signal(df, name, target):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = last["Close"]
    candle_type = analyze_candle(df)
    signal = "buy" if candle_type == "صاعدة" else "sell"
    strength = "قوية" if (
        (signal == "buy" and prev["EMA9"] < prev["EMA21"] and last["EMA9"] > last["EMA21"] and last["RSI"] < 35)
        or
        (signal == "sell" and prev["EMA9"] > prev["EMA21"] and last["EMA9"] < last["EMA21"] and last["RSI"] > 65)
    ) else "ضعيفة – للمراقبة فقط"

    entry = price
    goal = entry + target if signal == "buy" else entry - target
    active_trades[name] = {"type": signal, "entry": entry, "target": goal}
    trade_start_times[name] = datetime.now()

    news_alert = get_upcoming_news()
    msg = (
        f"#{name}\n"
        f"نوع الشمعة: {candle_type}\n"
        f"إشارة: {signal.upper()} ({strength})\n"
        f"الدخول: {entry:.2f} → الهدف: {goal:.2f}\n"
        f"RSI: {last['RSI']:.2f}, EMA9: {last['EMA9']:.2f}, EMA21: {last['EMA21']:.2f}\n"
        f"الدعم: {last['Support']:.2f}, المقاومة: {last['Resistance']:.2f}\n"
        f"الوقت: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
        f"{news_alert}"
    )
    send_telegram_message(msg)

def monitor_trades():
    for name in list(active_trades.keys()):
        df = fetch_data(assets[name]["symbol"])
        if df is None:
            continue
        current_price = df["Close"].iloc[-1]
        trade = active_trades[name]
        if (trade["type"] == "buy" and current_price >= trade["target"]) or (
            trade["type"] == "sell" and current_price <= trade["target"]):
            send_telegram_message(f"#{name} تحقق الهدف: {trade['type'].upper()} عند {trade['target']:.2f}")
            del active_trades[name]
            del trade_start_times[name]
        else:
            elapsed = datetime.utcnow() - trade_start_times[name]
            if elapsed.total_seconds() >= 4 * 3600:
                send_telegram_message(f"#{name} | تم إغلاق الصفقة بعد 4 ساعات دون تحقيق الهدف.")
                del active_trades[name]
                del trade_start_times[name]

def summarize():
    global last_summary_time
    if time.time() - last_summary_time >= 86400:
        summary = f"ملخص يومي: عدد التوصيات الحالية: {len(active_trades)}"
        send_telegram_message(summary)
        last_summary_time = time.time()

def main_loop():
    last_checked_hour = -1
    while True:
        now = datetime.utcnow()
        if now.hour % 4 == 0 and now.hour != last_checked_hour:
            last_checked_hour = now.hour
            for name, info in assets.items():
                df = fetch_data(info["symbol"])
                if df is not None and not df.empty:
                    df = calculate_indicators(df)
                    check_signal(df, name, info["target"])
        monitor_trades()
        summarize()
        time.sleep(900)

if __name__ == "__main__":
    keep_alive()
    send_telegram_message("✅ تم تشغيل المحلل الذكي VIP بنجاح مع ربط الأخبار الاقتصادية.")
    main_loop()
