#!/usr/bin/env python3
"""Sweep SMA crossover parameters and confront in-sample with out-of-sample.

    python examples/parameter_sweep.py --days 800 --seed 4
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bt.data import synthetic_gbm
from bt.strategies import SmaCrossover
from bt.sweep import sweep


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=800)
    parser.add_argument("--seed", type=int, default=4)
    args = parser.parse_args()

    bars = synthetic_gbm(days=args.days, seed=args.seed)
    rows = sweep(
        bars,
        SmaCrossover,
        {"fast": [5, 10, 15, 20, 30], "slow": [40, 50, 80, 120]},
    )

    print(f"{'params':>12} {'IS ret':>8} {'IS sharpe':>10} {'OOS ret':>8} {'OOS sharpe':>11}")
    rows.sort(key=lambda r: r["out_of_sample"]["sharpe"], reverse=True)
    for r in rows:
        p = r["params"]
        print(f"{p['fast']:>5}/{p['slow']:<6} {r['in_sample']['total_return']:>+8.1%} "
              f"{r['in_sample']['sharpe']:>10.2f} {r['out_of_sample']['total_return']:>+8.1%} "
              f"{r['out_of_sample']['sharpe']:>11.2f}")

    best_is = max(rows, key=lambda r: r["in_sample"]["sharpe"])
    print(f"\nbest in-sample: {best_is['params']} -> OOS sharpe "
          f"{best_is['out_of_sample']['sharpe']:.2f}")
    print("if the best IS params do not hold up OOS, that gap is the overfitting tax")


if __name__ == "__main__":
    main()
