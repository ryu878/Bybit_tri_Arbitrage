"""Console table output using pandas and tabulate."""

import os
import pandas as pd
from tabulate import tabulate
from core.models import ArbitrageSnapshot


def _bps_str(bps: float) -> str:
    return f"{round(bps, 1):.1f} bps"


def clear_and_print(
    snapshots: list[ArbitrageSnapshot],
    top_n: int,
    *,
    max_edge_bps: float | None = None,
) -> None:
    """Clear screen and print table: triangle, raw_edge, net_edge (in bps)."""
    os.system("cls" if os.name == "nt" else "clear")

    if not snapshots:
        msg = "No arbitrage data yet."
        if max_edge_bps is not None:
            msg += f"  Max edge: {max_edge_bps:.1f} bps"
        print(msg)
        return

    rows = snapshots[:top_n]
    df = pd.DataFrame(
        [
            {
                "triangle": s.path_str,
                "raw_edge": _bps_str(s.raw_edge_bps),
                "net_edge": _bps_str(s.edge_bps),
            }
            for s in rows
        ]
    )
    print(tabulate(df, headers="keys", tablefmt="simple", showindex=False))
