import time
import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.sql_utils import SQLUtils
from services.tcbs_socket import tcbs_stream
from services.tcbs_service import tcbs_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_sync():
    print("--- Testing SQL Real-time Sync ---")
    
    # 1. Test manual upsert
    print("Test 1: Manual Upsert...")
    SQLUtils.upsert_price("VND_TEST", 15.5, 1000000)
    price = SQLUtils.get_price("VND_TEST")
    if price == 15.5:
        print("[OK] Manual Upsert/Get successful.")
    else:
        print(f"[FAILED] Manual Upsert/Get. Got {price}")
        return

    # 2. Test WebSocket Integration (Simulation)
    if not tcbs_service.token:
        print("[SKIP] WebSocket test (No token).")
        return

    print("Test 2: WebSocket Sync Simulation...")
    tcbs_stream.token = tcbs_service.token
    tcbs_stream.running = True # Fast-track running state
    
    # Start SQL worker
    import threading
    worker = threading.Thread(target=tcbs_stream._sql_worker_loop, daemon=True)
    worker.start()
    
    # Push dummy data into queue
    print("Pushing data to queue...")
    tcbs_stream.sql_queue.put(("TCB_TEST", 45.5, 2000000))
    tcbs_stream.sql_queue.put(("FPT_TEST", 120.0, 3000000))
    
    print("Waiting 3 seconds for batch sync...")
    time.sleep(3)
    
    p_tcb = SQLUtils.get_price("TCB_TEST")
    p_fpt = SQLUtils.get_price("FPT_TEST")
    
    if p_tcb == 45.5 and p_fpt == 120.0:
        print("[OK] WebSocket Worker Sync successful.")
    else:
        print(f"[FAILED] Worker Sync. TCB: {p_tcb}, FPT: {p_fpt}")
    
    tcbs_stream.running = False

if __name__ == "__main__":
    test_sync()
