"""Bybit spot instruments, conversion graph, and triangle path discovery.

Fetches all tradeable spot pairs via pybit and builds directed triangles
(start -> mid1 -> mid2 -> start) so no symbol list in .env is needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from pybit.unified_trading import HTTP

from core.config import BYBIT_TESTNET
from core.debug_log import debug_log, init_log
from core.models import Triangle


@dataclass(frozen=True)
class SpotInstrument:
    symbol: str
    base_coin: str
    quote_coin: str


@dataclass(frozen=True)
class Edge:
    from_coin: str
    to_coin: str
    symbol: str
    side: str  # BUY or SELL


@dataclass(frozen=True)
class TrianglePath:
    start: str
    mid1: str
    mid2: str
    leg1: Edge
    leg2: Edge
    leg3: Edge

    def label(self) -> str:
        return f"{self.start} -> {self.mid1} -> {self.mid2} -> {self.start}"


def fetch_bybit_spot_instruments() -> List[SpotInstrument]:
    """Fetch all spot instruments with status Trading from Bybit via pybit HTTP."""
    try:
        session = HTTP(testnet=BYBIT_TESTNET)
        payload = session.get_instruments_info(category="spot")
    except Exception as e:
        debug_log("SPOT", f"Failed to fetch spot instruments: {e}")
        return []
    items = payload.get("result", {}).get("list", [])
    instruments: List[SpotInstrument] = []
    for item in items:
        if item.get("status") != "Trading":
            continue
        instruments.append(
            SpotInstrument(
                symbol=item["symbol"],
                base_coin=item["baseCoin"],
                quote_coin=item["quoteCoin"],
            )
        )
    return instruments


def build_conversion_graph(
    instruments: List[SpotInstrument],
) -> Dict[str, List[Edge]]:
    """
    For symbol BASEQUOTE:
    - SELL BASEQUOTE converts BASE -> QUOTE
    - BUY  BASEQUOTE converts QUOTE -> BASE
    """
    graph: Dict[str, List[Edge]] = {}
    for inst in instruments:
        base = inst.base_coin
        quote = inst.quote_coin
        symbol = inst.symbol
        graph.setdefault(base, []).append(
            Edge(from_coin=base, to_coin=quote, symbol=symbol, side="SELL")
        )
        graph.setdefault(quote, []).append(
            Edge(from_coin=quote, to_coin=base, symbol=symbol, side="BUY")
        )
    return graph


def build_triangle_paths(
    instruments: List[SpotInstrument],
    allowed_starts: Set[str] | None = None,
) -> List[TrianglePath]:
    """Find all directed triangles start -> mid1 -> mid2 -> start."""
    graph = build_conversion_graph(instruments)
    starts = allowed_starts or set(graph.keys())
    triangles: List[TrianglePath] = []
    seen: Set[Tuple[str, str, str]] = set()

    for start in sorted(starts):
        if start not in graph:
            continue
        for leg1 in graph[start]:
            mid1 = leg1.to_coin
            if mid1 not in graph or mid1 == start:
                continue
            for leg2 in graph[mid1]:
                mid2 = leg2.to_coin
                if mid2 in {start, mid1} or mid2 not in graph:
                    continue
                for leg3 in graph[mid2]:
                    if leg3.to_coin != start:
                        continue
                    key = (start, mid1, mid2)
                    if key in seen:
                        continue
                    seen.add(key)
                    triangles.append(
                        TrianglePath(
                            start=start,
                            mid1=mid1,
                            mid2=mid2,
                            leg1=leg1,
                            leg2=leg2,
                            leg3=leg3,
                        )
                    )
    return triangles


def path_to_triangle(path: TrianglePath) -> Triangle:
    """Convert TrianglePath to the app's Triangle model (id, legs, path_str)."""
    tid = "|".join([path.leg1.symbol, path.leg2.symbol, path.leg3.symbol])
    legs = [
        (path.leg1.symbol, path.leg1.side.lower()),
        (path.leg2.symbol, path.leg2.side.lower()),
        (path.leg3.symbol, path.leg3.side.lower()),
    ]
    return Triangle(
        id=tid,
        legs=legs,
        path_str=path.label(),
    )


def triangles_from_spot(allowed_starts: Set[str]) -> tuple[List[Triangle], List[str]]:
    """
    Fetch Bybit spot instruments, build triangle paths, convert to Triangle list.
    Returns (triangles, symbols_to_subscribe) for the dashboard.
    """
    instruments = fetch_bybit_spot_instruments()
    if not instruments:
        init_log("SPOT", "No spot instruments loaded. Check Bybit API / network.")
        return ([], [])
    init_log("SPOT", f"Loaded {len(instruments)} spot instruments")
    paths = build_triangle_paths(instruments, allowed_starts=allowed_starts)
    triangles = [path_to_triangle(p) for p in paths]
    symbols_to_subscribe = sorted(
        set(s for t in triangles for (s, _) in t.legs)
    )
    init_log(
        "SPOT",
        f"Triangles: {len(triangles)}, subscribing to {len(symbols_to_subscribe)} symbols",
    )
    return (triangles, symbols_to_subscribe)
