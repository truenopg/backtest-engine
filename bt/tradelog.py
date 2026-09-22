"""Export fills to CSV for per-trade analysis outside the engine."""
from __future__ import annotations

import csv
from typing import List

from .core import Fill


def write_trades_csv(fills: List[Fill], path: str) -> int:
    """Write ts, side, qty, price, commission, and cash value per fill."""
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ts", "side", "qty", "price", "commission", "value"])
        for f in fills:
            writer.writerow([f.ts.isoformat(), f.side.value, f.qty,
                             f.price, f.commission, f.qty * f.price])
    return len(fills)
