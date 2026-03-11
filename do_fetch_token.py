import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.tcbs_service import tcbs_service

otp = "216944"
success = tcbs_service.fetch_token_with_otp(otp)
if success:
    print(f"SUCCESS: Token generated and saved to .tcbs_token")
else:
    print("FAILED to generate token.")
