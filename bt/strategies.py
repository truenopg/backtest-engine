"""Reference strategies."""
from __future__ import annotations

from collections import deque
from typing import Optional

from .broker import Broker
from .core import Bar, Order, Side


class BuyAndHold:
    """Buys once with a fixed fraction of the initial cash and holds."""

    def __init__(self, fraction: float = 0.95) -> None:
        self.fraction = fraction
        self._done = False

    def on_bar(self, bar: Bar, broker: Broker) -> Optional[Order]:
        if self._done:
            return None
        self._done = True
        qty = broker.cash * self.fraction / bar.close
        return Order(Side.BUY, qty)


class SmaCrossover:
    """Goes long when the fast SMA crosses above the slow SMA, flat when below.

    Position sizing is all-in/all-out on the current equity - deliberately
    simple; risk management belongs in a sizing layer, not the signal.
    """

    def __init__(self, fast: int = 20, slow: int = 50) -> None:
        if fast >= slow:
            raise ValueError("fast window must be smaller than slow window")
        self.fast = fast
        self.slow = slow
        self._closes: deque = deque(maxlen=slow)

    def _sma(self, window: int) -> float:
        values = list(self._closes)[-window:]
        return sum(values) / len(values)

    def on_bar(self, bar: Bar, broker: Broker) -> Optional[Order]:
        self._closes.append(bar.close)
        if len(self._closes) < self.slow:
            return None
        bullish = self._sma(self.fast) > self._sma(self.slow)
        if bullish and broker.position <= 0:
            qty = broker.equity(bar.close) * 0.95 / bar.close - broker.position
            return Order(Side.BUY, qty) if qty > 0 else None
        if not bullish and broker.position > 0:
            return Order(Side.SELL, broker.position)
        return None
