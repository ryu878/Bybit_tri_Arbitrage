"""Calculate triangular cycle result with fees and slippage."""

from core.config import SLIPPAGE_BPS_BUFFER, TAKER_FEE_BPS
from core.models import ArbitrageSnapshot, OrderBookTop, Triangle


def _base_quote(symbol: str) -> tuple[str, str]:
    """Return (base, quote) for a pair symbol. USDT first so BTCUSDT -> BTC, USDT."""
    if symbol.endswith("USDT"):
        return symbol[:-4], "USDT"
    if symbol.endswith("BTC"):
        return symbol[:-3], "BTC"
    if symbol.endswith("ETH"):
        return symbol[:-3], "ETH"
    return symbol, ""


def _path_str(triangle: Triangle) -> str:
    """Human-readable path e.g. USDT->BTC->ETH->USDT from triangle legs."""
    legs = triangle.legs
    if len(legs) != 3:
        return triangle.id
    (s1, _side1), (s2, side2), (s3, _side3) = legs
    b1, q1 = _base_quote(s1)
    b2, q2 = _base_quote(s2)
    _b3, q3 = _base_quote(s3)
    # Leg1 buy: start quote1, get base1. Leg2: if buy get base2, if sell get quote2. Leg3 sell: get quote3.
    mid = b2 if side2 == "buy" else q2
    return f"{q1}->{b1}->{mid}->{q3}"


def _apply_fee(amount: float, bps: float) -> float:
    return amount * (1 - bps / 10_000)


def _apply_slippage(amount: float, bps: float) -> float:
    return amount * (1 - bps / 10_000)


def calc_triangle(
    triangle: Triangle,
    orderbooks: dict[str, OrderBookTop],
    start_amount: float = 1.0,
) -> ArbitrageSnapshot | None:
    """
    Compute result of one triangular cycle.
    BUY uses ask price, SELL uses bid price.
    raw_edge_bps = gross edge (no fees/slippage); net edge_bps = after TAKER_FEE_BPS and SLIPPAGE_BPS_BUFFER.
    """
    fee_bps = TAKER_FEE_BPS
    slip_bps = SLIPPAGE_BPS_BUFFER
    amount_raw = start_amount
    amount_net = start_amount
    ts = 0
    leg_descs: list[str] = []

    for symbol, side in triangle.legs:
        top = orderbooks.get(symbol)
        if not top:
            return None
        ts = max(ts, top.timestamp)

        if side == "buy":
            price = top.ask
            amount_raw = amount_raw / price
            amount_net = amount_net / price
            amount_net = _apply_fee(amount_net, fee_bps)
            amount_net = _apply_slippage(amount_net, slip_bps)
            leg_descs.append(f"{symbol}(ask={price:.4f})")
        else:
            price = top.bid
            amount_raw = amount_raw * price
            amount_net = amount_net * price
            amount_net = _apply_fee(amount_net, fee_bps)
            amount_net = _apply_slippage(amount_net, slip_bps)
            leg_descs.append(f"{symbol}(bid={price:.4f})")

    raw_edge_bps = (amount_raw / start_amount - 1) * 10_000
    net_edge_bps = (amount_net / start_amount - 1) * 10_000

    return ArbitrageSnapshot(
        triangle_id=triangle.id,
        path_str=_path_str(triangle),
        raw_edge_bps=raw_edge_bps,
        edge_bps=net_edge_bps,
        leg1=leg_descs[0] if len(leg_descs) > 0 else "",
        leg2=leg_descs[1] if len(leg_descs) > 1 else "",
        leg3=leg_descs[2] if len(leg_descs) > 2 else "",
        end_amount=amount_net,
        timestamp=ts,
        start_amount=start_amount,
    )
