"""
Tests for technical indicators.
"""

import pytest
import pandas as pd
import numpy as np

from src.analysis.indicators import IndicatorRegistry
from src.analysis.indicators.trend import SMAIndicator, MACDIndicator, MABullishIndicator
from src.analysis.indicators.momentum import RSIIndicator, MomentumScoreIndicator
from src.analysis.indicators.volatility import ATRIndicator, BollingerBandsIndicator
from src.analysis.indicators.volume import VolumeRatioIndicator


@pytest.fixture
def sample_data():
    """Generate sample OHLCV data."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range('2024-01-01', periods=n)
    
    # Generate trending price
    trend = np.linspace(100, 150, n)
    noise = np.random.normal(0, 2, n)
    close = trend + noise
    
    df = pd.DataFrame({
        'open': close - np.abs(np.random.randn(n)),
        'high': close + np.abs(np.random.randn(n) * 2),
        'low': close - np.abs(np.random.randn(n) * 2),
        'close': close,
        'volume': np.random.randint(1000000, 10000000, n)
    }, index=dates)
    
    return df


class TestSMAIndicator:
    def test_calculation(self, sample_data):
        sma = SMAIndicator(period=20)
        result = sma.calculate(sample_data)
        
        assert result.name == "sma"
        assert len(result.values) == len(sample_data)
        assert result.metadata["period"] == 20
        # First 19 values should be NaN
        assert result.values.iloc[:19].isna().all()
        assert not result.values.iloc[20:].isna().any()
    
    def test_validation(self, sample_data):
        sma = SMAIndicator()
        assert sma.validate(sample_data) is True
    
    def test_validation_missing_columns(self):
        bad_data = pd.DataFrame({'close': [1, 2, 3]})
        sma = SMAIndicator()
        with pytest.raises(Exception):
            sma.validate(bad_data)


class TestRSIIndicator:
    def test_calculation(self, sample_data):
        rsi = RSIIndicator(period=14)
        result = rsi.calculate(sample_data)
        
        assert result.name == "rsi"
        # RSI should be between 0 and 100
        valid_values = result.values.dropna()
        assert (valid_values >= 0).all()
        assert (valid_values <= 100).all()
    
    def test_overbought_oversold(self, sample_data):
        rsi = RSIIndicator()
        result = rsi.calculate(sample_data)
        
        assert "overbought" in result.metadata
        assert "oversold" in result.metadata


class TestMACDIndicator:
    def test_calculation(self, sample_data):
        macd = MACDIndicator()
        result = macd.calculate(sample_data)
        
        assert result.name == "macd"
        assert "signal" in result.metadata
        assert "histogram" in result.metadata
        assert "golden_cross" in result.metadata


class TestATRIndicator:
    def test_calculation(self, sample_data):
        atr = ATRIndicator(period=14)
        result = atr.calculate(sample_data)
        
        assert result.name == "atr"
        valid_values = result.values.dropna()
        assert (valid_values > 0).all()
        assert "atr_pct" in result.metadata


class TestBollingerBandsIndicator:
    def test_calculation(self, sample_data):
        bb = BollingerBandsIndicator(period=20, std_dev=2.0)
        result = bb.calculate(sample_data)
        
        assert result.name == "bollinger_bands"
        assert "upper" in result.metadata
        assert "lower" in result.metadata
        assert "position" in result.metadata
        
        # Position should be between 0 and 1
        position = result.metadata["position"].dropna()
        assert (position >= 0).all()
        assert (position <= 1).all()


class TestVolumeRatioIndicator:
    def test_calculation(self, sample_data):
        vr = VolumeRatioIndicator(period=20)
        result = vr.calculate(sample_data)
        
        assert result.name == "volume_ratio"
        valid_values = result.values.dropna()
        assert (valid_values > 0).all()


class TestIndicatorRegistry:
    def test_list_indicators(self):
        indicators = IndicatorRegistry.list_indicators()
        assert "sma" in indicators
        assert "rsi" in indicators
        assert "macd" in indicators
        assert "atr" in indicators
    
    def test_get_indicator(self):
        indicator_class = IndicatorRegistry.get("rsi")
        assert indicator_class == RSIIndicator
    
    def test_create_indicator(self):
        indicator = IndicatorRegistry.create("sma", period=50)
        assert isinstance(indicator, SMAIndicator)
        assert indicator.params["period"] == 50
    
    def test_get_unknown_indicator(self):
        with pytest.raises(KeyError):
            IndicatorRegistry.get("unknown_indicator")


class TestMomentumScoreIndicator:
    def test_calculation(self, sample_data):
        ms = MomentumScoreIndicator()
        result = ms.calculate(sample_data)
        
        assert result.name == "momentum_score"
        valid_values = result.values.dropna()
        assert (valid_values >= 0).all()
        assert (valid_values <= 100).all()
