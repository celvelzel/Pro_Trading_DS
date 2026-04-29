"""
Tests for signal generator.
"""

import pytest
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from analysis.signals import SignalGenerator


@pytest.fixture
def sample_data_with_indicators():
    """Generate sample data with required indicators."""
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
    
    # Add required indicator columns
    df['slope_daily'] = 0.001
    df['slope_weekly'] = 0.0005
    df['slope_monthly'] = 0.0003
    df['rsi'] = 55.0
    df['volume_ratio'] = 1.2
    df['macd_golden'] = False
    df['ma_bullish'] = True
    df['bb_position'] = 0.6
    df['ma20'] = df['close'].rolling(20).mean()
    
    return df


class TestSignalGenerator:
    def test_initialization(self):
        gen = SignalGenerator()
        assert gen is not None
        assert hasattr(gen, 'calculate_score')
    
    def test_calculate_score(self, sample_data_with_indicators):
        gen = SignalGenerator()
        score = gen.calculate_score(sample_data_with_indicators)
        
        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert score > 0  # Should have some score with bullish data
    
    def test_calculate_probability(self, sample_data_with_indicators):
        gen = SignalGenerator()
        prob = gen.calculate_probability_up(sample_data_with_indicators)
        
        assert isinstance(prob, float)
        assert 0 <= prob <= 100
    
    def test_generate_signal(self, sample_data_with_indicators):
        gen = SignalGenerator()
        signal = gen.generate_signal(sample_data_with_indicators)
        
        assert signal.symbol == ""
        assert signal.score >= 0
        assert signal.score <= 100
        assert signal.probability_up >= 0
        assert signal.probability_up <= 100
        assert isinstance(signal.reasons, list)
    
    def test_signal_types(self, sample_data_with_indicators):
        gen = SignalGenerator()
        
        # Test with high score
        df_high = sample_data_with_indicators.copy()
        df_high['slope_daily'] = 0.05
        df_high['rsi'] = 40
        df_high['volume_ratio'] = 3.0
        df_high['macd_golden'] = True
        
        signal_high = gen.generate_signal(df_high)
        assert signal_high.signal_type in ["强烈推荐", "推荐"]
        assert signal_high.score >= 50
        
        # Test with low score
        df_low = sample_data_with_indicators.copy()
        df_low['slope_daily'] = -0.05
        df_low['rsi'] = 80
        df_low['volume_ratio'] = 0.3
        df_low['ma_bullish'] = False
        
        signal_low = gen.generate_signal(df_low)
        assert signal_low.signal_type in ["观望", "持有"]
    
    def test_reasons_generation(self, sample_data_with_indicators):
        gen = SignalGenerator()
        signal = gen.generate_signal(sample_data_with_indicators)
        
        assert len(signal.reasons) > 0
        # Should include trend reason
        assert any("趋势" in r for r in signal.reasons)
