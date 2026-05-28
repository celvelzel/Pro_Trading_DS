"""
Lobster Quant - Polygon.io Provider
Data provider implementation using Polygon.io Aggregates API for US stocks.
"""

from typing import Optional, cast
from datetime import datetime, timedelta

import pandas as pd
import requests

from .base import DataProvider, DataProviderFactory, RateLimiter
from ...utils.exceptions import DataFetchError
from ...utils.logging import get_logger

logger = get_logger()

# Polygon.io rate limit: 5 requests/minute on free tier
_POLYGON_RPM = 5
_MAX_RETRIES = 2


class PolygonProvider(DataProvider):
    """Polygon.io data provider for US stocks."""

    BASE_URL = "https://api.polygon.io"

    def __init__(self, api_key: str, timeout: int = 15):
        super().__init__(
            name="polygon",
            timeout=timeout,
            rate_limiter=RateLimiter(calls_per_minute=_POLYGON_RPM),
        )
        self._api_key = api_key

    def fetch_daily(self, symbol: str, years: int = 3) -> Optional[pd.DataFrame]:
        """Fetch daily OHLCV data from Polygon.io.

        Uses the Aggregates (Bars) endpoint to retrieve daily OHLCV candles.
        Handles pagination automatically if results exceed the per-request limit.

        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL')
            years: Number of years of historical data

        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        try:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=years * 365)

            from_str = from_date.strftime("%Y-%m-%d")
            to_str = to_date.strftime("%Y-%m-%d")

            all_results: list[dict] = []
            url: Optional[str] = (
                f"{self.BASE_URL}/v2/aggs/ticker/{symbol}/range/1/day/{from_str}/{to_str}"
            )
            params: dict = {
                "adjusted": "true",
                "sort": "asc",
                "limit": 50000,
                "apiKey": self._api_key,
            }

            # Paginate through results
            while url is not None:
                self._acquire_rate_limit()
                response = requests.get(url, params=params, timeout=self._timeout)

                # Handle rate limiting with retry
                if response.status_code == 429:
                    for attempt in range(_MAX_RETRIES):
                        logger.warning(
                            f"Polygon rate limit hit for {symbol}, "
                            f"retrying (attempt {attempt + 1}/{_MAX_RETRIES})"
                        )
                        self._acquire_rate_limit()
                        response = requests.get(url, params=params, timeout=self._timeout)
                        if response.status_code != 429:
                            break
                    else:
                        logger.error(f"Polygon rate limit exceeded for {symbol} after retries")
                        raise DataFetchError(symbol, self.name, "Rate limit exceeded")

                # Handle unauthorized (invalid API key)
                if response.status_code == 401:
                    logger.error("Polygon API authentication failed: invalid API key")
                    raise DataFetchError(symbol, self.name, "Invalid API key")

                response.raise_for_status()
                data = response.json()

                # Check for API-level errors
                if data.get("status") == "ERROR":
                    error_msg = data.get("error", "Unknown API error")
                    logger.error(f"Polygon API error for {symbol}: {error_msg}")
                    raise DataFetchError(symbol, self.name, error_msg)

                results = data.get("results", [])
                if results:
                    all_results.extend(results)

                # Check for next page cursor
                next_url = data.get("next_url")
                if next_url:
                    # next_url already contains query params; use empty params
                    url = next_url
                    params = {"apiKey": self._api_key}
                else:
                    url = None

            if not all_results:
                logger.warning(f"No data returned for {symbol} from Polygon")
                return None

            # Build DataFrame from results
            df = pd.DataFrame(all_results)

            # Rename columns: o->open, h->high, l->low, c->close, v->volume, t->timestamp
            column_map = {
                "o": "open",
                "h": "high",
                "l": "low",
                "c": "close",
                "v": "volume",
                "t": "timestamp",
            }
            df = df.rename(columns=column_map)

            # Keep only OHLCV + timestamp
            df = cast(
                pd.DataFrame, df[["open", "high", "low", "close", "volume", "timestamp"]].copy()
            )

            # Convert timestamp (ms) to datetime index
            df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.set_index("date")
            df = df.drop(columns=["timestamp"])

            # Ensure numeric types
            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").astype("int64")  # type: ignore[arg-type]

            # Sort ascending by date
            df.index.name = "date"
            df.sort_index(inplace=True)

            # Remove any timezone info
            try:
                df.index = df.index.tz_localize(None)  # type: ignore[union-attr]
            except (TypeError, AttributeError):
                pass

            # Remove duplicate dates (can happen across pagination pages)
            df = cast(pd.DataFrame, df[~df.index.duplicated(keep="first")])

            if df.empty:
                logger.warning(f"No data for {symbol} after processing")
                return None

            logger.debug(f"Fetched {len(df)} daily rows for {symbol} from Polygon")
            return df

        except requests.RequestException as e:
            logger.error(f"Network error fetching {symbol} from Polygon: {e}")
            raise DataFetchError(symbol, self.name, str(e))
        except DataFetchError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch daily data for {symbol}: {e}")
            raise DataFetchError(symbol, self.name, str(e))

    def health_check(self) -> bool:
        """Check if Polygon.io API is accessible.

        Makes a lightweight query to verify connectivity and API key validity.
        """
        try:
            # Use a small date range for a lightweight check
            self._acquire_rate_limit()

            to_date = datetime.now()
            from_date = to_date - timedelta(days=5)

            url = (
                f"{self.BASE_URL}/v2/aggs/ticker/AAPL/range/1/day"
                f"/{from_date.strftime('%Y-%m-%d')}/{to_date.strftime('%Y-%m-%d')}"
            )
            params = {
                "adjusted": "true",
                "sort": "asc",
                "limit": 5,
                "apiKey": self._api_key,
            }

            response = requests.get(url, params=params, timeout=self._timeout)

            if response.status_code == 401:
                logger.error("Polygon health check failed: invalid API key")
                self._health_status = False
                return False

            if response.status_code == 429:
                # Rate limited but API is reachable
                logger.warning("Polygon rate limited during health check")
                self._health_status = True
                self._last_health_check = datetime.now()
                return True

            response.raise_for_status()
            data = response.json()

            if data.get("status") == "ERROR":
                logger.error(f"Polygon health check failed: {data.get('error', 'Unknown error')}")
                self._health_status = False
                return False

            self._health_status = True
            self._last_health_check = datetime.now()
            return True

        except Exception as e:
            logger.error(f"Polygon health check failed: {e}")
            self._health_status = False
            return False


def _register():
    """Register Polygon provider with the factory."""
    DataProviderFactory.register("polygon", PolygonProvider)
