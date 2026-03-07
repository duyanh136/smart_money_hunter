import requests
import json
import pandas as pd

# VNDirect Finfo API (Public)
# https://finfo-api.vndirect.com.vn/v4/stock_prices?symbol=TVN&sort=date&size=100&page=1

symbols = ["TVN", "PVS", "OIL", "VIC"]
url_base = "https://finfo-api.vndirect.com.vn/v4/stock_prices"

print("--- DEBUGGING VNDIRECT API ---")

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

for sym in symbols:
    print(f"\nFetching {sym}...", end=" ")
    try:
        params = {
            "symbol": sym,
            "sort": "date:desc",
            "size": 5, # Get last 5 days to verify
            "page": 1
        }
        res = requests.get(url_base, params=params, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            if 'data' in data and len(data['data']) > 0:
                print("[SUCCESS]")
                first = data['data'][0]
                print(f"  Date: {first['date']}")
                print(f"  Close: {first['close']}")
                print(f"  Vol: {first['mnVolume']}") # Matched Volume?
            else:
                print("[FAIL] Empty Data")
        else:
            print(f"[FAIL] Status {res.status_code}")
            
    except Exception as e:
        print(f"[ERROR] {e}")

print("\n--- END DEBUG ---")
