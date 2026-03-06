"""Dashboard: WebSocket orderbook, triangular arbitrage scan, Redis storage, console print."""

import asyncio
import threading
import time
from core.config import (
    DEBUG_MODE,
    PRINT_EVERY_SEC,
    SLIPPAGE_BPS_BUFFER,
    TAKER_FEE_BPS,
    TOP_N,
    TRIANGLE_START_COINS,
)
from core.debug_log import debug_log, init_log
from core.models import ArbitrageSnapshot
from core import redis_store
from core.bybit_spot import triangles_from_spot
from services.dashboard.ws_client import OrderbookCache, run_ws_client
from services.dashboard.paths import build_paths_and_index
from services.dashboard.edge_calc import calc_edge_direct
from services.dashboard.printer import clear_and_print
from services.dashboard import telegram_notify


def _min_net_edge_threshold() -> float:
    """Report opportunity only when net edge (after fee + slippage) is above this."""
    return (3 * TAKER_FEE_BPS) + SLIPPAGE_BPS_BUFFER


def _is_above_threshold(snap: ArbitrageSnapshot) -> bool:
    """Net (edge_bps) already includes fee and slippage; compare directly to threshold."""
    return snap.edge_bps > _min_net_edge_threshold()


async def run_dashboard() -> None:
    stop = asyncio.Event()
    cache: OrderbookCache = {}

    triangles, symbols_to_subscribe = triangles_from_spot(TRIANGLE_START_COINS)
    if not triangles:
        init_log("SPOT", "No triangles found. Check Bybit API and TRIANGLE_START_COINS.")
        return

    paths, symbol_to_indices = build_paths_and_index(triangles)
    n_paths = len(paths)
    if n_paths == 0:
        init_log("SPOT", "No triangle paths built.")
        return

    dirty_symbols: set[str] = set()
    dirty_lock = threading.Lock()

    redis_client = await redis_store.get_redis()
    if DEBUG_MODE:
        debug_log("INIT", "Dashboard started, DEBUG_MODE=true")
        debug_log("INIT", f"Paths: {n_paths}, symbol_to_indices: {len(symbol_to_indices)} symbols, Redis connected")

    async def ws_task() -> None:
        await run_ws_client(
            cache,
            stop,
            symbols=symbols_to_subscribe,
            dirty_symbols=dirty_symbols,
            dirty_lock=dirty_lock,
        )

    sent_for: set[str] = set()
    snapshots: list[ArbitrageSnapshot | None] = [None] * n_paths
    first_scan = True

    async def scan_and_print() -> None:
        nonlocal sent_for, first_scan
        while not stop.is_set():
            with dirty_lock:
                dirty = set(dirty_symbols)
                dirty_symbols.clear()
            if first_scan:
                affected_indices = set(range(n_paths))
                first_scan = False
            else:
                affected_indices = set()
                for sym in dirty:
                    affected_indices.update(symbol_to_indices.get(sym, ()))

            for i in affected_indices:
                if i < n_paths:
                    snapshots[i] = calc_edge_direct(paths[i], cache)

            all_calc_snaps = [s for s in snapshots if s is not None]
            orderbook_count = len(cache)
            if DEBUG_MODE:
                debug_log("SCAN", f"Orderbooks: {orderbook_count} in cache, recalc {len(affected_indices)} paths, {len(all_calc_snaps)} with data")

            above_threshold = [s for s in all_calc_snaps if _is_above_threshold(s)]
            above_threshold.sort(key=lambda x: -x.edge_bps)
            sorted_snaps = above_threshold
            max_edge_bps = max((s.edge_bps for s in all_calc_snaps), default=None)

            if DEBUG_MODE and all_calc_snaps:
                debug_log("SCAN", f"Triangles: {n_paths} total, {len(all_calc_snaps)} with data, {len(sorted_snaps)} above threshold")
                for s in sorted(all_calc_snaps, key=lambda x: -x.edge_bps)[:5]:
                    debug_log("SCAN", f"  {s.path_str}  net={s.edge_bps:.1f} bps")

            current_ids = {s.triangle_id for s in sorted_snaps}
            new_ids = current_ids - sent_for
            for snap in sorted_snaps:
                if snap.triangle_id in new_ids:
                    await telegram_notify.send_arb_notification(snap)
                    sent_for.add(snap.triangle_id)
            if new_ids and DEBUG_MODE:
                debug_log("TELEGRAM", f"Sent {len(new_ids)} new opportunity notification(s)")
            sent_for &= current_ids

            for s in sorted_snaps:
                await redis_store.write_arb_snapshot(redis_client, s)
            await redis_store.write_arb_top(redis_client, sorted_snaps[:TOP_N])
            if DEBUG_MODE:
                debug_log("REDIS", f"Wrote {len(sorted_snaps)} snapshots, top {min(TOP_N, len(sorted_snaps))} to arb:top")

            display_snaps = sorted(all_calc_snaps, key=lambda x: -x.edge_bps)[:TOP_N]
            clear_and_print(
                display_snaps,
                TOP_N,
                max_edge_bps=max_edge_bps,
                orderbook_count=orderbook_count,
                triangle_count=n_paths,
                opportunities_above_threshold=len(sorted_snaps),
            )
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
