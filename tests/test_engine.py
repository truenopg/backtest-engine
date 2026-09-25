import unittest
from datetime import datetime, timedelta

from bt import Backtest, Bar, Broker, Order, Side
from bt.stats import (cagr, calmar, max_drawdown, max_drawdown_duration,
                      sharpe, sortino, total_return)
from bt.strategies import BuyAndHold, SmaCrossover


def make_bars(prices):
    ts = datetime(2024, 1, 1)
    bars = []
    for p in prices:
        bars.append(Bar(ts, p, p, p, p, 100.0))
        ts += timedelta(days=1)
    return bars


class TestBroker(unittest.TestCase):
    def test_buy_moves_cash_to_position(self):
        broker = Broker(1000.0)
        broker.execute(Order(Side.BUY, 5.0), make_bars([100.0])[0])
        self.assertEqual(broker.position, 5.0)
        self.assertLess(broker.cash, 1000.0 - 500.0 + 1)  # costs on top

    def test_equity_marks_to_market(self):
        broker = Broker(1000.0)
        broker.execute(Order(Side.BUY, 5.0), make_bars([100.0])[0])
        self.assertAlmostEqual(broker.equity(110.0), broker.cash + 550.0)


class TestLookAhead(unittest.TestCase):
    def test_order_fills_next_bar_open_not_signal_bar(self):
        class BuyFirst:
            def __init__(self):
                self.n = 0
            def on_bar(self, bar, broker):
                self.n += 1
                return Order(Side.BUY, 1.0) if self.n == 1 else None

        bars = make_bars([100.0, 200.0, 300.0])
        bt = Backtest(BuyFirst(), Broker(10_000.0))
        bt.run(bars)
        # signal on bar 1 (open 100) must fill at bar 2's open (200), not 100
        self.assertEqual(bt.broker.fills[0].price, 200.0 * 1.0001)


class TestStrategies(unittest.TestCase):
    def test_buy_and_hold_buys_once(self):
        bt = Backtest(BuyAndHold(), Broker(10_000.0))
        bt.run(make_bars([100.0] * 10))
        self.assertEqual(len(bt.broker.fills), 1)
        self.assertEqual(bt.broker.fills[0].side, Side.BUY)

    def test_sma_crossover_waits_for_slow_window(self):
        bt = Backtest(SmaCrossover(fast=2, slow=5), Broker(10_000.0))
        bt.run(make_bars([100.0] * 4))
        self.assertEqual(len(bt.broker.fills), 0)


class TestStats(unittest.TestCase):
    def test_total_return(self):
        self.assertAlmostEqual(total_return([100.0, 110.0]), 0.10)

    def test_flat_equity(self):
        self.assertEqual(total_return([100.0, 100.0]), 0.0)
        self.assertEqual(sharpe([100.0] * 10), 0.0)

    def test_max_drawdown(self):
        self.assertAlmostEqual(max_drawdown([100.0, 120.0, 90.0, 110.0]), -0.25)


class TestRiskMetrics(unittest.TestCase):
    def test_sortino_hand_computed(self):
        # returns [-0.1, +0.2]: mean 0.05, downside dev sqrt(0.01/2)
        import math
        expected = 0.05 / math.sqrt(0.005) * math.sqrt(252)
        self.assertAlmostEqual(sortino([100.0, 90.0, 108.0]), expected)

    def test_sortino_does_not_punish_upside_vol(self):
        rising = [100.0, 105.0, 121.0]
        self.assertGreater(sharpe(rising), 0.0)
        self.assertEqual(sortino(rising), 0.0)  # no downside deviation

    def test_sortino_negative_when_only_downside(self):
        self.assertLess(sortino([100.0, 90.0, 81.0]), 0.0)

    def test_calmar_is_cagr_over_drawdown(self):
        equity = [100.0, 80.0, 120.0, 110.0]
        self.assertAlmostEqual(calmar(equity), cagr(equity) / abs(max_drawdown(equity)))

    def test_calmar_zero_without_drawdown(self):
        self.assertEqual(calmar([100.0, 110.0, 121.0]), 0.0)

    def test_max_drawdown_duration(self):
        self.assertEqual(max_drawdown_duration([100.0, 90.0, 95.0, 110.0, 105.0, 100.0]), 2)
        self.assertEqual(max_drawdown_duration([100.0, 110.0, 120.0]), 0)


if __name__ == "__main__":
    unittest.main()


class TestSizing(unittest.TestCase):
    def test_fixed_risk(self):
        from bt.sizing import fixed_risk
        # risk 1% of 10k = 100; stop 5 away -> 20 units
        self.assertAlmostEqual(fixed_risk(10_000.0, 0.01, 100.0, 95.0), 20.0)

    def test_fixed_risk_zero_distance_raises(self):
        from bt.sizing import fixed_risk
        with self.assertRaises(ValueError):
            fixed_risk(10_000.0, 0.01, 100.0, 100.0)

    def test_volatility_target(self):
        from bt.sizing import volatility_target
        # 20% target on 10k = 2000 vol budget; price 100, vol 20% -> 200 units
        self.assertAlmostEqual(volatility_target(10_000.0, 0.20, 100.0, 0.20), 100.0)


class TestMeanReversion(unittest.TestCase):
    def test_buys_the_dip_and_exits_at_mean(self):
        from bt.strategies import MeanReversion
        from bt import Backtest, Broker
        # calm series, then a sharp dip, then recovery
        prices = [100.0] * 30 + [92.0, 90.0] + [100.0] * 5
        bt = Backtest(MeanReversion(window=20, entry_z=2.0), Broker(10_000.0))
        bt.run(make_bars(prices))
        from bt.core import Side
        sides = [f.side for f in bt.broker.fills]
        self.assertGreaterEqual(len(sides), 2)  # bought the dip, exited on reversion
        self.assertEqual(sides[0], Side.BUY)
        self.assertEqual(sides[-1], Side.SELL)


class TestSweep(unittest.TestCase):
    def test_chronological_split(self):
        from bt.sweep import split_bars
        bars = make_bars([100.0 + i for i in range(100)])
        ins, oos = split_bars(bars, 0.7)
        self.assertEqual(len(ins), 70)
        self.assertEqual(len(oos), 30)
        self.assertLess(ins[-1].ts, oos[0].ts)  # no future in the past

    def test_sweep_skips_invalid_combos(self):
        from bt.strategies import SmaCrossover
        from bt.sweep import sweep
        rows = sweep(make_bars([100.0 + (i % 7) for i in range(120)]),
                     SmaCrossover, {"fast": [2, 60], "slow": [5, 50]})
        # valid: (2,5),(2,50),(60,...none>=50?) -> fast=60,slow=50 invalid, fast=60 slow=... 
        fast_slow = {(r["params"]["fast"], r["params"]["slow"]) for r in rows}
        self.assertNotIn((60, 50), fast_slow)
        self.assertIn((2, 5), fast_slow)


class TestBreakout(unittest.TestCase):
    def test_buys_new_high_and_exits_on_breakdown(self):
        from bt import Backtest, Broker
        from bt.core import Side
        from bt.strategies import Breakout
        # flat base, breakout bar, then a collapse through the exit channel
        prices = [100.0] * 8 + [101.0, 105.0] + [103.0] * 3 + [95.0] * 3
        bt = Backtest(Breakout(entry=6, exit=4), Broker(10_000.0))
        bt.run(make_bars(prices))
        sides = [f.side for f in bt.broker.fills]
        self.assertGreaterEqual(len(sides), 2)
        self.assertEqual(sides[0], Side.BUY)
        self.assertEqual(sides[-1], Side.SELL)

    def test_no_position_without_breakout(self):
        from bt import Backtest, Broker
        from bt.strategies import Breakout
        bt = Backtest(Breakout(entry=6, exit=4), Broker(10_000.0))
        bt.run(make_bars([100.0] * 20))
        self.assertEqual(len(bt.broker.fills), 0)


class TestShortSelling(unittest.TestCase):
    def test_short_flip_when_bearish(self):
        from bt.strategies import SmaCrossover
        from bt import Backtest, Broker
        from bt.core import Side
        # rising then falling: crosses up then down
        prices = [100.0 + i for i in range(8)] + [108.0 - 3 * i for i in range(8)]
        bt = Backtest(SmaCrossover(fast=2, slow=4, allow_short=True), Broker(10_000.0))
        bt.run(make_bars(prices))
        self.assertLess(bt.broker.position, 0)  # ends short
        self.assertTrue(any(f.side is Side.SELL for f in bt.broker.fills))

    def test_long_flat_default_never_short(self):
        from bt.strategies import SmaCrossover
        from bt import Backtest, Broker
        prices = [100.0 + i for i in range(8)] + [108.0 - 3 * i for i in range(8)]
        bt = Backtest(SmaCrossover(fast=2, slow=4), Broker(10_000.0))
        bt.run(make_bars(prices))
        self.assertGreaterEqual(bt.broker.position, 0)


class TestTradeStats(unittest.TestCase):
    def test_round_trip_pnl(self):
        from bt import Broker, Order, Side
        from bt.stats import round_trips, trade_stats
        broker = Broker(10_000.0)
        bars = make_bars([100.0, 110.0])
        broker.execute(Order(Side.BUY, 10.0), bars[0])
        broker.execute(Order(Side.SELL, 10.0), bars[1])
        trips = round_trips(broker.fills)
        self.assertEqual(len(trips), 1)
        self.assertEqual(trips[0]["side"], "long")
        self.assertGreater(trips[0]["pnl"], 0)  # 110 exit vs 100 entry
        stats = trade_stats(broker.fills)
        self.assertEqual(stats["trades"], 1)
        self.assertEqual(stats["win_rate"], 1.0)
