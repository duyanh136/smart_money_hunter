from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
from services.symbol_loader import SymbolLoader
import pandas as pd

def find_example():
    stocks = SymbolLoader.get_liquid_stocks()
    print(f"Scanning {len(stocks)} stocks for an example...")
    
    for symbol in stocks:
        try:
            # Try fetching with .VN first (standard for yfinance/Vietnam)
            ticker = symbol if symbol.endswith('.VN') else f"{symbol}.VN"
            df = MarketService.get_history(ticker, period='2mo')
            
            # If failed, try without suffix (sometimes works for indices or global)
            if df is None or df.empty:
                df = MarketService.get_history(symbol, period='2mo')
                
            if df is None or df.empty: continue
            
            df = SmartMoneyAnalyzer.analyze(df)
            last_row = df.iloc[-1]
            
            signal = None
            if last_row.get('Signal_BigMoney'): signal = "RỒNG (Tiền Lớn)"
            elif last_row.get('Signal_Breakout'): signal = "ĐỘT PHÁ (Breakout)"
            elif last_row.get('Signal_BuyDip'): signal = "MUA KHI GIÁ GIẢM (Buy Dip)"
            elif last_row.get('Signal_VoTeo'): signal = "VÔ TEO (Tích lũy)"
            
            if signal:
                print(f"\nFOUND EXAMPLE: {symbol}")
                print(f"Signal: {signal}")
                print(f"Price: {last_row['Close']}")
                print(f"Volume: {last_row['Volume']}")
                print(f"Avg Vol 20: {last_row['Avg_Vol_20']}")
                print(f"RSI: {last_row['RSI']}")
                return
        except Exception as e:
            continue
            
    print("\nNo signals found in the scan list mainly because market might be boring or data issue.")

if __name__ == "__main__":
    find_example()
