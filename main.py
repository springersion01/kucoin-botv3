from fastapi import FastAPI
from pydantic import BaseModel
from typing import Union
import time, hmac, base64, hashlib, requests, os

app = FastAPI()

class TradeSignal(BaseModel):
    symbol: str
    side: str
    qty: Union[float, str]  # can be float or "ALL"
    action: str = "entry"   # default to 'entry' if not provided

# Function to fetch current balance for a given asset
def get_balance(symbol: str) -> float:
    now = str(int(time.time() * 1000))
    endpoint = "/api/v1/accounts"
    str_to_sign = now + "GET" + endpoint

    signature = base64.b64encode(
        hmac.new(os.getenv("KUCOIN_API_SECRET").encode(), str_to_sign.encode(), hashlib.sha256).digest()
    )
    passphrase = base64.b64encode(
        hmac.new(os.getenv("KUCOIN_API_SECRET").encode(), os.getenv("KUCOIN_PASSPHRASE").encode(), hashlib.sha256).digest()
    )

    headers = {
        "KC-API-KEY": os.getenv("KUCOIN_API_KEY"),
        "KC-API-SIGN": signature.decode(),
        "KC-API-TIMESTAMP": now,
        "KC-API-PASSPHRASE": passphrase.decode(),
        "KC-API-KEY-VERSION": "2",
        "Content-Type": "application/json"
    }

    response = requests.get("https://api.kucoin.com" + endpoint, headers=headers)
    data = response.json()

    if "data" not in data:
        print("Error fetching balance:", data)
        return 0.0

    base_asset = symbol.split("-")[0]  # e.g., "SOL" from "SOL-USDT"
    for account in data["data"]:
        if account["currency"] == base_asset and account["type"] == "trade":
            return float(account["available"])

    return 0.0

@app.post("/trade")
async def trade(signal: TradeSignal):
    print("Webhook received:", signal.dict())

    try:
        now = str(int(time.time() * 1000))
        order = {
            "clientOid": now,
            "side": signal.side,
            "symbol": signal.symbol,
            "type": "market"
        }

        # Handle exits with dynamic balance
        if signal.action == "exit" and str(signal.qty).upper() == "ALL":
            actual_size = get_balance(signal.symbol)
            if actual_size <= 0:
                return {"status": "error", "message": "No balance available to exit."}
            order["size"] = str(actual_size)
        else:
            order["funds"] = str(signal.qty)

        json_body = str(order).replace("'", '"')

        str_to_sign = now + "POST" + "/api/v1/orders" + json_body
        signature = base64.b64encode(
            hmac.new(os.getenv("KUCOIN_API_SECRET").encode(), str_to_sign.encode(), hashlib.sha256).digest()
        )
        passphrase = base64.b64encode(
            hmac.new(os.getenv("KUCOIN_API_SECRET").encode(), os.getenv("KUCOIN_PASSPHRASE").encode(), hashlib.sha256).digest()
        )

        headers = {
            "KC-API-KEY": os.getenv("KUCOIN_API_KEY"),
            "KC-API-SIGN": signature.decode(),
            "KC-API-TIMESTAMP": now,
            "KC-API-PASSPHRASE": passphrase.decode(),
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.post("https://api.kucoin.com/api/v1/orders", headers=headers, data=json_body)
        print("KuCoin response:", response.json())

        return {"status": "sent", "details": response.json()}

    except Exception as e:
        print("Error:", str(e))
        return {"status": "error", "message": str(e)}
