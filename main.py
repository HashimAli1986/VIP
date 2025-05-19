import yfinance as yf
import pandas as pd
import numpy as np
import time
from datetime import datetime
import telebot
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

# ------------------- إعدادات التليجرام ------------------- #
BOT_TOKEN = "7883771248:AAFfwmcF3hcHz17_IG0KfyOCSGLjMBzyg8E"
CHANNEL_ID = "@hashimali1986"
bot = telebot.TeleBot(BOT_TOKEN)

# ------------------- إعدادات الأصول ------------------- #
ASSETS = {
    "ذهب": "GC=F",
    "بيتكوين": "BTC-USD",
    "S&P500": "^GSPC",
    "Nasdaq": "^NDX"
}

TIMEFRAME = "5m"  # الإطار الزمني (5 دقائق)

# ------------------- الدوال الأساسية (مُحدَّثة) ------------------- #
def fetch_realtime_data(symbol):
    """جلب البيانات وتحويلها إلى 1D بشكل آمن"""
    data = yf.download(symbol, period="1d", interval=TIMEFRAME)
    if not data.empty:
        # تحويل الأعمدة إلى 1D باستخدام .values.flatten()
        for col in data.columns:
            data[col] = data[col].values.flatten()
    return data.dropna()

def calculate_indicators(df):
    """حساب المؤشرات مع ضمان 1D"""
    close_prices = df['Close'].values.flatten()  # تأكيد 1D
    
    # حساب المؤشرات باستخدام بيانات 1D
    df['EMA9'] = EMAIndicator(close_prices, window=9).ema_indicator()
    df['EMA21'] = EMAIndicator(close_prices, window=21).ema_indicator()
    df['RSI'] = RSIIndicator(close_prices, window=14).rsi()
    
    bb = BollingerBands(close_prices, window=20, window_dev=2)
    df['BB_Upper'] = bb.bollinger_hband()
    df['BB_Lower'] = bb.bollinger_lband()
    
    macd = MACD(close_prices, window_slow=26, window_fast=12, window_sign=9)
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    
    return df

def generate_signals(df):
    """إنشاء إشارات التداول مع بيانات 1D"""
    close = df['Close'].values.flatten()
    ema9 = df['EMA9'].values.flatten()
    ema21 = df['EMA21'].values.flatten()
    rsi = df['RSI'].values.flatten()
    bb_upper = df['BB_Upper'].values.flatten()
    bb_lower = df['BB_Lower'].values.flatten()
    
    # إشارات الشراء والبيع
    df['Buy_Signal'] = (ema9 > ema21) & (rsi < 30) & (close < bb_lower)
    df['Sell_Signal'] = (ema9 < ema21) & (rsi > 70) & (close > bb_upper)
    
    return df

def send_alert(asset, signal_type, df):
    """إرسال التنبيه مع تحويل القيم إلى Scalars"""
    last_row = df.iloc[-1]
    price = np.asscalar(last_row['Close'])  # تحويل إلى قيمة مفردة
    rsi = np.asscalar(last_row['RSI'])
    time_str = datetime.now().strftime("%H:%M:%S")
    
    message = f"""
    🚨 **إشارة {signal_type} لـ {asset}** 🚨
    - السعر: `{price:.2f}`
    - RSI: `{rsi:.2f}`
    - الوقت: `{time_str}`
    """
    bot.send_message(CHANNEL_ID, message, parse_mode="Markdown")

# ------------------- المراقبة التلقائية ------------------- #
def monitor_assets():
    while True:
        try:
            for asset, symbol in ASSETS.items():
                df = fetch_realtime_data(symbol)
                if df.empty:
                    continue
                df = calculate_indicators(df)
                df = generate_signals(df)
                last_row = df.iloc[-1]
                
                if last_row['Buy_Signal']:
                    send_alert(asset, "شراء", df)
                elif last_row['Sell_Signal']:
                    send_alert(asset, "بيع", df)
            
            time.sleep(300)  # انتظر 5 دقائق
        
        except Exception as e:
            error_msg = f"⚠️ خطأ: {str(e)}"
            bot.send_message(CHANNEL_ID, error_msg)
            time.sleep(60)

# ------------------- التشغيل الرئيسي ------------------- #
if __name__ == "__main__":
    bot.send_message(CHANNEL_ID, "✅ النظام يعمل الآن!")
    monitor_assets()
