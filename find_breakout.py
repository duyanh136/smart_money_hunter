from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
from services.symbol_loader import SymbolLoader

def find_breakout():
    stocks = SymbolLoader.get_liquid_stocks()
    print(f"Scanning {len(stocks)} stocks for 'Breakout' signals...")
    
    found_list = []
    
    for symbol in stocks:
        try:
            df = MarketService.get_history(symbol, period='3mo')
            if df is None or df.empty: continue
            
            df = SmartMoneyAnalyzer.analyze(df)
            last_row = df.iloc[-1]
            
            if last_row.get('Signal_Breakout'):
                print(f"FOUND BREAKOUT: {symbol}")
                found_list.append(symbol)
        except Exception:
            continue
            
    if not found_list:
        print("No stock with 'Breakout' signal found today.")
    else:
        print(f"\nBreakout symbols: {', '.join(found_list)}")

if __name__ == "__main__":
    find_breakout()
