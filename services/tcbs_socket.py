import websocket
import threading
import time
import json
import logging
import base64
from typing import Dict, Any, Optional, List
import queue
from services.sql_utils import SQLUtils

logger = logging.getLogger(__name__)

class TCBSStreamService:
    WS_URL = "wss://openapi.tcbs.com.vn/ws/thesis/v1/stream/normal"
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.ws = None
        self.thread = None
        self.running = False
        self.latest_data: Dict[str, Any] = {} # Symbol -> Data Snapshot
        self.subscribed_topics = set()
        self.lock = threading.Lock()
        self.on_update_callback = None # Callback function(symbol, data)
        
        # SQL Sync Queue
        self.sql_queue = queue.Queue()
        self.sql_worker_thread = None

        # Safeguard & Alerts
        self.retry_count = 0
        self.max_retries = 3
        self.last_alert_time = 0
        self.alert_cooldown = 1800 # 30 minutes

    def start(self):
        if not self.token:
            logger.warning("TCBSStream: No token provided. Cannot start.")
            return

        self.running = True
        # websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(self.WS_URL,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        
        self.thread = threading.Thread(target=self.ws.run_forever, kwargs={'ping_interval': 10, 'ping_timeout': 5})
        self.thread.daemon = True
        self.thread.start()
        
        # Start Heartbeat Thread
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        
        # Start SQL Worker Thread
        if not self.sql_worker_thread or not self.sql_worker_thread.is_alive():
            self.sql_worker_thread = threading.Thread(target=self._sql_worker_loop, daemon=True)
            self.sql_worker_thread.start()

    def _sql_worker_loop(self):
        """Background worker to batch SQL updates and avoid thread explosion"""
        logger.info("TCBSStream: SQL Worker Started.")
        batch = {} # symbol -> {price, volume}
        last_sync = time.time()
        
        while self.running:
            try:
                # Wait for data with timeout to allow periodic batch commits
                try:
                    symbol, price, volume = self.sql_queue.get(timeout=1.0)
                    batch[symbol] = {'price': price, 'volume': volume}
                except queue.Empty:
                    pass
                
                # Sync to DB every 2 seconds if there's data
                if (time.time() - last_sync > 2.0) and batch:
                    for sym, vals in batch.items():
                        SQLUtils.upsert_price(sym, vals['price'], vals['volume'])
                    batch.clear()
                    last_sync = time.time()
                    
            except Exception as e:
                logger.error(f"SQL Worker Error: {e}")
                time.sleep(1)

    def _heartbeat_loop(self):
        while self.running:
            time.sleep(2)
            if self.ws and getattr(self.ws, 'sock', None) and self.ws.sock.connected:
                try:
                    self.ws.send("d|p|||") # Ping
                except:
                    pass

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()

    def on_open(self, ws):
        logger.info("TCBSStream: Connected.")
        # Auth
        # Spec: d|a|||base64(token)
        encoded_token = base64.b64encode(self.token.encode('utf-8')).decode('utf-8')
        auth_msg = f"d|a|||{encoded_token}"
        ws.send(auth_msg)
        logger.info("TCBSStream: Sent Auth.")

        if self.subscribed_topics:
            topics = list(self.subscribed_topics)
            logger.info(f"TCBSStream: Auto-resubscribing to {len(topics)} topics...")
            def delayed_sub():
                time.sleep(1)
                self.subscribe(topics)
            threading.Thread(target=delayed_sub, daemon=True).start()

    def on_message(self, ws, message):
        try:
            # Format: type|len|data
            # Realtime data usually starts with 's' or 'd'
            # Spec says "Text frame".
            # Response: s|1|... s|2|...
            
            # Simple parsing
            parts = message.split('|')
            if len(parts) < 3: return
            
            msg_type = parts[0]
            # msg_len = parts[1]
            payload = parts[2]
            
            if msg_type == 'd':
                # System message
                # check auth success: d|0|{"success":true...}
                try:
                    data = json.loads(payload)
                    if data.get('success') is False:
                        reason = data.get('message', 'Unknown reason')
                        logger.error(f"TCBSStream: Auth Failed! {reason}")
                        self._handle_fatal_error(f"Xác thực thất bại: {reason}")
                    elif data.get('success') is True:
                        logger.info("TCBSStream: Auth Success.")
                        self.retry_count = 0 # Reset on successful auth
                except:
                    pass
                
            elif msg_type == 's':
                # Data message
                # s|1|{...} (Bid), s|2| (Offer), s|4| (Base), s|5| (Match), s|6| (TickerMatch)
                try:
                    data = json.loads(payload)
                    symbol = data.get('symbol', '').upper()
                    if symbol:
                        if symbol not in self.latest_data:
                            self.latest_data[symbol] = {}
                        
                        # Merge data
                        self.latest_data[symbol].update(data)

                        # Queue for SQL Sync
                        # Prioritize matchPrice, fallback to current price or reference price
                        price = data.get('matchPrice') or data.get('price') or data.get('refPrice')
                        vol = data.get('matchVolume') or data.get('accumulatedVolume') or 0
                        if price:
                            # Normalize price (TCBS often sends in 1000s, but not always)
                            real_price = price / 1000 if price > 1000 else price
                            self.sql_queue.put((symbol, real_price, vol))
                        
                        # Notify external callback
                        if self.on_update_callback:
                            self.on_update_callback(symbol, self.latest_data[symbol])
                except json.JSONDecodeError:
                    pass # Silently ignore non-JSON 's' messages if any
        except Exception as e:
            logger.error(f"TCBSStream: Error parsing message - {e}")

    def on_error(self, ws, error):
        # Suppress common close frame noise (opcode 8) from terminal
        err_str = str(error)
        if "opcode=8" in err_str or "fin=1" in err_str:
            logger.info("TCBSStream: Server suggested connection close.")
            return
        logger.error(f"TCBSStream Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logger.info(f"TCBSStream: Connection closed (Status: {close_status_code or 'N/A'})")
        was_running = self.running
        self.running = False
        if was_running:
            self.retry_count += 1
            if self.retry_count >= self.max_retries:
                logger.error(f"TCBSStream: Max retries ({self.max_retries}) reached. Stopping.")
                self._handle_fatal_error(f"Kết nối thất bại {self.max_retries} lần liên tiếp. Dừng để bảo vệ IP.")
                return

            logger.info(f"TCBSStream: Reconnect attempt {self.retry_count}/{self.max_retries} in 10 seconds...")
            def reconnect():
                time.sleep(10)
                from services.tcbs_service import tcbs_service
                # Ensure we have the latest token
                self.token = tcbs_service.token
                self.start()
            threading.Thread(target=reconnect, daemon=True).start()

    def _handle_fatal_error(self, message: str):
        """Stops the service and sends a Telegram alert with cooldown"""
        self.running = False
        if self.ws:
            self.ws.close()
        
        now = time.time()
        if now - self.last_alert_time > self.alert_cooldown:
            from services.telegram_bot import send_system_alert
            alert_text = (
                f"⚠️ <b>TCBS Connection Error</b>\n"
                f"Lý do: {message}\n\n"
                f"💡 <b>Hành động:</b> Vui lòng kiểm tra lại Token hoặc lấy Token mới bằng file <code>Update_TCBS_Token.bat</code>."
            )
            send_system_alert(alert_text)
            self.last_alert_time = now
        
    def subscribe(self, symbols: list):
        if not self.ws or getattr(self.ws, 'sock', None) is None or not getattr(self.ws.sock, 'connected', False):
            return
            
        # Filter symbols
        unique_syms = set(s.upper() for s in symbols)
        self.subscribed_topics.update(unique_syms)
        
        # Chunking: URL/Message limit? Let's do 20 at a time
        chunk = []
        for s in unique_syms:
            chunk.append(s)
            if len(chunk) >= 20:
                self._send_sub(chunk)
                chunk = []
        if chunk:
            self._send_sub(chunk)

    def _send_sub(self, symbols: list):
        sym_str = ",".join(symbols)
        msg = f"d|s|tk|bp+bi+tm+mp+op+fe|{sym_str}"
        try:
            self.ws.send(msg)
            logger.info(f"Subscribed to {len(symbols)} stocks.")
        except Exception as e:
            logger.error(f"Subscribe failed: {e}")

    def get_price(self, symbol: str) -> Optional[float]:
        with self.lock:
            data = self.latest_data.get(symbol.upper())
            if data:
                # Priority: Match Price -> RefPrice
                # data might be partial (e.g. only received 'matchPrice' update)
                # Should store 'price' in latest_data
                
                # Check for 'matchPrice' (string) or 'price'
                p = data.get('matchPrice')
                if p: return float(p)
                
                # If we received Base Price (s|4)
                if 'refPrice' in data:
                    return float(data['refPrice'])
                    
        return None
        
    def get_full_info(self, symbol: str) -> Dict[str, Any]:
        with self.lock:
            return self.latest_data.get(symbol.upper(), {}).copy()

# Global instance
tcbs_stream = TCBSStreamService()
