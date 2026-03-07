from services.tcbs_service import tcbs_service
import json
import os

def debug_authenticated():
    print(f"Token file exists: {os.path.exists('.tcbs_token')}")
    if tcbs_service.token:
        print(f"Token (first 20 chars): {tcbs_service.token[:20]}...")
        
        print("\n--- Testing get_ticker_info('BVS') ---")
        info = tcbs_service.get_ticker_info("BVS")
        if info:
            print("SUCCESS! Ticker Info:")
            print(json.dumps(info, indent=2))
        else:
            print("FAILED to get ticker info.")
            
        print("\n--- Testing get_history('BVS') ---")
        df = tcbs_service.get_history("BVS")
        if df is not None and not df.empty:
            print("SUCCESS! History DF:")
            print(df)
        else:
            print("FAILED to get history.")
    else:
        print("No token loaded.")

if __name__ == "__main__":
    debug_authenticated()
