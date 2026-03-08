import pyodbc
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def create_database_and_table():
    # Connect to master or a default available DB first to create the new one
    # Note: User provided HISDATAPKSERVER\NETCONN as server.
    # Usually, we connect to 'master' to run CREATE DATABASE.
    
    server = os.getenv('SQL_SERVER')
    user = os.getenv('SQL_USER')
    password = os.getenv('SQL_PASSWORD')
    driver = os.getenv('SQL_DRIVER', '{ODBC Driver 18 for SQL Server}')
    
    # Try connecting to master
    base_conn_str = (
        f"DRIVER={driver};"
        f"SERVER={server};"
        f"DATABASE=master;"
        f"UID={user};"
        f"PWD={password};"
        "TrustServerCertificate=yes;"
    )
    
    new_db_name = "SmartMoney_Hunter"
    
    try:
        print(f"Connecting to master on {server}...")
        conn = pyodbc.connect(base_conn_str, autocommit=True)
        cursor = conn.cursor()
        
        # Check if DB exists
        cursor.execute(f"SELECT name FROM sys.databases WHERE name = '{new_db_name}'")
        if not cursor.fetchone():
            print(f"Creating database {new_db_name}...")
            cursor.execute(f"CREATE DATABASE {new_db_name}")
            print(f"Database {new_db_name} created.")
        else:
            print(f"Database {new_db_name} already exists.")
        
        conn.close()
        
        # Now connect to the new DB and create the table
        conn_str = (
            f"DRIVER={driver};"
            f"SERVER={server};"
            f"DATABASE={new_db_name};"
            f"UID={user};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )
        
        print(f"Connecting to {new_db_name} to create table...")
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
        
        return new_db_name
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    db_name = create_database_and_table()
    if db_name:
        print(f"SUCCESS_DB_NAME:{db_name}")
