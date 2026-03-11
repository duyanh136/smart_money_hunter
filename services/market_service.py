import yfinance as yf
import pandas as pd
import logging
from typing import Optional, Dict, Any
import time

from services.tcbs_service import tcbs_service
from services.tcbs_socket import tcbs_stream

logger = logging.getLogger(__name__)

class MarketService:
    _cache = {}
    _cache_expiry = 60 # seconds

    @staticmethod
    def get_history(symbol: str, period: str = "6mo", interval: str = "1d") -> Optional[pd.DataFrame]:
        """Fetch historical data. Tries TCBS (REST) first, then yfinance."""
        symbol = symbol.upper()
        now = time.time()
        
        # Helper to map period to count_back (trading days)
        period_map = {
            '1d': 2, '5d': 5, '1mo': 25, '3mo': 65, '6mo': 130, 
            '1y': 260, '2y': 520, 'ytd': 260, 'max': 1000
        }
        count_back = period_map.get(period, 260)
        
        # 1. Try TCBS Service (for stocks)
        # Skip for indices like ^VNINDEX which TCBS might not have standardized
        if not symbol.startswith('^'):
            resolution = 'D' if interval in ['1d', '1wk', '1mo'] else '1'
            df = tcbs_service.get_history(symbol, resolution=resolution, count_back=count_back)
            if df is not None and not df.empty:
                return df
                
        # 2. Fallback to Yahoo Finance (Legacy logic)
        # Suffix trial list for Vietnamese stocks (Yahoo Finance uses varied suffixes)
        suffixes = []
        if len(symbol) == 3 and not ("-" in symbol):
            suffixes = [".VN", ".HN", ".SS", ".S", ".BS", ""] 
        else:
            suffixes = [""]

        # Try each suffix
        for suffix in suffixes:
            yf_symbol = f"{symbol}{suffix}" if suffix else symbol
            cache_key = f"{yf_symbol}_{period}_{interval}"
            
            # Check cache for this specific suffix
            if cache_key in MarketService._cache:
                data, timestamp = MarketService._cache[cache_key]
                if now - timestamp < MarketService._cache_expiry:
                    return data

            try:
                ticker = yf.Ticker(yf_symbol)
                hist = ticker.history(period=period, interval=interval)
                
                if not hist.empty:
                    # Cache it and return
                    MarketService._cache[cache_key] = (hist, now)
                    return hist
                    
                if len(symbol) == 3: break 
            except Exception:
                pass

        logger.warning(f"Final failure to fetch data for {symbol}")
        return None

    @staticmethod
    def get_latest_price(symbol: str) -> float:
        # 1. Try Socket Realtime (Local Collector Mode)
        p = tcbs_stream.get_price(symbol)
        if p: return p
            
        # 2. Try SQL Server (Vercel / Remote Mode)
        # If we are on Vercel or the local socket isn't running, check the DB
        import os
        from services.sql_utils import SQLUtils
        
        # Check if we are running in a cloud/serverless environment or socket is down
        if os.getenv("VERCEL") or not tcbs_stream.running:
            db_price = SQLUtils.get_price(symbol)
            if db_price:
                return db_price

        # 3. Fallback to History
        df = MarketService.get_history(symbol, period="5d")
        if df is not None and not df.empty:
            return df['Close'].iloc[-1]
        return 0.0

    @staticmethod
    def get_market_health() -> list:
        """
        Calculates VN-INDEX vs VN-INDEX (Excluding Vin Family).
        Market Health Check.
        """
        from services.sql_utils import SQLUtils
        cached = SQLUtils.get_cached_data('market_health')
        if cached: return cached

        try:
            # Fetch VN-INDEX and Vin Group
            indices = ['^VNINDEX', 'VIC.VN', 'VHM.VN', 'VRE.VN']
            # data = yf.download(indices, period="1mo", progress=False)['Close']
            # yf.download structure changed in recent versions, safer to use Tickers
            
            # Use cached or simple fetch
            end_date = pd.Timestamp.now()
            start_date = end_date - pd.Timedelta(days=30)
            
            data = yf.download(indices, start=start_date, end=end_date, progress=False)
            
            if data.empty:
                return {}
                
            # Handle MultiIndex columns if present (common in new yfinance)
            if isinstance(data.columns, pd.MultiIndex):
                try:
                    close_data = data['Close']
                except KeyError:
                    close_data = data
            else:
                close_data = data['Close'] if 'Close' in data else data

            if close_data.empty:
                 return {}

            # Approximate Weight of Vin Family (Dynamic would be better, but fixed for estimation)
            # Assuming Vin group affects ~10-15% of index points roughly or use price correlation
            # Simple approach: Reconstruct Index by subtracting weighted Vin prices (Not accurate but visual)
            
            vnindex = close_data['^VNINDEX']
            
            # Vin Basket
            # Check if columns exist
            vic = close_data['VIC.VN'] if 'VIC.VN' in close_data.columns else pd.Series(0, index=vnindex.index)
            vhm = close_data['VHM.VN'] if 'VHM.VN' in close_data.columns else pd.Series(0, index=vnindex.index)
            vre = close_data['VRE.VN'] if 'VRE.VN' in close_data.columns else pd.Series(0, index=vnindex.index)
            
            vin_basket = vic + vhm + vre
            
            # Let's return the series for charting
            result = []
            for date, val in vnindex.items():
                idx_val = val
                # Vin Total Price (associated with this date)
                try:
                    vin_val = vin_basket.loc[date]
                except:
                    vin_val = 0
                
                result.append({
                    'time': date.strftime('%Y-%m-%d'),
                    'vnindex': idx_val,
                    'vin_basket': vin_val
                })
                
                
            SQLUtils.set_cached_data('market_health', result, expiry_mins=30)
            return result

        except Exception as e:
            logger.error(f"Error calculating market health: {e}")
            return []

    @staticmethod
    def get_market_weather() -> Dict[str, Any]:
        """
        Determines 'Market Weather' (Sunny, Rainy, Storm).
        Based on:
        1. Index Trend (MA20)
        2. Liquidity (Vol)
        3. Leading Sectors (Banks, Oil, Tech)
        """
        from services.sql_utils import SQLUtils
        cached = SQLUtils.get_cached_data('market_weather')
        if cached: return cached

        try:
            # Mocking Interbank Interest Rate (Critical for 'Macro' view)
            # In real app, fetch from state bank website or specialized API
            interest_rate = 4.5 # Stable
            money_supply_status = "Bình Thường" 
            if interest_rate > 6.0: money_supply_status = "Thắt Chặt (Tiền Ít)"
            elif interest_rate < 3.0: money_supply_status = "Nới Lỏng (Tiền Rẻ)"
            
            # Fetch Index Data
            vnindex = MarketService.get_history("^VNINDEX", period="1mo")
            
            weather = "Mưa Rào (Sideway)"
            action = "Quan Sát / Mua Gom"
            bg_class = "weather-rainy" # css class
            
            if vnindex is not None and not vnindex.empty:
                last_price = vnindex['Close'].iloc[-1]
                sma20 = vnindex['Close'].rolling(window=20).mean().iloc[-1]
                
                # Simple Logic
                if last_price > sma20 * 1.01:
                    weather = "Nắng Đẹp (Uptrend)"
                    action = "Full Hàng / Margin"
                    bg_class = "weather-sunny"
                elif last_price < sma20 * 0.98:
                    weather = "Bão (Downtrend)"
                    action = "Cầm Tiền / Đi Chơi"
                    bg_class = "weather-storm"
            
            res = {
                "weather": weather,
                "action": action,
                "macro": f"Lãi suất NH: {interest_rate}% ({money_supply_status})",
                "class": bg_class
            }
            
            SQLUtils.set_cached_data('market_weather', res, expiry_mins=30)
            return res
        except Exception as e:
            logger.error(f"Error getting market weather: {e}")
            return {
                "weather": "Không xác định",
                "action": "N/A",
                "macro": "N/A",
                "class": "weather-rainy"
            }

    @staticmethod
    def get_top_leaders(limit: int = 5) -> list:
        # 1. Check if we already have today's leaders saved in SQL (Historical refined)
        today = datetime.now().date().strftime('%Y-%m-%d')
        cached_leaders = SQLUtils.get_top_leaders_history(today)
        if cached_leaders and len(cached_leaders) >= limit:
            logger.info("Returning refined top leaders from SQL.")
            return cached_leaders[:limit]
            
        # 2. Try the broader MarketAnalysis cache (Pre-computed)
        logger.info("Checking MarketAnalysis cache for leaders...")
        all_analysis = SQLUtils.get_all_market_analysis()
        if all_analysis:
            # Sort by LeaderScore descending
            sorted_leaders = sorted(all_analysis, key=lambda x: x.get('LeaderScore', 0), reverse=True)
            if sorted_leaders:
                # Map MarketAnalysis fields to TopLeaders format
                mapped_leaders = []
                for l in sorted_leaders[:limit]:
                    mapped_leaders.append({
                        'symbol': l['Symbol'],
                        'price': l['Price'],
                        'change': l['ChangePct'],
                        'score': l.get('LeaderScore', 0),
                        'is_shark_dominated': l.get('IsSharkDominated', False),
                        'is_storm_resistant': l.get('IsStormResistant', False),
                        'tag': l.get('ActionRecommendation', 'Theo dõi')
                    })
                logger.info(f"Returning {len(mapped_leaders)} leaders from MarketAnalysis cache.")
                return mapped_leaders

        # 3. Fallback to real-time scan (Last resort, slow)
        logger.warning("No cache found for leaders. Falling back to real-time scan...")
        leader_universe = SymbolLoader.get_liquid_stocks()
        
        results = []
        
        # Get SSI as proxy for VNINDEX to measure market sentiment/resistance
        idx_df = MarketService.get_history("SSI", period="3mo")
        
        def score_symbol(symbol):
            try:
                # Fetch recent history
                df = MarketService.get_history(symbol, period="6mo")
                if df is not None and not df.empty:
                    df = SmartMoneyAnalyzer.analyze(df)
                    score_data = SmartMoneyAnalyzer.calc_leader_score(df, index_df=idx_df)
                    score = score_data.get('score', 0)
                    
                    last_row = df.iloc[-1]
                    class_info = SmartMoneyAnalyzer.classify_stock(symbol)
                    
                    return {
                        'symbol': symbol,
                        'score': score,
                        'is_shark_dominated': score_data.get('is_shark_dominated', False),
                        'is_storm_resistant': score_data.get('is_storm_resistant', False),
                        'tag': class_info.get('tag', ''),
                        'price': last_row['Close'],
                        'change': round((last_row['Close'] - df.iloc[-2]['Close'])/df.iloc[-2]['Close'] * 100, 2),
                        'action': last_row.get('Action_Recommendation', 'N/A'),
                        'signal_buydip': bool(last_row.get('Signal_BuyDip', False) or last_row.get('Signal_VoTeo', False)),
                        'rsi': round(last_row.get('RSI', 50), 1)
                    }
            except Exception as e:
                logger.error(f"Error scoring {symbol}: {e}")
            return None

        # Process in parallel to speed up 100+ requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {executor.submit(score_symbol, sym): sym for sym in leader_universe}
            for future in concurrent.futures.as_completed(future_to_symbol):
                res = future.result()
                if res is not None:
                    results.append(res)
                
        # Sort by score descending and take top N
        results.sort(key=lambda x: x['score'], reverse=True)
        final_leaders = results[:limit]
        
        # Optional: Save to history automatically if it's during trading hours or end of day
        # For now, we just return it. The 16:00 job handles the persistent daily save.
        
        return final_leaders

    @staticmethod
    def run_full_market_scan():
        """
        Scans all major stocks and saves pre-computed analysis to SQL Server.
        This allows the web UI to load nearly instantly.
        """
        from services.symbol_loader import SymbolLoader
        from services.smart_money import SmartMoneyAnalyzer
        from services.sql_utils import SQLUtils
        import concurrent.futures
        
        # Get all liquid stocks
        universe = SymbolLoader.get_liquid_stocks()
        logger.info(f"Starting full market scan for {len(universe)} symbols...")
        
        # Get proxy for Index Correlation
        idx_df = MarketService.get_history("SSI", period="3mo")
        
        results = []
        
        def analyze_sym(symbol):
            try:
                df = MarketService.get_history(symbol, period="6mo")
                if df is not None and not df.empty:
                    df = SmartMoneyAnalyzer.analyze(df)
                    if df is not None and not df.empty:
                        last_row = df.iloc[-1]
                        score_data = SmartMoneyAnalyzer.calc_leader_score(df, index_df=idx_df)
                        
                        return {
                            'symbol': symbol,
                            'price': last_row['Close'],
                            'change': round((last_row['Close'] - df.iloc[-2]['Close'])/df.iloc[-2]['Close'] * 100, 2),
                            'vol_ratio': round(last_row.get('Vol_Ratio', 0), 2),
                            'rsi': round(last_row.get('RSI', 50), 1),
                            'market_phase': df['Market_Phase'].iloc[-1],
                            'action': df['Action_Recommendation'].iloc[-1],
                            'signal_voteo': bool(last_row.get('Signal_VoTeo')),
                            'signal_buydip': bool(last_row.get('Signal_BuyDip')),
                            'signal_super': bool(last_row.get('Signal_Super')),
                            'signal_breakout': bool(last_row.get('Signal_Breakout')),
                            'signal_squeeze': bool(last_row.get('Signal_Squeeze')),
                            'signal_distribution': bool(last_row.get('Signal_Distribution')),
                            'signal_upbo': bool(last_row.get('Signal_Upbo')),
                            'signal_goldensell': bool(last_row.get('Signal_GoldenSell')),
                            'signal_bigmoney': bool(last_row.get('Signal_BigMoney')),
                            'radar_panicsell': bool(last_row.get('Signal_PanicSell')),
                            'radar_phankyam': bool(last_row.get('Signal_PhanKyAmMACD')),
                            'radar_sangtay': bool(last_row.get('Signal_SangTayNhoLe')),
                            'radar_daodong': bool(last_row.get('Signal_DaoDongLongLeo')),
                            'radar_gaynen': bool(last_row.get('Signal_GayNenTestLai')),
                            'radar_chammay': bool(last_row.get('Signal_ChamMayKenhDuoi')),
                            'pyramid_action': SmartMoneyAnalyzer.get_pyramid_sizing(df),
                            'base_distance_pct': df['Base_Distance_Pct'].iloc[-1] if 'Base_Distance_Pct' in df else 0,
                            'score': score_data.get('score', 0),
                            'is_shark_dominated': bool(score_data.get('is_shark_dominated', False)),
                            'is_storm_resistant': bool(score_data.get('is_storm_resistant', False)),
                            'buy_signal_status': SmartMoneyAnalyzer.get_buy_signal_status(df)
                        }
            except Exception as e:
                logger.error(f"Error analyzing {symbol} during full scan: {e}")
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_symbol = {executor.submit(analyze_sym, sym): sym for sym in universe}
            for future in concurrent.futures.as_completed(future_to_symbol):
                res = future.result()
                if res:
                    # Additional call to get the Vietnamese signal status
                    try:
                        # We need the dataframe again or we should have returned it from analyze_sym
                        # Let's optimize: analyze_sym already has the df.
                        # I'll update analyze_sym to include buy_signal_status
                        pass
                    except: pass
                    results.append(res)

        # Ranking logic: Sort by score descending
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        for i, res in enumerate(results):
            res['rank'] = i + 1 if i < 10 else None # Only rank top 10
            
        # Save to database
        if results:
            SQLUtils.save_market_analysis(results)
            logger.info(f"Full market scan complete. Saved {len(results)} results with rankings.")
        return results
