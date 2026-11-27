import unittest

from invest_generator import WindDrivenMarket


class WindDrivenMarketTests(unittest.TestCase):
    def test_wind_can_cause_sharp_falls_and_rallies_without_zero_prices(self):
        market = WindDrivenMarket(initial_prices={"TEST": 1000}, seed=2026)
        snapshots = [market.update() for _ in range(500)]
        changes = [snapshot.price_changes_pct["TEST"] for snapshot in snapshots]

        self.assertLessEqual(min(changes), -20)
        self.assertGreaterEqual(max(changes), 20)
        self.assertTrue(all(-10 <= snapshot.wind <= 10 for snapshot in snapshots))
        self.assertTrue(all(snapshot.prices["TEST"] > 0 for snapshot in snapshots))


if __name__ == "__main__":
    unittest.main()
