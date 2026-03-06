"""Dashboard: WebSocket orderbook, triangular arbitrage scan, Redis storage, console print."""

import asyncio
import time
from core.config import (
    DEBUG_MODE,
    MAX_STALE_MS,
    PRINT_EVERY_SEC,
    SLIPPAGE_BPS_BUFFER,
    TAKER_FEE_BPS,
    TOP_N,
    TRIANGLE_START_COINS,
)
from core.debug_log import debug_log, init_log
from core.models import ArbitrageSnapshot, OrderBookTop
from core import redis_store
from core.bybit_spot import triangles_from_spot
from services.dashboard.ws_client import OrderbookCache, run_ws_client
from services.dashboard.calc import calc_triangle
from services.dashboard.printer import clear_and_print
from services.dashboard import telegram_notify


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

    # Fetch Bybit spot instruments and build triangles from conversion graph
    triangles, symbols_to_subscribe = triangles_from_spot(TRIANGLE_START_COINS)
    if not triangles:
        init_log("SPOT", "No triangles found. Check Bybit API and TRIANGLE_START_COINS.")
        return

    redis_client = await redis_store.get_redis()
    if DEBUG_MODE:
        debug_log("INIT", "Dashboard started, DEBUG_MODE=true")
        debug_log("INIT", f"Redis connected")

    async def ws_task() -> None:
        await run_ws_client(cache, stop, symbols=symbols_to_subscribe)

    sent_for: set[str] = set()  # triangle_ids we've already sent Telegram for; clear when arb disappears

    async def scan_and_print() -> None:
        nonlocal sent_for
        while not stop.is_set():
            orderbooks = cache_to_orderbooks(cache)
            debug_log("SCAN", f"Orderbooks: {len(orderbooks)} symbols (fresh, within MAX_STALE_MS)")

            snapshots: list[tuple[str, float, int, ArbitrageSnapshot]] = []
            all_calc_snaps: list[ArbitrageSnapshot] = []
            min_net = _min_net_edge_bps()
            calculated = 0
            for t in triangles:
                snap = calc_triangle(t, orderbooks)
                if snap:
                    calculated += 1
                    all_calc_snaps.append(snap)
                    if snap.edge_bps > min_net:
                        snapshots.append((snap.triangle_id, snap.edge_bps, snap.timestamp, snap))
            debug_log("SCAN", f"Triangles: {len(triangles)} total, {calculated} with data, {len(snapshots)} above threshold (net > {min_net:.1f} bps)")

            max_edge_bps = max((s.edge_bps for s in all_calc_snaps), default=None)
            snapshots.sort(key=lambda x: -x[1])
            sorted_snaps = [x[3] for x in snapshots]

            current_ids = {s.triangle_id for s in sorted_snaps}
            new_ids = current_ids - sent_for
            for snap in sorted_snaps:
                if snap.triangle_id in new_ids:
                    await telegram_notify.send_arb_notification(snap)
                    sent_for.add(snap.triangle_id)
            if new_ids:
                debug_log("TELEGRAM", f"Sent {len(new_ids)} new opportunity notification(s)")
            sent_for -= sent_for - current_ids

            for s in sorted_snaps:
                await redis_store.write_arb_snapshot(redis_client, s)
            await redis_store.write_arb_top(redis_client, sorted_snaps[:TOP_N])
            debug_log("REDIS", f"Wrote {len(sorted_snaps)} snapshots, top {min(TOP_N, len(sorted_snaps))} to arb:top")

            clear_and_print(sorted_snaps, TOP_N, max_edge_bps=max_edge_bps)
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
