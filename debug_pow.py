from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
import pandas as pd

symbol = "POW"
print(f"Fetching data for {symbol}...")
try:
    df = MarketService.get_history(symbol, period="6mo")

    if df is not None and not df.empty:
        # Analyze
        df = SmartMoneyAnalyzer.analyze(df)
        
        row = df.iloc[-1]
        
        print(f"--- Analysis for {symbol} ---")
        print(f"Close: {row['Close']}")
        print(f"SMA_20: {row['SMA_20']}")
        print(f"SMA_50: {row['SMA_50']}")
        print(f"Is Uptrend (SMA20 > SMA50): {row['SMA_20'] > row['SMA_50']}")
        print(f"Market Phase: {row['Market_Phase']}")
        print(f"Action: {row['Action_Recommendation']}")
        
    else:
        print("Could not fetch data.")
except Exception as e:
    import traceback
    traceback.print_exc()
