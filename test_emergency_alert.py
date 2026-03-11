import time
from services.telegram_bot import init_portfolio_cache, check_realtime_stoploss, portfolio_cache, load_portfolio
import json

print("1. Initializing Bot Cache from portfolio.json...")
init_portfolio_cache()

print(f"Current Cache State: {json.dumps(portfolio_cache, indent=2)}")

symbol = 'POW'
# Portfolio has BCM with SL around 62.0
crash_price = 55.0

print(f"\n2. Simulating a WebSocket Flash Crash for {symbol} to {crash_price}...")
check_realtime_stoploss(symbol, crash_price)

print("\n3. Verifying Cache Cooldown Flag...")
print(f"Cache State after crash: {json.dumps(portfolio_cache, indent=2)}")

print("\n4. Simulating another WebSocket ping 1 second later (Spam attempt)...")
check_realtime_stoploss(symbol, crash_price - 1.0)
print("If no second Telegram message was sent, the Cooldown worked perfectly!")

print("\n5. Checking portfolio.json file to ensure flag was persisted...")
saved = load_portfolio()
print(f"Saved Portfolio State: {json.dumps(saved, indent=2)}")

# Reset the alert flag for manual live testing later
import os
PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), 'portfolio.json')
try:
    with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        if item.get('symbol') == symbol:
            item['alert_sent'] = False
    with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
except Exception as e:
    pass
