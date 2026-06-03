"""
Lobster Quant - Options Data Provider
Real options chain data from yfinance with 15-minute caching.
Falls back to price-based estimation when options data is unavailable.
"""

import time
import warnings
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from ...utils.logging import get_logger

logger = get_logger()


@dataclass
class OptionsResult:
    """Result from options data fetch."""

    max_pain: float
    put_call_ratio: float
    support: list[float]
    resistance: list[float]
    is_real: bool = True
    expiration: Optional[str] = None


class OptionsProvider:
    """Fetches real options chain data from yfinance with caching.

    Computes max pain, put/call ratio, and support/resistance from
    actual options chain open interest and volume data.
    """

    _CACHE_TTL = 900  # 15 minutes in seconds

    def __init__(self):
        self._cache: dict[str, tuple[float, OptionsResult]] = {}

    def _get_cached(self, symbol: str) -> Optional[OptionsResult]:
        """Return cached result if still valid."""
        if symbol in self._cache:
            ts, result = self._cache[symbol]
            if time.time() - ts < self._CACHE_TTL:
                return result
            del self._cache[symbol]
        return None

    def _set_cache(self, symbol: str, result: OptionsResult) -> None:
        """Store result in cache."""
        self._cache[symbol] = (time.time(), result)

    def fetch_options(self, symbol: str) -> Optional[OptionsResult]:
        """Fetch real options chain data from yfinance.

        Args:
            symbol: Stock ticker symbol (e.g., AAPL)

        Returns:
            OptionsResult with computed metrics, or None on failure.
        """
        cached = self._get_cached(symbol)
        if cached is not None:
            return cached

        try:
            import yfinance as yf

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ticker = yf.Ticker(symbol)
                options_dates = ticker.options

            if not options_dates:
                logger.warning(f"No options dates available for {symbol}")
                return None

            # Use nearest expiration
            nearest_expiration = options_dates[0]
            opt_chain = ticker.option_chain(nearest_expiration)

            calls = opt_chain.calls
            puts = opt_chain.puts

            if calls.empty and puts.empty:
                logger.warning(f"Empty options chain for {symbol}")
                return None

            # Get current price from options data or history
            current_price = None
            if not calls.empty and "lastPrice" in calls.columns:
                atm_idx = (calls["strike"] - calls["lastPrice"].median()).abs().idxmin()
                current_price = float(calls.loc[atm_idx, "lastPrice"])
            if current_price is None:
                hist = ticker.history(period="5d")
                if not hist.empty:
                    current_price = float(hist["Close"].iloc[-1])

            if current_price is None:
                logger.warning(f"Cannot determine current price for {symbol}")
                return None

            # Compute metrics from real options data
            max_pain = self._calc_max_pain(calls, puts, current_price)
            put_call_ratio = self._calc_put_call_ratio(calls, puts)
            support, resistance = self._find_support_resistance(
                calls, puts, current_price
            )

            result = OptionsResult(
                max_pain=max_pain,
                put_call_ratio=put_call_ratio,
                support=support,
                resistance=resistance,
                is_real=True,
                expiration=nearest_expiration,
            )

            self._set_cache(symbol, result)
            logger.info(
                f"Fetched real options for {symbol}: "
                f"max_pain={max_pain:.2f}, pcr={put_call_ratio:.2f}, "
                f"exp={nearest_expiration}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to fetch options for {symbol}: {e}")
            return None

    @staticmethod
    def _calc_max_pain(
        calls: pd.DataFrame, puts: pd.DataFrame, current_price: float
    ) -> float:
        """Calculate max pain strike from open interest.

        Max pain is the strike where option writers (sellers) have the
        least total dollar value of options outstanding.
        """
        all_strikes: set[float] = set()

        if not calls.empty and "strike" in calls.columns:
            for _, row in calls.iterrows():
                oi_val = row.get("openInterest", 0)
                oi = float(oi_val) if oi_val is not None else 0.0
                if oi > 0:
                    all_strikes.add(float(row["strike"]))  # type: ignore[arg-type]

        if not puts.empty and "strike" in puts.columns:
            for _, row in puts.iterrows():
                oi_val = row.get("openInterest", 0)
                oi = float(oi_val) if oi_val is not None else 0.0
                if oi > 0:
                    all_strikes.add(float(row["strike"]))  # type: ignore[arg-type]

        if not all_strikes:
            return current_price

        min_loss = float("inf")
        max_pain = current_price

        for strike in all_strikes:
            # Total dollar value lost by option holders at this strike
            call_loss = 0.0
            if not calls.empty:
                for _, row in calls.iterrows():
                    oi_val = row.get("openInterest", 0)
                    oi = float(oi_val) if oi_val is not None else 0.0
                    s = float(row.get("strike", 0))  # type: ignore[arg-type]
                    call_loss += max(0.0, strike - s) * oi

            put_loss = 0.0
            if not puts.empty:
                for _, row in puts.iterrows():
                    oi_val = row.get("openInterest", 0)
                    oi = float(oi_val) if oi_val is not None else 0.0
                    s = float(row.get("strike", 0))  # type: ignore[arg-type]
                    put_loss += max(0.0, s - strike) * oi

            total_loss = call_loss + put_loss
            if total_loss < min_loss:
                min_loss = total_loss
                max_pain = strike

        return float(max_pain)

    @staticmethod
    def _calc_put_call_ratio(
        calls: pd.DataFrame, puts: pd.DataFrame
    ) -> float:
        """Calculate put/call ratio by open interest."""
        call_oi: float = 0.0
        if not calls.empty and "openInterest" in calls.columns:
            call_oi = float(calls["openInterest"].fillna(0).sum())  # type: ignore[arg-type]

        put_oi: float = 0.0
        if not puts.empty and "openInterest" in puts.columns:
            put_oi = float(puts["openInterest"].fillna(0).sum())  # type: ignore[arg-type]

        if call_oi == 0:
            return 1.0  # Neutral when no call data

        return put_oi / call_oi

    @staticmethod
    def _find_support_resistance(
        calls: pd.DataFrame,
        puts: pd.DataFrame,
        current_price: float,
    ) -> tuple[list[float], list[float]]:
        """Derive support and resistance levels from options open interest.

        Support: Put strikes with highest open interest (below current price).
        Resistance: Call strikes with highest open interest (above current price).
        """
        support_levels: list[float] = []
        resistance_levels: list[float] = []

        # Put OI below current price → support
        if not puts.empty and "strike" in puts.columns:
            puts_below = puts[
                (puts["strike"] < current_price) & (puts["openInterest"] > 0)
            ].copy()
            if not puts_below.empty:
                puts_below = puts_below.nlargest(3, "openInterest")  # type: ignore[arg-type]
                support_levels = sorted(
                    [float(s) for s in puts_below["strike"]], reverse=True
                )

        # Call OI above current price → resistance
        if not calls.empty and "strike" in calls.columns:
            calls_above = calls[
                (calls["strike"] > current_price) & (calls["openInterest"] > 0)
            ].copy()
            if not calls_above.empty:
                calls_above = calls_above.nlargest(3, "openInterest")  # type: ignore[arg-type]
                resistance_levels = sorted(
                    [float(s) for s in calls_above["strike"]]
                )

        return support_levels, resistance_levels


# Module-level singleton
_options_provider: Optional[OptionsProvider] = None


def get_options_provider() -> OptionsProvider:
    """Get or create the singleton OptionsProvider."""
    global _options_provider
    if _options_provider is None:
        _options_provider = OptionsProvider()
    return _options_provider
