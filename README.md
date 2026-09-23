# backtest-engine

A small event-driven backtesting engine in Python, built to be correct about
the things most toy backtests get wrong.

## What it does

- **Next-bar fills**: a signal computed on bar *t* fills at the open of bar
  *t+1*, never on the bar that produced it. Filling on the signal bar is the
  look-ahead bias that quietly makes most backtests lie.
- **Realistic costs**: proportional commission plus slippage in basis points,
  applied to every fill. Strategies that look great gross of costs often do
  not survive this.
- **Event-driven loop**: bars stream in, the strategy returns orders, the
  broker tracks cash/position, the equity curve is marked to market on every
  bar close.
- **Position sizing** (`bt/sizing.py`): fixed-risk (size from stop distance)
  and volatility-target sizings. How much to risk matters more than the
  signal, so it gets its own module.
- **Reference strategies**: buy & hold, SMA crossover (optionally long/short),
  Bollinger-style mean reversion, and a Donchian breakout - the four canonical
  archetypes, used as sanity-check benchmarks.
- **Performance stats**: total return, CAGR, Sharpe, max drawdown.
- **Parameter sweeps** (`bt/sweep.py`): grid-search any strategy over a
  chronological in-sample / out-of-sample split, and see the overfitting tax
  directly - the best in-sample params usually do not hold up out-of-sample.
- **Synthetic data**: a GBM generator so everything runs without a data
  vendor, plus a CSV loader for real data (ts, open, high, low, close, volume).

## Why

Backtests are how trading ideas die or survive. The failure modes are well
known (look-ahead bias, ignoring costs, overfitting), so this engine bakes
the first two into its core and keeps the third honest with simple,
few-parameter reference strategies.

## Run it

```bash
python examples/run_backtest.py --days 500 --seed 4 --plot equity.png
python -m unittest discover -s tests
```

Sample output (seed 4, 500 synthetic days):

```
   buy&hold: return +2.6%  cagr +1.3%  sharpe 0.16  maxDD -26.1%  fills 1
  sma 20/50: return +4.7%  cagr +2.3%  sharpe 0.24  maxDD -16.1%  fills 8
mean-rev 20/2: return -5.0%  cagr -2.5%  sharpe -0.24  maxDD -20.3%  fills 18
breakout 55/20: return -7.8%  cagr -4.0%  sharpe -0.33  maxDD -18.9%  fills 10
```

The losing mean-reversion and breakout lines are the honest ones: GBM has
independent increments, so there is no mean to revert to and no trend to
follow. An engine that can't surface those null results is not trustworthy
for strategies that do work.

## Layout

```
bt/core.py        Bar, Order, Fill types
bt/broker.py      cash/position accounting + cost model
bt/engine.py      event loop (next-bar fills)
bt/strategies.py  reference strategies
bt/stats.py       performance statistics
bt/sweep.py       parameter sweeps with IS/OOS split
bt/data.py        synthetic GBM + CSV loader
examples/         runnable demo
tests/            unittest suite
```

## Roadmap

- Trade log export (CSV) and per-trade analytics

## License

MIT - see [LICENSE](LICENSE).
