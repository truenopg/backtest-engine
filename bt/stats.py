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


def sortino(equity: List[float], periods_per_year: int = 252) -> float:
    """Annualized return over downside deviation (target 0, all periods).

    Like Sharpe but only returns below zero count as risk, so upside
    volatility is not penalized. Returns 0.0 when there is no downside
    deviation at all.
    """
    rets = _returns(equity)
    if len(rets) < 2:
        return 0.0
    mean = sum(rets) / len(rets)
    downside_var = sum(min(r, 0.0) ** 2 for r in rets) / len(rets)
    dd = math.sqrt(downside_var)
    return mean / dd * math.sqrt(periods_per_year) if dd else 0.0


def calmar(equity: List[float], periods_per_year: int = 252) -> float:
    """CAGR over absolute max drawdown. 0.0 when there was no drawdown."""
    mdd = max_drawdown(equity)
    if mdd == 0:
        return 0.0
    return cagr(equity, periods_per_year) / abs(mdd)


def max_drawdown_duration(equity: List[float]) -> int:
    """Longest run of consecutive bars spent below the running peak."""
    peak = -math.inf
    longest = current = 0
    for v in equity:
        if v >= peak:
            peak = v
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def summary(equity: List[float]) -> dict:
    return {
        "total_return": total_return(equity),
        "cagr": cagr(equity),
        "sharpe": sharpe(equity),
        "sortino": sortino(equity),
        "max_drawdown": max_drawdown(equity),
        "calmar": calmar(equity),
        "max_drawdown_duration": max_drawdown_duration(equity),
    }


def round_trips(fills) -> List[dict]:
    """Pair fills into round trips (flat -> position -> flat) with P&L.

    Handles both long and short round trips. A round trip closes when the
    position returns to (or crosses through) zero; partial overshoots start
    the next trip with the remainder.
    """
    trips: List[dict] = []
    open_side = None
    open_qty = 0.0
    open_cost = 0.0  # signed cash spent opening (incl. commission)
    entry_ts = None
    for f in fills:
        signed = f.qty if f.side.value == "buy" else -f.qty
        cash_flow = -signed * f.price - f.commission
        if open_side is None:
            open_side = "long" if signed > 0 else "short"
            open_qty = signed
            open_cost = cash_flow
            entry_ts = f.ts
            continue
        same_direction = (open_side == "long" and signed > 0) or (open_side == "short" and signed < 0)
        if same_direction:
            open_qty += signed
            open_cost += cash_flow
            continue
        # closing or flipping
        closing_qty = min(abs(signed), abs(open_qty))
        close_cash = cash_flow * (closing_qty / abs(signed))
        pnl = open_cost * (closing_qty / abs(open_qty)) + close_cash
        trips.append({
            "side": open_side,
            "qty": closing_qty,
            "entry_ts": entry_ts,
            "exit_ts": f.ts,
            "pnl": pnl,
        })
        remainder = signed + open_qty
        if remainder != 0:
            open_side = "long" if remainder > 0 else "short"
            open_qty = remainder
            open_cost = cash_flow * (abs(remainder) / abs(signed))
            entry_ts = f.ts
        else:
            open_side = None
            open_qty = 0.0
            open_cost = 0.0
    return trips


def trade_stats(fills) -> dict:
    """Win rate, profit factor, and expectancy over closed round trips."""
    trips = round_trips(fills)
    if not trips:
        return {"trades": 0, "win_rate": 0.0, "profit_factor": 0.0, "expectancy": 0.0}
    wins = [t for t in trips if t["pnl"] > 0]
    losses = [t for t in trips if t["pnl"] <= 0]
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = -sum(t["pnl"] for t in losses)
    return {
        "trades": len(trips),
        "win_rate": len(wins) / len(trips),
        "profit_factor": gross_win / gross_loss if gross_loss else float("inf"),
        "expectancy": sum(t["pnl"] for t in trips) / len(trips),
    }
