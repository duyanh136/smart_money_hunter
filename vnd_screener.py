import requests

def get_liquid_stocks():
    url = "https://finfo-api.vndirect.com.vn/v4/screener"
    payload = {
        "filters": [
            {"key": "avgTradingValue20Day", "operator": "GTE", "value": 5000000000}, # > 5 ty
            {"key": "type", "operator": "EQ", "value": "STOCK"}
        ],
        "size": 1000,
        "offset": 0
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers)
        data = res.json()
        
        # VNDirect doesn't support 'type' in screener sometimes. Let's try GET instead if POST fails
        if "data" in data and "hitElements" in data["data"]:
            return [x["code"] for x in data["data"]["hitElements"]]
    except Exception as e:
        print("Error:", e)

print(get_liquid_stocks())
