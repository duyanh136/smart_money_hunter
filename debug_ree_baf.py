import sys
sys.stdout.reconfigure(encoding='utf-8')
from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer

def debug_stocks():
    for symbol in ['REE', 'BAF']:
        print(f"Checking {symbol}...")
        df = MarketService.get_history(symbol, period='6mo')
        if df is None or df.empty:
            print(f"No data for {symbol}")
            continue
        
        df = SmartMoneyAnalyzer.analyze(df)
        last = df.iloc[-1]
        
        print(f"  Price: {last['Close']}")
        print(f"  Phase: {last.get('Market_Phase')}")
        print(f"  Action: '{last.get('Action_Recommendation')}'")
        print(f"  Signal VoTeo: {last.get('Signal_VoTeo')}")
        print(f"  Shark: {last.get('Shark_Bar')}")
        print(f"  Retail: {last.get('Retail_Bar')}")
        print("-" * 20)

if __name__ == "__main__":
    debug_stocks()
