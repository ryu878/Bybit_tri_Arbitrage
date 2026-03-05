"""Bybit WebSocket client: subscribe to orderbook.1.<symbol> and push to orderbook cache."""

import asyncio
import orjson
import websockets
from core.config import BYBIT_WS_PUBLIC_SPOT, SYMBOLS

# In-memory orderbook cache: symbol -> (bid, bid_qty, ask, ask_qty, timestamp)
OrderbookCache = dict[str, tuple[float, float, float, float, int]]


async def run_ws_client(
    cache: OrderbookCache,
    stop_event: asyncio.Event,
) -> None:
    """
    Connect to Bybit spot public WS, subscribe to orderbook.1 for each symbol,
    parse messages and update cache. Runs until stop_event is set.
    """
    url = BYBIT_WS_PUBLIC_SPOT

    async def handler(ws: websockets.WebSocketClientProtocol) -> None:
        # Subscribe to orderbook.1 for all symbols
        topics = [f"orderbook.1.{s}" for s in SYMBOLS]
        sub = {"op": "subscribe", "args": topics}
        await ws.send(orjson.dumps(sub).decode())

        while not stop_event.is_set():
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
            except asyncio.TimeoutError:
                continue
            msg = orjson.loads(raw)
            if "data" not in msg:
                continue
            data = msg["data"]
            if isinstance(data, dict):
                data = [data]
            ts = msg.get("ts") or 0
            for d in data:
                s = d.get("s")
                if not s:
                    continue
                bids = d.get("b") or []
                asks = d.get("a") or []
                if not bids or not asks:
                    continue
                try:
                    bid = float(bids[0][0])
                    bid_qty = float(bids[0][1])
                    ask = float(asks[0][0])
                    ask_qty = float(asks[0][1])
                except (IndexError, TypeError, ValueError):
                    continue
                cache[s] = (bid, bid_qty, ask, ask_qty, ts)

    while not stop_event.is_set():
        try:
            async with websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            ) as ws:
                await handler(ws)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(2.0)
