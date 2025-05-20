import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
import telebot
import requests

BOT_TOKEN = "7883771248:AAFfwmcF3hcHz17_IG0KfyOCSGLjMBzyg8E"
CHANNEL_ID = "@hashimali1986"
bot = telebot.TeleBot(BOT_TOKEN)

ASSETS = {
    "ذهب": "GC=F",
    "بيتكوين": "BTC-USD",
    "S&P500": "^GSPC",
    "Nasdaq": "^NDX"
}

TIMEFRAME = "5m"

def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger_bands(series, period=20, num_std=2):
    ma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    return upper, lower

def calculate_macd(series, fast=12, slow=26, signal=9):
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    return macd_line, signal_line

def check_upcoming_news():
    try:
        url = "https://site.api.efxdata.com/calendar?days=1"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return False
        data = response.json()
        now = datetime.utcnow()
        for item in data.get("data", []):
            event_time = datetime.strptime(item["datetime"], "%Y-%m-%dT%H:%M:%SZ")
            if 0 <= (event_time - now).total_seconds() <= 900 and item["impact"] in ["High", "Medium"]:
                return True
        return False
    except:
        return False

def fetch_realtime_data(symbol):
    data = yf.download(symbol, period="7d", interval=TIMEFRAME)
    return data.dropna().tail(1000)

def calculate_indicators(df):
    close = df['Close'].squeeze()
    df['EMA9'] = calculate_ema(close, 9)
    df['EMA21'] = calculate_ema(close, 21)
    df['RSI'] = calculate_rsi(close)
    df['BB_Upper'], df['BB_Lower'] = calculate_bollinger_bands(close)
    df['MACD'], df['MACD_Signal'] = calculate_macd(close)
    return df

def detect_trend_pattern(df):
    last_1000 = df.tail(1000)
    bullish = (last_1000['Close'] > last_1000['Open']).sum()
    bearish = (last_1000['Close'] < last_1000['Open']).sum()
    total = len(last_1000)
    ratio_bull = bullish / total
    ratio_bear = bearish / total
    if ratio_bull > 0.6:
        return "صعودي"
    elif ratio_bear > 0.6:
        return "هبوطي"
    else:
        return "جانبي"

def generate_signals(df):
    df['Buy_Signal'] = ((df['EMA9'] > df['EMA21']) & (df['RSI'] < 30) & (df['Close'] < df['BB_Lower']))
    df['Sell_Signal'] = ((df['EMA9'] < df['EMA21']) & (df['RSI'] > 70) & (df['Close'] > df['BB_Upper']))
    return df

def send_alert(asset, signal_type, df, trend_type):
    last_row = df.iloc[-1]
    price = float(last_row['Close'])
    rsi = float(last_row['RSI'])
    time_str = datetime.now().strftime("%H:%M:%S")
    message = f"""
🚨 **إشارة {signal_type} لـ {asset}** 🚨
- السعر: `{price:.2f}`
- RSI: `{rsi:.2f}`
- نمط آخر 1000 شمعة: `{trend_type}`
- الوقت: `{time_str}`
    """
    bot.send_message(CHANNEL_ID, message, parse_mode="Markdown")

def monitor_assets():
    while True:
        try:
            if check_upcoming_news():
                bot.send_message(CHANNEL_ID, "⏸️ تم إيقاف التنبيهات مؤقتًا بسبب خبر اقتصادي مهم خلال دقائق.")
                time.sleep(300)
                continue

            for asset, symbol in ASSETS.items():
                df = fetch_realtime_data(symbol)
                if df.empty or len(df) < 100:
                    continue
                df = calculate_indicators(df)
                trend_type = detect_trend_pattern(df)
                df = generate_signals(df)
                if df['Buy_Signal'].iloc[-1]:
                    send_alert(asset, "شراء", df, trend_type)
                elif df['Sell_Signal'].iloc[-1]:
                    send_alert(asset, "بيع", df, trend_type)
            time.sleep(300)
        except Exception as e:
            bot.send_message(CHANNEL_ID, f"⚠️ خطأ: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    bot.send_message(CHANNEL_ID, "✅ النظام يعمل الآن: مؤشرات + تحليل 1000 شمعة + اتجاه (صعود/هبوط) + مراقبة أخبار.")
    monitor_assets()
