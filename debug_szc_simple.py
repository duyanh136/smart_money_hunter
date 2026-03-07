from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
import pandas as pd

symbol = "SZC"
df = MarketService.get_history(symbol, period="6mo")

if df is not None and not df.empty:
    df = SmartMoneyAnalyzer.analyze(df)
    row = df.iloc[-1]
    
    with open("szc_simple_out.txt", "w") as f:
        f.write(f"SYMBOL: {symbol}\n")
        f.write(f"Weakness (MACD Div): {row.get('Signal_MACD_Weakness')}\n")
        f.write(f"Loose (Bien Dong Long): {row.get('Signal_Loose')}\n")
        f.write(f"Shooting Star: {row.get('Signal_ShootingStar')}\n")
        f.write(f"MACD Cross Down: {row.get('MACD_Cross_Down')}\n")
        f.write(f"Up Bo (Trap): {row.get('Signal_UpBo')}\n")
        f.write(f"RSI: {row['RSI']}\n")
        f.write(f"Vol Ratio: {row['Volume'] / row['Avg_Vol_20']:.2f}\n")
        f.write(f"Close < Max20: {row['Close'] < row['Rolling_Max_20']}\n")
else:
    print("No data")
