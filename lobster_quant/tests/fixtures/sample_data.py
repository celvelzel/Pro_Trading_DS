"""
Shared test data generators for Lobster Quant tests.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_ohlcv(n: int = 100, trend: float = 0.001, volatility: float = 0.02, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic OHLCV data.
    
    Args:
        n: Number of rows
        trend: Daily return trend
        volatility: Daily volatility
        seed: Random seed
        
    Returns:
        DataFrame with columns: open, high, low, close, volume
    """
    rng = np.random.RandomState(seed)
    dates = pd.date_range('2024-01-01', periods=n, freq='B')
    close = 100 * np.exp(np.cumsum(rng.normal(trend, volatility, n)))
    high = close * (1 + np.abs(rng.normal(0, 0.01, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.01, n)))
    open_ = close * (1 + rng.normal(0, 0.005, n))
    volume = rng.randint(1_000_000, 10_000_000, n)

    return pd.DataFrame({
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    }, index=dates)


def generate_trending_ohlcv(n: int = 100, direction: str = "up", seed: int = 42) -> pd.DataFrame:
    """Generate OHLCV data with a clear trend.
    
    Args:
        n: Number of rows
        direction: "up" or "down"
        seed: Random seed
        
    Returns:
        DataFrame with trending price data
    """
    trend = 0.003 if direction == "up" else -0.003
    return generate_ohlcv(n=n, trend=trend, volatility=0.01, seed=seed)


def generate_volatile_ohlcv(n: int = 100, seed: int = 42) -> pd.DataFrame:
    """Generate OHLCV data with high volatility.
    
    Args:
        n: Number of rows
        seed: Random seed
        
    Returns:
        DataFrame with volatile price data
    """
    return generate_ohlcv(n=n, trend=0.0, volatility=0.05, seed=seed)
