import requests
import time

# SSI iBoard API (Public)
# https://iboard.ssi.com.vn/dchart/api/history?resolution=D&symbol=TVN&from=1708300000&to=1740000000

symbols = ["TVN", "PVS", "OIL", "VIC"]
url_base = "https://iboard.ssi.com.vn/dchart/api/history"

print("--- DEBUGGING SSI API ---")

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

end_ts = int(time.time())
start_ts = end_ts - (30 * 24 * 60 * 60) # 30 days

for sym in symbols:
    print(f"\nFetching {sym}...", end=" ")
    try:
        params = {
            "resolution": "D",
            "symbol": sym,
            "from": start_ts,
            "to": end_ts
        }
        res = requests.get(url_base, params=params, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            # SSI returns {t: [], c: [], ...} (TradingView format)
            if 't' in data and len(data['t']) > 0:
                print("[SUCCESS]")
                print(f"  Last Time: {data['t'][-1]}")
                print(f"  Last Close: {data['c'][-1]}")
            else:
                print("[FAIL] Empty Data or Invalid Format")
        else:
            print(f"[FAIL] Status {res.status_code}")
            
    except Exception as e:
        print(f"[ERROR] {e}")

print("\n--- END DEBUG ---")
