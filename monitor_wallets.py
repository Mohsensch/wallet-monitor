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

# ============== ارسال پیام تلگرام ==============
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
        
        response = requests.post(url, json=payload, timeout=12)
        if not response.ok:
            print(f"تلگرام خطا داد: {response.text[:180]}")
        return response.ok
    except Exception as e:
        print(f"❌ خطا ارسال پیام تلگرام: {e}")
        return False

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

# ============== دریافت آپدیت‌های تلگرام ==============
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
        
        # acknowledge آپدیت‌ها
        if last_update_id > 0:
            requests.get(
                f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}'
            )
        
        return commands
    
    except Exception as e:
        print(f"❌ خطا در گرفتن آپدیت تلگرام: {e}")
        return []

# ============== پردازش دستورات ==============
def process_commands(commands):
    wallets = load_wallets()
    responses = []
    
    for cmd in commands:
        cmd = cmd.strip()
        
        # اضافه کردن ولت با ارسال آدرس
        if len(cmd) in [43, 44] and cmd[0].isalpha() and cmd.isalnum():
            if cmd not in wallets:
                wallets.append(cmd)
                save_wallets(wallets)
                responses.append(f"✅ ولت اضافه شد:\n`{cmd[:8]}...{cmd[-8:]}`")
            else:
                responses.append("⚠️ این آدرس قبلاً اضافه شده است")
        
        elif cmd == "📋 لیست ولت‌ها":
            if not wallets:
                responses.append("📭 لیست ولت‌ها خالی است")
            else:
                msg = "📋 **لیست ولت‌ها:**\n\n"
                for i, w in enumerate(wallets, 1):
                    msg += f"{i}. `{w[:8]}...{w[-8:]}`\n"
                msg += f"\nتعداد کل: {len(wallets)}"
                responses.append(msg)
        
        elif cmd == "➕ اضافه کردن ولت":
            responses.append("لطفاً آدرس کامل ولت را بفرستید (۴۴ کاراکتر)")
        
        elif cmd == "❌ حذف ولت":
            if not wallets:
                responses.append("📭 هیچ ولتی وجود ندارد")
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
                
                msg = "❌ **انتخاب ولت برای حذف:**\n\n"
                for i, w in enumerate(wallets, 1):
                    msg += f"{i}. `{w[:8]}...{w[-8:]}`\n"
                send_telegram_message(msg, keyboard)
                return []  # منتظر انتخاب می‌مانیم
        
        elif cmd.startswith("حذف "):
            try:
                index = int(cmd.split()[1]) - 1
                if 0 <= index < len(wallets):
                    removed = wallets.pop(index)
                    save_wallets(wallets)
                    responses.append(f"🗑️ حذف شد: `{removed[:8]}...{removed[-8:]}`")
                else:
                    responses.append("شماره نامعتبر")
            except:
                responses.append("خطا در حذف")
        
        elif cmd == "📊 گزارش امروز":
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
            weekday = weekdays[now.weekday()]
            
            msg = f"📊 **گزارش امروز – {today}**\n{weekday}\n\n"
            msg += f"تعداد ولت تحت نظارت: {len(wallets)}\n"
            msg += "وضعیت: فعال"
            responses.append(msg)
        
        elif cmd == "🔄 بررسی تراکنش‌ها":
            responses.append("در حال بررسی...")
            check_all_wallets()
        
        elif cmd == "ℹ️ وضعیت ربات":
            msg = "🤖 **وضعیت ربات**\n\n"
            msg += f"ولت‌ها: {len(wallets)}\n"
            msg += f"آخرین اجرا: {datetime.now().strftime('%H:%M:%S')}\n"
            msg += "شبکه: Solana Mainnet"
            responses.append(msg)
        
        elif cmd == "🔙 بازگشت":
            responses.append("بازگشت به منو")
    
    return responses

# ============== بررسی تراکنش‌ها (بخش اصلی اصلاح‌شده) ==============
def get_recent_transactions(wallet):
    try:
        client = Client(SOLANA_RPC)
        resp = client.get_signatures_for_address(
            wallet,
            limit=15,
            commitment=Confirmed
        )
        if resp.value is None:
            return []
        return resp.value
    except Exception as e:
        print(f"RPC خطا برای {wallet[:9]}...: {str(e)[:140]}")
        return []

def check_all_wallets():
    wallets = load_wallets()
    if not wallets:
        print("هیچ ولتی برای چک کردن وجود ندارد")
        return

    state = load_state()
    new_state = state.copy()

    print(f"─ شروع چک کردن {len(wallets)} ولت ─")

    for wallet in wallets:
        last_sig = state.get(wallet)
        signatures = get_recent_transactions(wallet)

        if not signatures:
            continue

        new_txs = []

        for sig_info in signatures:
            sig = sig_info.signature

            # اگر به آخرین sig شناخته‌شده رسیدیم → بقیه قدیمی هستند
            if last_sig is not None and sig == last_sig:
                break

            time_str = "زمان نامشخص"
            if sig_info.block_time:
                dt = datetime.fromtimestamp(sig_info.block_time)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

            new_txs.append((time_str, sig))

        if new_txs:
            new_txs.reverse()  # قدیمی → جدید

            print(f"→ {wallet[:8]}... : {len(new_txs)} تراکنش جدید")

            for time_str, sig in new_txs:
                message = (
                    f"🔔 **تراکنش جدید**\n"
                    f"والت: `{wallet[:8]}...{wallet[-8:]}`\n"
                    f"🕒 {time_str}\n"
                    f"🔗 [Solscan](https://solscan.io/tx/{sig})"
                )
                send_telegram_message(message)
                time.sleep(0.8)   # جلوگیری از rate limit تلگرام

            # به‌روزرسانی آخرین signature
            new_state[wallet] = signatures[0].signature

    if new_state != state:
        save_state(new_state)
        print("state به‌روزرسانی شد")
    else:
        print("تغییر جدیدی نبود")

# ============== گزارش روزانه ==============
def send_daily_report():
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    last_date = load_last_date()
    
    if last_date != today:
        weekdays = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
        weekday = weekdays[now.weekday()]
        
        wallets_count = len(load_wallets())
        
        message = f"🌅 **گزارش روزانه – {today}**\n{weekday}\n\n"
        message += f"تعداد ولت تحت نظارت: {wallets_count}\n"
        message += "از منو استفاده کنید:"
        
        send_telegram_message(message, main_menu())
        save_last_date(today)

# ============== حلقه اصلی ==============
def main():
    print("اسکریپت شروع شد ...")
    
    # گزارش روزانه (در صورت نیاز)
    send_daily_report()
    
    # گرفتن دستورات تلگرام
    commands = get_telegram_updates()
    
    if commands:
        responses = process_commands(commands)
        for resp in responses:
            if "بازگشت" in resp:
                send_telegram_message("منوی اصلی:", main_menu())
            else:
                send_telegram_message(resp, main_menu())
    
    # همیشه چک کردن تراکنش‌ها (حتی بدون دستور)
    check_all_wallets()
    
    print("اجرای این دور تمام شد")

if __name__ == "__main__":
    main()
