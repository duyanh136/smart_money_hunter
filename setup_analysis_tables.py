import pyodbc
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def setup_tables():
    server = os.getenv('SQL_SERVER')
    database = os.getenv('SQL_DATABASE')
    user = os.getenv('SQL_USER')
    password = os.getenv('SQL_PASSWORD')
    driver = os.getenv('SQL_DRIVER', '{SQL Server}')
    
    conn_str = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={user};PWD={password};TrustServerCertificate=yes;'
    
    print(f"Attempting to connect to {server}...")
    try:
        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()
        print("Connected successfully!")
        # Drop existing tables to ensure clean slate
        print("Dropping existing tables...")
        cursor.execute("IF OBJECT_ID('[dbo].[MarketAnalysis]', 'U') IS NOT NULL DROP TABLE [dbo].[MarketAnalysis]")
        cursor.execute("IF OBJECT_ID('[dbo].[MarketAnalysisHistory]', 'U') IS NOT NULL DROP TABLE [dbo].[MarketAnalysisHistory]")
        
        # Create MarketAnalysis table
        print("Creating table [dbo].[MarketAnalysis]...")
        cursor.execute("""
        CREATE TABLE [dbo].[MarketAnalysis] (
            [Symbol] VARCHAR(20) PRIMARY KEY,
            [Price] FLOAT,
            [Change] FLOAT,
            [VolRatio] FLOAT,
            [RSI] FLOAT,
            [MarketPhase] NVARCHAR(100),
            [Action] NVARCHAR(100),
            [LeaderScore] INT,
            [IsSharkDominated] BIT,
            [IsStormResistant] BIT,
            [Tag] NVARCHAR(200),
            [SignalVoTeo] BIT,
            [SignalBuyDip] BIT,
            [SignalBreakout] BIT,
            [SignalGoldenSell] BIT,
            [SignalWarning] BIT,
            [RadarPanicSell] BIT,
            [RadarSangTay] BIT,
            [RadarGayNen] BIT,
            [RadarPhanKyAm] BIT,
            [RadarDaoDong] BIT,
            [RadarChamMay] BIT,
            [PyramidAction] NVARCHAR(100),
            [BaseDistancePct] FLOAT,
            [LastUpdated] DATETIME DEFAULT GETDATE()
        )
        """)
        
        # Create MarketAnalysisHistory table
        print("Creating table [dbo].[MarketAnalysisHistory]...")
        cursor.execute("""
        CREATE TABLE [dbo].[MarketAnalysisHistory] (
            [Id] INT IDENTITY(1,1) PRIMARY KEY,
            [Symbol] VARCHAR(20),
            [Price] FLOAT,
            [Change] FLOAT,
            [VolRatio] FLOAT,
            [RSI] FLOAT,
            [MarketPhase] NVARCHAR(100),
            [Action] NVARCHAR(100),
            [LeaderScore] INT,
            [IsSharkDominated] BIT,
            [IsStormResistant] BIT,
            [SignalVoTeo] BIT,
            [SignalBuyDip] BIT,
            [SignalBreakout] BIT,
            [SignalGoldenSell] BIT,
            [SignalWarning] BIT,
            [AnalysisDate] DATETIME DEFAULT GETDATE()
        )
        """)
        
        conn.commit()
        print("Tables setup completed successfully!")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    setup_tables()
