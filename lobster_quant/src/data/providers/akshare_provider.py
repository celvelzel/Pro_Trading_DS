"""
Lobster Quant - AkShare Provider
Data provider implementation for A-shares using akshare.
"""

from typing import Optional
import pandas as pd

from .base import DataProvider, DataProviderFactory
from src.utils.exceptions import DataFetchError
from src.utils.logging import get_logger

logger = get_logger()


class AkShareProvider(DataProvider):
    """AkShare data provider for A-shares (Chinese stocks)."""
    
    def __init__(self, timeout: int = 10):
        super().__init__(name="akshare", timeout=timeout)
        self._ak = None
        self._ensure_import()
    
    def _ensure_import(self) -> None:
        """Lazy import akshare to avoid startup overhead."""
        if self._ak is None:
            try:
                import akshare as ak
                self._ak = ak
            except ImportError:
                raise DataProviderError(
                    "akshare package not installed. "
                    "Install with: pip install akshare"
                )
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize A-share symbol to akshare format.
        
        Examples:
            '600519' -> '600519' (sh)
            '000001' -> '000001' (sz)
            '300308' -> '300308' (sz, 创业�?
        """
        # Remove any suffixes
        symbol = symbol.upper().replace('.SZ', '').replace('.SH', '')
        return symbol
    
    def fetch_daily(self, symbol: str, years: int = 3) -> Optional[pd.DataFrame]:
        """Fetch daily OHLCV data for A-shares."""
        try:
            self._ensure_import()
            code = self._normalize_symbol(symbol)
            
            # Calculate start date
            from datetime import datetime, timedelta
            start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y%m%d")
            end_date = "20500101"
            
            df = self._ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if df.empty:
                logger.warning(f"No data returned for A-share {symbol}")
                return None
            
            # Standardize column names
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')[['open', 'high', 'low', 'close', 'volume']]
            df = df.astype(float)
            
            logger.debug(f"Fetched {len(df)} daily rows for A-share {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch A-share data for {symbol}: {e}")
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
    
    def health_check(self) -> bool:
        """Check if AkShare API is accessible."""
        try:
            self._ensure_import()
            # Try to fetch a well-known stock
            df = self._ak.stock_zh_a_hist(
                symbol="600519",
                period="daily",
                start_date="20240101",
                end_date="20240102"
            )
            return not df.empty
        except Exception as e:
            logger.warning(f"AkShare health check failed: {e}")
            self._health_status = False
            return False


# Register provider (lazy)
def _register():
    DataProviderFactory.register("akshare", AkShareProvider)

