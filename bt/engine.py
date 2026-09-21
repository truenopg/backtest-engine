"""The event loop: bars in, orders out, equity curve recorded."""
from __future__ import annotations

from typing import Iterable, List, Optional, Protocol

from .broker import Broker
from .core import Bar, Order


class Strategy(Protocol):
    """A strategy sees each bar (and the broker state) and may return an order.

    Orders are filled at the NEXT bar's open - never the bar that produced
    the signal, which is the look-ahead trap most toy backtesters fall into.
    """

    def on_bar(self, bar: Bar, broker: Broker) -> Optional[Order]:
        ...


class Backtest:
    def __init__(self, strategy: Strategy, broker: Broker) -> None:
        self.strategy = strategy
        self.broker = broker
        self.equity_curve: List[float] = []
        self.timestamps: List = []

    def run(self, bars: Iterable[Bar]) -> None:
        pending: Optional[Order] = None
        for bar in bars:
            if pending is not None:
                self.broker.execute(pending, bar)
                pending = None
            pending = self.strategy.on_bar(bar, self.broker)
            self.equity_curve.append(self.broker.equity(bar.close))
            self.timestamps.append(bar.ts)
