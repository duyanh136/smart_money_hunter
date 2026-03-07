from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
from services.symbol_loader import SymbolLoader
import pandas as pd

def find_mua_gom():
    stocks = SymbolLoader.get_liquid_stocks()
    print(f"Scanning {len(stocks)} stocks for 'MUA GOM' action...")
    
    found_list = []
    
    for symbol in stocks:
        try:
            df = MarketService.get_history(symbol, period='3mo')
            if df is None or df.empty: continue
            
            df = SmartMoneyAnalyzer.analyze(df)
            last_row = df.iloc[-1]
            
            # Action logic from smart_money.py:
            # is_uptrend = row['SMA_20'] > row['SMA_50']
            # row['Close'] < row['Rolling_Max_20']
            # row['Signal_VoTeo']
            # row['Shark_Bar'] >= 0 and row['Retail_Bar'] <= 0
            
            action = last_row.get('Action_Recommendation')
            phase = last_row.get('Market_Phase')
            
            if action == "MUA GOM / HOLD":
                print(f"FOUND: {symbol} - {phase}")
                found_list.append(symbol)
        except Exception:
            continue
            
    if not found_list:
        print("No stock with 'MUA GOM' action found today.")
    else:
        print(f"\nExample symbols: {', '.join(found_list[:3])}")

if __name__ == "__main__":
    find_mua_gom()
