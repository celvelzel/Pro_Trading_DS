"""
Lobster Quant - Alpha Vantage Provider
Data provider implementation using Alpha Vantage API for US and HK stocks.
"""

from typing import Optional, cast
from datetime import datetime, timedelta

import pandas as pd
import requests

from .base import DataProvider, DataProviderFactory, RateLimiter
from ...utils.exceptions import DataFetchError
from ...utils.logging import get_logger

logger = get_logger()

# Alpha Vantage free tier: 5 requests per minute, 500 per day
_ALPHA_VANTAGE_RPM = 5


class AlphaVantageProvider(DataProvider):
    """Alpha Vantage data provider for US and HK stocks."""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str, timeout: int = 15):
        super().__init__(
            name="alpha_vantage",
            timeout=timeout,
            rate_limiter=RateLimiter(calls_per_minute=_ALPHA_VANTAGE_RPM),
        )
        self._api_key = api_key

    def fetch_daily(self, symbol: str, years: int = 3) -> Optional[pd.DataFrame]:
        """Fetch daily OHLCV data from Alpha Vantage.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', '0700.HK')
            years: Number of years of historical data

        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        try:
            # Rate limit before making the request
            self._acquire_rate_limit()

            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "apikey": self._api_key,
                "outputsize": "full",
            }

            response = requests.get(self.BASE_URL, params=params, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()

            # Handle API errors
            if "Error Message" in data:
                error_msg = data["Error Message"]
                logger.error(f"Alpha Vantage API error for {symbol}: {error_msg}")
                raise DataFetchError(symbol, self.name, error_msg)

            if "Note" in data:
                # Rate limit hit despite our limiter — retry once after a pause
                logger.warning(f"Alpha Vantage rate limit hit for {symbol}: {data['Note']}")
                self._acquire_rate_limit()
                response = requests.get(self.BASE_URL, params=params, timeout=self._timeout)
                response.raise_for_status()
                data = response.json()

                if "Note" in data or "Error Message" in data:
                    error_msg = data.get("Note", data.get("Error Message", "Unknown error"))
                    raise DataFetchError(symbol, self.name, error_msg)

            # Parse time series data
            time_series_key = "Time Series (Daily)"
            if time_series_key not in data:
                logger.error(f"No time series data in response for {symbol}: {list(data.keys())}")
                raise DataFetchError(symbol, self.name, "No time series data in response")

            time_series = data[time_series_key]

            # Convert to DataFrame
            df = pd.DataFrame.from_dict(time_series, orient="index")

            # Standardize column names (strip numeric prefix like '1. open')
            df.columns = [col.split(". ")[1] if ". " in col else col for col in df.columns]
            df.columns = [col.lower() for col in df.columns]

            # Keep only OHLCV columns
            df = cast(pd.DataFrame, df[["open", "high", "low", "close", "volume"]].copy())

            # Convert to numeric types
            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").astype("int64")  # type: ignore[arg-type]

            # Convert index to datetime and sort ascending
            df.index = pd.to_datetime(df.index)
            df.index.name = "date"
            df.sort_index(inplace=True)

            # Filter by requested years
            cutoff = datetime.now() - timedelta(days=years * 365)
            df = cast(pd.DataFrame, df[df.index >= cutoff])

            if df.empty:
                logger.warning(f"No data returned for {symbol} after {years}-year filter")
                return None

            # Remove timezone if present (shouldn't be for AV, but safe)
            try:
                df.index = df.index.tz_localize(None)  # type: ignore[union-attr]
            except (TypeError, AttributeError):
                pass

            logger.debug(f"Fetched {len(df)} daily rows for {symbol} from Alpha Vantage")
            return df

        except requests.RequestException as e:
            logger.error(f"Network error fetching {symbol} from Alpha Vantage: {e}")
            raise DataFetchError(symbol, self.name, str(e))
        except DataFetchError:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch daily data for {symbol}: {e}")
            raise DataFetchError(symbol, self.name, str(e))

    def health_check(self) -> bool:
        """Check if Alpha Vantage API is accessible.

        Makes a lightweight query to verify connectivity and API key validity.
        """
        try:
            self._acquire_rate_limit()

            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": "IBM",
                "apikey": self._api_key,
                "outputsize": "compact",
            }

            response = requests.get(self.BASE_URL, params=params, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()

            # Check for invalid API key or other errors
            if "Error Message" in data:
                logger.error(f"Alpha Vantage health check failed: {data['Error Message']}")
                self._health_status = False
                return False

            if "Note" in data:
                logger.warning(f"Alpha Vantage rate limited during health check: {data['Note']}")
                # Rate limited but API is reachable
                self._health_status = True
                self._last_health_check = datetime.now()
                return True

            self._health_status = True
            self._last_health_check = datetime.now()
            return True

        except Exception as e:
            logger.error(f"Alpha Vantage health check failed: {e}")
            self._health_status = False
            return False


def _register():
    """Register Alpha Vantage provider with the factory."""
    DataProviderFactory.register("alpha_vantage", AlphaVantageProvider)
