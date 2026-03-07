from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
import pandas as pd

# We need to find a stock that might trigger this or just print the logic verification.
# Let's try to scan the watchlist for any stock with this signal.

watchlist = ['SZC', 'GMD', 'VSC', 'FPT', 'DGC', 'SSI', 'VND', 'DIG', 'CEO']

print("Scanning for Golden Sell signals...")
found = False

for symbol in watchlist:
    try:
        df = MarketService.get_history(symbol, period="6mo")
        if df is not None and not df.empty:
            df = SmartMoneyAnalyzer.analyze(df)
            row = df.iloc[-1]
            
            if row['Signal_GoldenSell']:
                print(f"\nExample found: {symbol}")
                print(f"RSI: {row['RSI']}")
                print(f"Volume: {row['Volume']}")
                print(f"Avg Vol: {row['Avg_Vol_20']}")
                print(f"Close: {row['Close']}, Open: {row['Open']}")
                print(f"Action: {row['Action_Recommendation']}")
                found = True
            elif row['RSI'] > 65: # Close enough to check manually
                print(f"\nNear miss: {symbol} (RSI {row['RSI']:.1f})")
                print(f"Action: {row['Action_Recommendation']}")
                
    except Exception as e:
        print(f"Error {symbol}: {e}")

if not found:
    print("\nNo strict Golden Sell signal found in sample watchlist today.")
    print("Logic is implemented but market conditions may not match exactly right now.")
