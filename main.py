def analyze_and_send():
    msg = f"📊 تحديث التحليل الفني – {datetime.utcnow().strftime('%H:%M')} UTC\n\n"
    
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

    for symbol, name in assets.items():
        df_1h = fetch_data(symbol, "1h")
        df_1d = fetch_data(symbol, "1d")

        if df_1h is None or df_1d is None:
            msg += f"{name}: ⚠️ تعذر جلب البيانات.\n\n"
            continue

        df_1h = calculate_indicators(df_1h)
        df_1d = calculate_indicators(df_1d)

        dir_1h = interpret_trend(df_1h)
        dir_1d = interpret_trend(df_1d)
        price = df_1h["Close"].iloc[-1]

        msg += (
            f"{name} – {datetime.utcnow().strftime('%H:%M')} UTC\n"
            f"السعر الحالي: {price:.2f}\n"
            f"فريم الساعة: {dir_1h}\n"
            f"فريم اليومي: {dir_1d}\n"
            f"الاتجاه العام: "
            f"{'صاعدة قوية' if dir_1h == 'صاعدة' and dir_1d == 'صاعدة' else 'هابطة قوية' if dir_1h == 'هابطة' and dir_1d == 'هابطة' else 'تذبذب أو غير مؤكد'}\n\n"
        )

    send_telegram_message(msg.strip())
