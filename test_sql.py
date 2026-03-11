from services.sql_utils import SQLUtils
print("Testing SQL connection from WSL...")
conn = SQLUtils.get_connection()
if conn:
    print("SUCCESS: Connected to SQL Server!")
    conn.close()
else:
    print("FAILED to connect to SQL Server. Network or credential issue.")
