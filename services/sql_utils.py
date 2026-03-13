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
    def init_analysis_tables():
        conn = SQLUtils.get_connection()
        if not conn: return
        
        sql = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='MarketAnalysis' AND xtype='U')
        CREATE TABLE MarketAnalysis (
            Symbol VARCHAR(20) PRIMARY KEY,
            Price FLOAT,
            ChangePct FLOAT,
            VolRatio FLOAT,
            RSI FLOAT,
            Score FLOAT,
            MarketPhase NVARCHAR(MAX),
            ActionRecommendation NVARCHAR(MAX),
            PyramidAction NVARCHAR(MAX),
            BuySignalStatus NVARCHAR(MAX),
            Tag NVARCHAR(MAX),
            BaseDistancePct FLOAT,
            IsSharkDominated BIT,
            IsStormResistant BIT,
            SignalVoTeo BIT,
            SignalBuyDip BIT,
            SignalBreakout BIT,
            SignalGoldenSell BIT,
            SignalWarning BIT,
            RadarPanicSell BIT,
            RadarSangTay BIT,
            RadarGayNen BIT,
            RadarPhanKyAm BIT,
            RadarDaoDong BIT,
            RadarChamMay BIT,
            UpdatedAt DATETIME DEFAULT GETDATE()
        );

        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='MarketAnalysisHistory' AND xtype='U')
        CREATE TABLE MarketAnalysisHistory (
            Symbol VARCHAR(20),
            AnalysisDate DATE,
            Price FLOAT,
            ChangePct FLOAT,
            VolRatio FLOAT,
            RSI FLOAT,
            Score FLOAT,
            MarketPhase NVARCHAR(MAX),
            ActionRecommendation NVARCHAR(MAX),
            PyramidAction NVARCHAR(MAX),
            BuySignalStatus NVARCHAR(MAX),
            Tag NVARCHAR(MAX),
            BaseDistancePct FLOAT,
            IsSharkDominated BIT,
            IsStormResistant BIT,
            SignalVoTeo BIT,
            SignalBuyDip BIT,
            SignalBreakout BIT,
            SignalGoldenSell BIT,
            SignalWarning BIT,
            RadarPanicSell BIT,
            RadarSangTay BIT,
            RadarGayNen BIT,
            RadarPhanKyAm BIT,
            RadarDaoDong BIT,
            RadarChamMay BIT,
            UpdatedAt DATETIME,
            PRIMARY KEY (Symbol, AnalysisDate)
        );
        """
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            if not getattr(conn, 'autocommit', False):
                conn.commit()
        except Exception as e:
            logger.error(f"Error initializing analysis tables: {e}")
        finally:
            conn.close()

    @staticmethod
    def upsert_market_analysis(data_list: List[Dict[str, Any]]):
        if not data_list: return
        
        # 1. Archive old data if day changed
        SQLUtils.archive_market_analysis()
        
        conn = SQLUtils.get_connection()
        if not conn: return
        
        p = SQLUtils._get_placeholder(conn)
        
        # Mapping frontend/service keys to DB columns
        keys_map = {
            'symbol': 'Symbol', 'price': 'Price', 'change': 'ChangePct', 'vol_ratio': 'VolRatio',
            'rsi': 'RSI', 'score': 'Score', 'market_phase': 'MarketPhase',
            'action': 'ActionRecommendation', 'pyramid_action': 'PyramidAction',
            'buy_signal_status': 'BuySignalStatus', 'tag': 'Tag',
            'base_distance_pct': 'BaseDistancePct', 'is_shark_dominated': 'IsSharkDominated',
            'is_storm_resistant': 'IsStormResistant', 'signal_voteo': 'SignalVoTeo',
            'signal_buydip': 'SignalBuyDip', 'signal_breakout': 'SignalBreakout',
            'signal_goldensell': 'SignalGoldenSell', 'signal_warning': 'SignalWarning',
            'radar_panicsell': 'RadarPanicSell', 'radar_sangtay': 'RadarSangTay',
            'radar_gaynen': 'RadarGayNen', 'radar_phankyam': 'RadarPhanKyAm',
            'radar_daodong': 'RadarDaoDong', 'radar_chammay': 'RadarChamMay'
        }
        
        fields = list(keys_map.values())
        columns_str = ", ".join(fields) + ", UpdatedAt"
        placeholders_str = ", ".join([p] * len(fields)) + ", GETDATE()"
        update_str = ", ".join([f"{col} = {p}" for col in fields]) + ", UpdatedAt = GETDATE()"
        
        try:
            cursor = conn.cursor()
            for item in data_list:
                # Extract values in order of fields
                vals = []
                for k in keys_map.keys():
                    val = item.get(k)
                    # Convert Booleans to Win BIT (0/1) if needed, but pyodbc/pymssql usually handle it
                    vals.append(val)
                
                # Check exist
                check_sql = f"SELECT 1 FROM MarketAnalysis WHERE Symbol = {p}"
                cursor.execute(check_sql, (item['symbol'],))
                exists = cursor.fetchone()
                
                if exists:
                    up_sql = f"UPDATE MarketAnalysis SET {update_str} WHERE Symbol = {p}"
                    cursor.execute(up_sql, (*vals, item['symbol']))
                else:
                    in_sql = f"INSERT INTO MarketAnalysis ({columns_str}) VALUES ({placeholders_str})"
                    cursor.execute(in_sql, tuple(vals))
            
            if not getattr(conn, 'autocommit', False):
                conn.commit()
        except Exception as e:
            logger.error(f"Error upserting market analysis: {e}")
        finally:
            conn.close()

    @staticmethod
    def archive_market_analysis():
        """Moves data to history if day changed"""
        conn = SQLUtils.get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            
            # Check if there is data from a previous day
            cursor.execute("SELECT TOP 1 CAST(UpdatedAt AS DATE) FROM MarketAnalysis")
            row = cursor.fetchone()
            if not row: return # Empty table, nothing to archive
            
            last_saved_date = row[0]
            from datetime import date
            today = date.today()
            
            if last_saved_date < today:
                logger.info(f"Day transition detected: {last_saved_date} -> {today}. Archiving MarketAnalysis...")
                
                # Move to history
                # We use a join or similar? Or simple INSERT INTO ... SELECT
                move_sql = """
                INSERT INTO MarketAnalysisHistory (
                    Symbol, AnalysisDate, Price, ChangePct, VolRatio, RSI, Score, 
                    MarketPhase, ActionRecommendation, PyramidAction, BuySignalStatus, Tag, 
                    BaseDistancePct, IsSharkDominated, IsStormResistant, 
                    SignalVoTeo, SignalBuyDip, SignalBreakout, SignalGoldenSell, SignalWarning, 
                    RadarPanicSell, RadarSangTay, RadarGayNen, RadarPhanKyAm, RadarDaoDong, RadarChamMay, 
                    UpdatedAt
                )
                SELECT 
                    Symbol, CAST(UpdatedAt AS DATE), Price, ChangePct, VolRatio, RSI, Score, 
                    MarketPhase, ActionRecommendation, PyramidAction, BuySignalStatus, Tag, 
                    BaseDistancePct, IsSharkDominated, IsStormResistant, 
                    SignalVoTeo, SignalBuyDip, SignalBreakout, SignalGoldenSell, SignalWarning, 
                    RadarPanicSell, RadarSangTay, RadarGayNen, RadarPhanKyAm, RadarDaoDong, RadarChamMay, 
                    UpdatedAt
                FROM MarketAnalysis
                WHERE Symbol NOT IN (
                    SELECT Symbol FROM MarketAnalysisHistory WHERE AnalysisDate = CAST(MarketAnalysis.UpdatedAt AS DATE)
                )
                """
                cursor.execute(move_sql)
                
                # Clear current
                cursor.execute("DELETE FROM MarketAnalysis")
                
                if not getattr(conn, 'autocommit', False):
                    conn.commit()
                logger.info("MarketAnalysis archived and reset successfully.")
                
        except Exception as e:
            logger.error(f"Error archiving market analysis: {e}")
        finally:
            conn.close()
