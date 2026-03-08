import sys
import os
import time
import logging
import json

# Add current dir to path
sys.path.append(os.path.abspath(os.curdir))

from services.tcbs_socket import TCBSStreamService
from unittest.mock import MagicMock, patch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_retry_limit():
    print("\n--- Testing Retry Limit (3 failures) ---")
    service = TCBSStreamService(token="invalid_token")
    service.max_retries = 3
    service.alert_cooldown = 0 # No cooldown for testing
    
    with patch('services.telegram_bot.send_system_alert') as mock_alert:
        # Simulate 3 closes
        for i in range(1, 4):
            print(f"Simulating Close #{i}")
            service.running = True
            service.on_close(None, None, None)
            time.sleep(0.1)
        
        if service.retry_count == 3 and not service.running:
            print("âœ… SUCCESS: Service stopped after 3 retries.")
        else:
            print(f"âŒ FAILED: retry_count={service.retry_count}, running={service.running}")
            
        if mock_alert.called:
            print("âœ… SUCCESS: Telegram alert was triggered.")
        else:
            print("âŒ FAILED: Telegram alert NOT triggered.")

def test_auth_failure_message():
    print("\n--- Testing Auth Failure Message Detection ---")
    service = TCBSStreamService(token="invalid_token")
    service.alert_cooldown = 0
    
    with patch('services.telegram_bot.send_system_alert') as mock_alert:
        service.running = True
        # Simulate TCBS sending auth failure message
        fail_payload = json.dumps({"success": False, "message": "Invalid Token for testing"})
        service.on_message(None, f"d|0|{fail_payload}")
        
        if not service.running:
            print("âœ… SUCCESS: Service stopped immediately on Auth Failure.")
        else:
            print("âŒ FAILED: Service still running after Auth Failure.")
            
        if mock_alert.called:
            print("âœ… SUCCESS: Telegram alert was triggered with reason.")
        else:
            print("âŒ FAILED: Telegram alert NOT triggered.")

if __name__ == "__main__":
    test_retry_limit()
    test_auth_failure_message()
