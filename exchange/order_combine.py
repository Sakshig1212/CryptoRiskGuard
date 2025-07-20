import ccxt
import requests
import json
import pprint

# =====================
# REST API: OKX (Perpetual Futures)
# =====================

def fetch_orderbook_okx():
    try:
        okx = ccxt.okx({
            'enableRateLimit': True,
            'timeout': 30000,
        })
        okx.load_markets()
        symbol = "BTC-USDT-SWAP"  # Use the exact OKX symbol
        ob = okx.fetch_order_book(symbol)
        return {'exchange': 'OKX', 'bids': ob['bids'][:3], 'asks': ob['asks'][:3]}
    except Exception as e:
        return {'exchange': 'OKX', 'error': str(e)}

# =====================
# REST API: Bybit (Spot or Perpetual)
# =====================

def fetch_orderbook_bybit(symbol="BTC/USDT"):
    try:
        bybit = ccxt.bybit({
            'enableRateLimit': True,
            'timeout': 30000,
        })
        bybit.load_markets()
        ob = bybit.fetch_order_book(symbol)
        return {'exchange': 'Bybit', 'bids': ob['bids'][:3], 'asks': ob['asks'][:3]}
    except Exception as e:
        return {'exchange': 'Bybit', 'error': str(e)}

# =====================
# REST API: Deribit (Perpetual Futures)
# =====================

def fetch_orderbook_deribit():
    try:
        url = "https://www.deribit.com/api/v2/public/get_order_book?instrument_name=BTC-PERPETUAL"
        response = requests.get(url)
        data = response.json()["result"]
        bids = data["bids"][:3]
        asks = data["asks"][:3]
        return {'exchange': 'Deribit', 'bids': bids, 'asks': asks}
    except Exception as e:
        return {'exchange': 'Deribit', 'error': str(e)}

# =====================
# Unified Runner
# =====================

def run_fetchers():
    print("Fetching OKX...")
    pprint.pprint(fetch_orderbook_okx())

    print("\nFetching Bybit...")
    pprint.pprint(fetch_orderbook_bybit())

    print("\nFetching Deribit...")
    pprint.pprint(fetch_orderbook_deribit())


if __name__ == "__main__":
    run_fetchers()
