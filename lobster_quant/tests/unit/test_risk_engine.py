"""
Tests for risk engine (OFF filter).
"""

import pytest
import pandas as pd
import numpy as np

from src.core.risk_engine import RiskEngine


@pytest.fixture
def sample_risk_data():
    """Generate sample data for risk assessment."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range('2024-01-01', periods=n)
    
    # Normal market data
    trend = np.linspace(100, 110, n)
    noise = np.random.normal(0, 1, n)
    close = trend + noise
    
    df = pd.DataFrame({
        'open': close - np.abs(np.random.randn(n) * 0.5),
        'high': close + np.abs(np.random.randn(n)),
        'low': close - np.abs(np.random.randn(n)),
        'close': close,
        'volume': np.random.randint(1000000, 10000000, n),
        'atr_pct': np.full(n, 0.02),  # Normal ATR
        'ma200': np.linspace(95, 105, n),  # Rising MA200
        'volume_ratio': np.full(n, 1.0)
    }, index=dates)
    
    return df


@pytest.fixture
def high_risk_data():
    """Generate high-risk market data."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range('2024-01-01', periods=n)
    
    # Volatile market data
    close = 100 + np.cumsum(np.random.normal(0, 3, n))
    
    df = pd.DataFrame({
        'open': close - np.abs(np.random.randn(n) * 2),
        'high': close + np.abs(np.random.randn(n) * 3),
        'low': close - np.abs(np.random.randn(n) * 3),
        'close': close,
        'volume': np.random.randint(1000000, 10000000, n),
        'atr_pct': np.full(n, 0.10),  # High ATR
        'ma200': np.linspace(110, 90, n),  # Falling MA200
        'volume_ratio': np.full(n, 0.02)  # Low volume
    }, index=dates)
    
    return df


class TestRiskEngine:
    def test_initialization(self):
        engine = RiskEngine()
        assert engine is not None
        assert engine.atr_threshold > 0
    
    def test_normal_market(self, sample_risk_data):
        engine = RiskEngine()
        results = engine.assess(sample_risk_data)
        
        assert 'is_off' in results.columns
        # Most days should be ON in normal market
        off_pct = results['is_off'].mean()
        assert off_pct < 0.5  # Less than 50% OFF days
    
    def test_high_risk_market(self, high_risk_data):
        engine = RiskEngine()
        results = engine.assess(high_risk_data)
        
        # More OFF days in high-risk market
        off_pct = results['is_off'].mean()
        assert off_pct > 0.3  # More than 30% OFF days
    
    def test_stats_calculation(self, sample_risk_data):
        engine = RiskEngine()
        results = engine.assess(sample_risk_data)
        stats = engine.get_stats(sample_risk_data, results)
        
        assert 'total_days' in stats
        assert 'off_days' in stats
        assert 'on_pct' in stats
        assert 'off_pct' in stats
        assert 'reasons' in stats
        assert stats['total_days'] == len(sample_risk_data)
    
    def test_latest_status(self, sample_risk_data):
        engine = RiskEngine()
        status = engine.get_latest_status(sample_risk_data)
        
        assert status.is_on or status.is_off
        assert isinstance(status.reasons, list)
    
    def test_should_trade(self, sample_risk_data):
        engine = RiskEngine()
        should_trade, reasons = engine.should_trade(sample_risk_data)
        
        assert isinstance(should_trade, bool)
        assert isinstance(reasons, list)
    
    def test_with_benchmark(self, sample_risk_data):
        engine = RiskEngine()
        benchmark = sample_risk_data.copy()
        results = engine.assess(sample_risk_data, benchmark)
        
        assert 'is_off' in results.columns
        assert '大盘风险' in results.columns
