import websocket
import threading
import time
import json
import logging
import base64
from typing import Dict, Any, Optional

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

    def _heartbeat_loop(self):
        while self.running:
            time.sleep(2)
            if self.ws and self.ws.sock and self.ws.sock.connected:
                try:
                    self.ws.send("d|p|||") # Ping
                except:
                    pass

    def on_open(self, ws):
        logger.info("TCBSStream: Connected.")
        # Auth
        # Spec: d|a|||base64(token)
        encoded_token = base64.b64encode(self.token.encode('utf-8')).decode('utf-8')
        auth_msg = f"d|a|||{encoded_token}"
        ws.send(auth_msg)
        logger.info("TCBSStream: Sent Auth.")

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
                pass
                
            elif msg_type == 's':
                # Data message
                # s|1|{...} (Bid), s|2| (Offer), s|4| (Base), s|5| (Match), s|6| (TickerMatch)
                # Parse JSON
                try:
                    data = json.loads(payload)
                    symbol = data.get('symbol', '').upper()
                    if not symbol: return
                    
                    with self.lock:
                        if symbol not in self.latest_data:
                            self.latest_data[symbol] = {}
                        
                        # Merge data
                        self.latest_data[symbol].update(data)
                        
                        # Notify external callback
                        if self.on_update_callback:
                            self.on_update_callback(symbol, self.latest_data[symbol])
                        
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.error(f"Stream Parse Error: {e}")

    def on_error(self, ws, error):
        logger.error(f"TCBSStream Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logger.info("TCBSStream: Closed.")
        # Reconnect logic could go here
        
    def subscribe(self, symbols: list):
        if not self.ws or not self.ws.sock or not self.ws.sock.connected:
            return
            
        # Filter symbols
        unique_syms = set(s.upper() for s in symbols)
        # Check against already subscribed? No, just resubscribe is fine or diff
        # Spec: d|s|tk|bp+bi+tm+mp+op+fe|MX1,MX2
        
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
