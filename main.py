from fastapi import FastAPI, Request
from pydantic import BaseModel
import time, hmac, base64, hashlib, requests, os

app = FastAPI()

# Environment variables (set in Railway)
API_KEY = os.getenv("6819428a61d4190001720013")
API_SECRET = os.getenv("65f5d589-ed17-4cae-a0c0-7e38693ff669")
API_PASSPHRASE = os.getenv("zoeiscute")

# KuCoin endpoint
KUCOIN_URL = "https://api.kucoin.com"

# Data format expected from TradingView alert
class TradeSignal(BaseModel):
    symbol: str
    side: str   # "buy" or "sell"
    qty: float

@app.post("/trade")
async def trade(signal: TradeSignal):
    try:
        # Timestamp in ms
        now = str(int(time.time() * 1000))

        # Request body
        order = {
            "clientOid": str(int(time.time() * 1000)),
            "side": signal.side,
            "symbol": signal.symbol,
            "type": "market",
            "size": str(signal.qty)
        }

        body = json_string = str(order).replace("'", '"')
        str_to_sign = now + "POST" + "/api/v1/orders" + json_string
        signature = base64.b64encode(
            hmac.new(API_SECRET.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest()
        )

        passphrase = base64.b64encode(
            hmac.new(API_SECRET.encode('utf-8'), API_PASSPHRASE.encode('utf-8'), hashlib.sha256).digest()
        )

        headers = {
            "KC-API-KEY": API_KEY,
            "KC-API-SIGN": signature.decode(),
            "KC-API-TIMESTAMP": now,
            "KC-API-PASSPHRASE": passphrase.decode(),
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }

        response = requests.post(f"{KUCOIN_URL}/api/v1/orders", headers=headers, data=json_string)
        print(response.json())

        if response.status_code == 200 or response.status_code == 201:
            return {"status": "success", "order": response.json()}
        else:
            return {"status": "error", "details": response.json()}

    except Exception as e:
        return {"status": "error", "message": str(e)}
