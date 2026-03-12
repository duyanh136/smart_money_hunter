import logging
import os
from dotenv import load_dotenv
from services.telegram_bot import send_top10_alert

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_manual_alert():
    print("--- MANUAL TELEGRAM TOP 10 ALERT TEST ---")
    load_dotenv()
    
    # Check if env vars are present
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing in .env")
        return

    print(f"Using Bot Token: {bot_token[:10]}...")
    print(f"Using Chat ID: {chat_id}")
    
    print("\nTriggering send_top10_alert()...")
    send_top10_alert()
    print("\nTest completed. Please check your Telegram chat.")

if __name__ == "__main__":
    test_manual_alert()
