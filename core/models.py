"""Data models for orderbook top, triangles, and arbitrage snapshots."""

from dataclasses import dataclass


@dataclass
class OrderBookTop:
    """Best bid/ask for a single symbol."""

    symbol: str
    bid: float
    bid_qty: float
    ask: float
    ask_qty: float
    timestamp: int  # ms


@dataclass
class Triangle:
    """A triangular cycle: 3 legs (symbol, side)."""

    id: str
    legs: list[tuple[str, str]]  # (symbol, "buy" | "sell")
    path_str: str = ""  # e.g. "USDT -> BTC -> ETH -> USDT"; set when built from spot graph


@dataclass
class ArbitrageSnapshot:
    """Result of one triangular arbitrage calculation."""

    triangle_id: str
    path_str: str  # e.g. USDT->BTC->ETH->USDT
    raw_edge_bps: float
    edge_bps: float  # net_edge_bps = raw - fees - slippage
    leg1: str
    leg2: str
    leg3: str
    end_amount: float
    timestamp: int  # ms
    start_amount: float = 1.0
