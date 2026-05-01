"""
Lobster Quant - Mock Data Provider
Test data provider with synthetic data generation.
"""

from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from .base import DataProvider, DataProviderFactory
from src.utils.logging import get_logger

logger = get_logger()


class MockProvider(DataProvider):
    """Mock data provider for testing.
    
    Generates synthetic OHLCV data with configurable trends and volatility.
    """
    
    def __init__(self, 
                 trend: float = 0.0001,
                 volatility: float = 0.02,
                 seed: int = 42,
                 timeout: int = 10):
        super().__init__(name="mock", timeout=timeout)
        self.trend = trend
        self.volatility = volatility
        self.rng = np.random.RandomState(seed)
    
    def fetch_daily(self, symbol: str, years: int = 3) -> pd.DataFrame:
        """Generate synthetic daily data."""
        days = years * 252  # Trading days per year
        
        # Generate price series with random walk
        returns = self.rng.normal(self.trend, self.volatility, days)
        prices = 100 * np.exp(np.cumsum(returns))
        
        # Generate dates
        end_date = datetime.now()
        dates = pd.bdate_range(end=end_date, periods=days)
        
        # Generate OHLCV from close prices
        df = pd.DataFrame(index=dates)
        df['close'] = prices
        
        # Generate realistic OHLC from close
        daily_range = prices * self.volatility * 0.5
        df['high'] = df['close'] + self.rng.uniform(0, daily_range)
        df['low'] = df['close'] - self.rng.uniform(0, daily_range)
        df['open'] = df['close'].shift(1)
        df['open'] = df['open'].fillna(df['close'] * (1 + self.rng.normal(0, self.volatility)))
        
        # Ensure OHLC consistency
        df['high'] = df[['high', 'open', 'close']].max(axis=1)
        df['low'] = df[['low', 'open', 'close']].min(axis=1)
        
        # Generate volume
        df['volume'] = self.rng.randint(1_000_000, 10_000_000, days)
        
        logger.debug(f"Generated {len(df)} mock daily rows for {symbol}")
        return df[['open', 'high', 'low', 'close', 'volume']]
    
    def health_check(self) -> bool:
        """Mock provider is always healthy."""
        return True


# Register provider (lazy)
def _register():
    DataProviderFactory.register("mock", MockProvider)

