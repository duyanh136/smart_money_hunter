import requests
import json

try:
    response = requests.get("http://127.0.0.1:5000/api/history?symbol=VND")
    data = response.json()
    last_item = data["data"][-1]
    print(f"Symbol: {data['symbol']}")
    print(f"Action: {data['action']}")
    print(f"Last Price: {last_item['close']}")
    print(f"MA20: {last_item['ma20']}")
    print(f"MA50: {last_item['ma50']}")
    print(f"RSI: {last_item['rsi']}")
    print(f"MACD Line: {last_item['macd_line']}")
    print(f"MACD Hist: {last_item['macd_hist']}")
    
    if last_item['ma20'] > 0 and last_item['rsi'] > 0:
        print("SUCCESS: Indicators are behaving correctly.")
    else:
        print("WARNING: Some indicators are zero. Check data length or calculation.")
except Exception as e:
    print(f"ERROR: {e}")
