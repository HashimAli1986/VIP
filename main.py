import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import telebot
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import ccxt  # للتكامل مع منصات التداول (اختياري)

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

LEVERAGE = 5  # الرافعة المالية (اختياري)
TIMEFRAME = "5m"  # الإطار الزمني (5 دقائق)

# ------------------- الدوال الأساسية ------------------- #
def fetch_realtime_data(symbol):
    """جلب البيانات المباشرة من Yahoo Finance"""
    data = yf.download(symbol, period="1d", interval=TIMEFRAME)
    return data.dropna()

def calculate_indicators(df):
    """حساب المؤشرات الفنية لكل أصل"""
    # المتوسطات المتحركة
    df['EMA9'] = EMAIndicator(df['Close'], window=9).ema_indicator()
    df['EMA21'] = EMAIndicator(df['Close'], window=21).ema_indicator()
    
    # RSI
    df['RSI'] = RSIIndicator(df['Close'], window=14).rsi()
    
    # Bollinger Bands
    bb = BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_Upper'] = bb.bollinger_hband()
    df['BB_Lower'] = bb.bollinger_lband()
    
    # MACD
    macd = MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    
    return df

def generate_signals(df):
    """إنشاء إشارات التداول بناءً على المؤشرات"""
    # إشارة الشراء: EMA9 > EMA21 + RSI < 30 + السعر تحت Bollinger Lower
    df['Buy_Signal'] = (
        (df['EMA9'] > df['EMA21']) & 
        (df['RSI'] < 30) & 
        (df['Close'] < df['BB_Lower'])
    )
    
    # إشارة البيع: EMA9 < EMA21 + RSI > 70 + السعر فوق Bollinger Upper
    df['Sell_Signal'] = (
        (df['EMA9'] < df['EMA21']) & 
        (df['RSI'] > 70) & 
        (df['Close'] > df['BB_Upper'])
    )
    
    return df

def send_alert(asset, signal_type, price):
    """إرسال تنبيه عبر التليجرام مع تفاصيل الأصل"""
    message = f"""
    🚨 **إشارة {signal_type} لـ {asset}** 🚨
    - السعر الحالي: **{price:.2f}**
    - الوقت: `{datetime.now().strftime("%H:%M:%S")}`
    """
    bot.send_message(CHANNEL_ID, message, parse_mode="Markdown")

# ------------------- التداول الآلي (اختياري) ------------------- #
def execute_trade(symbol, side, quantity):
    """تنفيذ الصفقات عبر Binance (يتطلب API Keys)"""
    exchange = ccxt.binance({
        'apiKey': 'YOUR_BINANCE_API_KEY',
        'secret': 'YOUR_BINANCE_SECRET_KEY',
    })
    try:
        order = exchange.create_market_order(symbol, side, quantity)
        print(f"تم التنفيذ: {order}")
    except Exception as e:
        print(f"فشل التنفيذ: {e}")

# ------------------- المراقبة التلقائية ------------------- #
def monitor_assets():
    while True:
        try:
            for asset, symbol in ASSETS.items():
                df = fetch_realtime_data(symbol)
                df = calculate_indicators(df)
                df = generate_signals(df)
                last_row = df.iloc[-1]
                
                if last_row['Buy_Signal']:
                    send_alert(asset, "شراء", last_row['Close'])
                    # execute_trade(symbol, "buy", 0.01)  # تفعيل التداول الآلي
                    
                elif last_row['Sell_Signal']:
                    send_alert(asset, "بيع", last_row['Close'])
                    # execute_trade(symbol, "sell", 0.01)  # تفعيل التداول الآلي
                    
            time.sleep(300)  # انتظر 5 دقائق
            
        except Exception as e:
            error_msg = f"⚠️ خطأ في النظام: {str(e)}"
            bot.send_message(CHANNEL_ID, error_msg)
            time.sleep(60)

# ------------------- التشغيل الرئيسي ------------------- #
if __name__ == "__main__":
    bot.send_message(CHANNEL_ID, "✅ تم تشغيل النظام بنجاح! المراقبة جارية...")
    monitor_assets()
