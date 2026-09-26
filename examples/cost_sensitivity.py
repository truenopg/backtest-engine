#!/usr/bin/env python3
"""How much transaction cost each strategy's edge can absorb.

    python examples/cost_sensitivity.py --days 500 --seed 4

Re-runs every reference strategy at increasing total cost per side
(commission + slippage, split evenly) on the same data and prints total
return at each level. High-turnover strategies decay fastest - that is
the point of measuring it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bt.broker import Broker, CostModel
from bt.data import load_csv, synthetic_gbm
from bt.engine import Backtest
from bt.stats import summary, trade_stats
from bt.strategies import Breakout, BuyAndHold, MeanReversion, SmaCrossover

LEVELS_BPS = [0, 2, 5, 10, 25, 50]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=str, default=None,
                        help="load bars from CSV instead of synthetic data")
    parser.add_argument("--days", type=int, default=500)
    parser.add_argument("--seed", type=int, default=4)
    parser.add_argument("--cash", type=float, default=10_000.0)
    args = parser.parse_args()

    bars = load_csv(args.csv) if args.csv else synthetic_gbm(days=args.days, seed=args.seed)
    strategies = [
        ("buy&hold", BuyAndHold),
        ("sma 20/50", lambda: SmaCrossover(20, 50)),
        ("mean-rev 20/2", lambda: MeanReversion(window=20, entry_z=2.0)),
        ("breakout 55/20", lambda: Breakout(entry=55, exit=20)),
    ]

    print(f"{'cost bps/side':>15}" + "".join(f"{name:>16}" for name, _ in strategies))
    for bps in LEVELS_BPS:
        row = f"{bps:>15}"
        for name, make in strategies:
            cost = CostModel(commission_bps=bps / 2, slippage_bps=bps / 2)
            bt = Backtest(make(), Broker(args.cash, cost))
            bt.run(bars)
            s = summary(bt.equity_curve)
            n = trade_stats(bt.broker.fills)["trades"]
            row += f"{s['total_return']:+.1%} ({n:>2})".rjust(16) if bps == 0 else f"{s['total_return']:+.1%}".rjust(16)
        print(row)


if __name__ == "__main__":
    main()
