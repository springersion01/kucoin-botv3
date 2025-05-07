from fastapi import FastAPI, Request
from pydantic import BaseModel
import time, hmac, base64, hashlib, requests, os

app = FastAPI()

class TradeSignal(BaseModel):
    symbol: str
    side: str
    qty: str  # Can be "ALL" for exit or float for buy
    action: str = "entry"  # Optional, default to entry

@app.post("/trade")
async def trade(signal: TradeSignal):
    print("Webhook received:", signal.dict())

    try:
        now = str(int(time.time() * 1000))
        order = {
            "clientOid": str(int(time.time() * 1000)),
            "side": signal.side,
            "symbol": signal.symbol,
            "type": "market"
        }

        # Handle entry (buy with funds) vs exit (sell all)
        if signal.action == "exit" and signal.qty == "ALL":
            order["size"] = "100"  # TODO: replace with actual position size if needed
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

