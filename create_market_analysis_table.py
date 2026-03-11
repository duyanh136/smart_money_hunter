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
        
        # Table for Pre-computed Market Analysis Results
        create_table_sql = """
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[MarketAnalysis]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[MarketAnalysis] (
                [Symbol] [varchar](10) NOT NULL PRIMARY KEY,
                [Price] [float],
                [ChangePct] [float],
                [VolRatio] [float],
                [RSI] [float],
                [MarketPhase] [nvarchar](50),
                [ActionRecommendation] [nvarchar](100),
                [SignalVoTeo] [bit],
                [SignalBuyDip] [bit],
                [SignalSuper] [bit],
                [SignalBreakout] [bit],
                [SignalSqueeze] [bit],
                [SignalDistribution] [bit],
                [SignalUpbo] [bit],
                [RadarPanicSell] [bit],
                [RadarPhanKyAm] [bit],
                [RadarSangTay] [bit],
                [RadarDaoDong] [bit],
                [RadarGayNen] [bit],
                [RadarChamMay] [bit],
                [PyramidAction] [nvarchar](50),
                [BaseDistancePct] [float],
                [UpdatedAt] [datetime] DEFAULT GETDATE()
            );
            CREATE INDEX IX_MarketAnalysis_UpdatedAt ON [dbo].[MarketAnalysis] (UpdatedAt);
        END
        """
        
        cursor.execute(create_table_sql)
        if hasattr(conn, 'commit'):
            conn.commit()
        logger.info("Table MarketAnalysis created or already exists.")
        
    except Exception as e:
        logger.error(f"Error creating table: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_table()
