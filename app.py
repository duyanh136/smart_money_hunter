import sys
import io
import os

# Set Numba cache dir to /tmp for Vercel Serverless read-only filesystem compatibility
os.environ["NUMBA_CACHE_DIR"] = "/tmp"

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from flask import Flask, render_template, jsonify, request
from concurrent.futures import ThreadPoolExecutor
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO, emit
import logging
from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
from services.tcbs_service import tcbs_service
from services.tcbs_socket import tcbs_stream
from services.telegram_bot import run_bot_scheduler, check_realtime_stoploss, load_portfolio, reload_telegram_bot_cache
from services.sql_utils import SQLUtils
from services.db_service import DBService
import threading
import pandas as pd
import json
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'smart-money-hunter-secret'
CORS(app)

# Vercel detection
IS_VERCEL = os.getenv('VERCEL') == '1'

# For Vercel, we must use polling as WebSocket isn't sustained in serverless
if IS_VERCEL:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', transports=['polling'])
else:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/history')
def get_history_data():
    symbol = request.args.get('symbol', 'VND')
    period = request.args.get('period', '1y')
    
    df = MarketService.get_history(symbol, period=period)
    if df is None:
        return jsonify({'error': 'Not found'}), 404
    
    # Analyze
    df = SmartMoneyAnalyzer.analyze(df)
    
    # Classification & Strategy
    class_info = SmartMoneyAnalyzer.classify_stock(symbol)
    
    # Convert to JSON friendly format
    result = []
    
    for index, row in df.iterrows():
        row = row.fillna(0)
        
        result.append({
            'time': index.strftime('%Y-%m-%d'),
            'open': row['Open'],
            'high': row['High'],
            'low': row['Low'],
            'close': row['Close'],
            'volume': row['Volume'],
            'shark_bar': row['Shark_Bar'] if 'Shark_Bar' in row else 0,
            'retail_bar': row['Retail_Bar'] if 'Retail_Bar' in row else 0,
            'signal_voteo': bool(row['Signal_VoTeo']) if 'Signal_VoTeo' in row else False,
            'signal_buydip': bool(row['Signal_BuyDip']) if 'Signal_BuyDip' in row else False,
            'signal_super': bool(row['Signal_Super']) if 'Signal_Super' in row else False,
            'signal_upbo': bool(row['Signal_UpBo']) if 'Signal_UpBo' in row else False,
            'signal_breakout': bool(row['Signal_Breakout']) if 'Signal_Breakout' in row else False,
            'signal_squeeze': bool(row['Signal_Squeeze']) if 'Signal_Squeeze' in row else False,
            'signal_ma50_test': bool(row['Signal_MA50_Test']) if 'Signal_MA50_Test' in row else False,
            'signal_poc': bool(row['Signal_POC_Support']) if 'Signal_POC_Support' in row else False,
            'signal_distribution': bool(row['Signal_Distribution']) if 'Signal_Distribution' in row else False,
            'signal_loose': bool(row['Signal_Loose']) if 'Signal_Loose' in row else False,
            'signal_shootingstar': bool(row['Signal_ShootingStar']) if 'Signal_ShootingStar' in row else False,
            'signal_goldensell': bool(row['Signal_GoldenSell']) if 'Signal_GoldenSell' in row else False,
            'market_phase': row['Market_Phase'] if 'Market_Phase' in row else "N/A",
            'action': row['Action_Recommendation'] if 'Action_Recommendation' in row else "N/A",
            'poc': row['POC'] if 'POC' in row else 0,
            'rsi': row['RSI'] if 'RSI' in row else 50,
            'ma20': row['SMA_20'] if 'SMA_20' in row else 0,
            'ma50': row['SMA_50'] if 'SMA_50' in row else 0,
            'macd_line': row['MACD_Line'] if 'MACD_Line' in row else 0,
            'macd_hist': row['MACD_Hist'] if 'MACD_Hist' in row else 0,
            'pyramid_action': row['Pyramid_Action'] if 'Pyramid_Action' in row else "Quan Sát",
            'base_distance_pct': row['Base_Distance_Pct'] if 'Base_Distance_Pct' in row else 0
        })
        
    # Try to get pre-computed analysis from SQL to save time
    cached = SQLUtils.get_analysis_by_symbol(symbol)

    return jsonify({
        'symbol': symbol,
        'group': class_info['group'],
        'strategy': class_info['strategy'],
        'market_phase': (cached['MarketPhase'] if cached else (df['Market_Phase'].iloc[-1] if 'Market_Phase' in df else "N/A")),
        'action': (cached['ActionRecommendation'] if cached else (df['Action_Recommendation'].iloc[-1] if 'Action_Recommendation' in df else "N/A")),
        'poc': df['POC'].iloc[-1] if 'POC' in df else 0,
        'pyramid_action': cached['PyramidAction'] if cached else SmartMoneyAnalyzer.get_pyramid_sizing(df),
        'base_distance_pct': cached['BaseDistancePct'] if cached else (df['Base_Distance_Pct'].iloc[-1] if 'Base_Distance_Pct' in df else 0),
        'is_shark_dominated': cached['IsSharkDominated'] if cached else False,
        'is_storm_resistant': cached['IsStormResistant'] if cached else False,
        'buy_signal_status': cached['BuySignalStatus'] if cached else SmartMoneyAnalyzer.get_buy_signal_status(df),
        'data': result
    })

@app.route('/api/export_excel')
def export_excel():
    try:
        limit = int(request.args.get('limit', 10))
        leaders = MarketService.get_top_leaders(limit=limit)
        
        if not leaders:
            return jsonify({'error': 'No data'}), 404
            
        df = pd.DataFrame(leaders)
        
        # Define readable headers and column order
        cols_mapping = {
            'symbol': 'Symbol', 'price': 'Price', 'change': 'ChangePct', 'vol_ratio': 'VolRatio',
            'rsi': 'RSI', 'market_phase': 'MarketPhase', 'action': 'ActionRecommendation',
            'score': 'LeaderScore', 'is_shark_dominated': 'IsSharkDominated',
            'is_storm_resistant': 'IsStormResistant', 'tag': 'Tag', 'signal_voteo': 'SignalVoTeo',
            'signal_buydip': 'SignalBuyDip', 'signal_breakout': 'SignalBreakout',
            'signal_goldensell': 'SignalGoldenSell', 'signal_warning': 'SignalWarning',
            'radar_panicsell': 'RadarPanicSell', 'radar_sangtay': 'RadarSangTay',
            'radar_gaynen': 'RadarGayNen', 'radar_phankyam': 'RadarPhanKyAm',
            'radar_daodong': 'RadarDaoDong', 'radar_chammay': 'RadarChamMay',
            'pyramid_action': 'PyramidAction', 'base_distance_pct': 'BaseDistancePct',
            'rank': 'Rank', 'buy_signal_status': 'BuySignalStatus', 'updated_at': 'UpdatedAt'
        }
        
        # Filter for existing columns and rename
        existing_cols = [c for c in cols_mapping.keys() if c in df.columns]
        df = df[existing_cols]
        df.rename(columns=cols_mapping, inplace=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Top Leaders')
            
            # Formatting
            workbook = writer.book
            worksheet = writer.sheets['Top Leaders']
            
            from openpyxl.styles import Font, Alignment, PatternFill
            
            header_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
            header_font = Font(color='FFFFFF', bold=True)
            alignment = Alignment(horizontal='center', vertical='center')
            
            # Header styling
            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = alignment
                
            # Auto-adjust column widths
            for column_cells in worksheet.columns:
                max_length = 0
                column = column_cells[0].column_letter
                for cell in column_cells:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column].width = adjusted_width

        output.seek(0)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"SmartMoney_Top10_{timestamp}.xlsx"
        
        from flask import send_file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Excel Export Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

from services.symbol_loader import SymbolLoader
import concurrent.futures

@app.route('/api/market_health')
def get_market_health():
    health_data = MarketService.get_market_health()
    weather_data = MarketService.get_market_weather()
    
    return jsonify({
        'health': health_data,
        'weather': weather_data
    })

@app.route('/api/top_leaders')
def get_top_leaders():
    try:
        limit = int(request.args.get('limit', 10))
        leaders = MarketService.get_top_leaders(limit=limit)
        
        # Save to SQLite for history in background (only for default limit or if not on Vercel)
        if limit >= 5 and not IS_VERCEL:
            threading.Thread(target=DBService.save_top_leaders, args=(leaders,), daemon=True).start()
            
        return jsonify(leaders)
    except Exception as e:
        logger.error(f"API top_leaders error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/top_leaders_history')
def get_top_leaders_history():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date is required'}), 400
    
    leaders = DBService.get_history_by_date(date_str)
    if leaders:
        return jsonify(leaders)
    else:
        # Fallback to SQLUtils if available
        try:
            history = SQLUtils.get_top_leaders_history(date_str)
            if history: return jsonify(history)
        except:
            pass
        return jsonify({'error': 'No data for this date'}), 404

@app.route('/api/top_leaders_dates')
def get_top_leaders_dates():
    dates = DBService.get_available_dates()
    return jsonify(dates)
@app.route('/api/strategy_performance')
def get_strategy_performance():
    from services.performance_analyzer import StrategyPerformanceAnalyzer
    stats = StrategyPerformanceAnalyzer.get_performance_stats()
    return jsonify(stats)

@app.route('/api/debug_seed')
def debug_seed():
    try:
        from seed_test_data import seed_history
        seed_history()
        return jsonify({"status": "success", "message": "Dummy data seeded successfully."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/save_symbols', methods=['POST'])
def save_symbols():
    try:
        # Collect all unique symbols: WATCHLIST + Portfolio
        portfolio = load_portfolio()
        portfolio_symbols = [item['symbol'].strip().upper() for item in portfolio if item.get('symbol')]
        all_symbols = list(set(WATCHLIST + portfolio_symbols))
        
        # SQL Connection
        import pyodbc
        conn_str = (
            f"DRIVER={os.getenv('SQL_DRIVER', '{ODBC Driver 17 for SQL Server}')};"
            f"SERVER={os.getenv('SQL_SERVER')};"
            f"DATABASE={os.getenv('SQL_DATABASE')};"
            f"UID={os.getenv('SQL_USER')};"
            f"PWD={os.getenv('SQL_PASSWORD')};"
            "TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Create table if not exists
        sql_create = """
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='StockSymbols' AND xtype='U')
        CREATE TABLE StockSymbols (
            Symbol VARCHAR(20) PRIMARY KEY,
            CreatedAt DATETIME DEFAULT GETDATE()
        )
        """
        cursor.execute(sql_create)
        
        # Insert/Upsert symbols
        # Using a simple check for existence for basic SQL Server compatibility
        for sym in all_symbols:
            cursor.execute("""
                IF NOT EXISTS (SELECT 1 FROM StockSymbols WHERE Symbol = ?)
                INSERT INTO StockSymbols (Symbol) VALUES (?)
            """, sym, sym)
            
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully saved {len(all_symbols)} symbols to database.")
        return jsonify({"status": "success", "count": len(all_symbols)})
    except Exception as e:
        logger.error(f"Error saving symbols to DB: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Global Watchlist
WATCHLIST = [
    # VN30
    'ACB', 'BCM', 'BID', 'BVH', 'CTG', 'FPT', 'GAS', 'GVR', 'HDB', 'HPG',
    'MBB', 'MSN', 'MWG', 'PLX', 'POW', 'SAB', 'SHB', 'SSB', 'SSI', 'STB',
    'TCB', 'TPB', 'VCB', 'VHM', 'VIB', 'VIC', 'VJC', 'VNM', 'VPB', 'VRE',
    # Banking & Finance
    'LPB', 'MSB', 'OCB', 'EIB', 'VIX', 'VND', 'ORS', 'CTS', 'FTS', 'BSI', 
    'HCM', 'AGR', 'MBS', 'BVS', 'VDS',
    # Real Estate & Construction
    'DIG', 'CEO', 'DXG', 'PDR', 'NVL', 'KBC', 'IDC', 'SZC', 'VGC', 'DXS',
    'HDG', 'HQC', 'ITA', 'KHG', 'LG', 'SCR', 'TCH', 'CRE', 'IJC', 'L14',
    'HUT', 'CII', 'NBB', 'HTN', 'HBC', 'CTD', 'LCG', 'HHV', 'VCG', 'FCN', 'KSB',
    # Steel & Materials
    'NKG', 'HSG', 'TLH', 'POM', 'TVN', 'SMC',
    # Oil & Gas, Power
    'PVD', 'PVS', 'PVT', 'PVC', 'BSR', 'OIL', 'GEG', 'NT2', 'REE', 'PC1', 'TV2',
    # Retail, Consumer, Agriculture
    'DGW', 'FRT', 'PET', 'PNJ', 'VGI', 'DBC', 'HAG', 'HNG', 'PAN', 'TAR', 'LTG',
    # Chemicals & Fertilizer
    'DGC', 'DPM', 'DCM', 'CSV', 'LAS', 'DDV',
    # Logistics & Others
    'GMD', 'HAH', 'VOS', 'VSC', 'ANV', 'VHC', 'IDI', 'ASM', 'GIL', 'TNG', 'MSH'
]

import math

@app.route('/api/stoploss_tool', methods=['POST'])
def stoploss_tool():
    """
    Nhận danh mục từ Frontend, tính toán Stop-loss (2x ATR)
    bằng cách so sánh High - 2*ATR với mức Stop-loss cũ một cách tròn giá.
    """
    data = request.json or {}
    portfolio = data.get('portfolio', [])
    results = []

    def process_item(item):
        symbol = str(item.get('symbol', '')).strip().upper()
        if not symbol: return None
        
        try:
            cost = float(item.get('cost', 0))
        except: cost = 0
        try:
            init_sl = float(item.get('init_sl', 0)) # Giá cắt lỗ ban đầu
        except: init_sl = 0
        try:
            old_sl = float(item.get('old_sl', 0)) # Giá cắt lỗ hiện tại
        except: old_sl = 0
        try:
            volume = float(item.get('volume', 0)) # Khối lượng ban đầu
        except: volume = 0

        df = MarketService.get_history(symbol, period='1mo')
        if df is None or df.empty:
            return None
        
        df = SmartMoneyAnalyzer.analyze(df)
        if df is None or df.empty:
            return None
            
        last_row = df.iloc[-1]
        high_price = last_row.get('High', 0)
        atr_14 = last_row.get('ATR_14', 0)
        close_price = last_row.get('Close', 0)
        
        import pandas as pd
        if pd.isna(atr_14): atr_14 = 0

        # Smart Sell Radar Triggers
        signal_sangtay = last_row.get('Signal_SangTayNhoLe', False)
        signal_gaynen = last_row.get('Signal_GayNenTestLai', False)
        signal_phankyam = last_row.get('Signal_PhanKyAmMACD', False)
        signal_daodong = last_row.get('Signal_DaoDongLongLeo', False)
        signal_chammay = last_row.get('Signal_ChamMayKenhDuoi', False)
        signal_panicsell = last_row.get('Signal_PanicSell', False)

        pnl_percent = ((close_price - cost) / cost) * 100 if cost > 0 else 0
        
        radar_alert = ""
        # Default action based on PnL sign
        if pnl_percent >= 0:
            action = "Gồng Lãi an toàn 🟢"
        else:
            action = "Theo dõi / Quản trị 🟡"
        
        if signal_panicsell:
            radar_alert = "🚨 PANIC SELL (BÁN THÁO)"
            action = "Bán Bằng Mọi Giá 🔴"
        elif pnl_percent <= -10:
            radar_alert = "💀 VI PHẠM NẶNG (-10%)"
            action = "BÁN HẾT - CẮT LỖ 🔴"
        elif pnl_percent <= -7:
            radar_alert = "✂️ QUẢN TRỊ RỦI RO (-7%)"
            action = "CẮT 1/2 - HẠ TỶ TRỌNG 🔴"
        elif signal_phankyam:
            radar_alert = "🛑 Phân Kỳ Âm MACD (Bán Hết)"
            action = "Bán Toàn Bộ 🔴"
        elif signal_daodong:
            radar_alert = "⚠️ Dao Động Lỏng Lẻo"
            action = "Chốt Lời Ngắn Hạn 🔴"
        elif signal_sangtay:
            radar_alert = "🚨 Lái Sang Tay"
            action = "Cân Nhắc Chốt Lời 🔴"
        elif signal_gaynen:
            radar_alert = "❌ Gãy Nền Test Lại"
            action = "Sút Dứt Khoát 🔴"
        elif signal_chammay:
            radar_alert = "☁️ Chạm Mây Kháng Cự"
            action = "Cơ Cấu Xoay Vòng 🔴"
            
        if pnl_percent > 50:
            if not radar_alert: radar_alert = "🔺 Siêu lợi nhuận >50%"
            else: radar_alert += " + Đã lãi >50%"
            action = "Chốt lời Hình Tháp"
        elif pnl_percent > 30:
            if not radar_alert: radar_alert = "🔺 Lãi >30% (An toàn)"
            else: radar_alert += " + Đã lãi >30%"
            
        return {
            "symbol": symbol,
            "cost": cost,
            "price": float(close_price),
            "pnl_percent": round(float(pnl_percent), 2),
            "radar_alert": radar_alert,
            "action": action
        }

    with ThreadPoolExecutor(max_workers=5) as executor:
        for res in executor.map(process_item, portfolio):
            if res:
                results.append(res)
                
    # Parse frontend array format back into our dict format for the backend DB
    new_db = []
    for item in results:
        # If the user already had an alert sent for this today, we want to retain it?
        # A bit tricky for stateless saving. But let's build a clean list.
        new_db.append({
            "symbol": item["symbol"],
            "cost": item["cost"],
            "volume": next((float(p.get("volume", 0)) for p in portfolio if p.get("symbol") == item["symbol"]), 0),
            "buy_date": next((p.get("buy_date") for p in portfolio if p.get("symbol") == item["symbol"]), None),
            "current_sl": item["cost"] * 0.9, # Safety floor: 10% from cost
            "alert_sent": False
        })
        
    # --- SAVE PORTFOLIO TO DISK FOR TELEGRAM BOT ---
    from services.telegram_bot import save_portfolio
    try:
        save_portfolio(new_db)
        logger.info("Saved Portfolio from Web UI to disk for Telegram Bot.")
    except Exception as e:
        logger.error(f"Error saving portfolio from UI: {e}")
                
    # --- DYNAMIC WEBSOCKET UPDATE ---
    # Update the websocket subscriptions to match the new portfolio
    try:
        portfolio_symbols = [item['symbol'].strip().upper() for item in portfolio if item.get('symbol')]
        combined_watchlist = list(set(WATCHLIST + portfolio_symbols))
        logger.info(f"Dynamically updating WebSocket subscriptions to: {combined_watchlist}")
        tcbs_stream.subscribe(combined_watchlist)
        
        # --- DYNAMIC TELEGRAM CACHE UPDATE ---
        # The user's portfolio list changed, and they may have saved it to disk from the frontend.
        # We need to explicitly reload the in-memory cache so old stocks don't trigger alerts.
        reload_telegram_bot_cache()
    except Exception as e:
        logger.error(f"Failed to dynamically update TCBS Stream / Bot Cache: {e}")
                
    return jsonify({"status": "success", "data": results})

@app.route('/api/scan', methods=['GET'])
@cross_origin()
def scan_market():
    """
    Scans market.
    Vercel Mode (Cloud): Fast DB lookup to avoid 10s timeout crash.
    Local Mode: Real-time scan as requested by user.
    """
    try:
        results = []
        if IS_VERCEL:
            # Use high-speed DB lookup for Vercel stability
            logger.info("Vercel Mode: Fetching analysis from SQL Database (High Speed)...")
            results = SQLUtils.get_all_market_analysis()
            if not results:
                 logger.warning("Vercel Mode: SQL Database is empty. Returning empty list.")
        else:
            # Full Real-time scan for Local environment (no 10s timeout)
            logger.info("Local Mode: Performing full real-time market scan...")
            results = MarketService.run_full_market_scan(save_history=False)
            
            if not results:
                # Fallback to last known SQL state if real-time fails locally
                logger.warning("Local Mode: Real-time scan failed, falling back to SQL.")
                results = SQLUtils.get_all_market_analysis()

        # Consistent mapping for both Cloud and Local data
        mapped_results = []
        for r in results:
            # Normalizing fields: database vs in-memory dict
            mapped_results.append({
                'symbol': r.get('symbol') or r.get('Symbol'),
                'price': r.get('price') or r.get('Price'),
                'change': r.get('change') or r.get('ChangePct'),
                'vol_ratio': r.get('vol_ratio') or r.get('VolRatio'),
                'rsi': r.get('rsi') or r.get('RSI'),
                'market_phase': r.get('market_phase') or r.get('MarketPhase'),
                'action': r.get('action') or r.get('ActionRecommendation'),
                'signal_voteo': bool(r.get('signal_voteo') or r.get('SignalVoTeo')),
                'signal_buydip': bool(r.get('signal_buydip') or r.get('SignalBuyDip')),
                'signal_super': bool(r.get('signal_super') or r.get('SignalSuper')),
                'signal_breakout': bool(r.get('signal_breakout') or r.get('SignalBreakout')),
                'signal_squeeze': bool(r.get('signal_squeeze') or r.get('SignalSqueeze')),
                'signal_distribution': bool(r.get('signal_distribution') or r.get('SignalDistribution')),
                'signal_upbo': bool(r.get('signal_upbo') or r.get('SignalUpbo')),
                'signal_goldensell': bool(r.get('signal_goldensell') or r.get('SignalGoldenSell')),
                'signal_bigmoney': bool(r.get('signal_bigmoney') or r.get('SignalBigMoney')),
                'radar_panicsell': bool(r.get('radar_panicsell') or r.get('RadarPanicSell')),
                'radar_phankyam': bool(r.get('radar_phankyam') or r.get('RadarPhanKyAm')),
                'radar_sangtay': bool(r.get('radar_sangtay') or r.get('RadarSangTay')),
                'radar_daodong': bool(r.get('radar_daodong') or r.get('RadarDaoDong')),
                'radar_gaynen': bool(r.get('radar_gaynen') or r.get('RadarGayNen')),
                'radar_chammay': bool(r.get('radar_chammay') or r.get('RadarChamMay')),
                'pyramid_action': r.get('pyramid_action') or r.get('PyramidAction'),
                'base_distance_pct': r.get('base_distance_pct') or r.get('BaseDistancePct'),
                'is_shark_dominated': bool(r.get('is_shark_dominated') or r.get('IsSharkDominated')),
                'is_storm_resistant': bool(r.get('is_storm_resistant') or r.get('IsStormResistant')),
                'rank': r.get('rank') or r.get('Rank'),
                'buy_signal_status': r.get('buy_signal_status') or r.get('BuySignalStatus', 'N/A')
            })
            
        return jsonify(mapped_results)
    except Exception as e:
        logger.error(f"Error in /api/scan (Emergency Fix Mode): {e}")
        return jsonify([])

if __name__ == '__main__':
    logger.info("Starting Smart Money Hunter (Flask)...")
    
    # ONLY Start background threads if NOT on Vercel
    if not IS_VERCEL:
        # Start Telegram Bot Scheduler in background
        logger.info("Starting Telegram Bot thread (Local Mode)...")
        bot_thread = threading.Thread(target=run_bot_scheduler, daemon=True)
        bot_thread.start()
        
        # Start TCBS Stream if token available
        if tcbs_service.token:
            try:
                logger.info("Initializing TCBS WebSocket (Local Mode)...")
                tcbs_stream.token = tcbs_service.token
                
                # Link to SocketIO
                def on_price_update(symbol, data):
                    price = data.get('matchPrice') or data.get('price') or data.get('refPrice')
                    vol = data.get('matchVolume') or data.get('accumulatedVolume')
                    real_price = price / 1000 if price and price > 1000 else price
                    
                    if real_price:
                        check_realtime_stoploss(symbol, real_price)
                    
                    socketio.emit('price_update', {
                        'symbol': symbol,
                        'price': price,
                        'vol': vol,
                        'raw': data
                    })
                
                tcbs_stream.on_update_callback = on_price_update
                tcbs_stream.start()
                
                # Sub watchlist + Portfolio symbols
                portfolio = load_portfolio()
                portfolio_symbols = [item['symbol'].strip().upper() for item in portfolio if item.get('symbol')]
                combined_watchlist = list(set(WATCHLIST + portfolio_symbols))
                
                time.sleep(1)
                tcbs_stream.subscribe(combined_watchlist)
            except Exception as e:
                logger.error(f"Failed to start TCBS Stream: {e}")
        # Start Market Analysis Sync (Every 30 mins)
        def run_analysis_sync():
            from services.market_service import MarketService
            from services.sql_utils import SQLUtils
            logger.info("Starting Market Analysis Sync background task...")
            SQLUtils.init_analysis_tables()
            while True:
                try:
                    # This will trigger analysis and upsert to DB
                    MarketService.get_top_leaders(limit=10)
                    logger.info("Periodic Market Analysis sync successful.")
                except Exception as e:
                    logger.error(f"Error in background Market Analysis sync: {e}")
                time.sleep(1800) # 30 minutes
        
        analysis_thread = threading.Thread(target=run_analysis_sync, daemon=True)
        analysis_thread.start()
    else:
        logger.info("Vercel Mode: Background threads disabled. Using SQL Sync fallback.")
        # On Vercel, we can't run background threads, 
        # but we can initialize tables if needed (though usually done via migrations)
        from services.sql_utils import SQLUtils
        try:
            SQLUtils.init_analysis_tables()
        except: pass

    @socketio.on('connect')
    def handle_connect():
        logger.info("Client connected")
        emit('server_status', {'status': 'connected', 'tcbs_stream': tcbs_stream.running})

    socketio.run(app, debug=False, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
