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
    def save_top_leaders_history(leaders_list: List[Dict[str, Any]]):
        """Saves a list of top leaders for the current day."""
        conn = SQLUtils.get_connection()
        if not conn: return
        
        p = SQLUtils._get_placeholder(conn)
        today = datetime.now().date().strftime('%Y-%m-%d')
        
        # SQL for deleting existing records for today to avoid duplicates if re-run
        delete_sql = f"DELETE FROM TopLeadersHistory WHERE ScanDate = {p}"
        # SQL for inserting new record
        insert_sql = f"""
        INSERT INTO TopLeadersHistory (ScanDate, Rank, Symbol, Score, Price, ChangePct, Signals)
        VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p})
        """
        
        try:
            cursor = conn.cursor()
            # Delete old records
            cursor.execute(delete_sql, (today,))
            
            # Insert new ones
            for i, leader in enumerate(leaders_list):
                rank = i + 1
                symbol = leader.get('symbol', '')
                score = leader.get('score', 0)
                price = leader.get('price', 0)
                change = leader.get('change', 0)
                # Combine signals into a string
                signals_list = []
                if leader.get('is_shark_dominated'): signals_list.append("Shark")
                if leader.get('is_storm_resistant'): signals_list.append("Storm")
                if leader.get('signal_buydip'): signals_list.append("BuyDip")
                
                cursor.execute(insert_sql, (
                    today, rank, symbol, score, price, change, ", ".join(signals_list)
                ))
            
            if not getattr(conn, 'autocommit', False):
                conn.commit()
            logger.info(f"Saved {len(leaders_list)} top leaders for {today}")
        except Exception as e:
            logger.error(f"Error saving top leaders history: {e}")
        finally:
            conn.close()

    @staticmethod
    def get_top_leaders_history(date_str: str) -> List[Dict[str, Any]]:
        """Retrieves top leaders for a specific date."""
        results = []
        conn = SQLUtils.get_connection()
        if not conn: return results
        
        p = SQLUtils._get_placeholder(conn)
        # Fix query placeholder logic
        sql = f"SELECT [Rank], [Symbol], [Score], [Price], [ChangePct], [Signals] FROM TopLeadersHistory WHERE ScanDate = {p} ORDER BY [Rank] ASC"
            
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (date_str,))
            for row in cursor.fetchall():
                results.append({
                    "rank": row[0],
                    "symbol": row[1],
                    "score": row[2],
                    "price": row[3],
                    "change": row[4],
                    "signals": row[5]
                })
        except Exception as e:
            logger.error(f"Error fetching top leaders history for {date_str}: {e}")
        finally:
            conn.close()
        return results
