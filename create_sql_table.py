import pyodbc
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def create_table():
    try:
        conn_str = (
            f"DRIVER={os.getenv('SQL_DRIVER', '{ODBC Driver 17 for SQL Server}')};"
            f"SERVER={os.getenv('SQL_SERVER')};"
            f"DATABASE={os.getenv('SQL_DATABASE')};"
            f"UID={os.getenv('SQL_USER')};"
            f"PWD={os.getenv('SQL_PASSWORD')};"
            "TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        sql = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='RealtimePrices' AND xtype='U')
        CREATE TABLE RealtimePrices (
            Symbol VARCHAR(20) PRIMARY KEY,
            Price FLOAT,
            Volume FLOAT,
            LastUpdated DATETIME DEFAULT GETDATE()
        )
        """
        cursor.execute(sql)
        conn.commit()
        print("Table RealtimePrices verified/created.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_table()
