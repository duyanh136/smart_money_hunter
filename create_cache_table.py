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
        
        # Table for Generic Application Cache
        create_table_sql = """
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[SystemCache]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[SystemCache] (
                [CacheKey] [varchar](50) NOT NULL PRIMARY KEY,
                [CacheValue] [nvarchar](max) NOT NULL,
                [ExpiryTime] [datetime] NOT NULL,
                [UpdatedAt] [datetime] DEFAULT GETDATE()
            );
        END
        """
        
        cursor.execute(create_table_sql)
        if hasattr(conn, 'commit'):
            conn.commit()
        logger.info("Table SystemCache created or already exists.")
        
    except Exception as e:
        logger.error(f"Error creating table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_table()
