import requests
import json
import yaml
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
import os
import time
from datetime import datetime

# -------------------- تنظیمات --------------------
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
CHAT_ID = os.environ.get('CHAT_ID', '')
# -------------------------------------------------

# فایل‌ها
WALLETS_FILE = 'wallets.json'  # لیست ولت‌ها
STATE_FILE = 'state.yaml'
LAST_DATE_FILE = 'last_date.txt'

# RPC عمومی
SOLANA_RPC = 'https://api.mainnet-beta.solana.com'

def load_wallets():
    """بارگذاری لیست ولت‌ها از فایل JSON"""
    if os.path.exists(WALLETS_FILE):
        with open(WALLETS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_wallets(wallets):
    """ذخیره لیست ولت‌ها در فایل JSON"""
    with open(WALLETS_FILE, 'w') as f:
        json.dump(wallets, f, indent=4)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return yaml.safe_load(f) or {}
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        yaml.safe_dump(state, f)

def load_last_date():
    if os.path.exists(LAST_DATE_FILE):
        with open(LAST_DATE_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_last_date(date):
    with open(LAST_DATE_FILE, 'w') as f:
        f.write(date)

def send_telegram_message(message):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
        response = requests.post(url, json=payload, timeout=10)
        print(f"📤 ارسال پیام: {message[:50]}...")
        return response
    except Exception as e:
        print(f"❌ خطا در ارسال پیام: {e}")
        return None

def check_telegram_commands():
    """چک کردن پیام‌های جدید توی تلگرام برای دریافت ولت جدید"""
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset=-1'
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not data.get('ok'):
            return
        
        messages = data.get('result', [])
        current_wallets = load_wallets()
        added_wallets = []
        
        for msg in messages:
            if 'message' in msg and 'text' in msg['message']:
                text = msg['message']['text'].strip()
                
                # بررسی فرمت ولت سولانا (حدود ۴۳-۴۴ کاراکتر)
                if len(text) == 44 and text[0].isalpha() and text.isalnum():
                    if text not in current_wallets:
                        current_wallets.append(text)
                        added_wallets.append(text)
                        print(f"✅ ولت جدید اضافه شد: {text[:10]}...")
        
        if added_wallets:
            save_wallets(current_wallets)
            # پیام تأیید
            confirm_msg = f"✅ {len(added_wallets)} ولت جدید به لیست نظارت اضافه شد:\n"
            for w in added_wallets:
                confirm_msg += f"• `{w[:8]}...{w[-8:]}`\n"
            confirm_msg += f"\n📊 کل ولت‌ها: {len(current_wallets)}"
            send_telegram_message(confirm_msg)
            
    except Exception as e:
        print(f"❌ خطا در دریافت پیام تلگرام: {e}")

def send_daily_message(wallets_count):
    """ارسال پیام روزانه"""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    last_date = load_last_date()
    
    if last_date != today:
        weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
        weekday = weekdays[now.weekday()]
        
        message = f"🌅 **گزارش روزانه - {today}**\n"
        message += f"📆 {weekday}\n\n"
        message += f"🤖 ربات نظارت والت‌های Solana\n"
        message += f"👁️ در حال پایش **{wallets_count}** والت\n"
        message += f"🟢 فعال و آماده..."
        
        send_telegram_message(message)
        save_last_date(today)
        print(f"📅 پیام روزانه ارسال شد")
        return True
    return False

def get_recent_transactions(wallet):
    try:
        client = Client(SOLANA_RPC)
        response = client.get_signatures_for_address(wallet, limit=5)
        if response and hasattr(response, 'value'):
            return response.value
        return []
    except Exception as e:
        print(f"❌ خطا در دریافت تراکنش‌های {wallet[:10]}: {e}")
        return []

def check_wallet(wallet, last_signature):
    transactions = get_recent_transactions(wallet)
    if not transactions:
        return None, last_signature
    
    current_first_sig = transactions[0].signature if transactions else None
    
    for tx in transactions:
        if tx.signature == last_signature:
            break
        
        if tx.block_time:
            tx_time = datetime.fromtimestamp(tx.block_time).strftime("%H:%M:%S")
            message = f"🔔 **والت {wallet[:8]}...{wallet[-8:]}**\n"
            message += f"🕐 {tx_time} - تراکنش جدید\n"
            message += f"🔗 [مشاهده در Solscan](https://solscan.io/tx/{tx.signature})"
            send_telegram_message(message)
            return current_first_sig, current_first_sig
    
    return None, last_signature

def main():
    print("🚀 شروع اجرای اسکریپت...")
    
    # ===== قابلیت جدید: چک کردن پیام‌های تلگرام برای ولت جدید =====
    check_telegram_commands()
    # ============================================================
    
    # بارگذاری لیست ولت‌ها
    WALLETS = load_wallets()
    print(f"📋 تعداد کل ولت‌ها: {len(WALLETS)}")
    
    if not WALLETS:
        print("⚠️ هیچ ولتی برای نظارت وجود ندارد!")
        send_telegram_message("⚠️ هشدار: لیست ولت‌ها خالی است!\nبرای اضافه کردن ولت جدید، آدرس ولت رو به ربات بفرست.")
        return
    
    # ارسال پیام روزانه
    send_daily_message(len(WALLETS))
    
    # بررسی تراکنش‌ها
    state = load_state()
    new_state = {}
    
    for i, wallet in enumerate(WALLETS, 1):
        print(f"🔍 بررسی ولت {i}/{len(WALLETS)}: {wallet[:10]}...")
        last_sig = state.get(wallet)
        _, new_sig = check_wallet(wallet, last_sig)
        if new_sig:
            new_state[wallet] = new_sig
            print(f"✅ بروزرسانی ولت {wallet[:10]}: {new_sig[:10]}...")
    
    if new_state:
        save_state({**state, **new_state})
        print(f"💾 وضعیت جدید ذخیره شد")
    else:
        print("📭 تراکنش جدیدی یافت نشد")
    
    print("✅ اجرا با موفقیت پایان یافت")

if __name__ == "__main__":
    main()
