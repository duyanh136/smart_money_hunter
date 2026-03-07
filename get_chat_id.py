import os
import requests
from dotenv import load_dotenv

load_dotenv()

bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

if not bot_token:
    print("Error: TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

try:
    response = requests.get(url)
    data = response.json()
    
    if data.get("ok"):
        results = data.get("result", [])
        if not results:
            print("\nWaiting for message... Please go to Telegram and send any message (e.g. 'hello') to your bot: @DanhMuc_CK_TCBS1_BOT")
        else:
            # Get the latest message
            latest_update = results[-1]
            if "message" in latest_update:
                chat_id = latest_update["message"]["chat"]["id"]
                username = latest_update["message"]["from"].get("username", "Unknown")
                print(f"\nSUCCESS! Found message from @{username}")
                print(f"Your Chat ID is: {chat_id}")
                print("We will now update your .env file with this Chat ID.")
            else:
                print("\nReceived an update, but it wasn't a standard message.")
    else:
        print(f"\nAPI Error: {data.get('description')}")
except Exception as e:
    print(f"Error fetching updates: {e}")
