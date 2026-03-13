import pandas as pd
import logging
from datetime import datetime, timedelta
from services.sql_utils import SQLUtils
from services.market_service import MarketService

logger = logging.getLogger(__name__)

class StrategyPerformanceAnalyzer:
    @staticmethod
    def get_performance_stats():
        """
        Calculates T+N returns for Top 10 stocks in history.
        Structure:
        1. Get all dates in MarketAnalysisHistory.
        2. For each date, identify Top 10 (by Score).
        3. Find prices for these Top 10 at T+3, T+5, T+10, T+20.
        """
        conn = SQLUtils.get_connection()
        if not conn:
            return {"error": "Database connection failed"}

        try:
            # 1. Load entire history into a DataFrame for efficient processing
            query = "SELECT Symbol, AnalysisDate, Price, Score FROM MarketAnalysisHistory ORDER BY AnalysisDate DESC"
            df = pd.read_sql(query, conn)
            conn.close()

            if df.empty:
                return {"error": "No historical data found. Please run some scans first."}

            df['AnalysisDate'] = pd.to_datetime(df['AnalysisDate'])
            all_dates = sorted(df['AnalysisDate'].unique())
            
            if len(all_dates) < 2:
                return {"error": "Need at least 2 days of historical data for comparison."}

            performance_by_day = []
            
            # T+N horizons
            horizons = [3, 5, 10, 20]
            
            # We iterate through all dates except the most recent ones (where we can't calculate T+N yet)
            for d in all_dates:
                # Top 10 on this day
                day_data = df[df['AnalysisDate'] == d].sort_values(by='Score', ascending=False).head(10)
                if day_data.empty: continue
                
                day_stats = {
                    "date": d.strftime('%Y-%m-%d'),
                    "top_10": day_data['Symbol'].tolist(),
                    "avg_return": 0,
                    "horizons": {}
                }
                
                # For each horizon, calculate average return of these 10 stocks
                for h in horizons:
                    # Target date (approximate trading days)
                    # Note: This is an approximation. A more accurate way would be to count rows in the date list.
                    try:
                        idx = all_dates.index(d)
                        if idx + h < len(all_dates):
                            target_date = all_dates[idx + h]
                            
                            returns = []
                            for _, row in day_data.iterrows():
                                symbol = row['Symbol']
                                buy_price = row['Price']
                                
                                # Look for price in the future data we already loaded
                                future_price_row = df[(df['AnalysisDate'] == target_date) & (df['Symbol'] == symbol)]
                                
                                if not future_price_row.empty:
                                    sell_price = future_price_row.iloc[0]['Price']
                                    ret = (sell_price - buy_price) / buy_price * 100
                                    returns.append(ret)
                            
                            if returns:
                                day_stats["horizons"][f"T+{h}"] = round(sum(returns) / len(returns), 2)
                    except Exception as e:
                        logger.debug(f"Error calculating T+{h} for {d}: {e}")
                
                performance_by_day.append(day_stats)

            # 2. Summarize Overall stats
            total_days = len(performance_by_day)
            summary = {
                "total_days_analyzed": total_days,
                "win_rate_t10": 0, # % of days where T+10 return was positive
                "avg_return_t10": 0,
                "best_stock": "N/A",
                "best_return": 0,
                "equity_curve": []
            }

            # Cumulative calculation
            cumulative_profit = 0
            win_count = 0
            valid_t10_days = 0
            
            for item in sorted(performance_by_day, key=lambda x: x['date']):
                ret_t10 = item["horizons"].get("T+10")
                if ret_t10 is not None:
                    cumulative_profit += ret_t10
                    valid_t10_days += 1
                    if ret_t10 > 0: win_count += 1
                
                summary["equity_curve"].append({
                    "date": item["date"],
                    "profit": round(cumulative_profit, 2)
                })

            if valid_t10_days > 0:
                summary["win_rate_t10"] = round(win_count / valid_t10_days * 100, 1)
                summary["avg_return_t10"] = round(cumulative_profit / valid_t10_days, 2)

            # Find best individual stock performance in Top 10 history
            # (Requires iterating over the raw pairings again or during previous loop)
            # For simplicity, let's return what we have.
            
            return {
                "summary": summary,
                "daily_stats": performance_by_day
            }

        except Exception as e:
            logger.error(f"Strategy Performance Error: {e}")
            return {"error": str(e)}
