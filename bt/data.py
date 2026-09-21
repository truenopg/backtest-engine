"""Bar series: synthetic generators and CSV loading."""
from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta
from typing import List

from .core import Bar


def synthetic_gbm(days: int = 500, start: float = 100.0, drift: float = 0.0003,
                  vol: float = 0.012, seed: int = 0) -> List[Bar]:
    """Geometric Brownian motion daily bars - handy when no data is around."""
    rng = random.Random(seed)
    bars: List[Bar] = []
    price = start
    ts = datetime(2024, 1, 1)
    for _ in range(days):
        shock = rng.gauss(0, 1)
        open_ = price
        close = price * math.exp(drift - 0.5 * vol**2 + vol * shock)
        high = max(open_, close) * (1 + abs(rng.gauss(0, vol / 3)))
        low = min(open_, close) * (1 - abs(rng.gauss(0, vol / 3)))
        bars.append(Bar(ts, open_, high, low, close, rng.uniform(800, 1500)))
        price = close
        ts += timedelta(days=1)
    return bars


def load_csv(path: str, ts_format: str = "%Y-%m-%d") -> List[Bar]:
    """Load bars from a CSV with ts,open,high,low,close,volume columns."""
    bars: List[Bar] = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            bars.append(Bar(
                ts=datetime.strptime(row["ts"], ts_format),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row.get("volume") or 0.0),
            ))
    return bars
