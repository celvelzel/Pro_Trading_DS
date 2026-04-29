"""
Lobster Quant - Yahoo Finance Provider
Data provider implementation using yfinance.
"""

import warnings
from typing import Optional
import pandas as pd
import yfinance as yf

from .base import DataProvider
from src.data.models import OptionsData
from src.utils.exceptions import DataFetchError
from src.utils.logging import get_logger

logger = get_logger()


class YFinanceProvider(DataProvider):
    """Yahoo Finance data provider for US and HK stocks."""
    
    def __init__(self, timeout: int = 10):
        super().__init__(name="yfinance", timeout=timeout)
    
    def fetch_daily(self, symbol: str, years: int = 3) -> Optional[pd.DataFrame]:
        """Fetch daily OHLCV data from Yahoo Finance."""
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=f"{years}y", timeout=self._timeout)
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            # Standardize column names
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            
            # Remove timezone info for consistency
            df.index = df.index.tz_localize(None)
            
            logger.debug(f"Fetched {len(df)} daily rows for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch daily data for {symbol}: {e}")
            raise DataFetchError(symbol, self.name, str(e))
    
    def fetch_weekly(self, symbol: str, years: int = 3) -> Optional[pd.DataFrame]:
        """Fetch weekly OHLCV data by resampling daily data."""
        daily = self.fetch_daily(symbol, years)
        if daily is None:
            return None
        
        weekly = daily.resample('W').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        return weekly
    
    def fetch_monthly(self, symbol: str, years: int = 3) -> Optional[pd.DataFrame]:
        """Fetch monthly OHLCV data by resampling daily data."""
        daily = self.fetch_daily(symbol, years)
        if daily is None:
            return None
        
        monthly = daily.resample('ME').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        return monthly
    
    def fetch_options(self, symbol: str) -> Optional[OptionsData]:
        """Fetch options chain data."""
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ticker = yf.Ticker(symbol)
                options_dates = ticker.options
            
            if not options_dates:
                return None
            
            nearest_expiration = options_dates[0]
            opt_chain = ticker.option_chain(nearest_expiration)
            
            calls = opt_chain.calls
            puts = opt_chain.puts
            
            calls_list = self._clean_records(calls) if not calls.empty else []
            puts_list = self._clean_records(puts) if not puts.empty else []
            
            # Get current price
            current_price = None
            hist = ticker.history(period="5d")
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
            
            return OptionsData(
                symbol=symbol,
                expiration=nearest_expiration,
                calls=calls_list,
                puts=puts_list,
                current_price=current_price
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch options for {symbol}: {e}")
            return None
    
    @staticmethod
    def _clean_records(df: pd.DataFrame) -> list[dict]:
        """Clean DataFrame records for JSON serialization."""
        records = []
        for record in df.to_dict("records"):
            cleaned = {}
            for k, v in record.items():
                if hasattr(v, 'isoformat'):
                    cleaned[k] = v.isoformat()
                elif hasattr(v, 'item'):
                    cleaned[k] = v.item()
                elif pd.isna(v):
                    cleaned[k] = None
                else:
                    cleaned[k] = v
            records.append(cleaned)
        return records
    
    def health_check(self) -> bool:
        """Check if Yahoo Finance API is accessible."""
        try:
            ticker = yf.Ticker("SPY")
            info = ticker.fast_info
            return info.last_price is not None
        except Exception as e:
            logger.warning(f"YFinance health check failed: {e}")
            self._health_status = False
            return False


# Register provider
DataProviderFactory.register("yfinance", YFinanceProvider)

