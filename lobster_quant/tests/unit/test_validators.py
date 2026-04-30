"""
Tests for validators.
"""

import pytest
import pandas as pd
from datetime import date
from src.utils.validators import (
    validate_symbol,
    validate_date_range,
    validate_dataframe_columns,
    validate_timeframe,
)
from src.utils.exceptions import ValidationError


class TestValidateSymbol:
    def test_valid_symbol(self):
        assert validate_symbol("AAPL") == "AAPL"
        assert validate_symbol("SPY") == "SPY"
        assert validate_symbol("BRK.B") == "BRK.B"

    def test_normalizes_to_uppercase(self):
        assert validate_symbol("aapl") == "AAPL"
        assert validate_symbol("spy ") == "SPY"

    def test_strips_whitespace(self):
        assert validate_symbol("  AAPL  ") == "AAPL"

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_symbol("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError):
            validate_symbol("   ")

    def test_invalid_characters_raises(self):
        with pytest.raises(ValidationError):
            validate_symbol("AAPL@#$")

    def test_hk_symbol(self):
        assert validate_symbol("0700.HK") == "0700.HK"

    def test_a_share_symbol(self):
        assert validate_symbol("600519.SH") == "600519.SH"


class TestValidateDateRange:
    def test_valid_range(self):
        start = date(2020, 1, 1)
        end = date(2023, 12, 31)
        result = validate_date_range(start, end)
        assert result == (start, end)

    def test_start_after_end_raises(self):
        with pytest.raises(ValidationError):
            validate_date_range(date(2025, 1, 1), date(2020, 1, 1))

    def test_range_too_large_raises(self):
        with pytest.raises(ValidationError):
            validate_date_range(date(2000, 1, 1), date(2025, 1, 1), max_years=10)

    def test_none_dates_raise(self):
        with pytest.raises(ValidationError):
            validate_date_range(None, date(2025, 1, 1))


class TestValidateDataframeColumns:
    def test_valid_dataframe(self):
        df = pd.DataFrame({'a': [1], 'b': [2]})
        assert validate_dataframe_columns(df, ['a', 'b']) is True

    def test_missing_columns_raises(self):
        df = pd.DataFrame({'a': [1]})
        with pytest.raises(ValidationError):
            validate_dataframe_columns(df, ['a', 'b', 'c'])

    def test_none_dataframe_raises(self):
        with pytest.raises(ValidationError):
            validate_dataframe_columns(None, ['a'])


class TestValidateTimeframe:
    def test_valid_timeframes(self):
        assert validate_timeframe("daily") == "daily"
        assert validate_timeframe("weekly") == "weekly"
        assert validate_timeframe("monthly") == "monthly"

    def test_normalizes_case(self):
        assert validate_timeframe("Daily") == "daily"
        assert validate_timeframe("WEEKLY") == "weekly"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            validate_timeframe("hourly")

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_timeframe("")
