from services.sql_utils import SQLUtils
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_sql():
    print("--- SQL Verification Start ---")
    conn = SQLUtils.get_connection()
    if not conn:
        print("FAILED: Could not connect to SQL Server.")
        return

    try:
        cursor = conn.cursor()
        print("SUCCESS: Connected to SQL Server.")
        
        # Check if Table exists
        cursor.execute("IF OBJECT_ID('RealtimePrices', 'U') IS NOT NULL SELECT 1 ELSE SELECT 0")
        exists = cursor.fetchone()[0]
        if exists:
            print("SUCCESS: Table 'RealtimePrices' exists.")
            # Check row count
            cursor.execute("SELECT COUNT(*) FROM RealtimePrices")
            count = cursor.fetchone()[0]
            print(f"INFO: Row count in RealtimePrices: {count}")
            if count > 0:
                print("INFO: Latest 5 entries:")
                cursor.execute("SELECT TOP 5 * FROM RealtimePrices ORDER BY LastUpdated DESC")
                for row in cursor.fetchall():
                    print(f"  {row}")
        else:
            print("WARNING: Table 'RealtimePrices' does NOT exist.")
            
    except Exception as e:
        print(f"ERROR during verification: {e}")
    finally:
        conn.close()
        print("--- SQL Verification End ---")

if __name__ == "__main__":
    verify_sql()
