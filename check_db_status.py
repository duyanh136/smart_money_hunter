import pyodbc
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def check_db():
    try:
        conn_str = (
            f"DRIVER={os.getenv('SQL_DRIVER', '{ODBC Driver 18 for SQL Server}')};"
            f"SERVER={os.getenv('SQL_SERVER')};"
            f"DATABASE={os.getenv('SQL_DATABASE')};"
            f"UID={os.getenv('SQL_USER')};"
            f"PWD={os.getenv('SQL_PASSWORD')};"
            "TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print(f"--- Checking Database: {os.getenv('SQL_DATABASE')} ---")
        
        # Check table exists
        cursor.execute("SELECT COUNT(*) FROM RealtimePrices")
        count = cursor.fetchone()[0]
        print(f"Total records in RealtimePrices: {count}")
        
        # Get latest 10 updates
        cursor.execute("SELECT TOP 10 Symbol, Price, LastUpdated FROM RealtimePrices ORDER BY LastUpdated DESC")
        rows = cursor.fetchall()
        
        if not rows:
            print("No data found in RealtimePrices table.")
        else:
            print(f"{'Symbol':<10} | {'Price':<10} | {'Last Updated':<20}")
            print("-" * 45)
            for row in rows:
                print(f"{row[0]:<10} | {row[1]:<10} | {row[2]}")
        
        # Check if current time is close to last update
        if rows:
            last_update = rows[0][2]
            now = datetime.now()
            diff = (now - last_update).total_seconds()
            print(f"\nLast update was {diff:.1f} seconds ago.")
            if diff < 60:
                print("STATUS: REAL-TIME DATA IS FLOWING! ✅")
            else:
                print("STATUS: DATA IS STALE. App might not be running or socket is disconnected. ❌")
        
        conn.close()
    except Exception as e:
        print(f"Error connecting to database: {e}")

if __name__ == "__main__":
    check_db()
