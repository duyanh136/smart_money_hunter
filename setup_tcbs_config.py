import base64
import os
import getpass
from services.config_loader import load_api_key

def main():
    print("=== TCBS CONFIG SETUP ===")
    print("This script will help you save your TCBS API Key securely (Base64 encoded).")
    
    # 1. Get Input
    api_key = input("Enter your TCBS API Key (hidden input): ").strip()
    if not api_key:
        api_key = getpass.getpass("Enter your TCBS API Key (hidden input): ").strip()
        
    if not api_key:
        print("Error: API Key cannot be empty.")
        return

    file_path = "tcbs_config.enc"
    
    # 2. Encode and Save
    try:
        encoded_bytes = base64.b64encode(api_key.encode('utf-8'))
        encoded_str = encoded_bytes.decode('utf-8')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(encoded_str)
            
        print(f"\n[SUCCESS] API Key saved to '{file_path}'")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to save config: {e}")
        return

    # 3. Verify (Read -> Decode -> Handle Error)
    print("\n--- Verifying Configuration ---")
    try:
        decoded_key = load_api_key(file_path)
        
        if decoded_key == api_key:
            mask_key = decoded_key[:5] + "*" * (len(decoded_key) - 5)
            print(f"[SUCCESS] Verified! Read back key: {mask_key}")
        else:
            print("[ERROR] Verification failed! Decoded key does not match input.")
            
    except FileNotFoundError:
        print(f"[ERROR] File '{file_path}' not found.")
    except ValueError as ve:
        print(f"[ERROR] Decoding failed: {ve}")
    except Exception as e:
        print(f"[ERROR] Unexpected error during verification: {e}")

if __name__ == "__main__":
    main()
