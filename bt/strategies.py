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
    """Goes long when the fast SMA crosses above the slow SMA.

    Long/flat by default; with ``allow_short`` it flips to a symmetric short
    when bearish instead of going flat. Position sizing is all-in/all-out on
    current equity - deliberately simple; risk management belongs in the
    sizing module, not the signal.
    """

    def __init__(self, fast: int = 20, slow: int = 50, allow_short: bool = False) -> None:
        if fast >= slow:
            raise ValueError("fast window must be smaller than slow window")
        self.fast = fast
        self.slow = slow
        self.allow_short = allow_short
        self._closes: deque = deque(maxlen=slow)

    def _sma(self, window: int) -> float:
        values = list(self._closes)[-window:]
        return sum(values) / len(values)

    def on_bar(self, bar: Bar, broker: Broker) -> Optional[Order]:
        self._closes.append(bar.close)
        if len(self._closes) < self.slow:
            return None
        bullish = self._sma(self.fast) > self._sma(self.slow)
        full = broker.equity(bar.close) * 0.95 / bar.close
        # trade only on regime change: enter/flip when the signal side differs
        # from the position side, otherwise hold (no daily rebalancing)
        if bullish and broker.position <= 0:
            return Order(Side.BUY, full - broker.position)
        if not bullish and broker.position >= 0:
            qty = broker.position + full if self.allow_short else broker.position
            if qty > 0:
                return Order(Side.SELL, qty)
        return None


class MeanReversion:
    """Buys stretched dips and exits back at the mean (Bollinger-style).

    Long-only: when the close sits more than ``entry_z`` standard deviations
    below its rolling mean, the strategy goes long; it exits when the close
    reverts to the mean. Sized all-in like the SMA strategy - the sizing
    module exists for when this gets a stop.
    """

    def __init__(self, window: int = 20, entry_z: float = 2.0) -> None:
        if entry_z <= 0:
            raise ValueError("entry_z must be positive")
        self.window = window
        self.entry_z = entry_z
        self._closes: deque = deque(maxlen=window)

    def _z(self, price: float) -> Optional[float]:
        if len(self._closes) < self.window:
            return None
        values = list(self._closes)
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / len(values)
        sd = var ** 0.5
        return (price - mean) / sd if sd else 0.0

    def on_bar(self, bar: Bar, broker: Broker) -> Optional[Order]:
        self._closes.append(bar.close)
        z = self._z(bar.close)
        if z is None:
            return None
        if z < -self.entry_z and broker.position <= 0:
            qty = broker.equity(bar.close) * 0.95 / bar.close
            return Order(Side.BUY, qty)
        if z >= 0 and broker.position > 0:
            return Order(Side.SELL, broker.position)
        return None


class Breakout:
    """Donchian-channel breakout: long on a new ``entry``-period high,
    out on a new ``exit``-period low. Long-only trend following.
    """

    def __init__(self, entry: int = 55, exit: int = 20) -> None:
        if entry < 2 or exit < 2:
            raise ValueError("windows must be >= 2")
        self.entry = entry
        self.exit = exit
        self._highs: deque = deque(maxlen=entry)
        self._lows: deque = deque(maxlen=exit)

    def on_bar(self, bar: Bar, broker: Broker) -> Optional[Order]:
        prev_high = max(self._highs) if len(self._highs) == self.entry else None
        prev_low = min(self._lows) if len(self._lows) == self.exit else None
        self._highs.append(bar.high)
        self._lows.append(bar.low)
        if prev_high is not None and bar.close > prev_high and broker.position <= 0:
            qty = broker.equity(bar.close) * 0.95 / bar.close
            return Order(Side.BUY, qty)
        if prev_low is not None and bar.close < prev_low and broker.position > 0:
            return Order(Side.SELL, broker.position)
        return None
