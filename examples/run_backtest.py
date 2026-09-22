#!/usr/bin/env python3
"""Backtest the reference strategies on synthetic GBM data.

    python examples/run_backtest.py --days 500 --seed 4 --plot equity.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bt.broker import Broker, CostModel
from bt.data import load_csv, synthetic_gbm
from bt.engine import Backtest
from bt.stats import summary
from bt.strategies import BuyAndHold, MeanReversion, SmaCrossover


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=str, default=None,
                        help="load bars from CSV instead of synthetic data")
    parser.add_argument("--days", type=int, default=500)
    parser.add_argument("--seed", type=int, default=4)
    parser.add_argument("--cash", type=float, default=10_000.0)
    parser.add_argument("--fast", type=int, default=20)
    parser.add_argument("--slow", type=int, default=50)
    parser.add_argument("--plot", type=str, default=None)
    parser.add_argument("--trades-out", type=str, default=None,
                        help="write the SMA strategy trade log to this CSV")
    args = parser.parse_args()

    bars = load_csv(args.csv) if args.csv else synthetic_gbm(days=args.days, seed=args.seed)
    curves = {}
    for name, strategy in [
        ("buy&hold", BuyAndHold()),
        (f"sma {args.fast}/{args.slow}", SmaCrossover(args.fast, args.slow)),
        ("mean-rev 20/2", MeanReversion(window=20, entry_z=2.0)),
    ]:
        bt = Backtest(strategy, Broker(args.cash, CostModel()))
        bt.run(bars)
        curves[name] = bt
        if args.trades_out and name.startswith("sma"):
            from bt.tradelog import write_trades_csv
            n = write_trades_csv(bt.broker.fills, args.trades_out)
        s = summary(bt.equity_curve)
        print(f"{name:>12}: return {s['total_return']:+.1%}  cagr {s['cagr']:+.1%}  "
              f"sharpe {s['sharpe']:.2f}  maxDD {s['max_drawdown']:.1%}  "
              f"fills {len(bt.broker.fills)}")

    if args.plot:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 5))
        for name, bt in curves.items():
            ax.plot(bt.timestamps, bt.equity_curve, label=name, lw=1.0)
        ax.legend()
        ax.set_ylabel("equity")
        fig.tight_layout()
        fig.savefig(args.plot, dpi=120)
        print(f"plot written to {args.plot}")


if __name__ == "__main__":
    main()
