"""Parameter sweeps with an in-sample / out-of-sample split.

The overfitting trap: the best in-sample parameters are usually not the best
out-of-sample. This harness makes that gap measurable instead of letting it
hide in a single flattering number.
"""
from __future__ import annotations

import itertools
from typing import Callable, Dict, List, Tuple

from .broker import Broker, CostModel
from .core import Bar
from .engine import Backtest, Strategy
from .stats import summary


def split_bars(bars: List[Bar], in_sample_fraction: float = 0.7) -> Tuple[List[Bar], List[Bar]]:
    """Chronological split - never shuffled, or the future leaks into the past."""
    if not 0 < in_sample_fraction < 1:
        raise ValueError("in_sample_fraction must be in (0, 1)")
    cut = int(len(bars) * in_sample_fraction)
    return bars[:cut], bars[cut:]


def sweep(bars: List[Bar], make_strategy: Callable[..., Strategy],
          param_grid: Dict[str, List], cash: float = 10_000.0,
          in_sample_fraction: float = 0.7) -> List[dict]:
    """Run the strategy over every parameter combination, on both halves.

    Returns one row per combination with in-sample and out-of-sample stats.
    """
    in_sample, out_of_sample = split_bars(bars, in_sample_fraction)
    names = sorted(param_grid)
    rows: List[dict] = []
    for values in itertools.product(*(param_grid[n] for n in names)):
        params = dict(zip(names, values))
        try:
            strategy = make_strategy(**params)
        except ValueError:
            continue  # invalid combo (e.g. fast >= slow)
        row = {"params": params}
        for label, segment in (("in_sample", in_sample), ("out_of_sample", out_of_sample)):
            bt = Backtest(strategy if label == "in_sample" else make_strategy(**params),
                          Broker(cash, CostModel()))
            bt.run(segment)
            row[label] = summary(bt.equity_curve)
        rows.append(row)
    return rows
