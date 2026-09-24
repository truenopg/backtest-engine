#!/usr/bin/env python3
"""Same signal, three sizing rules: how much does sizing move the needle?

Runs the SMA crossover signal with all-in sizing, fixed-risk sizing (1%
risk per trade, stop at 2x recent volatility), and volatility targeting,
then compares equity statistics.
"""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bt.broker import Broker, CostModel
from bt.core import Bar, Order, Side
from bt.data import synthetic_gbm
from bt.engine import Backtest
from bt.sizing import fixed_risk, volatility_target
from bt.stats import summary


class SmaWithSizing:
    """SMA crossover signal with a pluggable sizing rule."""

    def __init__(self, fast: int, slow: int, mode: str) -> None:
        if mode not in ("all-in", "fixed-risk", "vol-target"):
            raise ValueError(f"unknown sizing mode {mode}")
        self.fast, self.slow, self.mode = fast, slow, mode
        self._closes: deque = deque(maxlen=slow)

    def _sma(self, window: int) -> float:
        values = list(self._closes)[-window:]
        return sum(values) / len(values)

    def _vol(self) -> float:
        values = list(self._closes)
        rets = [b / a - 1 for a, b in zip(values, values[1:]) if a]
        if len(rets) < 2:
            return 0.0
        mean = sum(rets) / len(rets)
        return (sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)) ** 0.5

    def on_bar(self, bar: Bar, broker: Broker) -> Optional[Order]:
        self._closes.append(bar.close)
        if len(self._closes) < self.slow:
            return None
        bullish = self._sma(self.fast) > self._sma(self.slow)
        equity = broker.equity(bar.close)
        if bullish and broker.position <= 0:
            if self.mode == "all-in":
                qty = equity * 0.95 / bar.close
            elif self.mode == "fixed-risk":
                stop = bar.close * (1 - 2 * self._vol() * 5)
                qty = fixed_risk(equity, 0.01, bar.close, stop)
            else:
                qty = volatility_target(equity, 0.15 / (252 ** 0.5), bar.close,
                                        self._vol() or 1e-6)
            return Order(Side.BUY, qty - broker.position) if qty > 0 else None
        if not bullish and broker.position > 0:
            return Order(Side.SELL, broker.position)
        return None


def main() -> None:
    bars = synthetic_gbm(days=500, seed=4)
    for mode in ("all-in", "fixed-risk", "vol-target"):
        bt = Backtest(SmaWithSizing(20, 50, mode), Broker(10_000.0, CostModel()))
        bt.run(bars)
        s = summary(bt.equity_curve)
        print(f"{mode:>11}: return {s['total_return']:+.1%}  sharpe {s['sharpe']:.2f}  "
              f"maxDD {s['max_drawdown']:.1%}")


if __name__ == "__main__":
    main()
