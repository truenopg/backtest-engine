# backtest-engine

[![tests](https://github.com/truenopg/backtest-engine/actions/workflows/tests.yml/badge.svg)](https://github.com/truenopg/backtest-engine/actions/workflows/tests.yml)

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
  signal, so it gets its own module - `examples/sizing_experiment.py` runs the
  same signal under all-in, fixed-risk, and vol-target sizing and shows the
  drawdown profile change more than the return does.
- **Reference strategies**: buy & hold, SMA crossover (optionally long/short),
  Bollinger-style mean reversion, and a Donchian breakout - the four canonical
  archetypes, used as sanity-check benchmarks.
- **Performance stats**: total return, CAGR, Sharpe, Sortino, max
  drawdown (depth and duration), Calmar, plus
  per-trade analytics (round trips, win rate, profit factor, expectancy).
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
    buy&hold: return +2.6%  cagr +1.3%  sharpe 0.16  sortino 0.23  maxDD -26.1% (326 bars)  calmar 0.05  trades 0  win 0%  PF 0.00
   sma 20/50: return +4.7%  cagr +2.3%  sharpe 0.24  sortino 0.34  maxDD -16.1% (326 bars)  calmar 0.14  trades 4  win 50%  PF 1.42
mean-rev 20/2: return -5.0%  cagr -2.5%  sharpe -0.24  sortino -0.33  maxDD -20.3% (293 bars)  calmar -0.12  trades 9  win 67%  PF 0.75
breakout 55/20: return -7.8%  cagr -4.0%  sharpe -0.33  sortino -0.46  maxDD -18.9% (326 bars)  calmar -0.21  trades 5  win 40%  PF 0.52
```

The losing mean-reversion and breakout lines are the honest ones: GBM has
independent increments, so there is no mean to revert to and no trend to
follow. An engine that can't surface those null results is not trustworthy
for strategies that do work.

### Experiment: how much cost can an edge absorb?

`examples/cost_sensitivity.py` re-runs every reference strategy at rising
total cost per side (commission + slippage), same data:

```
  cost bps/side        buy&hold       sma 20/50   mean-rev 20/2  breakout 55/20
              0           +2.6%           +4.8%           -4.6%           -7.6%
              2           +2.6%           +4.7%           -5.0%           -7.8%
              5           +2.5%           +4.4%           -5.4%           -8.1%
             10           +2.5%           +4.0%           -6.3%           -8.5%
             25           +2.4%           +2.9%           -8.6%           -9.8%
             50           +2.1%           +0.9%          -12.5%          -12.0%
```

Decay speed tracks turnover: buy & hold barely notices 50 bps, the
9-round-trip mean-reversion bleeds ~0.4 pp per 10 bps, and the SMA edge
is halved at 50 bps. "Does it survive realistic costs?" is the first
question to ask any backtest, so the engine makes it a one-command check.

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
