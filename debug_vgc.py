from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
import pandas as pd

symbol = "VGC"
print(f"Fetching data for {symbol}...")
try:
    df = MarketService.get_history(symbol, period="6mo")

    if df is not None and not df.empty:
        # Analyze
        df = SmartMoneyAnalyzer.analyze(df)
        
        row = df.iloc[-1]
        
        print(f"--- Analysis for {symbol} ({df.index[-1].strftime('%Y-%m-%d')}) ---")
        print(f"Close: {row['Close']}")
        print(f"SMA_20: {row['SMA_20']}")
        print(f"Rolling_Max_20: {row['Rolling_Max_20']}")
        print(f"Volume: {row['Volume']}")
        print(f"Avg_Vol_20: {row['Avg_Vol_20']}")
        
        is_uptrend = row['SMA_20'] > row['SMA_50']
        print(f"Is Uptrend (SMA20 > SMA50): {is_uptrend}")
        
        # Check Buy Dip / Shakeout conditions
        cond_price_dip = row['Close'] < row['Rolling_Max_20']
        cond_voteo = row['Signal_VoTeo']
        
        print(f"Condition Price Dip (Close < Max20): {cond_price_dip}")
        print(f"Condition VoTeo (Vol < 0.6*Avg): {cond_voteo}")
        print(f"Condition Close > SMA20: {row['Close'] > row['SMA_20']}")
        
        print(f"Market Phase: {row['Market_Phase']}")
        print(f"Action: {row['Action_Recommendation']}")
        
    else:
        print("Could not fetch data.")
except Exception as e:
    import traceback
    traceback.print_exc()
