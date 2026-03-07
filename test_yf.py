import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_yfinance():
    symbol = "VND.VN"
    logger.info(f"Testing yfinance for {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo")
        if not hist.empty:
            logger.info("Success! Data found.")
            print(hist.head())
        else:
            logger.warning("No data found.")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    test_yfinance()
