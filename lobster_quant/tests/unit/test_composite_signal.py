"""
Tests for CompositeSignalGenerator.
"""

import pytest
from datetime import datetime
from src.analysis.signals.composite_signal import (
    CompositeSignalGenerator,
    CompositeSignalResult,
)
from src.data.models import StockData, SignalResult


@pytest.fixture
def composite_gen():
    return CompositeSignalGenerator()


@pytest.fixture
def mock_stock_data(sample_ohlcv_df):
    return StockData(symbol="TEST", daily=sample_ohlcv_df, last_update=datetime.now(), source="mock")


class TestCompositeSignalGenerator:
    def test_generate_returns_result(self, composite_gen, mock_stock_data):
        result = composite_gen.generate(mock_stock_data)
        assert isinstance(result, CompositeSignalResult)

    def test_result_has_signal(self, composite_gen, mock_stock_data):
        result = composite_gen.generate(mock_stock_data)
        assert isinstance(result.signal, SignalResult)
        assert result.signal.symbol == "TEST"

    def test_result_has_trading_allowed(self, composite_gen, mock_stock_data):
        result = composite_gen.generate(mock_stock_data)
        assert isinstance(result.is_trading_allowed, bool)

    def test_result_has_risk_reasons(self, composite_gen, mock_stock_data):
        result = composite_gen.generate(mock_stock_data)
        assert isinstance(result.risk_reasons, list)

    def test_signal_type_is_valid(self, composite_gen, mock_stock_data):
        result = composite_gen.generate(mock_stock_data)
        assert result.signal.signal_type in ["强烈推荐", "推荐", "持有", "观望"]

    def test_adjust_for_risk_downgrades(self, composite_gen):
        signal = SignalResult(symbol="TEST", signal_type="强烈推荐", score=80, probability_up=70, reasons=["test"])
        adjusted = composite_gen._adjust_for_risk(signal, True, ["VIX high"])
        assert adjusted.signal_type == "推荐"
        assert any("风险过滤" in r for r in adjusted.reasons)

    def test_adjust_for_risk_no_change_when_not_off(self, composite_gen):
        signal = SignalResult(symbol="TEST", signal_type="强烈推荐", score=80, probability_up=70, reasons=["test"])
        adjusted = composite_gen._adjust_for_risk(signal, False, [])
        assert adjusted.signal_type == "强烈推荐"
