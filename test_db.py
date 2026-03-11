import os
import sys
import logging
from dotenv import load_dotenv

# Set up logging to stdout
logging.basicConfig(level=logging.DEBUG)

load_dotenv()
print("Env SQL_SERVER:", os.getenv('SQL_SERVER'))
print("Env SQL_DATABASE:", os.getenv('SQL_DATABASE'))
print("Env SQL_USER:", os.getenv('SQL_USER'))
print("Env SQL_DRIVER:", os.getenv('SQL_DRIVER'))

try:
    from services.sql_utils import SQLUtils
    print('Testing conn...')
    conn = SQLUtils.get_connection()
    if conn:
        print('Connection Result: SUCCESS', type(conn))
        conn.close()
    else:
        print('Connection Result: FAILED (Returned None)')
except Exception as e:
    print('Exception:', e)
