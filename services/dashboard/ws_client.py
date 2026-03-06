"""Bybit WebSocket client: subscribe to orderbook.1.<symbol> and push to orderbook cache.

Uses pybit WebSocket for connection lifecycle and reconnects; multiple symbols
subscribed via orderbook_stream per symbol (spot, depth=1).
"""

import asyncio
import threading
import time
from pybit.unified_trading import WebSocket

from core.config import BYBIT_TESTNET, SYMBOLS
from core.debug_log import debug_log

# In-memory orderbook cache: symbol -> (bid, bid_qty, ask, ask_qty, timestamp)
OrderbookCache = dict[str, tuple[float, float, float, float, int]]

# Thread-safe stats for debug (updated from pybit callback thread)
_stats_lock = threading.Lock()
_updates_total = 0
_last_debug_ts = 0.0
_first_seen: set[str] = set()


def _make_callback(cache: OrderbookCache) -> object:
    """Build message handler that updates cache and logs debug info."""

    def handle_message(message: object) -> None:
        global _updates_total, _last_debug_ts
        if not isinstance(message, dict):
            return
        data = message.get("data")
        if not data:
            return
        s = data.get("s")
        if not s:
            return
        bids = data.get("b") or []
        asks = data.get("a") or []
        if not bids or not asks:
            return
        try:
            bid = float(bids[0][0])
            bid_qty = float(bids[0][1])
            ask = float(asks[0][0])
            ask_qty = float(asks[0][1])
        except (IndexError, TypeError, ValueError):
            return
        ts = message.get("ts") or 0
        cache[s] = (bid, bid_qty, ask, ask_qty, ts)
        with _stats_lock:
            _updates_total += 1
            first = s not in _first_seen
            if first:
                _first_seen.add(s)
        if first:
            debug_log("WS", f"First orderbook data received: {s} bid={bid} ask={ask}")
        now = time.monotonic()
        with _stats_lock:
            last = _last_debug_ts
        if now - last >= 5.0:
            with _stats_lock:
                _last_debug_ts = now
            debug_log(
                "WS",
                f"Orderbook updates: {len(cache)} symbols in cache, {_updates_total} total updates",
            )

    return handle_message


def _run_pybit_blocking(cache: OrderbookCache, stop_event: asyncio.Event) -> None:
    """Run pybit WebSocket in a thread: connect, subscribe, wait until stop."""
    global _updates_total, _last_debug_ts, _first_seen
    with _stats_lock:
        _updates_total = 0
        _last_debug_ts = 0.0
        _first_seen = set()
    debug_log("WS", "Connecting to Bybit spot WebSocket (pybit)...")
    try:
        ws = WebSocket(testnet=BYBIT_TESTNET, channel_type="spot")
    except Exception as e:
        debug_log("WS", f"Failed to create WebSocket client: {e}")
        return
    debug_log("WS", f"Subscribing to orderbook.1 for {len(SYMBOLS)} symbols: {SYMBOLS}")
    callback = _make_callback(cache)
    try:
        for symbol in SYMBOLS:
            ws.orderbook_stream(symbol=symbol, depth=1, callback=callback)
        debug_log("WS", "Subscribe calls sent. Waiting for data...")
    except Exception as e:
        debug_log("WS", f"Subscribe error: {e}")
        try:
            ws.exit()
        except Exception:
            pass
        return
    while not stop_event.is_set():
        time.sleep(1)
    debug_log("WS", "Stop requested, closing WebSocket...")
    try:
        ws.exit()
    except Exception as e:
        debug_log("WS", f"Exit warning: {e}")
    debug_log("WS", "WebSocket closed.")


async def run_ws_client(
    cache: OrderbookCache,
    stop_event: asyncio.Event,
) -> None:
    """
    Run pybit spot WebSocket in a thread: subscribe to orderbook.1 for each symbol,
    update cache from callbacks. Runs until stop_event is set.
    """
    debug_log("WS", f"WS task started (pybit spot, {len(SYMBOLS)} symbols: {SYMBOLS})")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        _run_pybit_blocking,
        cache,
        stop_event,
    )
