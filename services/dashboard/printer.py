"""Console table output using pandas and tabulate."""

import os
import pandas as pd
from tabulate import tabulate
from core.models import ArbitrageSnapshot


def clear_and_print(
    snapshots: list[ArbitrageSnapshot],
    top_n: int,
    *,
    max_edge_bps: float | None = None,
) -> None:
    """Clear screen and print table: triangle, leg1, leg2, leg3, net."""
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
                "leg1": s.leg1,
                "leg2": s.leg2,
                "leg3": s.leg3,
                "net": round(s.edge_bps, 1),
            }
            for s in rows
        ]
    )
    print(tabulate(df, headers="keys", tablefmt="simple", showindex=False))
