from services.sql_utils import SQLUtils
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_table():
    conn = SQLUtils.get_connection()
    if not conn:
        logger.error("Could not connect to database.")
        return
    
    try:
        cursor = conn.cursor()
        
        # Table for Top 10 Leaders History
        create_table_sql = """
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TopLeadersHistory]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[TopLeadersHistory] (
                [ID] [int] IDENTITY(1,1) NOT NULL PRIMARY KEY,
                [ScanDate] [date] NOT NULL,
                [Rank] [int] NOT NULL,
                [Symbol] [varchar](10) NOT NULL,
                [Score] [float] NOT NULL,
                [Price] [float] NULL,
                [ChangePct] [float] NULL,
                [Signals] [nvarchar](max) NULL,
                [CreatedAt] [datetime] DEFAULT GETDATE()
            );
            CREATE INDEX IX_TopLeadersHistory_ScanDate ON [dbo].[TopLeadersHistory](ScanDate);
        END
        """
        
        cursor.execute(create_table_sql)
        if hasattr(conn, 'commit'):
            conn.commit()
        logger.info("Table TopLeadersHistory created or already exists.")
        
    except Exception as e:
        logger.error(f"Error creating table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_table()
