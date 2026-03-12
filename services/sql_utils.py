import os
import logging
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

load_dotenv()
logger = logging.getLogger(__name__)

class SQLUtils:
    @staticmethod
    def get_connection():
        # Vercel / Serverless Environment detect
        is_serverless = os.getenv('VERCEL') == '1' or os.getenv('AWS_LAMBDA_FUNCTION_NAME')
        
        try:
            if is_serverless:
                # Use pymssql for serverless (No ODBC driver required)
                import pymssql
                return pymssql.connect(
                    server=os.getenv('SQL_SERVER'),
                    user=os.getenv('SQL_USER'),
                    password=os.getenv('SQL_PASSWORD'),
                    database=os.getenv('SQL_DATABASE'),
                    timeout=5,
                    login_timeout=5,
                    autocommit=True
                )
            else:
                # Local development - prefer pyodbc if driver exists
                try:
                    import pyodbc
                    conn_str = (
                        f"DRIVER={os.getenv('SQL_DRIVER', '{ODBC Driver 17 for SQL Server}')};"
                        f"SERVER={os.getenv('SQL_SERVER')};"
                        f"DATABASE={os.getenv('SQL_DATABASE')};"
                        f"UID={os.getenv('SQL_USER')};"
                        f"PWD={os.getenv('SQL_PASSWORD')};"
                        "TrustServerCertificate=yes;"
                    )
                    return pyodbc.connect(conn_str, timeout=5)
                except (ImportError, Exception) as pyodbc_err:
                    logger.warning(f"pyodbc failed or missing, falling back to pymssql: {pyodbc_err}")
                    import pymssql
                    server = os.getenv('SQL_SERVER')
                    return pymssql.connect(
                        server=server,
                        user=os.getenv('SQL_USER'),
                        password=os.getenv('SQL_PASSWORD'),
                        database=os.getenv('SQL_DATABASE'),
                        autocommit=True
                    )
        except Exception as e:
            logger.error(f"SQL Connection Error: {e}")
            return None

    @staticmethod
    def _get_placeholder(conn):
        # Detect if it's pymssql or pyodbc
        try:
            import pymssql
            if isinstance(conn, pymssql.Connection):
                return "%s"
        except ImportError:
            pass
        return "?"

    @staticmethod
    def upsert_price(symbol: str, price: float, volume: float):
        conn = SQLUtils.get_connection()
        if not conn: return
        
        p = SQLUtils._get_placeholder(conn)
        sql = f"""
        IF EXISTS (SELECT 1 FROM RealtimePrices WHERE Symbol = {p})
            UPDATE RealtimePrices SET Price = {p}, Volume = {p}, LastUpdated = GETDATE() WHERE Symbol = {p}
        ELSE
            INSERT INTO RealtimePrices (Symbol, Price, Volume, LastUpdated) VALUES ({p}, {p}, {p}, GETDATE())
        """
        
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (symbol, price, volume, symbol, symbol, price, volume))
            if not getattr(conn, 'autocommit', False):
                conn.commit()
        except Exception as e:
            logger.error(f"Error upserting price for {symbol}: {e}")
        finally:
            conn.close()

    @staticmethod
    def get_latest_prices() -> Dict[str, float]:
        """Returns a mapping of Symbol -> Latest Price"""
        prices = {}
        conn = SQLUtils.get_connection()
        if not conn: return prices
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT Symbol, Price FROM RealtimePrices")
            for row in cursor.fetchall():
                prices[row[0]] = row[1]
        except Exception as e:
            logger.error(f"Error fetching latest prices: {e}")
        finally:
            conn.close()
        return prices

    @staticmethod
    def get_price(symbol: str) -> Optional[float]:
        conn = SQLUtils.get_connection()
        if not conn: return None
        
        p = SQLUtils._get_placeholder(conn)
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT Price FROM RealtimePrices WHERE Symbol = {p}", (symbol.upper(),))
            row = cursor.fetchone()
            if row:
                return row[0]
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
        finally:
            conn.close()
        return None
    @staticmethod
    def save_market_analysis(data: Dict[str, Any]):
        conn = SQLUtils.get_connection()
        if not conn: return
        
        p = SQLUtils._get_placeholder(conn)
        sql = f"""
        IF EXISTS (SELECT 1 FROM MarketAnalysis WHERE Symbol = {p})
            UPDATE MarketAnalysis SET 
                Price = {p}, [Change] = {p}, VolRatio = {p}, RSI = {p}, 
                MarketPhase = {p}, [Action] = {p}, LeaderScore = {p}, 
                IsSharkDominated = {p}, IsStormResistant = {p}, Tag = {p},
                SignalVoTeo = {p}, SignalBuyDip = {p}, SignalBreakout = {p}, 
                SignalGoldenSell = {p}, SignalWarning = {p}, RadarPanicSell = {p}, 
                RadarSangTay = {p}, RadarGayNen = {p}, RadarPhanKyAm = {p}, 
                RadarDaoDong = {p}, RadarChamMay = {p}, PyramidAction = {p}, 
                BaseDistancePct = {p}, LastUpdated = GETDATE() 
            WHERE Symbol = {p}
        ELSE
            INSERT INTO MarketAnalysis (
                Symbol, Price, [Change], VolRatio, RSI, MarketPhase, [Action], 
                LeaderScore, IsSharkDominated, IsStormResistant, Tag,
                SignalVoTeo, SignalBuyDip, SignalBreakout, SignalGoldenSell, 
                SignalWarning, RadarPanicSell, RadarSangTay, RadarGayNen, 
                RadarPhanKyAm, RadarDaoDong, RadarChamMay, PyramidAction, 
                BaseDistancePct, LastUpdated
            ) VALUES (
                {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, 
                {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, GETDATE()
            )
        """
        
        args = (
            data['symbol'], data['price'], data['change'], data['vol_ratio'], data['rsi'],
            data['market_phase'], data['action'], data['leader_score'],
            1 if data['is_shark_dominated'] else 0, 1 if data['is_storm_resistant'] else 0, data['tag'],
            1 if data['signal_voteo'] else 0, 1 if data['signal_buydip'] else 0, 1 if data['signal_breakout'] else 0,
            1 if data['signal_goldensell'] else 0, 1 if data['signal_warning'] else 0, 1 if data['radar_panicsell'] else 0,
            1 if data['radar_sangtay'] else 0, 1 if data['radar_gaynen'] else 0, 1 if data['radar_phankyam'] else 0,
            1 if data['radar_daodong'] else 0, 1 if data['radar_chammay'] else 0, data['pyramid_action'],
            data['base_distance_pct'], data['symbol'], # Update params
            data['symbol'], data['price'], data['change'], data['vol_ratio'], data['rsi'],
            data['market_phase'], data['action'], data['leader_score'],
            1 if data['is_shark_dominated'] else 0, 1 if data['is_storm_resistant'] else 0, data['tag'],
            1 if data['signal_voteo'] else 0, 1 if data['signal_buydip'] else 0, 1 if data['signal_breakout'] else 0,
            1 if data['signal_goldensell'] else 0, 1 if data['signal_warning'] else 0, 1 if data['radar_panicsell'] else 0,
            1 if data['radar_sangtay'] else 0, 1 if data['radar_gaynen'] else 0, 1 if data['radar_phankyam'] else 0,
            1 if data['radar_daodong'] else 0, 1 if data['radar_chammay'] else 0, data['pyramid_action'],
            data['base_distance_pct'] # Insert params
        )
        
        try:
            cursor = conn.cursor()
            cursor.execute(sql, args)
            if not getattr(conn, 'autocommit', False):
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving market analysis for {data['symbol']}: {e}")
        finally:
            conn.close()

    @staticmethod
    def save_analysis_history(data: Dict[str, Any]):
        conn = SQLUtils.get_connection()
        if not conn: return
        
        p = SQLUtils._get_placeholder(conn)
        sql = f"""
        INSERT INTO MarketAnalysisHistory (
            Symbol, Price, [Change], VolRatio, RSI, MarketPhase, [Action], 
            LeaderScore, IsSharkDominated, IsStormResistant,
            SignalVoTeo, SignalBuyDip, SignalBreakout, SignalGoldenSell, 
            SignalWarning, AnalysisDate
        ) VALUES (
            {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, GETDATE()
        )
        """
        
        args = (
            data['symbol'], data['price'], data['change'], data['vol_ratio'], data['rsi'],
            data['market_phase'], data['action'], data['leader_score'],
            1 if data['is_shark_dominated'] else 0, 1 if data['is_storm_resistant'] else 0,
            1 if data['signal_voteo'] else 0, 1 if data['signal_buydip'] else 0, 1 if data['signal_breakout'] else 0,
            1 if data['signal_goldensell'] else 0, 1 if data['signal_warning'] else 0
        )
        
        try:
            cursor = conn.cursor()
            cursor.execute(sql, args)
            if not getattr(conn, 'autocommit', False):
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving analysis history for {data['symbol']}: {e}")
        finally:
            conn.close()
