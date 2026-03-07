from services.tcbs_service import tcbs_service
import json
import logging

# Configure logging to print to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

symbols = ["TVN", "PVS", "OIL", "PVC", "VIC"] # VIC as control (HOSE)

print("--- DEBUGGING TCBS DATA FETCH ---")

# Test Alternative Endpoints
test_urls = [
    "https://athena.tcbs.com.vn/stock-insight/v1/stock/bars-long-term",
]

symbol = "VIC"
print(f"Testing endpoints for {symbol}...")

import requests
headers = tcbs_service.get_headers()
# Add User-Agent and specific Origin/Referer for tcinvest
headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
headers["Accept"] = "application/json"
headers["Referer"] = "https://tcinvest.tcbs.com.vn/"
headers["Origin"] = "https://tcinvest.tcbs.com.vn"
headers["Sec-Fetch-Dest"] = "empty"
headers["Sec-Fetch-Mode"] = "cors"
headers["Sec-Fetch-Site"] = "same-origin"

for url_template in test_urls:
    url = url_template.replace("{ticker}", symbol)
    print(f"\nTrying: {url}")
    print(f"Headers Key Count: {len(headers)}")

for url_template in test_urls:
    url = url_template.replace("{ticker}", symbol)
    print(f"\nTrying: {url}")
    
    params = {
        "ticker": symbol,
        "type": "stock",
        "resolution": "D",
        "countBack": 100
    }
    
    try:
        res = requests.get(url, params=params, headers=headers)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            print(f"Success! Response: {res.text[:200]}...")
        else:
            print(f"Failed: {res.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")

print("\n--- END DEBUG ---")
