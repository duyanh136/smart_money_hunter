import base64
import os

def load_api_key(file_path):
    """
    Reads a file containing a base64 encoded API Key,
    decodes it, and returns the raw string.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            encoded_content = f.read().strip()
            
        # Decode
        decoded_bytes = base64.b64decode(encoded_content)
        api_key = decoded_bytes.decode('utf-8')
        return api_key
        
    except Exception as e:
        raise ValueError(f"Failed to decode config: {e}")
