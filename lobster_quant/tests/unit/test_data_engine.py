"""
Tests for DataEngine.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.core.data_engine import DataEngine, get_data_engine
from src.data.models import StockData


@pytest.fixture
def mock_engine():
    with patch('src.core.data_engine.get_settings') as mock_settings:
        mock_settings.return_value = MagicMock(
            enable_us_stock=True, enable_hk_stock=False, enable_a_stock=False,
            us_data_provider="mock", hk_data_provider="mock", a_data_provider="mock",
            data_years=1, data_cache_dir="./data/test_cache", data_cache_ttl=3600,
            data_timeout=10, benchmark_symbol="SPY"
        )
        engine = DataEngine()
        return engine


class TestDataEngine:
    def test_initialization(self, mock_engine):
        assert mock_engine is not None
        assert len(mock_engine.providers) > 0

    def test_get_market_us(self, mock_engine):
        assert mock_engine._get_market("AAPL") == "us_stock"
        assert mock_engine._get_market("SPY") == "us_stock"

    def test_get_market_hk(self, mock_engine):
        assert mock_engine._get_market("0700.HK") == "hk_stock"

    def test_get_market_a_share(self, mock_engine):
        assert mock_engine._get_market("600519") == "a_stock"
        assert mock_engine._get_market("600519.SH") == "a_stock"

    def test_fetch_stock_returns_stock_data(self, mock_engine):
        result = mock_engine.fetch_stock("AAPL", years=1)
        assert result is not None
        assert isinstance(result, StockData)
        assert len(result.daily) > 0

    def test_fetch_stock_caches_result(self, mock_engine):
        result1 = mock_engine.fetch_stock("AAPL", years=1)
        result2 = mock_engine.fetch_stock("AAPL", years=1)
        assert result1 is not None
        assert result2 is not None

    def test_get_health_status(self, mock_engine):
        status = mock_engine.get_health_status()
        assert isinstance(status, dict)

    def test_clear_cache(self, mock_engine):
        mock_engine.fetch_stock("AAPL", years=1)
        count = mock_engine.clear_cache()
        assert isinstance(count, int)

    def test_get_cache_stats(self, mock_engine):
        stats = mock_engine.get_cache_stats()
        assert isinstance(stats, dict)


class TestGetDataEngine:
    def test_returns_data_engine(self):
        engine = get_data_engine()
        assert isinstance(engine, DataEngine)

    def test_singleton(self):
        e1 = get_data_engine()
        e2 = get_data_engine()
        assert e1 is e2
