from services.tcbs_service import tcbs_service
import sys

symbols = ["TVN", "PVS", "OIL", "PVC", "VIC"]

print("--- DEBUGGING TICKER INFO (SNAPSHOT) ---")

for s in symbols:
    print(f"\nFetching info for {s}...", end=" ")
    try:
        info = tcbs_service.get_ticker_info(s)
        if info:
            print(f"[SUCCESS]")
            print(f"  Price: {info.get('price')}")
            print(f"  Vol: {info.get('volume')}")
            print(f"  Ref: {info.get('refPrice')}")
        else:
            print(f"[FAIL] Returned None.")
    except Exception as e:
        print(f"[ERROR] {e}")

print("\n--- END DEBUG ---")
