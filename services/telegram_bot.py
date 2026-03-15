import os
import json
import logging
import requests
import schedule
import time
import math
import threading
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from services.db_service import DBService

from services.market_service import MarketService
from services.smart_money import SmartMoneyAnalyzer
from services.sql_utils import SQLUtils

load_dotenv()

logger = logging.getLogger(__name__)

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), '..', 'portfolio.json')

# IN-MEMORY CACHE FOR REAL-TIME ALERTS
# Structure: { 'BCM': { 'current_sl': 62.0, 'alert_sent': False } }
portfolio_cache = {}

def init_portfolio_cache():
    global portfolio_cache
    portfolio = load_portfolio()
    new_cache = {}
    for item in portfolio:
        symbol = str(item.get('symbol', '')).strip().upper()
        if symbol:
            new_cache[symbol] = {
                'current_sl': float(item.get('current_sl', 0)),
                'alert_sent': bool(item.get('alert_sent', False))
            }
    portfolio_cache.clear()
    portfolio_cache.update(new_cache)

def reload_telegram_bot_cache():
    logger.info("Forcing Telegram Bot Portfolio Cache Reload...")
    init_portfolio_cache()

def sync_cache_to_file():
    global portfolio_cache
    portfolio = load_portfolio()
    updated = False
    
    # Track current valid symbols
    valid_symbols = set()
    
    for item in portfolio:
        symbol = str(item.get('symbol', '')).strip().upper()
        if not symbol: continue
        valid_symbols.add(symbol)
        
        if symbol in portfolio_cache:
            if item.get('alert_sent') != portfolio_cache[symbol]['alert_sent']:
                item['alert_sent'] = portfolio_cache[symbol]['alert_sent']
                updated = True
                
    # Cleanup memory cache for symbols no longer in portfolio
    stale_symbols = set(portfolio_cache.keys()) - valid_symbols
    for stale in stale_symbols:
        del portfolio_cache[stale]
        logger.info(f"Removed tracked symbol {stale} from Real-Time Cache.")
        
    if updated:
        save_portfolio(portfolio)

def check_realtime_stoploss(symbol: str, current_price: float):
    global portfolio_cache
    symbol = symbol.strip().upper()
    
    # 1. Very fast memory lookup
    if symbol not in portfolio_cache:
        return
        
    cache_item = portfolio_cache[symbol]
    
    # 2. Trigger Condition: Price <= Stop-Loss AND Alert not yet sent today
    if current_price <= cache_item['current_sl'] and not cache_item['alert_sent']:
        logger.warning(f"REAL-TIME ALERT TRIGGERED FOR {symbol} at {current_price} (SL: {cache_item['current_sl']})")
        
        # 3. Mark as sent immediately to prevent spam
        portfolio_cache[symbol]['alert_sent'] = True
        sync_cache_to_file()
        
        # 4. Format Emergency Message
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not bot_token or not chat_id:
            logger.warning("Emergency Alert: TELEGRAM_BOT_TOKEN or CHAT_ID missing.")
            return
            
        is_default_sl = cache_item.get('current_sl') == cache_item.get('cost', 0) * 0.9
        sl_type = "Mốc quản trị 10% (Tự động)" if is_default_sl else "Mốc nền hỗ trợ"
        
        emergency_msg = (
            f"🚨 <b>CẢNH BÁO KHẨN CẤP: VI PHẠM RỦI RO!</b> 🚨\n\n"
            f"📉 Mã CK: <b>{symbol}</b>\n"
            f"⚠️ Giá hiện tại: <b>{current_price:,.2f}</b> đã rớt dưới {sl_type}: <b>{cache_item['current_sl']:,.2f}</b>!\n"
            f"🩸 Trạng thái: Ngưỡng chịu đựng tối đa đã bị phá vỡ.\n\n"
            f"⚡️ <b>HÀNH ĐỘNG BẮT BUỘC:</b> SÚT DỨT KHOÁT để bảo vệ NAV ngay lập tức!"
        )
        
        # 5. Send to Telegram
        telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": emergency_msg,
            "parse_mode": "HTML"
        }
        try:
            resp = requests.post(telegram_url, json=payload)
            if resp.status_code == 200:
                logger.info(f"Emergency alert sent for {symbol}")
            else:
                logger.error(f"Failed to send emergency alert: {resp.text}")
        except Exception as e:
            logger.error(f"Error sending emergency alert: {e}")

def send_system_alert(message: str):
    """Sends a system/maintenance alert to Telegram"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.warning(f"System Alert (Dry Run): {message}")
        return

    formatted_msg = f"🛠 <b>HỆ THỐNG THÔNG BÁO</b>\n\n{message}"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": formatted_msg,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logger.error(f"Failed to send system alert: {e}")

def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        return []
    try:
        with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        return []

def save_portfolio(portfolio_data):
    try:
        with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
            json.dump(portfolio_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Error saving portfolio: {e}")

def vn_round(price):
    if price >= 50:
        return math.floor(price * 10) / 10
    elif price >= 10:
        return math.floor(price * 20) / 20
    else:
        return math.floor(price * 100) / 100

def check_portfolio_and_send_alert():
    logger.info("Starting Telegram Bot portfolio check...")
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. Doing a dry run (printing to console).")

    portfolio = load_portfolio()
    if not portfolio:
        logger.info("Portfolio is empty. Nothing to check.")
        return

    now = datetime.now()
    
    # Check if a new day has started to reset the alert_sent flag
    
    # Check if inside trading hours (Mon-Fri, 09:00 - 15:00)
    if now.weekday() >= 5: # Saturday or Sunday
        logger.info("Weekend. Skipping check.")
        return
    
    hour = now.hour
    minute = now.minute
    time_val = hour * 100 + minute
    
    if time_val < 900 or time_val > 1500:
        logger.info("Outside trading hours (09:00-15:00). Skipping check.")
        return

    messages = []
    total_pnl_vnd = 0
    updated_portfolio = []
    
    for item in portfolio:
        symbol = str(item.get('symbol', '')).strip().upper()
        if not symbol: 
            updated_portfolio.append(item)
            continue
            
        cost = float(item.get('cost', 0))
        volume = float(item.get('volume', 0))
        current_sl = float(item.get('current_sl', 0))
        alert_sent = bool(item.get('alert_sent', False))
        
        # Fetch Data
        df = MarketService.get_history(symbol, period='1mo')
        if df is None or df.empty:
            logger.warning(f"Could not fetch history for {symbol}")
            updated_portfolio.append(item)
            continue
            
        df = SmartMoneyAnalyzer.analyze(df)
        if df is None or df.empty:
            logger.warning(f"Could not analyze history for {symbol}")
            updated_portfolio.append(item)
            continue
            
        last_row = df.iloc[-1]
        raw_close = last_row.get('Close', 0)
        
        # Normalize to thousands
        close_price = raw_close / 1000 if raw_close > 1000 else raw_close
        cost_k = cost / 1000 if cost > 1000 else cost
        sl_k = current_sl / 1000 if current_sl > 1000 else current_sl
        
        # Smart Sell Radar Triggers
        signal_sangtay = last_row.get('Signal_SangTayNhoLe', False)
        signal_gaynen = last_row.get('Signal_GayNenTestLai', False)
        signal_phankyam = last_row.get('Signal_PhanKyAmMACD', False)
        signal_daodong = last_row.get('Signal_DaoDongLongLeo', False)
        signal_chammay = last_row.get('Signal_ChamMayKenhDuoi', False)
        signal_panicsell = last_row.get('Signal_PanicSell', False)

        # Cooldown management
        if close_price > sl_k and alert_sent:
            alert_sent = False
            item['alert_sent'] = False
            logger.info(f"{symbol} recovered above SL. Resetting alert_sent flag.")
            
        # Update global cache
        portfolio_cache[symbol] = {
            'current_sl': current_sl,
            'alert_sent': alert_sent
        }
            
        updated_portfolio.append(item)
        
        # PnL calculations
        pnl_vnd = (close_price - cost_k) * volume * 1000 
        pnl_percent = ((close_price - cost_k) / cost_k) * 100 if cost_k > 0 else 0
        total_pnl_vnd += pnl_vnd
        
        # ACTION & RADAR LOGIC
        if signal_panicsell:
            radar_alert = "🚨 <b>PANIC SELL (THIÊN NGA ĐEN):</b> Hiện tượng bán tháo hoảng loạn, rớt giá thảm khốc kèm Vol lớn. Sút ngay lập tức để bảo vệ vốn!"
            action = "BÁN THÁO (Cảnh Báo Sập) 🔴"
        elif pnl_percent <= -10:
            radar_alert = "💀 <b>VI PHẠM NẶNG (-10%):</b> Giá đã xuyên thủng ngưỡng chịu đựng tối đa. Cắt lỗ toàn bộ để bảo vệ vốn ngay lập tức!"
            action = "BÁN HẾT - CẮT LỖ 🔴"
        elif pnl_percent <= -7:
            radar_alert = "✂️ <b>QUẢN TRỊ RỦI RO (-7%):</b> Khoản lỗ đã chạm ngưỡng cảnh báo. Hãy bán ít nhất 1/2 vị thế để hạ tỷ trọng, đưa tài khoản về thế an toàn!"
            action = "CẮT 1/2 - HẠ TỶ TRỌNG 🔴"
        elif signal_phankyam:
            radar_alert = "🛑 <b>CẢNH BÁO TẠO ĐỈNH:</b> MACD đã xuất hiện phân kỳ âm 2/3 đoạn. Động lực tăng đã cạn. Chốt lời và thoát toàn bộ hàng!"
            action = "BÁN TOÀN BỘ 🔴"
        elif signal_daodong:
            radar_alert = "⚠️ <b>RỦI RO NGỰA HẠN:</b> Giá dao động lỏng lẻo, kéo xả biên độ lớn. Đây là vùng đỉnh ngắn hạn, chủ động chốt lời bảo vệ thành quả!"
            action = "CHỐT LỜI NGẮN HẠN 🔴"
        elif signal_sangtay:
            radar_alert = "🚨 <b>BÁO ĐỘNG:</b> Lái đang sang tay hàng cho nhỏ lẻ. Dòng tiền thông minh rút ra. Cân nhắc chốt lời ngay!"
            action = "CÂN NHẮC CHỐT LỜI 🔴"
        elif signal_gaynen:
            radar_alert = "❌ <b>BULL-TRAP:</b> Cổ phiếu gãy nền đang test lại hồi phục kỹ thuật. KHÔNG mua trung bình giá. Canh sút ngay lập tức!"
            action = "SÚT DỨT KHOÁT 🔴"
        elif signal_chammay:
            radar_alert = "☁️ <b>KHÁNG CỰ MÂY:</b> Hàng kênh dưới chạm biên trên kháng cự. Mây còn dày cộp không thể có Uptrend. Bán ngay để xoay vòng vốn!"
            action = "CƠ CẤU XOAY VÒNG 🔴"
        else:
            radar_alert = ""
            if pnl_percent >= 0:
                action = "Gồng Lãi an toàn 🟢"
            else:
                action = "Theo dõi / Quản trị 🟡"
            
        # Chốt lời hình tháp
        if pnl_percent > 50:
            radar_alert += f"\n🔺 <i>Nhắc nhở Hình Tháp:</i> Đã siêu lợi nhuận > 50%. Càng lên cao tỷ trọng càng phải giảm. Bán chốt lời từng phần!"
        elif pnl_percent > 30:
            radar_alert += f"\n🔺 <i>Nhắc nhở Hình Tháp:</i> Đã lãi > 30%. Hãy đưa bớt tiền về túi theo đà tăng kéo thốc."
            
        # Format message snippet
        emoji_pnl = "🟢" if pnl_vnd >= 0 else "🔴"
        sign_pnl = "+" if pnl_vnd >= 0 else ""
        
        msg_snip = (
            f"💠 <b>Mã CK: {symbol}</b> | Khối lượng: {int(volume):,}\n"
            f"Giá hiện tại: <b>{close_price:,.2f}</b> (Vốn: {cost_k:,.2f})\n"
            f"📊 Lợi nhuận: {emoji_pnl} {sign_pnl}{pnl_vnd:,.0f} VNĐ ({sign_pnl}{pnl_percent:.2f}%)\n"
        )
        
        if radar_alert:
            msg_snip += f"📡 <b>SMART SELL RADAR:</b>\n{radar_alert}\n"
            msg_snip += f"⚡️ Hành động: <b>{action}</b>"
            messages.append(msg_snip)
            
    save_portfolio(updated_portfolio)
    
    if not messages:
        logger.info("No Radar sell signals detected in periodic scan. Skipping notification.")
        return

    sign_total = "+" if total_pnl_vnd >= 0 else ""
    # Construct final message
    final_message = (
        f"TING! App Smart Money Hunter báo:\n"
        f"⏱ <b>BÁO CÁO DANH MỤC & ĐIỂM BÁN</b>\n"
        f"<i>Cập nhật: {now.strftime('%H:%M %d/%m/%Y')}</i>\n\n" +
        "\n\n".join(messages) +
        f"\n\n💰 <b>TỔNG LỢI NHUẬN TẠM TÍNH: {sign_total}{total_pnl_vnd:,.0f} VNĐ</b>"
    )
    
    # Send via Telegram API
    if not bot_token or not chat_id:
        logger.info(f"DRY RUN - WOULD SEND THE FOLLOWING TO TELEGRAM:\n{final_message}")
        return
        
    telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": final_message,
        "parse_mode": "HTML"
    }
    
    try:
        resp = requests.post(telegram_url, json=payload)
        if resp.status_code != 200:
            logger.error(f"Failed to send Telegram message: {resp.text}")
        else:
            logger.info("Telegram alert sent successfully.")
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")

def auto_save_daily_leaders():
    """Fetches Top 10 leaders and saves them to SQL History at 16:00 every day."""
    logger.info("Executing daily 16:00 Market Analysis History Backup...")
    try:
        # 1. Run the FULL market scan for all stocks and SAVE TO HISTORY (SQL Server)
        logger.info("Executing comprehensive full market scan with History Backup...")
        results = MarketService.run_full_market_scan(save_history=True)
        
        # 1.5 Save to Local SQLite History
        logger.info("Auto-Snapshot: Saving Top 5 Leaders to local SQLite...")
        DBService.take_snapshot()
        
        # 2. Extract Top 10 leaders from the results (they are already ranked)
        leaders = [r for r in results if r.get('rank') is not None and r.get('rank') <= 10]
        leaders.sort(key=lambda x: x.get('rank', 99))
        
        logger.info(f"Successfully finished full market scan. Saved {len(results)} symbols to history.")
        
        # 3. Send a detailed summary to Telegram
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if bot_token and chat_id:
            if leaders:
                leader_lines = []
                for l in leaders:
                    shark = "💎" if l.get('is_shark_dominated') else ""
                    storm = "🛡️" if l.get('is_storm_resistant') else ""
                    line = f"#{l['rank']} <b>{l['symbol']}</b> (P: {l['price']:.1f}, {l['change']:+.1f}%) {shark}{storm}"
                    leader_lines.append(line)
                
                leader_list_str = "\n".join(leader_lines)
                msg = (
                    f"📊 <b>BÁO CÁO KẾT PHIÊN {datetime.now().strftime('%d/%m/%Y')}</b>\n\n"
                    f"✅ Đã lưu trữ dữ liệu phân tích của {len(results)} mã vào SQL Server.\n\n"
                    f"🏆 <b>TOP 10 CỔ PHIẾU MẠNH NHẤT:</b>\n"
                    f"{leader_list_str}\n\n"
                    f"<i>Sau này bạn có thể truy vấn bảng MarketAnalysisHistory để xem lại.</i>"
                )
            else:
                msg = f"📊 <b>BÁO CÁO KẾT PHIÊN {datetime.now().strftime('%d/%m/%Y')}</b>\n\n✅ Đã hoàn thành sao lưu dữ liệu toàn thị trường vào SQL Server."
                
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=10)
            
    except Exception as e:
        logger.error(f"Error in auto_save_daily_leaders: {e}")
        send_system_alert(f"Lỗi khi lưu dữ liệu lịch sử lúc 16:00: {e}")

def send_top10_alert():
    """Fetches top 10 leaders and sends an alert to Telegram"""
    logger.info("Fetching Top 10 Leaders for Telegram Alert...")
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set. Skipping Top 10 Alert.")
        return

    try:
        leaders = MarketService.get_top_leaders(limit=10)
        if not leaders:
            logger.warning("No top leaders found for alert.")
            return

        now = datetime.now()
        
        # Format message
        header = (
            f"🏆 <b>DANH SÁCH TOP 10 SIÊU CỔ PHIẾU</b> 🏆\n"
            f"<i>Cập nhật: {now.strftime('%H:%M %d/%m/%Y')}</i>\n\n"
        )
        
        leader_msgs = []
        for i, res in enumerate(leaders):
            symbol = res['symbol']
            score = res['score']
            price = res['price']
            change = res['change']
            tag = res.get('tag', '')
            
            emoji = "🟢" if change >= 0 else "🔴"
            sign = "+" if change >= 0 else ""
            
            # Rank and Score
            msg = (
                f"{i+1}. <b>{symbol}</b> ({tag})\n"
                f"   💰 Giá: <b>{price:,.1f}</b> ({emoji} {sign}{change}%)\n"
                f"   🚀 Leader Score: <b>{score:.1f}</b>"
            )
            leader_msgs.append(msg)
            
        footer = "\n\n💡 <i>Hệ thống tự động lọc theo Leader Score (Dòng tiền + Sức mạnh giá).</i>"
        
        final_message = header + "\n\n".join(leader_msgs) + footer
        
        # Send via Telegram API
        telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": final_message,
            "parse_mode": "HTML"
        }
        
        resp = requests.post(telegram_url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Top 10 Telegram alert sent successfully.")
        else:
            logger.error(f"Failed to send Top 10 alert: {resp.text}")
            
    except Exception as e:
        logger.error(f"Error in send_top10_alert: {e}")

def run_bot_scheduler():
    logger.info("Initializing Telegram Bot Scheduler & Cache...")
    init_portfolio_cache()
    
    # Schedule every 30 minutes
    schedule.every(30).minutes.do(check_portfolio_and_send_alert)
    schedule.every(30).minutes.do(send_top10_alert)
    
    # Daily scan at 16:00
    schedule.every().day.at("16:00").do(auto_save_daily_leaders)
    
    # Hourly scan during trading session
    def hourly_trading_scan():
        now = datetime.now()
        if now.weekday() < 5 and 9 <= now.hour <= 16:
            logger.info("Scheduled Hourly Trading Scan triggered...")
            MarketService.run_full_market_scan()
            
    schedule.every().hour.at(":05").do(hourly_trading_scan)
    
    # Startup warmup
    def startup_warmup():
        logger.info("Startup cache warmup triggered...")
        MarketService.run_full_market_scan()
    
    threading.Thread(target=startup_warmup, daemon=True).start()

    logger.info("Telegram Bot Scheduler started.")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    check_portfolio_and_send_alert()
