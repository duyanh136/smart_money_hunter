import os
import logging
from datetime import datetime
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
    def save_market_analysis(analysis_data: List[Dict[str, Any]]):
        """Saves analysis results for multiple symbols."""
        conn = SQLUtils.get_connection()
        if not conn: return
        
        p = SQLUtils._get_placeholder(conn)
        
        sql_update = f"""
            UPDATE MarketAnalysis SET 
                Price = {p}, ChangePct = {p}, VolRatio = {p}, RSI = {p}, 
                MarketPhase = {p}, ActionRecommendation = {p},
                SignalVoTeo = {p}, SignalBuyDip = {p}, SignalBreakout = {p}, 
                SignalGoldenSell = {p}, SignalWarning = {p},
                RadarPanicSell = {p}, RadarPhanKyAm = {p}, RadarSangTay = {p}, 
                RadarDaoDong = {p}, RadarGayNen = {p}, RadarChamMay = {p},
                PyramidAction = {p}, BaseDistancePct = {p}, 
                LeaderScore = {p}, IsSharkDominated = {p}, IsStormResistant = {p},
                Rank = {p}, BuySignalStatus = {p}, Tag = {p},
                UpdatedAt = GETDATE()
            WHERE Symbol = {p}
        """
        
        sql_insert = f"""
            INSERT INTO MarketAnalysis (
                Symbol, Price, ChangePct, VolRatio, RSI, MarketPhase, ActionRecommendation,
                SignalVoTeo, SignalBuyDip, SignalBreakout, SignalGoldenSell, SignalWarning,
                RadarPanicSell, RadarPhanKyAm, RadarSangTay, RadarDaoDong, 
                RadarGayNen, RadarChamMay, PyramidAction, BaseDistancePct,
                LeaderScore, IsSharkDominated, IsStormResistant,
                Rank, BuySignalStatus, Tag, UpdatedAt
            ) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, GETDATE())
        """
        
        try:
            cursor = conn.cursor()
            for row in analysis_data:
                sym = row.get('symbol', '').upper()
                if not sym: continue
                
                # Mapping fields to match internal naming
                vals = (
                    row.get('price', 0), row.get('change', 0), row.get('vol_ratio', 0), row.get('rsi', 0),
                    row.get('market_phase', ''), row.get('action', ''),
                    row.get('signal_voteo', False), row.get('signal_buydip', False), row.get('signal_breakout', False),
                    row.get('signal_goldensell', False), row.get('signal_warning', False),
                    row.get('radar_panicsell', False), row.get('radar_phankyam', False),
                    row.get('radar_sangtay', False), row.get('radar_daodong', False),
                    row.get('radar_gaynen', False), row.get('radar_chammay', False),
                    row.get('pyramid_action', ''), row.get('base_distance_pct', 0),
                    row.get('leader_score', row.get('score', 0)), 
                    row.get('is_shark_dominated', False), row.get('is_storm_resistant', False),
                    row.get('rank'), row.get('buy_signal_status', 'QUAN SÁT'),
                    row.get('tag', '')
                )
                
                cursor.execute(sql_update, vals + (sym,))
                if cursor.rowcount == 0:
                    cursor.execute(sql_insert, (sym,) + vals)
            
            if not getattr(conn, 'autocommit', False):
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving market analysis: {e}")
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
    def get_analysis_by_symbol(symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieves latest market analysis for a specific symbol."""
        conn = SQLUtils.get_connection()
        if not conn: return None
        
        p = SQLUtils._get_placeholder(conn)
        sql = f"SELECT * FROM MarketAnalysis WHERE Symbol = {p}"
        
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (symbol.upper(),))
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
            if row:
                return dict(zip(columns, row))
        except Exception as e:
            logger.error(f"Error fetching analysis for {symbol}: {e}")
        finally:
            conn.close()
        return None

    @staticmethod
    def get_all_market_analysis() -> List[Dict[str, Any]]:
        """Retrieves all market analysis records from the database."""
        conn = SQLUtils.get_connection()
        if not conn: return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM MarketAnalysis")
            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            logger.error(f"Error fetching all market analysis: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def save_market_analysis_to_history(analysis_data: List[Dict[str, Any]], date_str: str = None):
        """Saves a snapshot of market analysis to the history table."""
        conn = SQLUtils.get_connection()
        if not conn: return
        
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')
            
        p = SQLUtils._get_placeholder(conn)
        sql_insert = f"""
            INSERT INTO MarketAnalysisHistory (
                Symbol, AnalysisDate, Price, ChangePct, VolRatio, RSI, MarketPhase, ActionRecommendation,
                LeaderScore, Rank, BuySignalStatus, IsSharkDominated, IsStormResistant,
                SignalVoTeo, SignalBuyDip, SignalBreakout, SignalGoldenSell, SignalWarning,
                RadarPanicSell, RadarPhanKyAm, RadarSangTay, RadarDaoDong, 
                RadarGayNen, RadarChamMay, CreatedAt
            ) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, GETDATE())
        """
        
        try:
            cursor = conn.cursor()
            for row in analysis_data:
                sym = row.get('symbol', '').upper()
                if not sym: continue
                
                # Avoid duplicates for the same day
                cursor.execute(f"DELETE FROM MarketAnalysisHistory WHERE Symbol = {p} AND AnalysisDate = {p}", (sym, date_str))
                
                vals = (
                    sym, date_str,
                    row.get('price', 0), row.get('change', 0), row.get('vol_ratio', 0), row.get('rsi', 0),
                    row.get('market_phase', ''), row.get('action', ''),
                    row.get('leader_score', row.get('score', 0)), row.get('rank'), row.get('buy_signal_status', 'QUAN SÁT'),
                    row.get('is_shark_dominated', False), row.get('is_storm_resistant', False),
                    row.get('signal_voteo', False), row.get('signal_buydip', False), 
                    row.get('signal_breakout', False), row.get('signal_goldensell', False), row.get('signal_warning', False),
                    row.get('radar_panicsell', False), row.get('radar_phankyam', False),
                    row.get('radar_sangtay', False), row.get('radar_daodong', False),
                    row.get('radar_gaynen', False), row.get('radar_chammay', False)
                )
                cursor.execute(sql_insert, vals)
            
            if not getattr(conn, 'autocommit', False):
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_top_leaders_history(date_str: str) -> List[Dict[str, Any]]:
        """Retrieves top leaders for a specific date from SQL History."""
        conn = SQLUtils.get_connection()
        if not conn: return []
        
        p = SQLUtils._get_placeholder(conn)
        sql = f"""
            SELECT Symbol, Price, ChangePct, VolRatio, RSI, MarketPhase, ActionRecommendation,
                   LeaderScore, Rank, BuySignalStatus, IsSharkDominated, IsStormResistant
            FROM MarketAnalysisHistory
            WHERE AnalysisDate = {p}
            ORDER BY Rank ASC
        """
        
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (date_str,))
            columns = [column[0] for column in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            # Map SQL names back to frontend expected names if different
            mapped_results = []
            for r in results:
                mapped_results.append({
                    'symbol': r['Symbol'],
                    'price': float(r['Price']),
                    'change': float(r['ChangePct']),
                    'vol_ratio': float(r['VolRatio']),
                    'rsi': float(r['RSI']),
                    'market_phase': r['MarketPhase'],
                    'action': r['ActionRecommendation'],
                    'score': int(r['LeaderScore']),
                    'rank': int(r['Rank']),
                    'buy_signal_status': r['BuySignalStatus'],
                    'is_shark_dominated': bool(r['IsSharkDominated']),
                    'is_storm_resistant': bool(r['IsStormResistant']),
                })
            return mapped_results
        except Exception as e:
            logger.error(f"Error fetching historical leaders for {date_str}: {e}")
            return []
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
    def get_available_history_dates() -> List[str]:
        """Retrieves list of dates that have historical analysis records."""
        conn = SQLUtils.get_connection()
        if not conn: return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT AnalysisDate FROM MarketAnalysisHistory ORDER BY AnalysisDate DESC")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching history dates: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def set_cached_data(key: str, data: Any, expiry_mins: int = 60):
        """Saves arbitrary JSON-serializable data to SystemCache."""
        conn = SQLUtils.get_connection()
        if not conn: return
        
        import json
        from datetime import timedelta
        p = SQLUtils._get_placeholder(conn)
        
        val_str = json.dumps(data)
        expiry_time = datetime.now() + timedelta(minutes=expiry_mins)
        
        sql = f"""
        IF EXISTS (SELECT 1 FROM SystemCache WHERE CacheKey = {p})
            UPDATE SystemCache SET CacheValue = {p}, ExpiryTime = {p}, UpdatedAt = GETDATE() WHERE CacheKey = {p}
        ELSE
            INSERT INTO SystemCache (CacheKey, CacheValue, ExpiryTime, UpdatedAt) VALUES ({p}, {p}, {p}, GETDATE())
        """
        
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (key, val_str, expiry_time, key, key, val_str, expiry_time))
            if not getattr(conn, 'autocommit', False):
                conn.commit()
        except Exception as e:
            logger.error(f"Error setting cache for {key}: {e}")
        finally:
            conn.close()

    @staticmethod
    def get_cached_data(key: str) -> Optional[Any]:
        """Retrieves data from SystemCache if not expired."""
        conn = SQLUtils.get_connection()
        if not conn: return None
        
        import json
        p = SQLUtils._get_placeholder(conn)
        sql = f"SELECT CacheValue, ExpiryTime FROM SystemCache WHERE CacheKey = {p}"
        
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (key,))
            row = cursor.fetchone()
            if row:
                val_str, expiry_time = row
                if expiry_time > datetime.now():
                    return json.loads(val_str)
        except Exception as e:
            logger.error(f"Error getting cache for {key}: {e}")
        finally:
            conn.close()
        return None
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
