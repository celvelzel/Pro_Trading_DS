#!/usr/bin/env python3
"""
Tests for quant_tool modules integrated into lobster_quant.
Based on original quant_tool tests.
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from legacy.quant_tool_data import fetch_daily_data, fetch_option_chain
from legacy.quant_tool_indicators import (
    calc_atr_percent,
    calc_ma200_dist,
    calc_gap_percent,
    calc_put_call_ratio,
    calc_max_pain,
    find_support_resistance,
)


class TestFetchDailyData:
    """Tests for fetch_daily_data function."""

    def test_valid_symbol_returns_dict_with_required_keys(self):
        result = fetch_daily_data("AAPL", period="5d")
        assert "error" not in result
        required_keys = ["date", "open", "high", "low", "close", "volume"]
        for key in required_keys:
            assert key in result

    def test_valid_symbol_returns_non_empty_data(self):
        result = fetch_daily_data("AAPL", period="5d")
        assert "error" not in result
        assert len(result["date"]) > 0
        assert len(result["close"]) > 0

    def test_invalid_symbol_returns_error_dict(self):
        result = fetch_daily_data("INVALIDXYZ123")
        assert "error" in result

    def test_empty_symbol_returns_error(self):
        result = fetch_daily_data("")
        assert "error" in result


class TestFetchOptionChain:
    """Tests for fetch_option_chain function."""

    def test_fetch_option_chain_with_options(self):
        result = fetch_option_chain("AAPL")
        if result is not None:
            assert "error" not in result
            assert "expiration" in result
            assert "calls" in result
            assert "puts" in result

    def test_fetch_option_chain_invalid_symbol(self):
        result = fetch_option_chain("INVALIDXYZ")
        assert result is None or "error" in result


class TestCalcAtrPercent:
    """Tests for calc_atr_percent function."""

    def test_atr_percent_basic(self):
        # Generate 20 rows of data to have enough for 14-period ATR
        np.random.seed(42)
        n = 20
        base = 100
        close = base + np.cumsum(np.random.randn(n) * 2)
        high = close + np.abs(np.random.randn(n) * 2)
        low = close - np.abs(np.random.randn(n) * 2)
        df = pd.DataFrame({
            "high": high,
            "low": low,
            "close": close,
        })
        result = calc_atr_percent(df)
        assert not result.empty
        # Check that after 14 periods we have valid values
        assert result.dropna().iloc[-1] > 0

    def test_atr_percent_empty_df(self):
        df = pd.DataFrame()
        result = calc_atr_percent(df)
        assert result.empty

    def test_atr_percent_missing_columns(self):
        df = pd.DataFrame({"close": [100, 101, 102]})
        with pytest.raises(ValueError):
            calc_atr_percent(df)


class TestCalcMa200Dist:
    """Tests for calc_ma200_dist function."""

    def test_ma200_dist_exact_200_rows(self):
        prices = list(range(100, 300))
        df = pd.DataFrame({"close": prices})
        result = calc_ma200_dist(df)
        assert len(result) == 200
        assert not pd.isna(result.iloc[-1])

    def test_ma200_dist_less_than_200_rows(self):
        df = pd.DataFrame({"close": [100, 101, 102]})
        result = calc_ma200_dist(df)
        assert pd.isna(result.iloc[-1])

    def test_ma200_dist_empty_df(self):
        df = pd.DataFrame()
        result = calc_ma200_dist(df)
        assert result.empty


class TestCalcGapPercent:
    """Tests for calc_gap_percent function."""

    def test_gap_percent_up_gap(self):
        df = pd.DataFrame({
            "open": [105, 108],
            "close": [107, 110],
        })
        result = calc_gap_percent(df)
        assert result.iloc[1] > 0  # Up gap

    def test_gap_percent_down_gap(self):
        df = pd.DataFrame({
            "open": [105, 102],
            "close": [107, 103],
        })
        result = calc_gap_percent(df)
        assert result.iloc[1] < 0  # Down gap

    def test_gap_percent_empty_df(self):
        df = pd.DataFrame()
        result = calc_gap_percent(df)
        assert result.empty


class TestCalcPutCallRatio:
    """Tests for calc_put_call_ratio function."""

    def test_put_call_ratio_basic(self):
        calls = [{"volume": 100}, {"volume": 200}]
        puts = [{"volume": 150}, {"volume": 100}]
        result = calc_put_call_ratio(calls, puts)
        assert result == 250 / 300

    def test_put_call_ratio_zero_call_volume(self):
        calls = [{"volume": 0}]
        puts = [{"volume": 100}]
        result = calc_put_call_ratio(calls, puts)
        assert result is None

    def test_put_call_ratio_empty_lists(self):
        result = calc_put_call_ratio([], [])
        assert result is None


class TestCalcMaxPain:
    """Tests for calc_max_pain function."""

    def test_max_pain_basic(self):
        calls = [
            {"strike": 100, "openInterest": 10},
            {"strike": 110, "openInterest": 20},
        ]
        puts = [
            {"strike": 100, "openInterest": 15},
            {"strike": 110, "openInterest": 25},
        ]
        result = calc_max_pain(calls, puts, 105)
        assert result is not None

    def test_max_pain_empty_lists(self):
        result = calc_max_pain([], [], 100)
        assert result is None

    def test_max_pain_no_oi(self):
        calls = [{"strike": 100, "openInterest": 0}]
        puts = [{"strike": 100, "openInterest": 0}]
        result = calc_max_pain(calls, puts, 100)
        assert result is None


class TestFindSupportResistance:
    """Tests for find_support_resistance function."""

    def test_support_resistance_basic(self):
        calls = [
            {"strike": 100, "openInterest": 50},
            {"strike": 110, "openInterest": 100},
        ]
        puts = [
            {"strike": 100, "openInterest": 80},
            {"strike": 110, "openInterest": 60},
        ]
        result = find_support_resistance(calls, puts)
        assert result is not None
        support, resistance = result
        assert support == 100  # Max put OI
        assert resistance == 110  # Max call OI

    def test_support_resistance_empty_lists(self):
        result = find_support_resistance([], [])
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
