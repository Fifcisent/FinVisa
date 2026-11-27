"""Random wind-driven stock price simulator."""

from __future__ import annotations

import math
import random
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Mapping, Optional

DEFAULT_INTERVAL_SECONDS = 60
MIN_WIND = -10
MAX_WIND = 10
MAX_WIND_STEP = 3
DEFAULT_STOCK_PRICES = {
    "SBER": 312.50,
    "YDEX": 4180.00,
}


@dataclass(frozen=True)
class MarketSnapshot:
    """A read-only-by-convention copy of the current simulated market."""

    timestamp: datetime
    wind: int
    wind_change: int
    prices: Mapping[str, float]
    price_changes_pct: Mapping[str, float]


class WindDrivenMarket:
    """Simulate independent stock prices influenced by bounded wind changes."""

    def __init__(
        self,
        initial_prices: Mapping[str, float] = DEFAULT_STOCK_PRICES,
        *,
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
        max_wind_step: int = MAX_WIND_STEP,
        seed: Optional[int] = None,
    ) -> None:
        if not initial_prices:
            raise ValueError("At least one stock price is required.")
        if not math.isfinite(interval_seconds) or interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero.")
        if not 1 <= max_wind_step < MAX_WIND:
            raise ValueError("max_wind_step must be between 1 and 9.")

        prices: Dict[str, float] = {}
        for ticker, price in initial_prices.items():
            if not isinstance(ticker, str) or not ticker.strip():
                raise ValueError("Stock tickers must be non-empty strings.")
            if (
                isinstance(price, bool)
                or not isinstance(price, (int, float))
                or not math.isfinite(price)
                or price <= 0
            ):
                raise ValueError("Stock prices must be finite and greater than zero.")
            prices[ticker] = float(price)

        self._prices = prices
        self._rng = random.Random(seed)
        self._interval_seconds = interval_seconds
        self._max_wind_step = max_wind_step
        self._wind = 0
        self._wind_change = 0
        self._price_changes_pct = {ticker: 0.0 for ticker in prices}
        self._sensitivities = {
            ticker: self._rng.uniform(0.15, 0.45) for ticker in prices
        }
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def snapshot(self) -> MarketSnapshot:
        """Return a copy of the latest prices and wind readings."""
        with self._lock:
            return self._snapshot_locked()

    def update(self) -> MarketSnapshot:
        """Apply one random wind gust and update every stock price."""
        with self._lock:
            wind_step = self._rng.randint(-self._max_wind_step, self._max_wind_step)
            new_wind = max(MIN_WIND, min(MAX_WIND, self._wind + wind_step))
            self._wind_change = new_wind - self._wind
            self._wind = new_wind

            old_prices = self._prices.copy()
            tickers = list(self._prices)
            self._rng.shuffle(tickers)

            wind_scale = 1 + abs(self._wind) / MAX_WIND
            for ticker in tickers:
                wind_effect_pct = (
                    (self._wind_change + self._wind * 0.4)
                    * self._sensitivities[ticker]
                    * wind_scale
                )
                independent_noise_pct = self._rng.uniform(-0.35, 0.35)
                shock_pct = 0.0
                if self._rng.random() < 0.03 + abs(self._wind) * 0.02:
                    if self._wind == 0:
                        shock_direction = self._rng.choice((-1, 1))
                    else:
                        shock_direction = 1 if self._wind > 0 else -1
                    shock_pct = shock_direction * self._rng.uniform(12.0, 40.0)
                price_change_pct = wind_effect_pct + independent_noise_pct + shock_pct
                self._prices[ticker] = max(
                    0.01,
                    round(
                        self._prices[ticker] * (1 + price_change_pct / 100),
                        2,
                    ),
                )
                self._price_changes_pct[ticker] = round(
                    (self._prices[ticker] / old_prices[ticker] - 1) * 100,
                    2,
                )

            return self._snapshot_locked()

    def start(
        self,
        on_update: Optional[Callable[[MarketSnapshot], None]] = None,
    ) -> None:
        """Start periodic updates; an optional callback receives each snapshot."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("The market generator is already running.")

            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                args=(on_update,),
                name="wind-driven-market",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        """Stop periodic updates and wait for the worker thread to finish."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join()
            self._thread = None

    def _run(
        self,
        on_update: Optional[Callable[[MarketSnapshot], None]],
    ) -> None:
        while not self._stop_event.wait(self._interval_seconds):
            current_snapshot = self.update()
            if on_update is not None:
                on_update(current_snapshot)

    def _snapshot_locked(self) -> MarketSnapshot:
        return MarketSnapshot(
            timestamp=datetime.now(timezone.utc),
            wind=self._wind,
            wind_change=self._wind_change,
            prices=self._prices.copy(),
            price_changes_pct=self._price_changes_pct.copy(),
        )


if __name__ == "__main__":
    market = WindDrivenMarket()

    def print_update(snapshot: MarketSnapshot) -> None:
        print(
            f"{snapshot.timestamp.isoformat()} | "
            f"wind={snapshot.wind:+d} ({snapshot.wind_change:+d}) | "
            f"prices={dict(snapshot.prices)}"
        )

    print_update(market.snapshot())
    market.start(print_update)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        market.stop()