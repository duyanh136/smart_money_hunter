import sys
sys.stdout.reconfigure(encoding='utf-8')
from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer

def check_bid():
    symbol = 'BID'
    print(f"Checking data for {symbol}...")
    df = MarketService.get_history(symbol, period='6mo')
    if df is None or df.empty:
        print("No data found for BID.")
        return
    
    df = SmartMoneyAnalyzer.analyze(df)
    last = df.iloc[-1]
    
    print("-" * 30)
    print(f"Price: {last['Close']}")
    print(f"Market Phase: {last.get('Market_Phase')}")
    print(f"Action: {last.get('Action_Recommendation')}")
    print(f"Vo Teo: {last.get('Signal_VoTeo')}")
    print(f"Big Money: {last.get('Signal_BigMoney')}")
    print(f"Shark Bar: {last.get('Shark_Bar')}")
    print(f"Retail Bar: {last.get('Retail_Bar')}")
    print("-" * 30)

if __name__ == "__main__":
    check_bid()
