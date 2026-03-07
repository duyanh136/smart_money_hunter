import yfinance as yf

symbols = ["TVN", "PVS", "OIL", "PVC"]
suffixes = [".VN", ".HN", ""]

print("--- DEBUGGING YAHOO FINANCE ---")

for s in symbols:
    print(f"\nChecking {s}...")
    for suf in suffixes:
        ticker = f"{s}{suf}"
        print(f"  Trying {ticker}...", end=" ")
        try:
            dat = yf.Ticker(ticker).history(period="5d")
            if not dat.empty:
                print(f"[SUCCESS] Found data! Last price: {dat['Close'].iloc[-1]}")
                break
            else:
                print("[FAIL] Empty.")
        except Exception as e:
            print(f"[ERROR] {e}")

print("\n--- END DEBUG ---")
