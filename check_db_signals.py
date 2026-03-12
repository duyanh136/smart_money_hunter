import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from services.market_service import MarketService
from services.sql_utils import SQLUtils
from services.smart_money import SmartMoneyAnalyzer

def check_signals():
    print("--- Diagnostic: Market Signals & DB Sync ---")
    
    # 1. Fetch data from SQL
    db_results = SQLUtils.get_all_market_analysis()
    if not db_results:
        print("❌ No data found in MarketAnalysis table.")
        return

    print(f"📊 Found {len(db_results)} records in database.")
    
    # Counter for statuses
    status_counts = {}
    
    # Check specifically for "BÁO ĐỘNG"
    found_alarm = False
    for r in db_results:
        status = r.get('BuySignalStatus', 'N/A')
        status_counts[status] = status_counts.get(status, 0) + 1
        
        if "BÁO ĐỘNG MÚC" in status:
            print(f"✅ FOUND ALARM: {r['Symbol']} -> {status}")
            found_alarm = True

    print("\n--- Status Distribution ---")
    for status, count in status_counts.items():
        print(f"- {status}: {count} symbols")

    if not found_alarm:
        print("\n⚠️ No 'BÁO ĐỘNG MÚC' signals currently stored in DB.")
        print("Analyzing why... checking top 3 LeaderScore stocks for missing flags.")
        
        # Sort by LeaderScore
        db_results.sort(key=lambda x: x.get('LeaderScore', 0), reverse=True)
        for r in db_results[:3]:
            # Fetch fresh data to see why Signal_Super is False
            print(f"\nTicker: {r['Symbol']} (Score: {r['LeaderScore']}, Current: {r['BuySignalStatus']})")
            # In our data structure:
            # SignalSuper (DB) maps to Signal_Super (Code)
            print(f"  - SignalSuper (SQL): {r.get('SignalSuper')}")
            print(f"  - SignalBuyDip (SQL): {r.get('SignalBuyDip')}")
            print(f"  - RSI (SQL): {r.get('RSI')}")

if __name__ == "__main__":
    check_signals()
