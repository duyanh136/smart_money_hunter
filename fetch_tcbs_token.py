import sys
import os
# Add the project directory to sys.path to import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.tcbs_service import tcbs_service
import getpass

def main():
    print("--- TCBS Token Fetcher ---")
    if not tcbs_service.api_key:
        print("Error: TCBS_API_KEY not found in .env")
        return

    print(f"API Key: {tcbs_service.api_key[:10]}...")
    otp = input("Please enter your TCBS iOTP (from TCInvest app): ")
    
    if tcbs_service.fetch_token_with_otp(otp):
        print("[SUCCESS] Token successfully fetched and saved to .tcbs_token")
        print("MarketService will now prioritize TCBS data.")
    else:
        print("[FAILED] Failed to fetch token. Check your API Key and OTP.")

if __name__ == "__main__":
    main()
