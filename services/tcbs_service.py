import requests
import os
import logging
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
# pandas is imported lazily in get_history to avoid unnecessary dependencies for token fetching
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

from services.config_loader import load_api_key

class TCBSService:
    BASE_URL = "https://openapi.tcbs.com.vn"
    TOKEN_FILE = ".tcbs_token"
    CONFIG_FILE = "tcbs_config.enc"

    def __init__(self):
        self.api_key = None
        
        # 1. Try loading from secure config file first
        try:
            if os.path.exists(self.CONFIG_FILE):
                self.api_key = load_api_key(self.CONFIG_FILE)
                logger.info("Loaded TCBS API Key from secure config.")
        except Exception as e:
            logger.error(f"Failed to load secure config: {e}")
            
        # 2. Fallback to env var
        if not self.api_key:
            self.api_key = os.getenv("TCBS_API_KEY")
            if self.api_key:
                logger.warning("Using insecure API Key from .env")

        self.token = os.getenv("TCBS_TOKEN")
        self._load_token_from_file()

    def _load_token_from_file(self):
        """Loads token from a local file if it exists and is not expired"""
        if os.path.exists(self.TOKEN_FILE):
            try:
                with open(self.TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    # Token is valid for 8 hours (28800 seconds)
                    # We check against 7 hours to be safe
                    if time.time() - data.get('timestamp', 0) < 7 * 3600:
                        self.token = data.get('token')
                        logger.info("Loaded TCBS token from file.")
            except Exception as e:
                logger.error(f"Error loading TCBS token: {e}")

    def _save_token_to_file(self, token: str):
        self.token = token
        try:
            with open(self.TOKEN_FILE, 'w') as f:
                json.dump({
                    'token': token,
                    'timestamp': time.time()
                }, f)
        except Exception as e:
            logger.error(f"Error saving TCBS token: {e}")

    def get_headers(self):
        if not self.token:
            return {}
        return {
            "Authorization": f"Bearer {self.token}",
            "Referer": "https://tcinvest.tcbs.com.vn/",
            "Origin": "https://tcinvest.tcbs.com.vn"
        }

    def fetch_token_with_otp(self, otp: str) -> bool:
        """Exchanges API Key + OTP for a JWT Token"""
        if not self.api_key:
            logger.error("TCBS_API_KEY not found in .env")
            return False

        url = f"{self.BASE_URL}/gaia/v1/oauth2/openapi/token"
        payload = {
            "apiKey": self.api_key,
            "otp": otp
        }
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                token = data.get("token") or data.get("accessToken")
                if token:
                    self._save_token_to_file(token)
                    logger.info("Successfully obtained TCBS Token.")
                    return True
            logger.error(f"Failed to fetch TCBS Token: {response.text}")
        except Exception as e:
            logger.error(f"Error fetching TCBS Token: {e}")
        return False

    def get_ticker_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetches latest snapshot for a symbol"""
        if not self.token:
            logger.warning("No TCBS Token. Call fetch_token_with_otp first.")
            return None

        url = f"{self.BASE_URL}/tartarus/v1/tickerCommons"
        params = {"tickers": symbol.upper()}
        
        try:
            response = requests.get(url, params=params, headers=self.get_headers())
            if response.status_code == 200:
                data = response.json()
                if data.get("data") and len(data["data"]) > 0:
                    return data["data"][0]
        except Exception as e:
            logger.error(f"Error fetching TCBS ticker info for {symbol}: {e}")
        return None

    def get_history(self, symbol: str, resolution: str = 'D', count_back: int = 200) -> Optional[Any]:
        """Fetches historical OHLCV bars for charts/indicators"""
        # public API, no token needed usually, or uses guest token
        url = "https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term"
        
        params = {
            "ticker": symbol.upper(),
            "type": "stock",
            "resolution": resolution,
            "countBack": count_back
        }
        
        try:
            # Try with token if available, else public
            headers = self.get_headers() if self.token else {}
            response = requests.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data and len(data['data']) > 0:
                    import pandas as pd
                    # API returns list of dicts: open, high, low, close, volume, tradingDate...
                    df = pd.DataFrame(data['data'])
                    
                    # Renaissance logic for dataframe adjustment
                    # Rename columns to match YF format: Open, High, Low, Close, Volume
                    rename_map = {
                        'open': 'Open', 'high': 'High', 'low': 'Low', 
                        'close': 'Close', 'volume': 'Volume', 
                        'tradingDate': 'Date'
                    }
                    df.rename(columns=rename_map, inplace=True)
                    
                    # Convert Date
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                    
                    return df.sort_index()
        except Exception as e:
            logger.error(f"Error fetching bar history for {symbol}: {e}")
            
        return None

tcbs_service = TCBSService()
