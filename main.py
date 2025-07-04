import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import logging
import yfinance as yf

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

# قائمة الشركات المعدلة
companies = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "GOOGL": "Alphabet A", 
    "AMZN": "Amazon", "META": "Meta Platforms", "TSLA": "Tesla", 
    "JPM": "JPMorgan Chase", "XOM": "Exxon Mobil", "JNJ": "Johnson & Johnson",
    "V": "Visa", "PG": "Procter & Gamble", "MA": "Mastercard", "HD": "Home Depot", 
    "COST": "Costco", "MRK": "Merck", "PEP": "PepsiCo", "WMT": "Walmart", 
    "KO": "Coca-Cola", "MSTR": "MicroStrategy", "AVGO": "Broadcom", 
    "GS": "Goldman Sachs", "MU": "Micron Technology", "COIN": "Coinbase", 
    "AMD": "Advanced Micro Devices"
}

def fetch_data(symbol, interval):
    try:
        # استخدام yfinance بدلاً من API المباشر
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        # تحويل الفاصل الزمني إلى صيغة yfinance
        interval_map = {
            '1h': '1h',
            '1d': '1d'
        }
        yf_interval = interval_map.get(interval, '1d')
        
        df = yf.download(
            symbol, 
            start=start_date, 
            end=end_date, 
            interval=yf_interval,
            progress=False
        )
        
        if df.empty:
            logging.warning(f"No data for {symbol} at interval {interval}")
            return None
        
        # إعادة تسمية الأعمدة لتتناسب مع الكود
        df = df.rename(columns={
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close'
        })
        
        return df[['Open', 'High', 'Low', 'Close']]
    except Exception as e:
        logging.error(f"fetch_data error ({symbol}): {e}")
        return None

def calculate_indicators(df):
    if df is None or df.empty:
        return df
    
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
    rs = avg_gain / (avg_loss + 1e-10)  # تجنب القسمة على الصفر
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # حساب MACD وخط الإشارة
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    
    return df

def interpret_trend(df):
    if df is None or len(df) < 3:
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
        
        processed = 0
        for symbol, name in companies.items():
            try:
                logging.info(f"Processing {name} ({symbol})...")
                
                # جلب البيانات
                df_1h = fetch_data(symbol, "1h")
                df_1d = fetch_data(symbol, "1d")
                
                if df_1h is None or df_1h.empty or df_1d is None or df_1d.empty:
                    logging.warning(f"Data not available for {symbol}")
                    msg += f"⚠️ {name}: لا توجد بيانات متاحة\n\n"
                    continue
                
                # حساب المؤشرات
                df_1h = calculate_indicators(df_1h)
                df_1d = calculate_indicators(df_1d)
                
                # تفسير الاتجاه
                dir_1h = interpret_trend(df_1h)
                dir_1d = interpret_trend(df_1d)
                
                # الحصول على السعر الحالي
                price = df_1h["Close"].iloc[-1] if len(df_1h) > 0 else 0
                
                # تحليل RSI
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
                
                # تحليل MACD
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
                
                # بناء الرسالة
                msg += (
                    f"📈 {name} – السعر: {price:.2f}\n"
                    f"اتجاه الساعة: {dir_1h}\n"
                    f"اتجاه اليوم: {dir_1d}\n"
                    f"{rsi_analysis}\n"
                    f"{macd_analysis}\n\n"
                )
                
                processed += 1
                # تأخير بين الطلبات لتجنب الحظر
                time.sleep(2)
                
            except Exception as e:
                logging.error(f"Error processing {name}: {str(e)}")
                msg += f"⚠️ {name}: خطأ في المعالجة\n\n"
                continue
        
        if processed > 0:
            # إضافة ملخص في بداية الرسالة
            summary = f"✅ تم تحليل {processed} من أصل {len(companies)} شركة\n\n"
            msg = summary + msg
        else:
            msg = "⚠️ فشل في معالجة جميع الشركات. يرجى مراجعة السجلات."
        
        # إرسال الرسالة
        if not send_telegram_message(msg.strip()):
            logging.error("Failed to send message")
            
        logging.info(f"Analysis completed. Processed {processed} companies.")
        
    except Exception as e:
        logging.error(f"General error in analyze_and_send: {str(e)}")
        send_telegram_message(f"⚠️ حدث خطأ جسيم في التحليل: {str(e)[:300]}")

def hourly_loop():
    logging.info("Hourly loop started")
    while True:
        now = datetime.utcnow()
        
        # إرسال مرة واحدة كل ساعة في الدقيقة 00
        if now.minute == 0:
            logging.info(f"Triggering analysis at {now}")
            try:
                analyze_and_send()
                # الانتظار لمدة دقيقة لتجنب الإرسال المتكرر
                time.sleep(60)
            except Exception as e:
                logging.error(f"Error in hourly analysis: {str(e)}")
        
        # فحص كل 30 ثانية
        time.sleep(30)

if __name__ == "__main__":
    logging.info("Application started")
    keep_alive()
    
    # إرسال رسالة البدء بعد التأكد من عمل البوت
    time.sleep(5)
    send_telegram_message("✅ تم تشغيل المحلل الفني بنجاح. جاري تحليل البيانات...")
    
    # بدء التحليل فورياً
    Thread(target=analyze_and_send).start()
    
    # بدء دورة الساعة
    hourly_loop()
