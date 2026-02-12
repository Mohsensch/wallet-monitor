import requests
import json
import yaml
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
import os
import time
from datetime import datetime

# -------------------- تنظیمات اجباری --------------------
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
CHAT_ID = os.environ.get('CHAT_ID', '')
# -------------------------------------------------------

# لیست والت‌های Solana برای نظارت
WALLETS = [
    'BC8yiFFQWFEKrEEj75zYsuK3ZDCfv6QEeMRif9oZZ9TW',
    '4Be9CvxqHW6BYiRAxW9Q3xu1ycTMWaL5z8NX4HR3ha7t',
    'AVAZvHLR2PcWpDf8BXY4rVxNHYRBytycHkcB5z5QNXYm',
    '4EtAJ1p8RjqccEVhEhaYnEgQ6kA4JHR8oYqyLFwARUj6',
    '8zFZHuSRuDpuAR7J6FzwyF3vKNx4CVW3DFHJerQhc7Zd',
    'H72yLkhTnoBfhBTXXaj1RBXuirm8s8G5fcVh2XpQLggM',
    '3xqUaVuAWsppb8yaSPJ2hvdvfjteMq2EbdCc3CLguaTE',
    '9UWZFoiCHeYRLmzmDJhdMrP7wgrTw7DMSpPiT2eHgJHe',
    'BKVaB3eNrGUVRCj3M4LiodKypBTzrpatoo7VBhmdv3eY',
    '4Kv5PsDSYQJkSLW8WaGnRR3BKq5nf5pchEq7FdbMqTeK'
]

# RPC عمومی رایگان Solana
SOLANA_RPC = 'https://api.mainnet-beta.solana.com'
STATE_FILE = 'state.yaml'
LAST_DATE_FILE = 'last_date.txt'  # فایل برای ذخیره آخرین تاریخ ارسال پیام

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
        payload = {'chat_id': CHAT_ID, 'text': message}
        response = requests.post(url, json=payload, timeout=10)
        print(f"📤 ارسال پیام: {message[:50]}...")
        return response
    except Exception as e:
        print(f"❌ خطا در ارسال پیام: {e}")
        return None

def send_daily_message():
    """ارسال پیام روزانه"""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    last_date = load_last_date()
    
    # اگه امروز هنوز پیام نفرستاده باشیم
    if last_date != today:
        # تاریخ شمسی تقریبی (برای دقیق تر نیاز به کتابخانه jdatetime هست)
        weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
        weekday = weekdays[now.weekday()]
        
        message = f"🌅 **گزارش روزانه - {today}**\n"
        message += f"📆 {weekday}\n\n"
        message += "🤖 ربات نظارت والت‌های Solana فعال است.\n"
        message += "🟢 در حال پایش ۱۰ والت برای تراکنش‌های جدید..."
        
        send_telegram_message(message)
        save_last_date(today)
        print(f"📅 پیام روزانه ارسال شد: {today}")
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
    
    new_transactions = []
    current_first_sig = transactions[0].signature if transactions else None
    
    for tx in transactions:
        if tx.signature == last_signature:
            break
        
        # گرفتن زمان تراکنش
        tx_time = datetime.fromtimestamp(tx.block_time).strftime("%H:%M:%S") if tx.block_time else "نامشخص"
        new_transactions.append(f"🕐 {tx_time} - تراکنش جدید: `{tx.signature[:8]}...{tx.signature[-8:]}`")
        break
    
    if new_transactions:
        message = f"🔔 **والت {wallet[:8]}...{wallet[-8:]}**\n"
        message += f"{new_transactions[0]}\n"
        message += f"🔗 [مشاهده در Solscan](https://solscan.io/tx/{tx.signature})"
        send_telegram_message(message)
        return current_first_sig, current_first_sig
    
    return None, last_signature

def main():
    print("🚀 شروع اجرای اسکریپت...")
    print(f"✅ توکن تنظیم شد: {TELEGRAM_TOKEN[:10]}...")
    print(f"✅ چت آیدی تنظیم شد: {CHAT_ID}")
    
    # ارسال پیام روزانه
    send_daily_message()
    
    state = load_state()
    print(f"📂 وضعیت قبلی: {state}")
    
    new_state = {}
    for i, wallet in enumerate(WALLETS, 1):
        print(f"🔍 بررسی والت {i}/{len(WALLETS)}: {wallet[:10]}...")
        last_sig = state.get(wallet)
        _, new_sig = check_wallet(wallet, last_sig)
        if new_sig:
            new_state[wallet] = new_sig
            print(f"✅ بروزرسانی والت {wallet[:10]}: {new_sig[:10]}...")
    
    if new_state:
        save_state({**state, **new_state})
        print(f"💾 وضعیت جدید ذخیره شد: {new_state}")
    else:
        print("📭 تراکنش جدیدی یافت نشد")
    
    print("✅ اجرا با موفقیت پایان یافت")

if __name__ == "__main__":
    main()
