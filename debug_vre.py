from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
import pandas as pd

# Fetch Data
symbol = "VRE"
print(f"Fetching data for {symbol}...")
df = MarketService.get_history(symbol, period="6mo")

if df is not None:
    # Analyze
    df = SmartMoneyAnalyzer.analyze(df)
    
    # Get last row
    row = df.iloc[-1]
    
    print(f"--- Analysis for {symbol} ({df.index[-1].strftime('%Y-%m-%d')}) ---")
    print(f"Close: {row['Close']}")
    print(f"SMA_20: {row['SMA_20']}")
    print(f"SMA_50: {row['SMA_50']}")
    
    is_uptrend = row['SMA_20'] > row['SMA_50']
    print(f"Is Uptrend (SMA20 > SMA50): {is_uptrend}")
    print(f"Price vs SMA20: {'Above' if row['Close'] > row['SMA_20'] else 'Below'}")
    
    print(f"Market Phase: {row['Market_Phase']}")
    print(f"Action: {row['Action_Recommendation']}")
else:
    print("Could not fetch data.")
