"""Performance statistics over a finished backtest."""
from __future__ import annotations

import math
from typing import List


def total_return(equity: List[float]) -> float:
    if len(equity) < 2 or equity[0] == 0:
        return 0.0
    return equity[-1] / equity[0] - 1


def cagr(equity: List[float], periods_per_year: int = 252) -> float:
    if len(equity) < 2 or equity[0] <= 0 or equity[-1] <= 0:
        return 0.0
    years = (len(equity) - 1) / periods_per_year
    return (equity[-1] / equity[0]) ** (1 / years) - 1 if years > 0 else 0.0


def _returns(equity: List[float]) -> List[float]:
    return [b / a - 1 for a, b in zip(equity, equity[1:]) if a]


def sharpe(equity: List[float], periods_per_year: int = 252) -> float:
    rets = _returns(equity)
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    sd = math.sqrt(var)
    return mean / sd * math.sqrt(periods_per_year) if sd else 0.0


def max_drawdown(equity: List[float]) -> float:
    peak = -math.inf
    worst = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            worst = min(worst, v / peak - 1)
    return worst


def summary(equity: List[float]) -> dict:
    return {
        "total_return": total_return(equity),
        "cagr": cagr(equity),
        "sharpe": sharpe(equity),
        "max_drawdown": max_drawdown(equity),
    }
