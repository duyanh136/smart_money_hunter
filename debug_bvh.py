from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
import pandas as pd

symbol = "BVH"
print(f"Fetching data for {symbol}...")
df = MarketService.get_history(symbol, period="6mo")

if df is not None and not df.empty:
    # Analyze
    df = SmartMoneyAnalyzer.analyze(df)
    
    row = df.iloc[-1]
    
    with open("bvh_analysis.txt", "w", encoding="utf-8") as f:
        f.write(f"--- Analysis for {symbol} ({df.index[-1].strftime('%Y-%m-%d')}) ---\n")
        f.write(f"Close: {row['Close']}\n")
        f.write(f"SMA_20: {row['SMA_20']}\n")
        f.write(f"SMA_50: {row['SMA_50']}\n")
        
        is_uptrend = row['SMA_20'] > row['SMA_50']
        f.write(f"Is Uptrend (SMA20 > SMA50): {is_uptrend}\n")
        
        f.write(f"Signal VoTeo: {row.get('Signal_VoTeo')}\n")
        f.write(f"Rolling Max 20: {row.get('Rolling_Max_20')}\n")
        f.write(f"Condition Close < Rolling Max 20: {row['Close'] < row['Rolling_Max_20']}\n")
        
        # MACD
        f.write(f"MACD Line: {row.get('MACD_Line')}\n")
        f.write(f"MACD Signal: {row.get('MACD_Signal')}\n")
        f.write(f"MACD Cross Down: {row.get('MACD_Cross_Down')}\n")
        f.write(f"Signal Distribution: {row.get('Signal_Distribution')}\n")
        
        f.write(f"Market Phase: {row['Market_Phase']}\n")
        f.write(f"Action: {row['Action_Recommendation']}\n")

    print("Analysis written to bvh_analysis.txt")
else:
    print("Could not fetch data.")
