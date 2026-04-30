"""
Tests for SignalEngine.
"""

import pytest
from datetime import datetime
from src.core.signal_engine import SignalEngine, get_signal_engine
from src.data.models import StockData, SignalResult


@pytest.fixture
def signal_engine():
    return SignalEngine()


@pytest.fixture
def mock_stock_data(sample_ohlcv_df):
    return StockData(symbol="TEST", daily=sample_ohlcv_df, last_update=datetime.now(), source="mock")


class TestSignalEngine:
    def test_generate_signal_returns_result(self, signal_engine, mock_stock_data):
        result = signal_engine.generate_signal(mock_stock_data)
        assert isinstance(result, SignalResult)
        assert result.symbol == "TEST"

    def test_signal_type_is_valid(self, signal_engine, mock_stock_data):
        result = signal_engine.generate_signal(mock_stock_data)
        assert result.signal_type in ["强烈推荐", "推荐", "持有", "观望"]

    def test_score_in_range(self, signal_engine, mock_stock_data):
        result = signal_engine.generate_signal(mock_stock_data)
        assert 0 <= result.score <= 100

    def test_probability_in_range(self, signal_engine, mock_stock_data):
        result = signal_engine.generate_signal(mock_stock_data)
        assert 0 <= result.probability_up <= 100

    def test_reasons_is_list(self, signal_engine, mock_stock_data):
        result = signal_engine.generate_signal(mock_stock_data)
        assert isinstance(result.reasons, list)

    def test_classify_strong(self, signal_engine):
        assert signal_engine._classify_signal(75, 65) == "强烈推荐"

    def test_classify_recommend(self, signal_engine):
        assert signal_engine._classify_signal(55, 55) == "推荐"

    def test_classify_hold(self, signal_engine):
        assert signal_engine._classify_signal(35, 40) == "持有"

    def test_classify_watch(self, signal_engine):
        assert signal_engine._classify_signal(20, 30) == "观望"


class TestGetSignalEngine:
    def test_returns_instance(self):
        engine = get_signal_engine()
        assert isinstance(engine, SignalEngine)

    def test_singleton(self):
        e1 = get_signal_engine()
        e2 = get_signal_engine()
        assert e1 is e2
