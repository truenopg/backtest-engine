"""Simulated broker: fills orders on the next bar's open, charges costs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .core import Bar, Fill, Order, Side


@dataclass
class CostModel:
    """Proportional commission plus slippage in basis points."""

    commission_bps: float = 1.0
    slippage_bps: float = 1.0

    def fill_price(self, side: Side, price: float) -> float:
        slip = price * self.slippage_bps / 10_000
        return price + slip if side is Side.BUY else price - slip

    def commission(self, qty: float, price: float) -> float:
        return abs(qty) * price * self.commission_bps / 10_000


class Broker:
    """Holds cash and position; executes orders at a given bar's open."""

    def __init__(self, cash: float, costs: Optional[CostModel] = None) -> None:
        self.cash = cash
        self.position = 0.0
        self.costs = costs or CostModel()
        self.fills: list[Fill] = []

    def execute(self, order: Order, bar: Bar) -> Fill:
        price = self.costs.fill_price(order.side, bar.open)
        signed = order.qty if order.side is Side.BUY else -order.qty
        commission = self.costs.commission(order.qty, price)
        self.position += signed
        self.cash -= signed * price + commission
        fill = Fill(bar.ts, order.side, order.qty, price, commission)
        self.fills.append(fill)
        return fill

    def equity(self, price: float) -> float:
        return self.cash + self.position * price
