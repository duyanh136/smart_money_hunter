from services.sql_utils import SQLUtils
from datetime import datetime, timedelta
import random

def seed_history():
    print("Seeding dummy historical data...")
    conn = SQLUtils.get_connection()
    if not conn:
        print("Failed to connect to DB")
        return
    
    symbols = ['VND', 'SSI', 'VCB', 'HPG', 'FPT', 'VIC', 'VHM', 'GAS', 'MSN', 'MWG']
    
    try:
        cursor = conn.cursor()
        
        # Clear existing history for clean test
        cursor.execute("DELETE FROM MarketAnalysisHistory")
        
        # Seed for last 30 days
        today = datetime.now().date()
        for i in range(30, -1, -1):
            analysis_date = today - timedelta(days=i)
            # Skip weekends
            if analysis_date.weekday() >= 5: continue
            
            for sym in symbols:
                # Random walk price
                base_price = 50.0
                price = base_price + random.uniform(-5, 10) + (30 - i) * 0.1 # Slighly upward trend
                score = random.uniform(60, 95)
                
                sql = """
                INSERT INTO MarketAnalysisHistory (
                    Symbol, AnalysisDate, Price, Score, UpdatedAt
                ) VALUES (?, ?, ?, ?, ?)
                """
                cursor.execute(sql, (sym, analysis_date, price, score, datetime.now()))
        
        conn.commit()
        print("Successfully seeded 30 days of history data.")
    except Exception as e:
        print(f"Error seeding data: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_history()
