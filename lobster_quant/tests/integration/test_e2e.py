"""
Lobster Quant - Integration Tests
End-to-end workflow tests using the new architecture.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_engine import DataEngine
from core.indicator_engine import IndicatorEngine, get_indicator_engine
from core.risk_engine import RiskEngine
from analysis.signals import SignalGenerator
from analysis.backtest import BacktestEngine
from data.providers.mock_provider import MockProvider
from data.models import StockData, SignalResult
from compat import LegacyAdapter


@pytest.fixture
def mock_engine():
    """Create a data engine with mock provider."""
    # Register mock provider for all markets
    engine = DataEngine()
    mock = MockProvider(trend=0.001, volatility=0.02, seed=42)
    engine.providers = {
        'us_stock': mock,
        'hk_stock': mock,
        'a_stock': mock,
    }
    return engine


@pytest.fixture
def sample_stock_data():
    """Generate sample stock data using mock provider."""
    mock = MockProvider(trend=0.001, volatility=0.02, seed=42)
    daily = mock.fetch_daily("TEST", years=3)
    return StockData(symbol="TEST", daily=daily, source="mock")


class TestEndToEndWorkflow:
    """Test complete analysis workflow."""
    
    def test_full_pipeline(self, mock_engine):
        """Test the full pipeline: fetch -> indicators -> signal -> risk."""
        # Step 1: Fetch data
        stock_data = mock_engine.fetch_stock("TEST", years=3)
        assert stock_data is not None
        assert stock_data.daily is not None
        assert len(stock_data.daily) > 100
        
        # Step 2: Compute indicators
        indicator_engine = get_indicator_engine()
        df = indicator_engine.compute_all(stock_data.daily)
        
        # Verify indicator columns exist
        assert 'slope_daily' in df.columns
        assert 'rsi' in df.columns
        assert 'volume_ratio' in df.columns
        assert 'macd' in df.columns
        assert 'atr' in df.columns
        assert 'ma20' in df.columns
        
        # Step 3: Generate signal
        signal_gen = SignalGenerator()
        signal = signal_gen.generate_signal(df)
        
        assert isinstance(signal, SignalResult)
        assert 0 <= signal.score <= 100
        assert 0 <= signal.probability_up <= 100
        assert signal.signal_type in ["强烈推荐", "推荐", "持有", "观望"]
        
        # Step 4: Risk assessment
        risk_engine = RiskEngine()
        off_results = risk_engine.assess(df)
        assert 'is_off' in off_results.columns
        
        status = risk_engine.get_latest_status(df)
        assert status.is_on or status.is_off
    
    def test_backtest_pipeline(self, mock_engine):
        """Test backtest workflow."""
        # Fetch and compute
        stock_data = mock_engine.fetch_stock("TEST", years=3)
        indicator_engine = get_indicator_engine()
        df = indicator_engine.compute_all(stock_data.daily)
        
        # Generate scores
        signal_gen = SignalGenerator()
        score_series = pd.Series(
            [signal_gen.calculate_score(df.iloc[:i+1]) for i in range(len(df))],
            index=df.index
        )
        
        # Run backtest
        backtest = BacktestEngine()
        result = backtest.run(df, score_series, symbol="TEST")
        
        assert result.symbol == "TEST"
        assert result.total_trades >= 0
        if result.total_trades > 0:
            assert 0 <= result.win_rate <= 1
    
    def test_indicator_engine_completeness(self, sample_stock_data):
        """Test that indicator engine produces all expected columns."""
        engine = get_indicator_engine()
        df = engine.compute_all(sample_stock_data.daily)
        
        expected_columns = [
            'slope_daily', 'slope_weekly', 'slope_monthly',
            'macd', 'macd_signal', 'macd_hist', 'macd_golden',
            'ma_bullish', 'ma20', 'ma50', 'ma200',
            'rsi', 'momentum_score',
            'atr', 'atr_pct',
            'bb_upper', 'bb_lower', 'bb_position', 'bb_width',
            'gap_pct', 'gap_zscore',
            'volume_ratio', 'volume_trend',
        ]
        
        for col in expected_columns:
            assert col in df.columns, f"Missing column: {col}"


class TestLegacyAdapter:
    """Test backward-compatible API."""
    
    def test_fetch_daily(self):
        adapter = LegacyAdapter()
        # Override provider with mock
        mock = MockProvider(trend=0.001, volatility=0.02, seed=42)
        adapter._data_engine = DataEngine()
        adapter._data_engine.providers = {
            'us_stock': mock,
            'hk_stock': mock,
            'a_stock': mock,
        }
        
        df = adapter.fetch_daily("TEST", years=1)
        assert df is not None
        assert len(df) > 100
        assert 'close' in df.columns
    
    def test_compute_indicators(self):
        adapter = LegacyAdapter()
        mock = MockProvider()
        df = mock.fetch_daily("TEST", years=1)
        
        result = adapter.compute_indicators(df)
        assert 'slope_daily' in result.columns
        assert 'rsi' in result.columns
    
    def test_get_signal(self):
        adapter = LegacyAdapter()
        mock = MockProvider(trend=0.002, volatility=0.015, seed=42)
        adapter._data_engine = DataEngine()
        adapter._data_engine.providers = {
            'us_stock': mock,
            'hk_stock': mock,
            'a_stock': mock,
        }
        
        signal = adapter.get_signal("TEST", years=1)
        assert signal is not None
        assert 'signal_type' in signal
        assert 'score' in signal
        assert 'reasons' in signal
    
    def test_assess_risk(self):
        adapter = LegacyAdapter()
        mock = MockProvider()
        df = mock.fetch_daily("TEST", years=1)
        df_with_indicators = adapter.compute_indicators(df)
        
        off_results = adapter.assess_risk(df_with_indicators)
        assert 'is_off' in off_results.columns
    
    def test_calculate_score(self):
        adapter = LegacyAdapter()
        mock = MockProvider(trend=0.001, volatility=0.02, seed=42)
        df = mock.fetch_daily("TEST", years=1)
        df = adapter.compute_indicators(df)
        
        score = adapter.calculate_score(df)
        assert 0 <= score <= 100


class TestDataProviderFactory:
    """Test data provider factory."""
    
    def test_mock_provider(self):
        from data.providers import DataProviderFactory, MockProvider
        
        provider = DataProviderFactory.create("mock", seed=42)
        assert isinstance(provider, MockProvider)
        
        df = provider.fetch_daily("TEST", years=1)
        assert df is not None
        assert len(df) > 200
    
    def test_factory_available(self):
        from data.providers import DataProviderFactory
        
        available = DataProviderFactory.get_available()
        assert "yfinance" in available
        assert "akshare" in available
        assert "mock" in available
    
    def test_factory_unknown(self):
        from data.providers import DataProviderFactory
        
        with pytest.raises(ValueError):
            DataProviderFactory.create("unknown_provider")


class TestCacheIntegration:
    """Test cache system integration."""
    
    def test_cache_roundtrip(self):
        from data.cache import DataCache
        
        cache = DataCache(cache_dir="./test_cache", default_ttl=300)
        
        # Set and get
        test_data = {"key": "value", "number": 42}
        cache.set("test_key", test_data)
        
        result = cache.get("test_key")
        assert result == test_data
        
        # Cleanup
        cache.clear()
    
    def test_cache_dataframe(self):
        from data.cache import DataCache
        
        cache = DataCache(cache_dir="./test_cache", default_ttl=300)
        
        df = pd.DataFrame({
            'close': [100, 101, 102],
            'volume': [1000, 2000, 3000]
        })
        
        cache.set("df_key", df)
        result = cache.get("df_key")
        
        assert result is not None
        pd.testing.assert_frame_equal(result, df)
        
        # Cleanup
        cache.clear()
    
    def test_cache_expiry(self):
        from data.cache import DataCache
        
        cache = DataCache(cache_dir="./test_cache", default_ttl=0)  # Immediate expiry
        
        cache.set("expire_key", "value")
        
        # Should be expired immediately
        import time
        time.sleep(0.1)
        result = cache.get("expire_key")
        assert result is None
        
        # Cleanup
        cache.clear()
    
    def test_cache_stats(self):
        from data.cache import DataCache
        
        cache = DataCache(cache_dir="./test_cache")
        cache.set("stat_key", "value")
        
        stats = cache.get_stats()
        assert 'memory_items' in stats
        assert 'disk_items' in stats
        
        cache.clear()
