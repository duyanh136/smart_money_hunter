import websocket
import threading
import time
import json
import logging
import base64
from services.tcbs_service import tcbs_service

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

WS_URL = "wss://openapi.tcbs.com.vn/ws/ouranos/v1/stream"

class OuranosDebug:
    def __init__(self):
        self.ws = None
        self.running = False
        
    def start(self):
        token = tcbs_service.token
        if not token:
            print("No Token found. Please run setup first or check .tcbs_token")
            return

        self.token = token
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(WS_URL,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        
        self.running = True
        t = threading.Thread(target=self.ws.run_forever)
        t.daemon = True
        t.start()
        
        # Keep alive loop
        try:
            while self.running:
                time.sleep(2)
                if self.ws.sock and self.ws.sock.connected:
                    # Spec: Client cần gửi message để giữ kết nối d|po
                    self.ws.send("d|po")
        except KeyboardInterrupt:
            self.running = False
            self.ws.close()

    def on_open(self, ws):
        print("### Connected ###")
        # Auth
        encoded_token = base64.b64encode(self.token.encode('utf-8')).decode('utf-8')
        auth_msg = f"d|a|||{encoded_token}"
        ws.send(auth_msg)
        print(f"Sent Auth: {auth_msg[:20]}...")

    def on_message(self, ws, message):
        # print(f"Raw: {message}")
        
        if message.startswith("d|0|"):
             # Auth response
             print(f"Auth Response: {message}")
             if "success\":true" in message:
                 # Subscribe after auth
                 # Spec: d|st|<code1+code2>|<ticker1,ticker2>
                 # C001: Price History (Intraday Match?)
                 # C002S60: Supply Demand 1m
                 tickers = "VIC,TCB" 
                 codes = "C001+C002S60"
                 sub_msg = f"d|st|{codes}|{tickers}"
                 ws.send(sub_msg)
                 print(f"Sent Subscribe: {sub_msg}")
                 
        elif "C001|" in message or "C002" in message:
             # Data
             # Format: C001|TCB|{json}
             parts = message.split('|')
             if len(parts) >= 3:
                 code = parts[0]
                 symbol = parts[1]
                 payload = parts[2]
                 print(f"\n[{code}] {symbol}: {payload}")

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("### Closed ###")
        self.running = False

if __name__ == "__main__":
    debug = OuranosDebug()
    debug.start()
