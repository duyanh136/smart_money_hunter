from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
import pandas as pd

symbol = "SZC"
print(f"Fetching data for {symbol}...")
df = MarketService.get_history(symbol, period="6mo")

if df is not None and not df.empty:
    # Analyze
    df = SmartMoneyAnalyzer.analyze(df)
    
    row = df.iloc[-1]
    
    print(f"--- Analysis for {symbol} ---")
    print(f"Close: {row['Close']}")
    print(f"SMA_20: {row['SMA_20']}")
    print(f"SMA_50: {row['SMA_50']}")
    print(f"Volume: {row['Volume']}")
    print(f"Avg_Vol_20: {row['Avg_Vol_20']}")
    
    is_uptrend = row['SMA_20'] > row['SMA_50']
    print(f"Is Uptrend (SMA20 > SMA50): {is_uptrend}")
    
    # Check Distribution Components
    print(f"Signal_Distribution (Total): {row.get('Signal_Distribution')}")
    print(f" - Signal_MACD_Weakness: {row.get('Signal_MACD_Weakness')}")
    print(f" - Signal_Loose (Biến động lỏng): {row.get('Signal_Loose')}")
    print(f" - Signal_ShootingStar (Nến đảo chiều): {row.get('Signal_ShootingStar')}")
    print(f" - MACD_Cross_Down: {row.get('MACD_Cross_Down')}")
    print(f" - Signal_UpBo: {row.get('Signal_UpBo')}")
    
    print(f"Market Phase: {row['Market_Phase']}")
    print(f"Action: {row['Action_Recommendation']}")
else:
    print("Could not fetch data.")
