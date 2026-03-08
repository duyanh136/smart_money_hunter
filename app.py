import sys
import io
import os

# Set Numba cache dir to /tmp for Vercel Serverless read-only filesystem compatibility
os.environ["NUMBA_CACHE_DIR"] = "/tmp"

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')
from flask import Flask, render_template, jsonify, request
from concurrent.futures import ThreadPoolExecutor
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging
from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
from services.tcbs_service import tcbs_service
from services.tcbs_socket import tcbs_stream
from services.telegram_bot import run_bot_scheduler, check_realtime_stoploss, load_portfolio, reload_telegram_bot_cache
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
        
    return jsonify({
        'symbol': symbol,
        'group': class_info['group'],
        'strategy': class_info['strategy'],
        'market_phase': df['Market_Phase'].iloc[-1] if 'Market_Phase' in df else "N/A", # Global Phase (Current)
        'action': df['Action_Recommendation'].iloc[-1] if 'Action_Recommendation' in df else "N/A",
        'poc': df['POC'].iloc[-1] if 'POC' in df else 0,
        'pyramid_action': SmartMoneyAnalyzer.get_pyramid_sizing(df),
        'base_distance_pct': df['Base_Distance_Pct'].iloc[-1] if 'Base_Distance_Pct' in df else 0,
        'data': result
    })

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
        return jsonify(leaders)
    except Exception as e:
        logger.error(f"API top_leaders error: {e}")
        return jsonify({'error': str(e)}), 500

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

@app.route('/api/scan')
def scan_market():
    results = []
    
    # Use ThreadPool to scan in parallel
    # We can scan all or limit
    
    def scan_symbol(symbol):
        try:
            # Get latest price from socket if available to skip REST call?
            # No, we need full history for analysis (Signals)
            # Get history
            df = MarketService.get_history(symbol, period='6mo')
            
            if df is not None and not df.empty:
                df = SmartMoneyAnalyzer.analyze(df)
                if df is not None and not df.empty:
                    last_row = df.iloc[-1]
                    
                    return {
                        'symbol': symbol,
                        'price': last_row['Close'],
                        'change': round((last_row['Close'] - df.iloc[-2]['Close'])/df.iloc[-2]['Close'] * 100, 2),
                        'vol_ratio': round(last_row['Vol_Ratio'], 2),
                        'rsi': round(last_row['RSI'], 1),
                        'market_phase': df['Market_Phase'].iloc[-1],
                        'action': df['Action_Recommendation'].iloc[-1],
                        # Signals
                        'signal_voteo': bool(last_row.get('Signal_VoTeo')),
                        'signal_buydip': bool(last_row.get('Signal_BuyDip')),
                        'signal_breakout': bool(last_row.get('Signal_Breakout')),
                        'signal_goldensell': bool(last_row.get('Signal_GoldenSell')),
                        'signal_warning': bool(last_row.get('Signal_Distribution') or last_row.get('Signal_UpBo')),
                        # Radar Signals
                        'radar_panicsell': bool(last_row.get('Signal_PanicSell')),
                        'radar_sangtay': bool(last_row.get('Signal_SangTayNhoLe')),
                        'radar_gaynen': bool(last_row.get('Signal_GayNenTestLai')),
                        'radar_phankyam': bool(last_row.get('Signal_PhanKyAmMACD')),
                        'radar_daodong': bool(last_row.get('Signal_DaoDongLongLeo')),
                        'radar_chammay': bool(last_row.get('Signal_ChamMayKenhDuoi')),
                        'pyramid_action': SmartMoneyAnalyzer.get_pyramid_sizing(df),
                        'base_distance_pct': round(last_row.get('Base_Distance_Pct', 0), 2)
                    }
                    
            # Fallback for stocks with no history (e.g. TCBS API broken for UPCOM)
            # Try to get snapshot info to at least show Price
            info = tcbs_service.get_ticker_info(symbol)
            if info:
                # { 'price': x, 'refPrice': y, 'volume': z, ... }
                curr_price = info.get('price') or info.get('refPrice') or 0
                ref_price = info.get('refPrice') or curr_price
                change = 0
                if ref_price > 0:
                    change = round((curr_price - ref_price) / ref_price * 100, 2)
                    
                return {
                    'symbol': symbol,
                    'price': curr_price,
                    'change': change,
                    'vol_ratio': 0,
                    'rsi': 0,
                    'market_phase': "Không có lịch sử",
                    'action': "Chỉ báo giá (N/A)",
                    # Signals all False
                    'signal_voteo': False,
                    'signal_buydip': False,
                    'signal_breakout': False,
                    'signal_goldensell': False,
                    'signal_warning': False,
                    # Radar Signals
                    'radar_panicsell': False,
                    'radar_sangtay': False,
                    'radar_phankyam': False,
                    'radar_daodong': False,
                    'radar_chammay': False,
                    'pyramid_action': "N/A",
                    'base_distance_pct': 0
                }

        except Exception as e:
            logger.error(f"Scan error {symbol}: {e}")
        return None

    # Limit max workers to avoid overload
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Check first 30 for now to be fast, or all?
        # User wants FAST.
        # Let's scan all but rely on cache in MarketService
        futures = executor.map(scan_symbol, WATCHLIST)
        for res in futures:
            if res:
                results.append(res)
    
    return jsonify(results)

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
    else:
        logger.info("Vercel Mode: Background threads disabled. Using SQL Sync fallback.")

    @socketio.on('connect')
    def handle_connect():
        logger.info("Client connected")
        emit('server_status', {'status': 'connected', 'tcbs_stream': tcbs_stream.running})

    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
