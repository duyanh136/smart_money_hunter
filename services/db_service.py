import sqlite3
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'smart_money_hunter.db')

class DBService:
    @staticmethod
    def init_db():
        """Initialize SQLite database and table for top leaders history."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS top_leaders_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE,
                    leaders_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
            logger.info(f"SQLite DB initialized at {DB_PATH}")
        except Exception as e:
            logger.error(f"Failed to initialize SQLite DB: {e}")

    @staticmethod
    def save_top_leaders(leaders):
        """Save a snapshot of top leaders for the current date."""
        if not leaders:
            return
            
        date_str = datetime.now().strftime('%Y-%m-%d')
        leaders_json = json.dumps(leaders)
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            # Insert or replace to ensure only one snapshot per day
            cursor.execute('''
                INSERT OR REPLACE INTO top_leaders_history (date, leaders_json)
                VALUES (?, ?)
            ''', (date_str, leaders_json))
            conn.commit()
            conn.close()
            logger.info(f"Saved Top Leaders for {date_str}")
        except Exception as e:
            logger.error(f"Failed to save Top Leaders to SQLite: {e}")

    @staticmethod
    def get_history_by_date(date_str):
        """Retrieve historical top leaders for a specific date."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT leaders_json FROM top_leaders_history WHERE date = ?', (date_str,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return json.loads(row[0])
        except Exception as e:
            logger.error(f"Failed to retrieve Top Leaders for {date_str}: {e}")
        return None

    @staticmethod
    def get_available_dates():
        """Get a list of all dates that have historical data."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT date FROM top_leaders_history ORDER BY date DESC')
            rows = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Failed to retrieve historical dates: {e}")
        return []

# Initialize DB when module loaded
DBService.init_db()
