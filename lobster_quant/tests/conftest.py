"""
pytest configuration and shared fixtures.
"""

import pytest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to path so we can import from src.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set test environment
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("ENABLE_US_STOCK", "false")
os.environ.setdefault("ENABLE_HK_STOCK", "false")
os.environ.setdefault("ENABLE_A_STOCK", "false")


@pytest.fixture
def sample_ohlcv_df():
    """Generate a minimal OHLCV DataFrame for testing."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range('2024-01-01', periods=n, freq='B')
    close = 100 + np.cumsum(np.random.normal(0.001, 0.02, n)) * 100
    high = close * (1 + np.abs(np.random.normal(0, 0.01, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, n)))
    open_ = close * (1 + np.random.normal(0, 0.005, n))
    volume = np.random.randint(1_000_000, 10_000_000, n)

    return pd.DataFrame({
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    }, index=dates)


@pytest.fixture
def sample_ohlcv_df_with_indicators(sample_ohlcv_df):
    """Generate OHLCV DataFrame with pre-computed technical indicators."""
    df = sample_ohlcv_df.copy()
    n = len(df)

    # Moving averages
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma50'] = df['close'].rolling(50).mean()
    df['ma200'] = df['close'].rolling(200).mean()

    # RSI
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # MACD
    exp12 = df['close'].ewm(span=12, adjust=False).mean()
    exp26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp12 - exp26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_golden'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))

    # Volume ratio
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

    # Slope
    df['slope_daily'] = df['close'].rolling(20).apply(
        lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == 20 else 0,
        raw=False
    )

    # MA bullish
    df['ma_bullish'] = (df['ma20'] > df['ma50'])

    # Bollinger Bands position
    bb_mid = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_position'] = (df['close'] - bb_mid) / (2 * bb_std) + 0.5

    # ATR
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    df['atr_pct'] = df['atr'] / df['close']

    # Gap
    df['gap_pct'] = (df['open'] - df['close'].shift(1)).abs() / df['close'].shift(1)

    return df


@pytest.fixture
def mock_stock_data(sample_ohlcv_df):
    """Create a StockData instance with mock data."""
    from src.data.models import StockData
    return StockData(
        symbol="MOCK",
        daily=sample_ohlcv_df,
        last_update=datetime.now(),
        source="mock"
    )
