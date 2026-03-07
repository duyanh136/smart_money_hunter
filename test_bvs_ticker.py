import yfinance as yf
import pandas as pd

def test_ticker(symbol):
    print(f"Testing {symbol}...")
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo")
        if not hist.empty:
            print(f"SUCCESS: {symbol} price = {hist['Close'].iloc[-1]}")
        else:
            print(f"FAILED: {symbol} is empty")
    except Exception as e:
        print(f"ERROR: {symbol} -> {e}")

if __name__ == "__main__":
    test_ticker("BVS.SS")
    test_ticker("BVS.S")
    test_ticker("BVS.BS")
    test_ticker("BVS.VN")
    test_ticker("BVS.HN")
    # Also check if it's lowercase or something
    test_ticker("bvs.ss")
