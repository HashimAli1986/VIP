import requests
import pandas as pd
import time
from datetime import datetime
from flask import Flask
from threading import Thread
import logging

# إعداد سجلات التتبع
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

app = Flask(__name__)

@app.route('/')
def home():
    return "تحليل مؤشر S&P 500 والشركات الكبرى يعمل بنجاح"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

BOT_TOKEN = "7883771248:AAFfwmcF3hcHz17_IG0KfyOCSGLjMBzyg8E"
CHANNEL_ID = "@hashimali1986"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHANNEL_ID, "text": text}
    try:
        response = requests.post(url, data=data)
        logging.info(f"Telegram response: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        logging.error(f"Telegram Error: {e}")
        return False

companies = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "GOOGL": "Alphabet A", "GOOG": "Alphabet C",
    "AMZN": "Amazon", "META": "Meta Platforms", "BRK.B": "Berkshire Hathaway", "TSLA": "Tesla", "LLY": "Eli Lilly",
    "V": "Visa", "JNJ": "Johnson & Johnson", "UNH": "UnitedHealth", "JPM": "JPMorgan Chase", "XOM": "Exxon Mobil",
    "PG": "Procter & Gamble", "MA": "Mastercard", "AVGO": "Broadcom", "HD": "Home Depot", "COST": "Costco",
    "MRK": "Merck", "PEP": "PepsiCo", "ABBV": "AbbVie", "WMT": "Walmart", "KO": "Coca-Cola",
    "MSTR": "MicroStrategy", "APP": "AppLovin", "SMCI": "Super Micro Computer", "GS": "Goldman Sachs",
    "MU": "Micron Technology", "COIN": "Coinbase", "CRWD": "CrowdStrike", "AMD": "Advanced Micro Devices"
}

def fetch_data(symbol, interval):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval={interval}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if "chart" not in data or "error" in data["chart"]:
            logging.error(f"Yahoo API error for {symbol}: {data.get('chart', {}).get('error', {})}")
            return None
            
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]

        if not all(key in quotes for key in ["close", "open", "high", "low"]):
            logging.warning(f"Incomplete data for {symbol}")
            return None

        df = pd.DataFrame({
            "Close": quotes["close"],
            "Open": quotes["open"],
            "High": quotes["high"],
            "Low": quotes["low"]
        })

        df["Date"] = pd.to_datetime(timestamps, unit="s")
        df.set_index("Date", inplace=True)
        return df.dropna()
    except Exception as e:
        logging.error(f"fetch_data error ({symbol}): {e}")
        return None

def calculate_indicators(df):
    # حساب المتوسطات المتحركة الأسية
    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    
    # حساب RSI
    delta = df["Close"].diff(1)
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14, min_periods=1).mean()
    avg_loss = loss.rolling(window=14, min_periods=1).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # حساب MACD وخط الإشارة
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    
    return df

def interpret_trend(df):
    if len(df) < 3:
        return "غير محدد"
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    rsi = last["RSI"]
    
    # تحديد تقاطع MACD
    macd_cross = (last["MACD"] > last["Signal"]) and (prev["MACD"] < prev["Signal"])
    macd_negative_cross = (last["MACD"] < last["Signal"]) and (prev["MACD"] > prev["Signal"])
    
    # تحديد ترتيب المتوسطات
    ema_cross = (last["EMA9"] > last["EMA21"]) and (last["EMA21"] > last["EMA50"])
    ema_negative_cross = (last["EMA9"] < last["EMA21"]) and (last["EMA21"] < last["EMA50"])
    
    if macd_cross and ema_cross and rsi < 70:
        return "صاعدة قوية"
    elif macd_negative_cross and ema_negative_cross and rsi > 60:
        return "هابطة قوية"
    elif last["MACD"] > last["Signal"] and rsi < 60:
        return "صاعدة"
    elif last["MACD"] < last["Signal"] and rsi > 40:
        return "هابطة"
    else:
        return "جانبية"

def analyze_and_send():
    try:
        logging.info("Starting analysis...")
        msg = f"📊 تحديث التحليل الفني – {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n\n"
        
        assets = {
            "MSTR": "MicroStrategy", "APP": "AppLovin", "AVGO": "Broadcom", "SMCI": "Super Micro Computer",
            "GS": "Goldman Sachs", "MU": "Micron Technology", "META": "Meta Platforms", "AAPL": "Apple",
            "COIN": "Coinbase", "TSLA": "Tesla", "LLY": "Eli Lilly", "CRWD": "CrowdStrike", "MSFT": "Microsoft",
            "AMD": "Advanced Micro Devices", "NVDA": "NVIDIA", "GOOGL": "Alphabet (Class A)", "GOOG": "Alphabet (Class C)",
            "AMZN": "Amazon", "BRK.B": "Berkshire Hathaway", "V": "Visa", "JNJ": "Johnson & Johnson",
            "UNH": "UnitedHealth", "JPM": "JPMorgan Chase", "XOM": "Exxon Mobil", "PG": "Procter & Gamble",
            "MA": "Mastercard", "HD": "Home Depot", "COST": "Costco", "MRK": "Merck", "PEP": "PepsiCo",
            "ABBV": "AbbVie", "WMT": "Walmart", "KO": "Coca-Cola"
        }

        processed = 0
        for symbol, name in assets.items():
            try:
                logging.info(f"Processing {name} ({symbol})...")
                df_1h = fetch_data(symbol, "1h")
                df_1d = fetch_data(symbol, "1d")

                if df_1h is None or df_1d is None:
                    msg += f"{name}: ⚠️ تعذر جلب البيانات.\n\n"
                    continue

                df_1h = calculate_indicators(df_1h)
                df_1d = calculate_indicators(df_1d)

                dir_1h = interpret_trend(df_1h)
                dir_1d = interpret_trend(df_1d)
                price = df_1h["Close"].iloc[-1] if len(df_1h) > 0 else 0
                
                # تحليل RSI و MACD
                rsi_1h = df_1h["RSI"].iloc[-1] if len(df_1h) > 0 else 0
                rsi_1d = df_1d["RSI"].iloc[-1] if len(df_1d) > 0 else 0
                
                rsi_analysis = ""
                if rsi_1h > 70:
                    rsi_analysis += "RSI الساعة: تشبع بيعي ⚠️"
                elif rsi_1h < 30:
                    rsi_analysis += "RSI الساعة: تشبع شرائي ✅"
                else:
                    rsi_analysis += "RSI الساعة: طبيعي"
                    
                if rsi_1d > 70:
                    rsi_analysis += " | RSI اليومي: تشبع بيعي ⚠️"
                elif rsi_1d < 30:
                    rsi_analysis += " | RSI اليومي: تشبع شرائي ✅"
                else:
                    rsi_analysis += " | RSI اليومي: طبيعي"
                    
                macd_analysis = ""
                if len(df_1h) > 0 and len(df_1d) > 0:
                    if df_1h["MACD"].iloc[-1] > df_1h["Signal"].iloc[-1]:
                        macd_analysis += "MACD الساعة: إيجابي 📈"
                    else:
                        macd_analysis += "MACD الساعة: سلبي 📉"
                        
                    if df_1d["MACD"].iloc[-1] > df_1d["Signal"].iloc[-1]:
                        macd_analysis += " | MACD اليومي: إيجابي 📈"
                    else:
                        macd_analysis += " | MACD اليومي: سلبي 📉"
                else:
                    macd_analysis = "بيانات MACD غير متوفرة"

                msg += (
                    f"📈 {name} – السعر: {price:.2f}\n"
                    f"فريم الساعة: {dir_1h}\n"
                    f"فريم اليومي: {dir_1d}\n"
                    f"{rsi_analysis}\n"
                    f"{macd_analysis}\n\n"
                )
                
                processed += 1
                # تأخير بين الطلبات لتجنب حظر ياهو
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"Error processing {name}: {str(e)}")
                msg += f"{name}: ⚠️ خطأ في المعالجة\n\n"
                continue

        if processed == 0:
            msg = "⚠️ فشل في معالجة جميع الشركات"

        # تقسيم الرسالة إذا كانت طويلة جداً
        max_length = 4000
        if len(msg) > max_length:
            parts = [msg[i:i+max_length] for i in range(0, len(msg), max_length)]
            for part in parts:
                if not send_telegram_message(part):
                    logging.error("Failed to send message part")
                time.sleep(1)
        else:
            if not send_telegram_message(msg):
                logging.error("Failed to send message")
                
        logging.info("Analysis completed and sent successfully")
        
    except Exception as e:
        logging.error(f"General error in analyze_and_send: {str(e)}")
        send_telegram_message(f"⚠️ حدث خطأ جسيم في التحليل: {str(e)[:300]}")

def hourly_loop():
    logging.info("Hourly loop started")
    last_sent_hour = -1
    while True:
        now = datetime.utcnow()
        current_hour = now.hour
        
        # إرسال مرة واحدة كل ساعة في الدقيقة 00
        if now.minute == 0 and current_hour != last_sent_hour:
            logging.info(f"Triggering analysis for hour {current_hour}")
            try:
                analyze_and_send()
                last_sent_hour = current_hour
                logging.info(f"Analysis for hour {current_hour} completed")
            except Exception as e:
                logging.error(f"Error in hourly analysis: {str(e)}")
            # انتظار حتى انتهاء الدقيقة
            time.sleep(60)
        else:
            # فحص كل 30 ثانية
            time.sleep(30)

if __name__ == "__main__":
    logging.info("Application started")
    keep_alive()
    send_telegram_message("✅ تم تشغيل تحليل مؤشر S&P 500 والشركات الكبرى مع مؤشرات RSI و MACD.")
    # بدء التحليل فوراً
    Thread(target=analyze_and_send).start()
    # بدء دورة الساعة
    Thread(target=hourly_loop).start()
