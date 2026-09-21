"""Position sizing: turn a signal into a quantity.

Strategies should decide direction and timing; how much to risk is a
separate decision with a bigger effect on the equity curve than the signal
itself. These are the two classical sizings.
"""
from __future__ import annotations


def fixed_risk(equity: float, risk_fraction: float, entry: float, stop: float) -> float:
    """Quantity that loses ``risk_fraction`` of equity if the stop is hit.

    qty = (equity * risk_fraction) / |entry - stop|

    Raises if the stop distance is zero - a position with no stop is not a
    sized position, it is a gamble.
    """
    distance = abs(entry - stop)
    if distance == 0:
        raise ValueError("stop distance is zero; cannot size the position")
    if not 0 < risk_fraction <= 1:
        raise ValueError("risk_fraction must be in (0, 1]")
    return equity * risk_fraction / distance


def volatility_target(equity: float, annual_target_vol: float,
                      price: float, annual_vol: float) -> float:
    """Quantity such that the position's volatility matches a target.

    qty = (equity * target_vol) / (price * asset_vol)

    Keeps the risk of each position comparable across regimes: quiet markets
    get bigger positions, wild markets get smaller ones.
    """
    if annual_vol <= 0:
        raise ValueError("asset volatility must be positive")
    if price <= 0:
        raise ValueError("price must be positive")
    return equity * annual_target_vol / (price * annual_vol)
