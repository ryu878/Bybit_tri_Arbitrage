"""Console table output using pandas and tabulate. No pandas in hot path; only here for display."""

import os
import pandas as pd
from tabulate import tabulate
from core.models import ArbitrageSnapshot


def clear_and_print(
    snapshots: list[ArbitrageSnapshot],
    top_n: int,
    *,
    max_edge_bps: float | None = None,
    orderbook_count: int | None = None,
    triangle_count: int | None = None,
    opportunities_above_threshold: int | None = None,
) -> None:
    """Clear screen, optional summary line, then table: triangle, leg1, leg2, leg3, raw, net, timestamp."""
    os.system("cls" if os.name == "nt" else "clear")

    if orderbook_count is not None or triangle_count is not None or opportunities_above_threshold is not None:
        parts = []
        if orderbook_count is not None:
            parts.append(f"orderbooks={orderbook_count}")
        if triangle_count is not None:
            parts.append(f"triangles={triangle_count}")
        if opportunities_above_threshold is not None:
            parts.append(f"above_threshold={opportunities_above_threshold}")
        if max_edge_bps is not None:
            parts.append(f"max_edge={max_edge_bps:.1f} bps")
        print("  ".join(parts))

    if not snapshots:
        print("No arbitrage data yet." + (f"  Max edge: {max_edge_bps:.1f} bps" if max_edge_bps is not None else ""))
        return

    rows = snapshots[:top_n]
    df = pd.DataFrame(
        [
            {
                "triangle": s.path_str,
                "leg1": s.leg1,
                "leg2": s.leg2,
                "leg3": s.leg3,
                "raw": round(s.raw_edge_bps, 1),
                "net": round(s.edge_bps, 1),
                "timestamp": s.timestamp,
            }
            for s in rows
        ]
    )
    print(tabulate(df, headers="keys", tablefmt="simple", showindex=False))
