from services.market_service import MarketService
import logging

# Configure logging to see the patching messages
logging.basicConfig(level=logging.INFO)

def verify_tcbs_integration():
    symbol = "BVS" # HNX stock with large discrepancy
    print(f"--- Verifying TCBS Integration for {symbol} ---")
    
    # Try to fetch history
    df = MarketService.get_history(symbol, period="5d")
    
    if df is not None and not df.empty:
        latest_close = df.iloc[-1]['Close']
        print(f"Latest Close Price: {latest_close}")
        
        if latest_close > 20: 
            print("[SUCCESS] Price is correctly reported as ~29+ (TCBS integration working).")
        else:
            print(f"[FAILED] Price is still {latest_close}. Make sure to run 'python fetch_tcbs_token.py' first.")
    else:
        print(f"[FAILED] Could not fetch data for {symbol}.")

if __name__ == "__main__":
    verify_tcbs_integration()
