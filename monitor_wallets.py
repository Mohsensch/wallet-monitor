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

# ============== پیام تلگرام با کیبورد ==============
def send_telegram_message(message, keyboard=None):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        payload = {
            'chat_id': CHAT_ID, 
            'text': message,
            'parse_mode': 'Markdown'
        }
        if keyboard:
            payload['reply_markup'] = json.dumps(keyboard)
        
        response = requests.post(url, json=payload, timeout=10)
        return response
    except Exception as e:
        print(f"❌ خطا در ارسال پیام: {e}")
        return None

# ============== منوی اصلی ==============
def main_menu():
    keyboard = {
        "keyboard": [
            ["📋 لیست ولت‌ها", "➕ اضافه کردن ولت"],
            ["❌ حذف ولت", "📊 گزارش امروز"],
            ["🔄 بررسی تراکنش‌ها", "ℹ️ وضعیت ربات"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    return keyboard

# ============== دریافت پیام‌های تلگرام ==============
def get_telegram_updates():
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates'
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if not data.get('ok'):
            return []
        
        messages = data.get('result', [])
        if not messages:
            return []
        
        commands = []
        last_update_id = 0
        
        for msg in messages:
            update_id = msg['update_id']
            last_update_id = max(last_update_id, update_id)
            
            if 'message' in msg and 'text' in msg['message']:
                text = msg['message']['text'].strip()
                commands.append(text)
        
        # پاک کردن پیام‌ها
        if last_update_id > 0:
            clean_url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}'
            requests.get(clean_url)
        
        return commands
        
    except Exception as e:
        print(f"❌ خطا در دریافت پیام: {e}")
        return []

# ============== پردازش دستورات ==============
def process_commands(commands):
    wallets = load_wallets()
    responses = []
    
    for cmd in commands:
        # ===== اضافه کردن ولت =====
        if len(cmd) in [43, 44] and cmd[0].isalpha() and cmd.isalnum():
            if cmd not in wallets:
                wallets.append(cmd)
                save_wallets(wallets)
                responses.append(f"✅ ولت `{cmd[:8]}...{cmd[-8:]}` با موفقیت اضافه شد!")
            else:
                responses.append(f"⚠️ این ولت قبلاً اضافه شده!")
        
        # ===== لیست ولت‌ها =====
        elif cmd == "📋 لیست ولت‌ها":
            if not wallets:
                responses.append("📭 لیست ولت‌ها خالی است!")
            else:
                msg = "📋 **لیست ولت‌ها:**\n\n"
                for i, w in enumerate(wallets, 1):
                    msg += f"{i}. `{w[:8]}...{w[-8:]}`\n"
                msg += f"\n📊 **تعداد کل:** {len(wallets)}"
                responses.append(msg)
        
        # ===== اضافه کردن ولت (دستی) =====
        elif cmd == "➕ اضافه کردن ولت":
            responses.append("📝 لطفاً آدرس ولت را بفرستید:")
        
        # ===== حذف ولت =====
        elif cmd == "❌ حذف ولت":
            if not wallets:
                responses.append("📭 لیست ولت‌ها خالی است!")
            else:
                keyboard = {"keyboard": [], "resize_keyboard": True}
                row = []
                for i, w in enumerate(wallets, 1):
                    short = f"{w[:4]}...{w[-4:]}"
                    row.append(f"حذف {i}")
                    if len(row) == 3:
                        keyboard["keyboard"].append(row)
                        row = []
                if row:
                    keyboard["keyboard"].append(row)
                keyboard["keyboard"].append(["🔙 بازگشت"])
                
                msg = "❌ **ولت مورد نظر برای حذف را انتخاب کنید:**\n\n"
                for i, w in enumerate(wallets, 1):
                    msg += f"{i}. `{w[:8]}...{w[-8:]}`\n"
                
                send_telegram_message(msg, keyboard)
                return []
        
        # ===== حذف ولت خاص =====
        elif cmd.startswith("حذف "):
            try:
                index = int(cmd.split()[1]) - 1
                if 0 <= index < len(wallets):
                    removed = wallets.pop(index)
                    save_wallets(wallets)
                    responses.append(f"✅ ولت `{removed[:8]}...{removed[-8:]}` حذف شد!")
                else:
                    responses.append("❌ شماره ولت نامعتبر است!")
            except:
                responses.append("❌ خطا در حذف ولت!")
        
        # ===== گزارش امروز =====
        elif cmd == "📊 گزارش امروز":
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
            weekday = weekdays[now.weekday()]
            
            msg = f"📊 **گزارش امروز - {today}**\n"
            msg += f"📆 {weekday}\n\n"
            msg += f"👁️ **ولت‌های تحت نظارت:** {len(wallets)}\n"
            msg += f"🟢 **وضعیت:** فعال"
            responses.append(msg)
        
        # ===== بررسی تراکنش‌ها =====
        elif cmd == "🔄 بررسی تراکنش‌ها":
            responses.append("🔄 در حال بررسی تراکنش‌ها...")
            # اینجا میتونی تابع check_all_wallets رو صدا بزنی
        
        # ===== وضعیت ربات =====
        elif cmd == "ℹ️ وضعیت ربات":
            msg = "🤖 **وضعیت ربات:**\n\n"
            msg += f"✅ **وضعیت:** فعال\n"
            msg += f"📊 **ولت‌ها:** {len(wallets)}\n"
            msg += f"⏰ **آخرین اجرا:** {datetime.now().strftime('%H:%M:%S')}\n"
            msg += f"🔗 **شبکه:** Solana Mainnet"
            responses.append(msg)
        
        # ===== بازگشت =====
        elif cmd == "🔙 بازگشت":
            responses.append("🔙 بازگشت به منوی اصلی")
    
    return responses

# ============== بررسی تراکنش‌ها ==============
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

def check_all_wallets():
    wallets = load_wallets()
    if not wallets:
        return
    
    state = load_state()
    new_state = {}
    
    for wallet in wallets:
        last_sig = state.get(wallet)
        transactions = get_recent_transactions(wallet)
        
        if transactions:
            current_sig = transactions[0].signature
            if current_sig != last_sig:
                if transactions[0].block_time:
                    tx_time = datetime.fromtimestamp(transactions[0].block_time).strftime("%H:%M:%S")
                    message = f"🔔 **والت {wallet[:8]}...{wallet[-8:]}**\n"
                    message += f"🕐 {tx_time} - تراکنش جدید\n"
                    message += f"🔗 [مشاهده در Solscan](https://solscan.io/tx/{current_sig})"
                    send_telegram_message(message)
                    new_state[wallet] = current_sig
    
    if new_state:
        save_state({**state, **new_state})

# ============== گزارش روزانه ==============
def send_daily_report():
    wallets = load_wallets()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    last_date = load_last_date()
    
    if last_date != today:
        weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
        weekday = weekdays[now.weekday()]
        
        message = f"🌅 **گزارش روزانه - {today}**\n"
        message += f"📆 {weekday}\n\n"
        message += f"🤖 ربات نظارت ولت‌های Solana\n"
        message += f"👁️ در حال پایش **{len(wallets)}** ولت\n\n"
        message += f"💡 از منوی زیر استفاده کنید:"
        
        send_telegram_message(message, main_menu())
        save_last_date(today)

# ============== اصلی ==============
def main():
    print("🚀 شروع اجرای اسکریپت...")
    
    # ===== دریافت دستورات از تلگرام =====
    commands = get_telegram_updates()
    
    # ===== پردازش دستورات =====
    if commands:
        responses = process_commands(commands)
        for response in responses:
            if "بازگشت به منوی اصلی" in response:
                send_telegram_message("🔙 منوی اصلی:", main_menu())
            else:
                send_telegram_message(response, main_menu())
    
    # ===== گزارش روزانه =====
    send_daily_report()
    
    # ===== بررسی تراکنش‌ها =====
    check_all_wallets()
    
    print("✅ اجرا پایان یافت")

if __name__ == "__main__":
    main()
