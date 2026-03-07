from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
import pandas as pd

def test_signals():
    # Curated list of stocks that usually have volume and data
    watchlist = ['SSI', 'VND', 'HPG', 'DIG', 'CEO', 'PDR', 'NVL', 'STB', 'MBB', 'TCB', 'VPB', 'ACB', 'VHM', 'VIC', 'MWG', 'MSN', 'GVR']
    
    print(f"Scanning {len(watchlist)} liquid stocks for an example signal...")
    
    found = False
    for symbol in watchlist:
        try:
            print(f"Checking {symbol}...", end=" ")
            df = MarketService.get_history(symbol, period='3mo')
            if df is None or df.empty: 
                print("No Data")
                continue
            
            df = SmartMoneyAnalyzer.analyze(df)
            last_row = df.iloc[-1]
            
            signals = []
            if last_row.get('Signal_BigMoney'): signals.append("BIG MONEY (Rong)")
            if last_row.get('Signal_Breakout'): signals.append("BREAKOUT (Dot Pha)")
            if last_row.get('Signal_BuyDip'): signals.append("BUY DIP (Mua Giam)")
            if last_row.get('Signal_VoTeo'): signals.append("VO TEO (Tich Luy)")
            
            if signals:
                print(f"FOUND: {', '.join(signals)}")
                print("-" * 30)
                print(f"Symbol: {symbol}")
                print(f"Price: {last_row['Close']:.2f}")
                print(f"Change: {last_row['Price_Change']:.2f}")
                print(f"Volume: {last_row['Volume']:,.0f}")
                print(f"AvgVol20: {last_row['Avg_Vol_20']:,.0f}")
                print(f"Signals: {', '.join(signals)}")
                print("-" * 30)
                found = True
                break # Just need one example
            else:
                print("No Signal")
                
        except Exception as e:
            print(f"Error: {e}")
            continue

    if not found:
        print("\nNo signals found in this short list. Market might be quiet.")

if __name__ == "__main__":
    test_signals()
