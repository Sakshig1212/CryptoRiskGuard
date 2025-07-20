import asyncio
import websockets
import json

async def deribit_orderbook():
    uri = "wss://www.deribit.com/ws/api/v2/"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "method": "public/subscribe",
            "params": {
                "channels": ["book.BTC-PERPETUAL.raw"]
            },
            "id": 42
        }))
        
        while True:
            msg = await ws.recv()
            print(json.loads(msg))

if __name__ == "__main__":
    asyncio.run(deribit_orderbook())
