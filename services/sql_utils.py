import pyodbc
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
        is_serverless = os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME')
        
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
                    conn_str = (
                        f"DRIVER={os.getenv('SQL_DRIVER', '{ODBC Driver 17 for SQL Server}')};"
                        f"SERVER={os.getenv('SQL_SERVER')};"
                        f"DATABASE={os.getenv('SQL_DATABASE')};"
                        f"UID={os.getenv('SQL_USER')};"
                        f"PWD={os.getenv('SQL_PASSWORD')};"
                        "TrustServerCertificate=yes;"
                    )
                    return pyodbc.connect(conn_str, timeout=5)
                except Exception as pyodbc_err:
                    logger.warning(f"pyodbc failed, falling back to pymssql: {pyodbc_err}")
                    import pymssql
                    # pymssql server format can be server\instance or server:port
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
    def upsert_price(symbol: str, price: float, volume: float):
        sql = """
        IF EXISTS (SELECT 1 FROM RealtimePrices WHERE Symbol = ?)
            UPDATE RealtimePrices SET Price = ?, Volume = ?, LastUpdated = GETDATE() WHERE Symbol = ?
        ELSE
            INSERT INTO RealtimePrices (Symbol, Price, Volume, LastUpdated) VALUES (?, ?, ?, GETDATE())
        """
        conn = SQLUtils.get_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (symbol, price, volume, symbol, symbol, price, volume))
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
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT Price FROM RealtimePrices WHERE Symbol = ?", (symbol.upper(),))
            row = cursor.fetchone()
            if row:
                return row[0]
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
        finally:
            conn.close()
        return None
