from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
from services.symbol_loader import SymbolLoader
import pandas as pd

def find_big_money():
    stocks = SymbolLoader.get_liquid_stocks()
    print(f"Scanning {len(stocks)} stocks for 'Big Money' (Rong) signals...")
    
    found_list = []
    
    for symbol in stocks:
        try:
            df = MarketService.get_history(symbol, period='3mo')
            if df is None or df.empty: continue
            
            df = SmartMoneyAnalyzer.analyze(df)
            last_row = df.iloc[-1]
            
            if last_row.get('Signal_BigMoney'):
                print(f"FOUND BIG MONEY: {symbol}")
                found_list.append(symbol)
        except Exception:
            continue
            
    if not found_list:
        print("No stock with 'Big Money' signal found today.")
    else:
        print(f"\nBig Money symbols: {', '.join(found_list)}")

if __name__ == "__main__":
    find_big_money()
