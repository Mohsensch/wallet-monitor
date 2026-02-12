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

WALLETS_FILE = 'wallets.json'
STATE_FILE = 'state.yaml'
LAST_DATE_FILE = 'last_date.txt'
LAST_UPDATE_FILE = 'last_update_id.txt'
SOLANA_RPC = 'https://api.mainnet-beta.solana.com'

# ============== مدیریت فایل‌ها ==============
def load_wallets():
    if os.path.exists(WALLETS_FILE):
        with open(WALLETS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_wallets(wallets):
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

def load_last_update_id():
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, 'r') as f:
            return int(f.read().strip())
    return 0

def save_last_update_id(update_id):
    with open(LAST_UPDATE_FILE, 'w') as f:
        f.write(str(update_id))

# ============== پیام تلگرام ==============
def send_telegram_message(message):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        payload = {
            'chat_id': CHAT_ID, 
            'text': message,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, json=payload, timeout=10)
        print(f"📤 ارسال پیام: {message[:50]}...")
        return response
    except Exception as e:
        print(f"❌ خطا در ارسال پیام: {e}")
        return None

# ============== دریافت ولت جدید از تلگرام ==============
def get_new_wallets_from_telegram():
    """دریافت ولت‌های جدید از تلگرام"""
    try:
        print("📡 بررسی پیام‌های تلگرام...")
        
        # ===== دریافت آخرین update_id پردازش شده =====
        last_update_id = load_last_update_id()
        print(f"🆔 آخرین update_id پردازش شده: {last_update_id}")
        
        # ===== دریافت پیام‌های جدید =====
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates'
        if last_update_id > 0:
            url += f'?offset={last_update_id + 1}'
        
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not data.get('ok'):
            print("❌ خطا در ارتباط با تلگرام")
            return []
        
        messages = data.get('result', [])
        if not messages:
            print("📭 پیام جدیدی نیست")
            return []
        
        print(f"📨 {len(messages)} پیام جدید دریافت شد")
        
        new_wallets = []
        max_update_id = last_update_id
        
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
        
        # ===== ذخیره آخرین update_id =====
        if max_update_id > last_update_id:
            save_last_update_id(max_update_id)
            print(f"💾 آخرین update_id ذخیره شد: {max_update_id}")
        
        print(f"🎯 {len(new_wallets)} ولت جدید پیدا شد")
        return new_wallets
        
    except Exception as e:
        print(f"❌ خطا در دریافت پیام: {e}")
        return []

# ============== ولت‌ها ==============
def get_recent_transactions(wallet):
    try:
        client = Client(SOLANA_RPC)
        response = client.get_signatures_for_address(wallet, limit=5)
        if response and hasattr(response, 'value'):
            return response.value
        return []
    except Exception as e:
        print(f"❌ خطا در دریافت تراکنش {wallet[:10]}: {e}")
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

# ============== گزارش روزانه ==============
def send_daily_report(wallets_count):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    last_date = load_last_date()
    
    if last_date != today:
        weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
        weekday = weekdays[now.weekday()]
        
        message = f"🌅 **گزارش روزانه - {today}**\n"
        message += f"📆 {weekday}\n\n"
        message += f"🤖 ربات نظارت ولت‌های Solana\n"
        message += f"👁️ در حال پایش **{wallets_count}** ولت\n\n"
        message += f"💡 برای اضافه کردن ولت جدید:\n"
        message += f"آدرس ولت رو به ربات بفرست"
        
        send_telegram_message(message)
        save_last_date(today)
        return True
    return False

# ============== اصلی ==============
def main():
    print("🚀 شروع اجرای اسکریپت...")
    print(f"✅ توکن: {TELEGRAM_TOKEN[:10]}...")
    print(f"✅ چت آیدی: {CHAT_ID}")
    
    # ===== ۱. دریافت ولت‌های جدید از تلگرام =====
    new_wallets = get_new_wallets_from_telegram()
    
    # ===== ۲. بارگذاری ولت‌های فعلی =====
    current_wallets = load_wallets()
    print(f"📋 ولت‌های فعلی: {len(current_wallets)}")
    
    # ===== ۳. اضافه کردن ولت‌های جدید =====
    added_wallets = []
    for wallet in new_wallets:
        if wallet not in current_wallets:
            current_wallets.append(wallet)
            added_wallets.append(wallet)
            print(f"✅ ولت جدید اضافه شد: {wallet[:10]}...")
    
    # ===== ۴. ذخیره ولت‌ها =====
    if added_wallets:
        save_wallets(current_wallets)
        print(f"💾 ذخیره شد: {len(added_wallets)} ولت جدید")
        
        # پیام تأیید
        confirm = f"✅ **{len(added_wallets)} ولت جدید اضافه شد:**\n\n"
        for w in added_wallets:
            confirm += f"• `{w[:8]}...{w[-8:]}`\n"
        confirm += f"\n📊 **کل ولت‌ها:** {len(current_wallets)}"
        send_telegram_message(confirm)
    else:
        print("⏭️ ولت جدیدی اضافه نشد")
    
    # ===== ۵. اگه ولتی نبود =====
    if not current_wallets:
        print("⚠️ لیست ولت‌ها خالی است!")
        send_telegram_message("⚠️ **هشدار: لیست ولت‌ها خالی است!**\nبرای اضافه کردن ولت جدید، آدرس ولت رو به ربات بفرست.")
        return
    
    # ===== ۶. گزارش روزانه =====
    send_daily_report(len(current_wallets))
    
    # ===== ۷. بررسی تراکنش‌ها =====
    state = load_state()
    new_state = {}
    
    for i, wallet in enumerate(current_wallets, 1):
        print(f"🔍 بررسی {i}/{len(current_wallets)}: {wallet[:10]}...")
        last_sig = state.get(wallet)
        _, new_sig = check_wallet(wallet, last_sig)
        if new_sig:
            new_state[wallet] = new_sig
            print(f"💰 تراکنش جدید برای {wallet[:10]}...")
    
    if new_state:
        save_state({**state, **new_state})
        print("💾 وضعیت تراکنش‌ها ذخیره شد")
    
    print("✅ اجرا پایان یافت")

if __name__ == "__main__":
    main()
