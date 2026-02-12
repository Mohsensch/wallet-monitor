def get_new_wallets_from_telegram():
    """دریافت ولت‌های جدید از تلگرام - فقط پیام‌های جدید"""
    try:
        print("📡 بررسی پیام‌های تلگرام...")
        
        # ===== فایل ذخیره آخرین update_id =====
        OFFSET_FILE = 'last_update_id.txt'
        
        # بارگذاری آخرین update_id پردازش شده
        last_processed_id = 0
        if os.path.exists(OFFSET_FILE):
            with open(OFFSET_FILE, 'r') as f:
                last_processed_id = int(f.read().strip())
        
        # دریافت فقط پیام‌های جدیدتر
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates'
        if last_processed_id > 0:
            url += f'?offset={last_processed_id + 1}'
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not data.get('ok'):
            print("❌ خطا در ارتباط با تلگرام")
            return []
        
        messages = data.get('result', [])
        if not messages:
            print("📭 پیام جدیدی نیست")
            return []
        
        print(f"📨 {len(messages)} پیام جدید پیدا شد")
        
        new_wallets = []
        max_update_id = last_processed_id
        
        for msg in messages:
            update_id = msg['update_id']
            max_update_id = max(max_update_id, update_id)
            
            if 'message' in msg and 'text' in msg['message']:
                text = msg['message']['text'].strip()
                print(f"📝 متن پیام: {text[:30]}...")
                
                # بررسی آدرس ولت
                if len(text) in [43, 44] and text[0].isalpha() and text.isalnum():
                    new_wallets.append(text)
                    print(f"✅ آدرس ولت شناسایی شد: {text[:10]}...")
        
        # ذخیره آخرین update_id پردازش شده
        if max_update_id > last_processed_id:
            with open(OFFSET_FILE, 'w') as f:
                f.write(str(max_update_id))
            print(f"💾 آخرین update_id ذخیره شد: {max_update_id}")
        
        return new_wallets
        
    except Exception as e:
        print(f"❌ خطا: {e}")
        return []
