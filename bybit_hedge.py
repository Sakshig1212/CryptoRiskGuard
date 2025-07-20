# bybit_hedge.py
import requests
import time
import hashlib
import hmac
import uuid
import json

from config import BYBIT_API_KEY as api_key, BYBIT_SECRET as secret_key

httpClient = requests.Session()
recv_window = str(5000)
url = "https://api-testnet.bybit.com"  # TESTNET URL

def genSignature(payload, timestamp):
    param_str = str(timestamp) + api_key + recv_window + payload
    hash = hmac.new(bytes(secret_key, "utf-8"), param_str.encode("utf-8"), hashlib.sha256)
    return hash.hexdigest()

def place_hedge_order(symbol="BTCUSDT", side="Buy", qty="0.001"):
    # ✅ Fetch a realistic market price via ccxt
    try:
        import ccxt
        bybit = ccxt.bybit({'enableRateLimit': True})
        bybit.set_sandbox_mode(True)
        ob = bybit.fetch_order_book(symbol.replace("USDT", "/USDT"))
        bid = ob['bids'][0][0] if ob['bids'] else 0
        ask = ob['asks'][0][0] if ob['asks'] else 0
        price = (bid + ask) / 2 if bid and ask else 10000  # fallback
        price = round(price - 10 if side == "Sell" else price + 10, 1)  # Use buffer
    except Exception as e:
        return False, f"❌ Error fetching market price: {e}"

    endpoint = "/v5/order/create"
    orderLinkId = uuid.uuid4().hex

    payload_dict = {
        "category": "linear",
        "symbol": symbol,
        "side": side,
        "positionIdx": 0,
        "orderType": "Limit",
        "qty": str(qty),
        "price": str(price),
        "timeInForce": "GTC",
        "orderLinkId": orderLinkId
    }

    payload = json.dumps(payload_dict)
    timestamp = str(int(time.time() * 1000))
    signature = genSignature(payload, timestamp)

    headers = {
        'X-BAPI-API-KEY': api_key,
        'X-BAPI-SIGN': signature,
        'X-BAPI-SIGN-TYPE': '2',
        'X-BAPI-TIMESTAMP': timestamp,
        'X-BAPI-RECV-WINDOW': recv_window,
        'Content-Type': 'application/json'
    }

    try:
        response = httpClient.post(url + endpoint, headers=headers, data=payload)
        data = response.json()
        if data["retCode"] == 0:
            return True, f"✅ Hedge order placed at {price} (linkId: {orderLinkId})"
        else:
            return False, f"❌ Hedge order failed: {data}"
    except Exception as e:
        return False, f"❌ Exception during hedge order: {e}"
