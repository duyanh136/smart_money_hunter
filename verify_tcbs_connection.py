from services.tcbs_service import tcbs_service
import sys

def mask_key(k):
    if not k: return "None"
    if len(k) < 8: return "****"
    return k[:4] + "*" * (len(k)-8) + k[-4:]

print("--- TCBS CONFIG & CONNECTION CHECK ---")

# 1. Check API Key
key = tcbs_service.api_key
if key:
    print(f"[OK] API Key Loaded: {mask_key(key)}")
else:
    print("[FAIL] API Key NOT loaded!")
    sys.exit(1)

# 2. Check Token
token = tcbs_service.token
if token:
    print(f"[OK] Token Found (Length: {len(token)})")
    
    # 3. Ping Server (Get Ticker Info)
    print("Pinging TCBS Server (Get VIC info)...")
    try:
        info = tcbs_service.get_ticker_info('VIC')
        if info:
            print(f"[SUCCESS] Server Responded. VIC Price: {info.get('price', 'N/A')}")
        else:
            print("[WARNING] Server responded but no data. Token might be expired.")
    except Exception as e:
        print(f"[ERROR] Connection Failed: {e}")
else:
    print("[INFO] No Token found (or expired). API Key is ready for OTP Login.")
    
print("--------------------------------------")
