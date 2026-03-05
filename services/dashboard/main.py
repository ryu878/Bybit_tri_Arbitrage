"""Dashboard: WebSocket orderbook, triangular arbitrage scan, Redis storage, console print."""

import asyncio
import time
from core.config import (
    MAX_STALE_MS,
    PRINT_EVERY_SEC,
    SLIPPAGE_BPS_BUFFER,
    SYMBOLS,
    TAKER_FEE_BPS,
    TOP_N,
)
from core.models import ArbitrageSnapshot, OrderBookTop
from core import redis_store
from services.dashboard.ws_client import OrderbookCache, run_ws_client
from services.dashboard.triangles import build_triangles
from services.dashboard.calc import calc_triangle
from services.dashboard.printer import clear_and_print


def _min_net_edge_bps() -> float:
    """Only report opportunity if net_edge_bps > (3 * TAKER_FEE_BPS) + SLIPPAGE_BPS_BUFFER."""
    return (3 * TAKER_FEE_BPS) + SLIPPAGE_BPS_BUFFER


def cache_to_orderbooks(cache: OrderbookCache) -> dict[str, OrderBookTop]:
    """Convert in-memory cache to OrderBookTop dict; exclude stale entries."""
    now_ms = int(time.time() * 1000)
    out: dict[str, OrderBookTop] = {}
    for symbol, (bid, bid_qty, ask, ask_qty, ts) in cache.items():
        if now_ms - ts > MAX_STALE_MS:
            continue
        out[symbol] = OrderBookTop(
            symbol=symbol,
            bid=bid,
            bid_qty=bid_qty,
            ask=ask,
            ask_qty=ask_qty,
            timestamp=ts,
        )
    return out


async def run_dashboard() -> None:
    stop = asyncio.Event()
    cache: OrderbookCache = {}
    triangles = build_triangles(SYMBOLS)

    redis_client = await redis_store.get_redis()

    async def ws_task() -> None:
        await run_ws_client(cache, stop)

    async def scan_and_print() -> None:
        while not stop.is_set():
            orderbooks = cache_to_orderbooks(cache)
            snapshots: list[tuple[str, float, int, ArbitrageSnapshot]] = []
            min_net = _min_net_edge_bps()
            for t in triangles:
                snap = calc_triangle(t, orderbooks)
                if snap and snap.edge_bps > min_net:
                    snapshots.append((snap.triangle_id, snap.edge_bps, snap.timestamp, snap))
            snapshots.sort(key=lambda x: -x[1])
            sorted_snaps = [x[3] for x in snapshots]

            for s in sorted_snaps:
                await redis_store.write_arb_snapshot(redis_client, s)
            await redis_store.write_arb_top(redis_client, sorted_snaps[:TOP_N])

            clear_and_print(sorted_snaps, TOP_N)
            await asyncio.sleep(PRINT_EVERY_SEC)

    ws = asyncio.create_task(ws_task())
    scan = asyncio.create_task(scan_and_print())
    try:
        await asyncio.gather(ws, scan)
    except asyncio.CancelledError:
        pass
    finally:
        stop.set()
        await redis_client.aclose()
