"""Core types for the event-driven backtesting engine."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Bar:
    """One OHLCV bar."""

    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class Order:
    """A market order requested by a strategy, sized in units."""

    side: Side
    qty: float


@dataclass
class Fill:
    """An executed order at a concrete price."""

    ts: datetime
    side: Side
    qty: float
    price: float
    commission: float
