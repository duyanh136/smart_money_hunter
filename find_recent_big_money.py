from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
from services.symbol_loader import SymbolLoader

def find_recent_big_money():
    stocks = SymbolLoader.get_liquid_stocks()
    print(f"Scanning {len(stocks)} stocks for recent 'Big Money' activity...")
    
    found_list = []
    
    for symbol in stocks:
        try:
            df = MarketService.get_history(symbol, period='3mo')
            if df is None or df.empty: continue
            
            df = SmartMoneyAnalyzer.analyze(df)
            
            # Look at last 5 days
            recent_rows = df.tail(5)
            for i in range(len(recent_rows)):
                row = recent_rows.iloc[i]
                if row.get('Signal_BigMoney'):
                    days_ago = len(recent_rows) - 1 - i
                    print(f"RECENT BIG MONEY: {symbol} ({days_ago} days ago)")
                    found_list.append((symbol, days_ago))
                    break
        except Exception:
            continue
            
    if not found_list:
        print("No recent 'Big Money' activity found.")
    else:
        found_list.sort(key=lambda x: x[1])
        print("\nRecent examples:")
        for sym, days in found_list[:5]:
            print(f"- {sym}: {days} days ago")

if __name__ == "__main__":
    find_recent_big_money()
