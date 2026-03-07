import sys, traceback
sys.stdout.reconfigure(encoding='utf-8')

from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer

sym = 'REE'
try:
    df = MarketService.get_history(sym, period='2mo')
    print(f"{sym} data rows: {len(df) if df is not None else 'None'}")
    df = SmartMoneyAnalyzer.analyze(df)
    last = df.iloc[-1]
    print(f"{sym}: Action={last.get('Action_Recommendation')}")
except Exception as e:
    traceback.print_exc()
