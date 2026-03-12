from services.market_service import MarketService
import logging

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    print("🚀 Triggering initial full market scan...")
    MarketService.run_full_market_scan()
    print("✅ Initial scan complete.")
