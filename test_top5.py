import sys
import os

# Add parent directory to path to allow importing local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.market_service import MarketService

def run_test():
    print("Fetching Top 5 Leaders...")
    leaders = MarketService.get_top_leaders(limit=5)
    
    print("\n--- TOP 5 LEADERS KHỎE NHẤT ---")
    for i, l in enumerate(leaders):
        print(f"{i+1}. {l['symbol']} | Điểm: {l['score']} | Giá: {l['price']} | Tăng: {l['change']}%")
        print(f"   Tag: {l['tag']}")
        print(f"   Hành động: {l['action']} | BuyDip: {l['signal_buydip']}")
        print("-" * 50)
        
if __name__ == '__main__':
    run_test()
