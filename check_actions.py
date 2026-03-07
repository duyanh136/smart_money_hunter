from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
from services.symbol_loader import SymbolLoader
import pandas as pd

def check_all():
    stocks = SymbolLoader.get_liquid_stocks()
    print(f"Scanning {len(stocks)} stocks...")
    
    found_mua_gom = []
    found_nam_giu = []
    
    for symbol in stocks:
        try:
            df = MarketService.get_history(symbol, period='3mo')
            if df is None or df.empty: continue
            
            df = SmartMoneyAnalyzer.analyze(df)
            last_row = df.iloc[-1]
            
            action = last_row.get('Action_Recommendation')
            
            if action == "MUA GOM / HOLD":
                found_mua_gom.append(symbol)
                if len(found_mua_gom) >= 2: break
            elif action == "Nắm Giữ":
                found_nam_giu.append(symbol)
                
        except Exception:
            continue

    print("-" * 30)
    if found_mua_gom:
        print(f"MUA GOM Examples: {', '.join(found_mua_gom)}")
    else:
        print("No MUA GOM found today.")
        
    if found_nam_giu:
        print(f"NAM GIU Examples: {', '.join(found_nam_giu[:5])}")
    print("-" * 30)

if __name__ == "__main__":
    check_all()
