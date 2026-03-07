from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
import pandas as pd

# Fetch Data
symbol = "GEE"
print(f"Fetching data for {symbol}...")
df = MarketService.get_history(symbol, period="6mo")

try:
    if df is not None:
        # Analyze
        df = SmartMoneyAnalyzer.analyze(df)
        
        # Get last row
        if not df.empty:
            row = df.iloc[-1]
            
            with open('gee_summary.txt', 'w', encoding='utf-8') as f:
                f.write(f"Symbol: {symbol}\n")
                f.write(f"Date: {df.index[-1].strftime('%Y-%m-%d')}\n")
                f.write(f"Close: {row['Close']}\n")
                f.write(f"SMA_20: {row['SMA_20']}\n")
                f.write(f"SMA_50: {row['SMA_50']}\n")
                f.write(f"Market Phase: {row['Market_Phase']}\n")
                f.write(f"Action: {row['Action_Recommendation']}\n")
                
            print("Summary written to gee_summary.txt")
        else:
            print("DataFrame is empty after analysis.")
    else:
        print("Could not fetch data (df is None).")
except Exception as e:
    import traceback
    traceback.print_exc()
