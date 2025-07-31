import ccxt

def fetch_orderbook_okx(symbol="BTC/USDT:USDT"):
    exchange = ccxt.okx()
    orderbook = exchange.fetch_order_book(symbol)
    return orderbook

def fetch_orderbook_bybit(symbol="BTC/USDT"):
    exchange = ccxt.bybit()
    orderbook = exchange.fetch_order_book(symbol)
    return orderbook

if __name__ == "__main__":
    print("✅ OKX Orderbook")
    okx_data = fetch_orderbook_okx()
    print(okx_data['bids'][:5], "\n")

    print("✅ Bybit Orderbook")
    bybit_data = fetch_orderbook_bybit()
    print(bybit_data['asks'][:5])
