import unittest
from datetime import datetime, timedelta

from bt import Backtest, Bar, Broker, Order, Side
from bt.stats import max_drawdown, sharpe, total_return
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
