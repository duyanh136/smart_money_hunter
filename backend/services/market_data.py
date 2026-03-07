import yfinance as yf
import pandas as pd
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MarketDataService:
    def __init__(self):
        self.cache: Dict[str, pd.DataFrame] = {}

    async def get_history(self, symbol: str, period: str = "1y", interval: str = "1d") -> Optional[pd.DataFrame]:
        """Fetches historical data from yfinance"""
        try:
            # Add .VN for Vietnamese stocks if not present
            if len(symbol) == 3 and not symbol.endswith(".VN"):
                symbol = f"{symbol}.VN"
            
            # Simple caching for now
            if symbol in self.cache:
                # In real app, check cache age
                return self.cache[symbol]

            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                return None
            
            self.cache[symbol] = hist
            return hist
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    async def get_live_price(self, symbol: str) -> float:
        """
        Simulates live price or fetches delayed price.
        For intraday "Smart Money" calc, we might need 1-minute data.
        """
        # TODO: Implement live fetching strategy
        pass
