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
        sl_type = "Má»c quáº£n trá» 10% (Tá»± Äá»ng)" if is_default_sl else "Má»c ná»n há» trá»£"
        
        emergency_msg = (
            f"ð¨ <b>Cáº¢NH BÃO KHáº¨N Cáº¤P: VI PHáº M Rá»¦I RO!</b> ð¨\n\n"
            f"ð MÃ£ CK: <b>{symbol}</b>\n"
            f"â ï¸ GiÃ¡ hiá»n táº¡i: <b>{current_price:,.2f}</b> ÄÃ£ rá»t dÆ°á»i {sl_type}: <b>{cache_item['current_sl']:,.2f}</b>!\n"
            f"ð©¸ Tráº¡ng thÃ¡i: NgÆ°á»¡ng chá»u Äá»±ng tá»i Äa ÄÃ£ bá» phÃ¡ vá»¡.\n\n"
            f"â¡ï¸ <b>HÃNH Äá»NG Báº®T BUá»C:</b> SÃT Dá»¨T KHOÃT Äá» báº£o vá» NAV ngay láº­p tá»©c!"
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

    formatted_msg = f"ð  <b>Há» THá»NG THÃNG BÃO</b>\n\n{message}"
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
    # If it's a new day, we want to allow alerts again if price is still bad. Wait, 
    # usually we might reset overnight. For simplicity, the 30-min job can 
    # reset alert_sent if the price recovers above the SL, or we reset it at midnight.
    # Let's rebuild the cache here on the scheduled run to ensure it's synced.
    
    # Check if inside trading hours (Mon-Fri, 09:00 - 15:00)
    # Allows a little buffer
    if now.weekday() >= 5: # Saturday or Sunday
        logger.info("Weekend. Skipping check.")
        # return # Comment out return for testing if needed
        pass
    
    hour = now.hour
    minute = now.minute
    time_val = hour * 100 + minute
    
    if time_val < 900 or time_val > 1500:
        logger.info("Outside trading hours (09:00-15:00). Skipping check.")
        # return # Comment out return for testing if needed
        pass

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
        
        # Normalize to thousands (e.g. 61900 -> 61.9)
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

        # Update cache values for realtime monitoring (SL is left as user input base)
        # Cooldown management: if price recovered ABOVE the sl, reset alert_sent
        if close_price > sl_k and alert_sent:
            alert_sent = False
            item['alert_sent'] = False
            logger.info(f"{symbol} recovered above SL. Resetting alert_sent flag.")
            
        # Update global cache with latest SL and alert flag state
        portfolio_cache[symbol] = {
            'current_sl': current_sl,
            'alert_sent': alert_sent
        }
            
        updated_portfolio.append(item)
        
        # PnL calculations
        pnl_vnd = (close_price - cost_k) * volume * 1000 # Assuming price is in '000 VND
        pnl_percent = ((close_price - cost_k) / cost_k) * 100 if cost_k > 0 else 0
        total_pnl_vnd += pnl_vnd
        
        # ACTION & RADAR LOGIC
        if signal_panicsell:
            radar_alert = "ð¨ <b>PANIC SELL (THIÃN NGA ÄEN):</b> Hiá»n tÆ°á»£ng bÃ¡n thÃ¡o hoáº£ng loáº¡n, rá»t giÃ¡ tháº£m khá»c kÃ¨m Vol lá»n. SÃºt ngay láº­p tá»©c Äá» báº£o vá» vá»n!"
            action = "BÃN THÃO (Cáº£nh BÃ¡o Sáº­p) ð´"
        elif pnl_percent <= -10:
            radar_alert = "ð <b>VI PHáº M Náº¶NG (-10%):</b> GiÃ¡ ÄÃ£ xuyÃªn thá»§ng ngÆ°á»¡ng chá»u Äá»±ng tá»i Äa. Cáº¯t lá» toÃ n bá» Äá» báº£o vá» vá»n ngay láº­p tá»©c!"
            action = "BÃN Háº¾T - Cáº®T Lá» ð´"
        elif pnl_percent <= -7:
            radar_alert = "âï¸ <b>QUáº¢N TRá» Rá»¦I RO (-7%):</b> Khoáº£n lá» ÄÃ£ cháº¡m ngÆ°á»¡ng cáº£nh bÃ¡o. HÃ£y bÃ¡n Ã­t nháº¥t 1/2 vá» tháº¿ Äá» háº¡ tá»· trá»ng, ÄÆ°a tÃ i khoáº£n vá» tháº¿ an toÃ n!"
            action = "Cáº®T 1/2 - Háº  Tá»¶ TRá»NG ð´"
        elif signal_phankyam:
            radar_alert = "ð <b>Cáº¢NH BÃO Táº O Äá»NH:</b> MACD ÄÃ£ xuáº¥t hiá»n phÃ¢n ká»³ Ã¢m 2/3 Äoáº¡n. Äá»ng lá»±c tÄng ÄÃ£ cáº¡n. Chá»t lá»i vÃ  thoÃ¡t toÃ n bá» hÃ ng!"
            action = "BÃN TOÃN Bá» ð´"
        elif signal_daodong:
            radar_alert = "â ï¸ <b>Rá»¦I RO NGá»°A Háº N:</b> GiÃ¡ dao Äá»ng lá»ng láº»o, kÃ©o xáº£ biÃªn Äá» lá»n. ÄÃ¢y lÃ  vÃ¹ng Äá»nh ngáº¯n háº¡n, chá»§ Äá»ng chá»t lá»i báº£o vá» thÃ nh quáº£!"
            action = "CHá»T Lá»I NGáº®N Háº N ð´"
        elif signal_sangtay:
            radar_alert = "ð¨ <b>BÃO Äá»NG:</b> LÃ¡i Äang sang tay hÃ ng cho nhá» láº». DÃ²ng tiá»n thÃ´ng minh rÃºt ra. CÃ¢n nháº¯c chá»t lá»i ngay!"
            action = "CÃN NHáº®C CHá»T Lá»I ð´"
        elif signal_gaynen:
            radar_alert = "â <b>BULL-TRAP:</b> Cá» phiáº¿u gÃ£y ná»n Äang test láº¡i há»i phá»¥c ká»¹ thuáº­t. KHÃNG mua trung bÃ¬nh giÃ¡. Canh sÃºt ngay láº­p tá»©c!"
            action = "SÃT Dá»¨T KHOÃT ð´"
        elif signal_chammay:
            radar_alert = "âï¸ <b>KHÃNG Cá»° MÃY:</b> HÃ ng kÃªnh dÆ°á»i cháº¡m biÃªn trÃªn khÃ¡ng cá»±. MÃ¢y cÃ²n dÃ y cá»p khÃ´ng thá» cÃ³ Uptrend. BÃ¡n ngay Äá» xoay vÃ²ng vá»n!"
            action = "CÆ  Cáº¤U XOAY VÃNG ð´"
        else:
            radar_alert = ""
            if pnl_percent >= 0:
                action = "Gá»ng LÃ£i an toÃ n ð¢"
            else:
                action = "Theo dÃµi / Quáº£n trá» ð¡"
            
        # Chá»t lá»i hÃ¬nh thÃ¡p (Scale-out logic)
        if pnl_percent > 50:
            radar_alert += f"\nðº <i>Nháº¯c nhá» HÃ¬nh ThÃ¡p:</i> ÄÃ£ siÃªu lá»£i nhuáº­n > 50%. CÃ ng lÃªn cao tá»· trá»ng cÃ ng pháº£i giáº£m. BÃ¡n chá»t lá»i tá»«ng pháº§n!"
        elif pnl_percent > 30:
            radar_alert += f"\nðº <i>Nháº¯c nhá» HÃ¬nh ThÃ¡p:</i> ÄÃ£ lÃ£i > 30%. HÃ£y ÄÆ°a bá»t tiá»n vá» tÃºi theo ÄÃ  tÄng kÃ©o thá»c."
            
        # Format message snippet
        emoji_pnl = "ð¢" if pnl_vnd >= 0 else "ð´"
        sign_pnl = "+" if pnl_vnd >= 0 else ""
        
        msg_snip = (
            f"ð  <b>MÃ£ CK: {symbol}</b> | Khá»i lÆ°á»£ng: {int(volume):,}\n"
            f"GiÃ¡ hiá»n táº¡i: <b>{close_price:,.2f}</b> (Vá»n: {cost_k:,.2f})\n"
            f"ð Lá»£i nhuáº­n: {emoji_pnl} {sign_pnl}{pnl_vnd:,.0f} VNÄ ({sign_pnl}{pnl_percent:.2f}%)\n"
        )
        
        if radar_alert:
            msg_snip += f"ð¡ <b>SMART SELL RADAR:</b>\n{radar_alert}\n"
            msg_snip += f"â¡ï¸ HÃ nh Äá»ng: <b>{action}</b>"
            messages.append(msg_snip)
            
    save_portfolio(updated_portfolio)
    
    if not messages:
        logger.info("No Radar sell signals detected in periodic scan. Skipping notification.")
        return

    sign_total = "+" if total_pnl_vnd >= 0 else ""
    # Construct final message
    final_message = (
        f"TING! App Smart Money Hunter bÃ¡o:\n"
        f"â± <b>BÃO CÃO DANH Má»¤C & ÄIá»M BÃN</b>\n"
        f"<i>Cáº­p nháº­t: {now.strftime('%H:%M %d/%m/%Y')}</i>\n\n" +
        "\n\n".join(messages) +
        f"\n\nð° <b>Tá»NG Lá»¢I NHUáº¬N Táº M TÃNH: {sign_total}{total_pnl_vnd:,.0f} VNÄ</b>"
    )
    
    # Send via Telegram API
    if not bdef auto_save_daily_leaders():
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
                    shark = "ð" if l.get('is_shark_dominated') else ""
                    storm = "ð¡ï¸" if l.get('is_storm_resistant') else ""
                    line = f"#{l['rank']} <b>{l['symbol']}</b> (P: {l['price']:.1f}, {l['change']:+.1f}%) {shark}{storm}"
                    leader_lines.append(line)
                
                leader_list_str = "\n".join(leader_lines)
                msg = (
                    f"ð <b>BÃO CÃO Káº¾T PHIÃN {datetime.now().strftime('%d/%m/%Y')}</b>\n\n"
                    f"â ÄÃ£ lÆ°u trá»¯ dá»¯ liá»u phÃ¢n tÃ­ch cá»§a {len(results)} mÃ£ vÃ o SQL Server.\n\n"
                    f"ð <b>TOP 10 Cá» PHIáº¾U Máº NH NHáº¤T:</b>\n"
                    f"{leader_list_str}\n\n"
                    f"<i>Sau nÃ y báº¡n cÃ³ thá» truy váº¥n báº£ng MarketAnalysisHistory Äá» xem láº¡i.</i>"
                )
            else:
                msg = f"ð <b>BÃO CÃO Káº¾T PHIÃN {datetime.now().strftime('%d/%m/%Y')}</b>\n\nâ ÄÃ£ hoÃ n thÃ nh sao lÆ°u dá»¯ liá»u toÃ n thá» trÆ°á»ng vÃ o SQL Server."
                
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=10)
            
    except Exception as e:
        logger.error(f"Error in auto_save_daily_leaders: {e}")
        send_system_alert(f"Lá»i khi lÆ°u dá»¯ liá»u lá»ch sá»­ lÃºc 16:00: {e}")

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
            f"ð <b>DANH SÃCH TOP 10 SIÃU Cá» PHIáº¾U</b> ð\n"
            f"<i>Cáº­p nháº­t: {now.strftime('%H:%M %d/%m/%Y')}</i>\n\n"
        )
        
        leader_msgs = []
        for i, res in enumerate(leaders):
            symbol = res['symbol']
            score = res['score']
            price = res['price']
            change = res['change']
            tag = res.get('tag', '')
            
            emoji = "ð¢" if change >= 0 else "ð´"
            sign = "+" if change >= 0 else ""
            
            # Rank and Score
            msg = (
                f"{i+1}. <b>{symbol}</b> ({tag})\n"
                f"   ð° GiÃ¡: <b>{price:,.1f}</b> ({emoji} {sign}{change}%)\n"
                f"   ð Leader Score: <b>{score:.1f}</b>"
            )
            leader_msgs.append(msg)
            
        footer = "\n\nð¡ <i>Há» thá»ng tá»± Äá»ng lá»c theo Leader Score (DÃ²ng tiá»n + Sá»©c máº¡nh giÃ¡).</i>"
        
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
» thá»ng tá»± Äá»ng lá»c theo Leader Score (DÃ²ng tiá»n + Sá»©c máº¡nh giÃ¡).</i>"
        
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
    
    # Daily scan at 16:00 (After Market Close)
    # Job 1: Daily scan at 16:00 (Saves to SQL Server AND SQLite)
    schedule.every().day.at("16:00").do(auto_save_daily_leaders)
    
    # Job 2: Hourly scan during trading session (9:00 - 15:00)
    # This ensures the cache is fresh for daytime users
    def hourly_trading_scan():
        now = datetime.now()
        # Mon-Fri, 9am-4pm
        if now.weekday() < 5 and 9 <= now.hour <= 16:
            logger.info("Scheduled Hourly Trading Scan triggered...")
            MarketService.run_full_market_scan()
            
    schedule.every().hour.at(":05").do(hourly_trading_scan)
    
    # Job 3: One-time scan at startup to warm up the cache
    def startup_warmup():
        logger.info("Startup cache warmup triggered...")
        MarketService.run_full_market_scan()
    
    # Run startup warmup in a separate thread to not block the main loop
    threading.Thread(target=startup_warmup, daemon=True).start()

    logger.info("Telegram Bot Scheduler started. Jobs scheduled: 16:00 Daily + Hourly Trading.")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    logger.info("Running manual check...")
    check_portfolio_and_send_alert()
