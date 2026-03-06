"""
Direct multiplier-based edge calculation. No step-by-step simulation.
BUY -> ask_px, SELL -> bid_px.
net = raw * fee_factor * slippage_factor (same as old calc: fee + slippage per leg).
"""

import time
from core.config import MAX_STALE_MS, SLIPPAGE_BPS_BUFFER, TAKER_FEE_BPS
from core.models import ArbitrageSnapshot, ScannerPath

# tob: symbol -> (bid_px, bid_qty, ask_px, ask_qty, ts_ms)
TOBCache = dict[str, tuple[float, float, float, float, int]]

_FEE_FACTOR = (1.0 - TAKER_FEE_BPS / 10_000) ** 3
_SLIPPAGE_FACTOR = (1.0 - SLIPPAGE_BPS_BUFFER / 10_000) ** 3


def _raw_mult_buy_buy_sell(a1: float, a2: float, b3: float) -> float:
    return b3 / (a1 * a2)


def _raw_mult_buy_buy_buy(a1: float, a2: float, a3: float) -> float:
    return 1.0 / (a1 * a2 * a3)


def _raw_mult_buy_sell_buy(a1: float, b2: float, a3: float) -> float:
    return b2 / (a1 * a3)


def _raw_mult_buy_sell_sell(a1: float, b2: float, b3: float) -> float:
    return (b2 * b3) / a1


def _raw_mult_sell_buy_buy(b1: float, a2: float, a3: float) -> float:
    return b1 / (a2 * a3)


def _raw_mult_sell_buy_sell(b1: float, a2: float, b3: float) -> float:
    return (b1 * b3) / a2


def _raw_mult_sell_sell_buy(b1: float, b2: float, a3: float) -> float:
    return (b1 * b2) / a3


def _raw_mult_sell_sell_sell(b1: float, b2: float, b3: float) -> float:
    return b1 * b2 * b3


def calc_edge_direct(path: ScannerPath, tob: TOBCache) -> ArbitrageSnapshot | None:
    """
    Compute edge for one path using direct multiplier. Returns None if any leg is missing or stale.
    """
    now_ms = int(time.time() * 1000)
    t1 = tob.get(path.s1)
    t2 = tob.get(path.s2)
    t3 = tob.get(path.s3)
    if not t1 or not t2 or not t3:
        return None
    b1, _, a1, _, ts1 = t1
    b2, _, a2, _, ts2 = t2
    b3, _, a3, _, ts3 = t3
    if now_ms - ts1 > MAX_STALE_MS or now_ms - ts2 > MAX_STALE_MS or now_ms - ts3 > MAX_STALE_MS:
        return None

    kind = f"{path.side1}_{path.side2}_{path.side3}"
    if kind == "BUY_BUY_SELL":
        raw_mult = _raw_mult_buy_buy_sell(a1, a2, b3)
    elif kind == "BUY_BUY_BUY":
        raw_mult = _raw_mult_buy_buy_buy(a1, a2, a3)
    elif kind == "BUY_SELL_BUY":
        raw_mult = _raw_mult_buy_sell_buy(a1, b2, a3)
    elif kind == "BUY_SELL_SELL":
        raw_mult = _raw_mult_buy_sell_sell(a1, b2, b3)
    elif kind == "SELL_BUY_BUY":
        raw_mult = _raw_mult_sell_buy_buy(b1, a2, a3)
    elif kind == "SELL_BUY_SELL":
        raw_mult = _raw_mult_sell_buy_sell(b1, a2, b3)
    elif kind == "SELL_SELL_BUY":
        raw_mult = _raw_mult_sell_sell_buy(b1, b2, a3)
    elif kind == "SELL_SELL_SELL":
        raw_mult = _raw_mult_sell_sell_sell(b1, b2, b3)
    else:
        return None

    # Fee + slippage per leg (match old calc.py behavior so displayed net is comparable)
    net_mult = raw_mult * _FEE_FACTOR * _SLIPPAGE_FACTOR
    raw_bps = (raw_mult - 1.0) * 10_000
    net_bps = (net_mult - 1.0) * 10_000
    ts = max(ts1, ts2, ts3)
    triangle_id = f"{path.s1}|{path.s2}|{path.s3}"
    leg1 = f"{path.side1} {path.s1}"
    leg2 = f"{path.side2} {path.s2}"
    leg3 = f"{path.side3} {path.s3}"

    return ArbitrageSnapshot(
        triangle_id=triangle_id,
        path_str=path.label,
        raw_edge_bps=raw_bps,
        edge_bps=net_bps,
        leg1=leg1,
        leg2=leg2,
        leg3=leg3,
        end_amount=net_mult,
        timestamp=ts,
        start_amount=1.0,
    )
