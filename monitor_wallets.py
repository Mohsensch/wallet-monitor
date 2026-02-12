name: Monitor Solana Wallets

on:
  schedule:
    - cron: '*/10 * * * *'  # هر ۱۰ دقیقه یکبار اجرا کن
  workflow_dispatch:        # برای اجرای دستی از تب Actions

jobs:
  monitor:
    runs-on: ubuntu-latest
    
    steps:
    - name: 📥 دریافت کد از مخزن
      uses: actions/checkout@v3
    
    - name: 🐍 نصب پایتون
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: 📦 نصب کتابخانه‌های مورد نیاز
      run: |
        python -m pip install --upgrade pip
        pip install solana requests pyyaml
    
    - name: 📋 لیست فایل‌ها (برای اطمینان)
      run: ls -la
    
    - name: 🚀 اجرای اسکریپت نظارت
      env:
        TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
        CHAT_ID: ${{ secrets.CHAT_ID }}
      run: python monitor_wallets.py
