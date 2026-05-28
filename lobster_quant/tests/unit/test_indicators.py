"""
Comprehensive tests for technical indicators.

Covers:
- IndicatorRegistry (register, get, create, list, clear)
- Indicator base class (validate, __call__, __repr__)
- IndicatorResult (last_value, is_valid)
- rolling_slope utility
- normalize_series utility
- SMA, EMA, Slope, MACD, MA_Bullish (trend)
- RSI, ROC, MomentumScore (momentum)
- ATR, BollingerBands, Gap (volatility)
- VolumeRatio, VolumeTrend, OBV (volume)
- IndicatorEngine.compute_all()
- Edge cases: insufficient data, all same prices, zero volume
"""

import numpy as np
import pandas as pd
import pytest

from src.analysis.indicators import IndicatorRegistry, normalize_series, rolling_slope
from src.analysis.indicators.base import Indicator, IndicatorResult
from src.analysis.indicators.momentum import MomentumScoreIndicator, ROCIndicator, RSIIndicator
from src.analysis.indicators.trend import (
    EMAIndicator,
    MABullishIndicator,
    MACDIndicator,
    SlopeIndicator,
    SMAIndicator,
)
from src.analysis.indicators.volatility import ATRIndicator, BollingerBandsIndicator, GapIndicator
from src.analysis.indicators.volume import OBVIndicator, VolumeRatioIndicator, VolumeTrendIndicator
from src.core.indicator_engine import IndicatorEngine
from src.utils.exceptions import IndicatorError

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def sample_data():
    """Generate sample OHLCV data (100 rows, trending up)."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n)
    trend = np.linspace(100, 150, n)
    noise = np.random.normal(0, 2, n)
    close = trend + noise
    df = pd.DataFrame(
        {
            "open": close - np.abs(np.random.randn(n)),
            "high": close + np.abs(np.random.randn(n) * 2),
            "low": close - np.abs(np.random.randn(n) * 2),
            "close": close,
            "volume": np.random.randint(1_000_000, 10_000_000, n),
        },
        index=dates,
    )
    return df


@pytest.fixture
def flat_price_data():
    """DataFrame where close is constant (all same prices)."""
    n = 50
    dates = pd.date_range("2024-01-01", periods=n)
    price = 100.0
    return pd.DataFrame(
        {
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": 1_000_000,
        },
        index=dates,
    )


@pytest.fixture
def zero_volume_data():
    """DataFrame with zero volume."""
    np.random.seed(99)
    n = 50
    dates = pd.date_range("2024-01-01", periods=n)
    close = 100 + np.cumsum(np.random.normal(0, 1, n))
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 0,
        },
        index=dates,
    )


@pytest.fixture
def small_data():
    """DataFrame with fewer than 20 rows (insufficient for validation)."""
    n = 10
    dates = pd.date_range("2024-01-01", periods=n)
    close = np.linspace(100, 110, n)
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1_000_000,
        },
        index=dates,
    )


@pytest.fixture
def large_data():
    """DataFrame with 250 rows (enough for SMA200)."""
    np.random.seed(7)
    n = 250
    dates = pd.date_range("2024-01-01", periods=n)
    close = 100 + np.cumsum(np.random.normal(0.05, 1, n))
    return pd.DataFrame(
        {
            "open": close - np.abs(np.random.randn(n) * 0.5),
            "high": close + np.abs(np.random.randn(n)),
            "low": close - np.abs(np.random.randn(n)),
            "close": close,
            "volume": np.random.randint(1_000_000, 10_000_000, n),
        },
        index=dates,
    )


# ============================================================
# IndicatorResult
# ============================================================


class TestIndicatorResult:
    def test_last_value(self, sample_data):
        s = sample_data["close"]
        result = IndicatorResult(name="test", values=s)
        assert result.last_value == s.iloc[-1]

    def test_last_value_empty(self):
        result = IndicatorResult(name="test", values=pd.Series([], dtype=float))
        assert result.last_value is None

    def test_is_valid(self, sample_data):
        result = IndicatorResult(name="test", values=sample_data["close"])
        assert result.is_valid is True

    def test_is_valid_all_nan(self):
        result = IndicatorResult(name="test", values=pd.Series([np.nan, np.nan]))
        assert result.is_valid is False

    def test_is_valid_empty(self):
        result = IndicatorResult(name="test", values=pd.Series([], dtype=float))
        assert result.is_valid is False


# ============================================================
# IndicatorRegistry
# ============================================================


class TestIndicatorRegistry:
    def test_list_indicators_contains_all(self):
        indicators = IndicatorRegistry.list_indicators()
        expected = [
            "atr",
            "bollinger_bands",
            "ema",
            "gap",
            "ma_bullish",
            "macd",
            "momentum_score",
            "obv",
            "roc",
            "rsi",
            "slope",
            "sma",
            "volume_ratio",
            "volume_trend",
        ]
        for name in expected:
            assert name in indicators, f"{name} not in registry"

    def test_get_returns_correct_class(self):
        assert IndicatorRegistry.get("sma") is SMAIndicator
        assert IndicatorRegistry.get("rsi") is RSIIndicator
        assert IndicatorRegistry.get("macd") is MACDIndicator
        assert IndicatorRegistry.get("atr") is ATRIndicator

    def test_create_with_kwargs(self):
        indicator = IndicatorRegistry.create("sma", period=50)
        assert isinstance(indicator, SMAIndicator)
        assert indicator.params["period"] == 50

    def test_create_default_params(self):
        indicator = IndicatorRegistry.create("rsi")
        assert isinstance(indicator, RSIIndicator)
        assert indicator.params["period"] == 14

    def test_get_unknown_raises_key_error(self):
        with pytest.raises(KeyError, match="not found"):
            IndicatorRegistry.get("nonexistent_indicator")

    def test_create_all_indicator_types(self):
        """Verify create() works for every registered indicator."""
        names = IndicatorRegistry.list_indicators()
        for name in names:
            indicator = IndicatorRegistry.create(name)
            assert isinstance(indicator, Indicator)
            assert indicator.name == name


# ============================================================
# Indicator Base - validate / __call__ / __repr__
# ============================================================


class TestIndicatorBase:
    def test_validate_passes(self, sample_data):
        sma = SMAIndicator()
        assert sma.validate(sample_data) is True

    def test_validate_missing_columns(self):
        bad = pd.DataFrame({"close": [1] * 25})
        sma = SMAIndicator()
        with pytest.raises(IndicatorError, match="Missing required columns"):
            sma.validate(bad)

    def test_validate_insufficient_rows(self, small_data):
        sma = SMAIndicator()
        with pytest.raises(IndicatorError, match="Insufficient data"):
            sma.validate(small_data)

    def test_call_delegates_to_calculate(self, sample_data):
        sma = SMAIndicator(period=20)
        result = sma(sample_data)
        assert isinstance(result, IndicatorResult)
        assert result.name == "sma"

    def test_repr(self):
        sma = SMAIndicator(period=10)
        r = repr(sma)
        assert "SMAIndicator" in r
        assert "sma" in r


# ============================================================
# rolling_slope utility
# ============================================================


class TestRollingSlope:
    def test_constant_series_returns_zero(self):
        s = pd.Series([5.0] * 30)
        result = rolling_slope(s, window=10)
        valid = result.dropna()
        np.testing.assert_allclose(valid.values, 0.0, atol=1e-10)

    def test_linear_upward_returns_positive(self):
        s = pd.Series(np.arange(30, dtype=float))
        result = rolling_slope(s, window=10)
        valid = result.dropna()
        # slope of y=x should be 1.0
        np.testing.assert_allclose(valid.values, 1.0, atol=1e-10)

    def test_linear_downward_returns_negative(self):
        s = pd.Series(-np.arange(30, dtype=float))
        result = rolling_slope(s, window=10)
        valid = result.dropna()
        np.testing.assert_allclose(valid.values, -1.0, atol=1e-10)

    def test_nan_before_window(self):
        s = pd.Series(np.arange(20, dtype=float))
        result = rolling_slope(s, window=10)
        assert result.iloc[:9].isna().all()
        assert not result.iloc[9:].isna().any()

    def test_short_series_all_nan(self):
        s = pd.Series([1.0, 2.0, 3.0])
        result = rolling_slope(s, window=10)
        assert result.isna().all()


# ============================================================
# normalize_series utility
# ============================================================


class TestNormalizeSeries:
    def test_zscore(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = normalize_series(s, method="zscore")
        assert abs(result.mean()) < 1e-10

    def test_minmax(self):
        s = pd.Series([10.0, 20.0, 30.0])
        result = normalize_series(s, method="minmax")
        assert result.min() == 0.0
        assert result.max() == 1.0

    def test_minmax_constant(self):
        s = pd.Series([5.0, 5.0, 5.0])
        result = normalize_series(s, method="minmax")
        np.testing.assert_allclose(result.values, 0.5)

    def test_rank(self):
        s = pd.Series([30.0, 10.0, 20.0])
        result = normalize_series(s, method="rank")
        assert result.iloc[0] > result.iloc[2] > result.iloc[1]

    def test_unknown_method_raises(self):
        s = pd.Series([1.0, 2.0])
        with pytest.raises(ValueError, match="Unknown normalization method"):
            normalize_series(s, method="invalid")


# ============================================================
# SMAIndicator
# ============================================================


class TestSMAIndicator:
    def test_name(self):
        sma = SMAIndicator()
        assert sma.name == "sma"

    def test_calculation_correctness(self, sample_data):
        sma = SMAIndicator(period=20)
        result = sma.calculate(sample_data)
        expected = sample_data["close"].rolling(window=20).mean()
        pd.testing.assert_series_equal(result.values, expected, check_names=False)

    def test_nan_handling(self, sample_data):
        sma = SMAIndicator(period=20)
        result = sma.calculate(sample_data)
        # First 19 values should be NaN (period-1)
        assert result.values.iloc[:19].isna().all()
        # From index 19 onward, no NaN
        assert not result.values.iloc[19:].isna().any()

    def test_different_period(self, sample_data):
        sma = SMAIndicator(period=10)
        result = sma.calculate(sample_data)
        assert result.metadata["period"] == 10
        assert result.values.iloc[:9].isna().all()
        assert not result.values.iloc[9:].isna().any()

    def test_period_1_equals_close(self, sample_data):
        sma = SMAIndicator(period=1)
        result = sma.calculate(sample_data)
        pd.testing.assert_series_equal(
            result.values, sample_data["close"], check_names=False
        )

    def test_result_metadata(self, sample_data):
        sma = SMAIndicator(period=50)
        result = sma.calculate(sample_data)
        assert result.name == "sma"
        assert result.metadata == {"period": 50}


# ============================================================
# EMAIndicator
# ============================================================


class TestEMAIndicator:
    def test_name(self):
        ema = EMAIndicator()
        assert ema.name == "ema"

    def test_calculation_uses_ewm(self, sample_data):
        ema = EMAIndicator(period=20)
        result = ema.calculate(sample_data)
        expected = sample_data["close"].ewm(span=20, adjust=False).mean()
        pd.testing.assert_series_equal(result.values, expected, check_names=False)

    def test_no_nan_values(self, sample_data):
        """EMA has values from the start (unlike SMA)."""
        ema = EMAIndicator(period=20)
        result = ema.calculate(sample_data)
        assert not result.values.isna().any()

    def test_ema_reacts_faster_than_sma(self, sample_data):
        """EMA should be closer to recent prices than SMA."""
        sma = SMAIndicator(period=20).calculate(sample_data)
        ema = EMAIndicator(period=20).calculate(sample_data)
        close = sample_data["close"]
        # At the end, EMA should be closer to last close than SMA
        last_close = close.iloc[-1]
        ema_diff = abs(ema.values.iloc[-1] - last_close)
        sma_diff = abs(sma.values.iloc[-1] - last_close)
        # This is generally true for trending data
        assert ema_diff <= sma_diff * 1.1  # small tolerance


# ============================================================
# SlopeIndicator
# ============================================================


class TestSlopeIndicator:
    def test_name(self):
        slope = SlopeIndicator()
        assert slope.name == "slope"

    def test_normalized_slope(self, sample_data):
        slope_ind = SlopeIndicator(period=20, normalize=True)
        result = slope_ind.calculate(sample_data)
        assert result.metadata["normalized"] is True
        # Normalized slope should be a small number (slope / price)
        valid = result.values.dropna()
        assert len(valid) > 0

    def test_unnormalized_slope(self, sample_data):
        slope_ind = SlopeIndicator(period=20, normalize=False)
        result = slope_ind.calculate(sample_data)
        assert result.metadata["normalized"] is False

    def test_upward_trend_positive_slope(self, sample_data):
        """Sample data trends upward, so slope should be positive."""
        slope_ind = SlopeIndicator(period=20, normalize=False)
        result = slope_ind.calculate(sample_data)
        valid = result.values.dropna()
        assert (valid > 0).sum() > (valid < 0).sum()  # mostly positive


# ============================================================
# MACDIndicator
# ============================================================


class TestMACDIndicator:
    def test_name_and_default_params(self):
        macd = MACDIndicator()
        assert macd.name == "macd"
        assert macd.params == {"fast": 12, "slow": 26, "signal": 9}

    def test_calculation_metadata_keys(self, sample_data):
        macd = MACDIndicator()
        result = macd.calculate(sample_data)
        assert "macd" in result.metadata
        assert "signal" in result.metadata
        assert "histogram" in result.metadata
        assert "golden_cross" in result.metadata

    def test_macd_line_is_fast_ema_minus_slow_ema(self, sample_data):
        macd = MACDIndicator()
        result = macd.calculate(sample_data)
        ema_fast = sample_data["close"].ewm(span=12, adjust=False).mean()
        ema_slow = sample_data["close"].ewm(span=26, adjust=False).mean()
        expected_macd = ema_fast - ema_slow
        pd.testing.assert_series_equal(
            result.values, expected_macd, check_names=False
        )

    def test_signal_line_is_ema_of_macd(self, sample_data):
        macd = MACDIndicator()
        result = macd.calculate(sample_data)
        expected_signal = result.values.ewm(span=9, adjust=False).mean()
        pd.testing.assert_series_equal(
            result.metadata["signal"], expected_signal, check_names=False
        )

    def test_histogram_is_macd_minus_signal(self, sample_data):
        macd = MACDIndicator()
        result = macd.calculate(sample_data)
        expected_hist = result.values - result.metadata["signal"]
        pd.testing.assert_series_equal(
            result.metadata["histogram"], expected_hist, check_names=False
        )

    def test_golden_cross_boolean(self, sample_data):
        macd = MACDIndicator()
        result = macd.calculate(sample_data)
        gc = result.metadata["golden_cross"]
        assert gc.dtype == bool
        # First value should be False (shift produces NaN)
        assert not gc.iloc[0] or pd.isna(gc.iloc[0])

    def test_custom_params(self, sample_data):
        macd = MACDIndicator(fast=5, slow=10, signal=3)
        result = macd.calculate(sample_data)
        assert result.metadata["fast"] == 5
        assert result.metadata["slow"] == 10
        assert result.metadata["signal_period"] == 3


# ============================================================
# MABullishIndicator
# ============================================================


class TestMABullishIndicator:
    def test_name(self):
        ma = MABullishIndicator()
        assert ma.name == "ma_bullish"

    def test_returns_integer_series(self, sample_data):
        ma = MABullishIndicator(short_period=5, long_period=20)
        result = ma.calculate(sample_data)
        assert result.values.dtype in [int, np.int64, np.int32, float]

    def test_values_are_0_or_1(self, sample_data):
        ma = MABullishIndicator(short_period=5, long_period=20)
        result = ma.calculate(sample_data)
        valid = result.values.dropna()
        unique = valid.unique()
        assert set(unique).issubset({0, 1})

    def test_metadata_contains_periods_and_mas(self, sample_data):
        ma = MABullishIndicator(short_period=5, long_period=20)
        result = ma.calculate(sample_data)
        assert result.metadata["short_period"] == 5
        assert result.metadata["long_period"] == 20
        assert "ma_short" in result.metadata
        assert "ma_long" in result.metadata

    def test_bullish_when_close_above_both_mas(self, sample_data):
        """When close > ma_short > ma_long, bullish should be 1."""
        ma = MABullishIndicator(short_period=5, long_period=20)
        result = ma.calculate(sample_data)
        meta = result.metadata
        # Check rows where close > ma_short > ma_long
        mask = (sample_data["close"] > meta["ma_short"]) & (
            meta["ma_short"] > meta["ma_long"]
        )
        valid_mask = mask & result.values.notna()
        if valid_mask.any():
            assert (result.values[valid_mask] == 1).all()


# ============================================================
# RSIIndicator
# ============================================================


class TestRSIIndicator:
    def test_name(self):
        rsi = RSIIndicator()
        assert rsi.name == "rsi"

    def test_range_0_to_100(self, sample_data):
        rsi = RSIIndicator(period=14)
        result = rsi.calculate(sample_data)
        valid = result.values.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_overbought_oversold_signals(self, sample_data):
        rsi = RSIIndicator(period=14)
        result = rsi.calculate(sample_data)
        assert "overbought" in result.metadata
        assert "oversold" in result.metadata
        ob = result.metadata["overbought"]
        os_ = result.metadata["oversold"]
        # Overbought should be True only where RSI > 70
        valid_ob = ob.dropna()
        if (valid_ob).any():
            rsi_at_ob = result.values[valid_ob]
            assert (rsi_at_ob > 70).all()
        # Oversold should be True only where RSI < 30
        valid_os = os_.dropna()
        if (valid_os).any():
            rsi_at_os = result.values[valid_os]
            assert (rsi_at_os < 30).all()

    def test_all_gains_rsi_near_100(self):
        """When price only goes up, RSI should be near 100."""
        n = 30
        dates = pd.date_range("2024-01-01", periods=n)
        close = np.arange(100, 100 + n, dtype=float)
        df = pd.DataFrame(
            {
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000_000,
            },
            index=dates,
        )
        rsi = RSIIndicator(period=14)
        result = rsi.calculate(df)
        valid = result.values.dropna()
        assert (valid > 90).all()

    def test_all_losses_rsi_near_0(self):
        """When price only goes down, RSI should be near 0."""
        n = 30
        dates = pd.date_range("2024-01-01", periods=n)
        close = np.arange(130, 130 - n, -1, dtype=float)
        df = pd.DataFrame(
            {
                "open": close + 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1_000_000,
            },
            index=dates,
        )
        rsi = RSIIndicator(period=14)
        result = rsi.calculate(df)
        valid = result.values.dropna()
        assert (valid < 10).all()

    def test_nan_for_first_period_rows(self, sample_data):
        rsi = RSIIndicator(period=14)
        result = rsi.calculate(sample_data)
        # First 13 values should be NaN (rolling window of 14 on diff)
        assert result.values.iloc[:13].isna().all()


# ============================================================
# ROCIndicator
# ============================================================


class TestROCIndicator:
    def test_name(self):
        roc = ROCIndicator()
        assert roc.name == "roc"

    def test_calculation(self, sample_data):
        roc = ROCIndicator(period=20)
        result = roc.calculate(sample_data)
        expected = sample_data["close"].pct_change(periods=20) * 100
        pd.testing.assert_series_equal(result.values, expected, check_names=False)

    def test_first_period_rows_nan(self, sample_data):
        roc = ROCIndicator(period=20)
        result = roc.calculate(sample_data)
        assert result.values.iloc[:19].isna().all()

    def test_upward_trend_positive_roc(self, sample_data):
        """Sample data trends up, so late ROC should be positive."""
        roc = ROCIndicator(period=10)
        result = roc.calculate(sample_data)
        # Last value should be positive (price went up over 10 periods)
        assert result.values.iloc[-1] > 0


# ============================================================
# MomentumScoreIndicator
# ============================================================


class TestMomentumScoreIndicator:
    def test_name(self):
        ms = MomentumScoreIndicator()
        assert ms.name == "momentum_score"

    def test_values_in_range(self, sample_data):
        ms = MomentumScoreIndicator()
        result = ms.calculate(sample_data)
        valid = result.values.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_metadata_contains_components(self, sample_data):
        ms = MomentumScoreIndicator()
        result = ms.calculate(sample_data)
        assert "rsi" in result.metadata
        assert "roc" in result.metadata
        assert "rsi_score" in result.metadata
        assert "roc_score" in result.metadata


# ============================================================
# ATRIndicator
# ============================================================


class TestATRIndicator:
    def test_name(self):
        atr = ATRIndicator()
        assert atr.name == "atr"

    def test_calculation_positive_values(self, sample_data):
        atr = ATRIndicator(period=14)
        result = atr.calculate(sample_data)
        valid = result.values.dropna()
        assert (valid > 0).all()

    def test_true_range_components(self, sample_data):
        atr = ATRIndicator(period=14)
        result = atr.calculate(sample_data)
        tr = result.metadata["true_range"]
        # True range should be >= high - low
        hl = sample_data["high"] - sample_data["low"]
        valid_idx = tr.dropna().index
        assert (tr.loc[valid_idx] >= hl.loc[valid_idx] - 1e-10).all()

    def test_atr_pct_metadata(self, sample_data):
        atr = ATRIndicator(period=14)
        result = atr.calculate(sample_data)
        assert "atr_pct" in result.metadata
        atr_pct = result.metadata["atr_pct"].dropna()
        assert (atr_pct > 0).all()

    def test_different_period(self, sample_data):
        atr = ATRIndicator(period=5)
        result = atr.calculate(sample_data)
        assert result.metadata["period"] == 5
        # NaN for first 4 rows (rolling window of 5 on TR which needs shift(1))
        # TR itself has NaN at index 0, then rolling(5) needs 5 values
        # So first 5 values of ATR should be NaN
        assert result.values.iloc[:4].isna().all()


# ============================================================
# BollingerBandsIndicator
# ============================================================


class TestBollingerBandsIndicator:
    def test_name_and_default_params(self):
        bb = BollingerBandsIndicator()
        assert bb.name == "bollinger_bands"
        assert bb.params == {"period": 20, "std_dev": 2.0}

    def test_metadata_keys(self, sample_data):
        bb = BollingerBandsIndicator(period=20, std_dev=2.0)
        result = bb.calculate(sample_data)
        assert "upper" in result.metadata
        assert "lower" in result.metadata
        assert "position" in result.metadata
        assert "bandwidth" in result.metadata

    def test_values_is_middle_band(self, sample_data):
        """result.values is the SMA (middle band)."""
        bb = BollingerBandsIndicator(period=20)
        result = bb.calculate(sample_data)
        expected_mid = sample_data["close"].rolling(window=20).mean()
        pd.testing.assert_series_equal(result.values, expected_mid, check_names=False)

    def test_upper_above_middle_above_lower(self, sample_data):
        bb = BollingerBandsIndicator(period=20, std_dev=2.0)
        result = bb.calculate(sample_data)
        valid_idx = result.values.dropna().index
        upper = result.metadata["upper"].loc[valid_idx]
        lower = result.metadata["lower"].loc[valid_idx]
        mid = result.values.loc[valid_idx]
        assert (upper >= mid).all()
        assert (mid >= lower).all()

    def test_position_clipped_0_to_1(self, sample_data):
        bb = BollingerBandsIndicator(period=20, std_dev=2.0)
        result = bb.calculate(sample_data)
        pos = result.metadata["position"].dropna()
        assert (pos >= 0).all()
        assert (pos <= 1).all()

    def test_bandwidth_positive(self, sample_data):
        bb = BollingerBandsIndicator(period=20, std_dev=2.0)
        result = bb.calculate(sample_data)
        bw = result.metadata["bandwidth"].dropna()
        assert (bw >= 0).all()

    def test_constant_price_bands_collapse(self, flat_price_data):
        """With constant price, upper == lower == close."""
        bb = BollingerBandsIndicator(period=10, std_dev=2.0)
        result = bb.calculate(flat_price_data)
        valid_idx = result.values.dropna().index
        if len(valid_idx) > 0:
            upper = result.metadata["upper"].loc[valid_idx]
            lower = result.metadata["lower"].loc[valid_idx]
            np.testing.assert_allclose(upper.values, 100.0, atol=1e-10)
            np.testing.assert_allclose(lower.values, 100.0, atol=1e-10)


# ============================================================
# GapIndicator
# ============================================================


class TestGapIndicator:
    def test_name(self):
        gap = GapIndicator()
        assert gap.name == "gap"

    def test_metadata_keys(self, sample_data):
        gap = GapIndicator(lookback=60)
        result = gap.calculate(sample_data)
        assert "gap_pct" in result.metadata
        assert "gap_zscore" in result.metadata
        assert "gap_std" in result.metadata
        assert "large_gap" in result.metadata

    def test_gap_calculation(self, sample_data):
        gap = GapIndicator(lookback=60)
        result = gap.calculate(sample_data)
        # gap = (open - prev_close) / prev_close
        expected = (sample_data["open"] - sample_data["close"].shift(1)) / sample_data[
            "close"
        ].shift(1)
        # Compare non-NaN values (first value is always NaN due to shift)
        valid = result.values.dropna()
        expected_valid = expected.loc[valid.index].dropna()
        common = valid.index.intersection(expected_valid.index)
        pd.testing.assert_series_equal(
            result.values.loc[common],
            expected.loc[common],
            check_names=False,
        )

    def test_large_gap_is_boolean(self, sample_data):
        gap = GapIndicator(lookback=60)
        result = gap.calculate(sample_data)
        lg = result.metadata["large_gap"]
        assert lg.dtype == bool


# ============================================================
# VolumeRatioIndicator
# ============================================================


class TestVolumeRatioIndicator:
    def test_name(self):
        vr = VolumeRatioIndicator()
        assert vr.name == "volume_ratio"

    def test_calculation(self, sample_data):
        vr = VolumeRatioIndicator(period=20)
        result = vr.calculate(sample_data)
        expected = sample_data["volume"] / sample_data["volume"].rolling(20).mean()
        # Compare non-NaN
        valid = result.values.dropna()
        expected_valid = expected.loc[valid.index]
        np.testing.assert_allclose(valid.values, expected_valid.values, rtol=1e-10)

    def test_positive_values(self, sample_data):
        vr = VolumeRatioIndicator(period=20)
        result = vr.calculate(sample_data)
        valid = result.values.dropna()
        assert (valid > 0).all()

    def test_high_low_volume_signals(self, sample_data):
        vr = VolumeRatioIndicator(period=20)
        result = vr.calculate(sample_data)
        assert "high_volume" in result.metadata
        assert "low_volume" in result.metadata
        hv = result.metadata["high_volume"].dropna()
        lv = result.metadata["low_volume"].dropna()
        # High volume: ratio > 1.5
        ratio_at_hv = result.values.loc[hv[hv].index]
        if len(ratio_at_hv) > 0:
            assert (ratio_at_hv > 1.5).all()
        # Low volume: ratio < 0.8
        ratio_at_lv = result.values.loc[lv[lv].index]
        if len(ratio_at_lv) > 0:
            assert (ratio_at_lv < 0.8).all()

    def test_nan_handling(self, sample_data):
        vr = VolumeRatioIndicator(period=20)
        result = vr.calculate(sample_data)
        # First 19 values should be NaN (rolling window)
        assert result.values.iloc[:19].isna().all()

    def test_zero_volume_produces_nan(self, zero_volume_data):
        vr = VolumeRatioIndicator(period=10)
        result = vr.calculate(zero_volume_data)
        # volume_ma is 0, replaced with NaN, so ratio is NaN
        valid = result.values.dropna()
        # All should be NaN since volume is 0
        assert len(valid) == 0


# ============================================================
# VolumeTrendIndicator
# ============================================================


class TestVolumeTrendIndicator:
    def test_name(self):
        vt = VolumeTrendIndicator()
        assert vt.name == "volume_trend"

    def test_metadata_keys(self, sample_data):
        vt = VolumeTrendIndicator(short_period=5, long_period=20)
        result = vt.calculate(sample_data)
        assert "increasing" in result.metadata
        assert "decreasing" in result.metadata
        assert "vol_short" in result.metadata
        assert "vol_long" in result.metadata

    def test_values_positive(self, sample_data):
        vt = VolumeTrendIndicator(short_period=5, long_period=20)
        result = vt.calculate(sample_data)
        valid = result.values.dropna()
        assert (valid > 0).all()

    def test_increasing_decreasing_signals(self, sample_data):
        vt = VolumeTrendIndicator(short_period=5, long_period=20)
        result = vt.calculate(sample_data)
        inc = result.metadata["increasing"].dropna()
        dec = result.metadata["decreasing"].dropna()
        # Increasing: trend > 1.2
        if inc.any():
            assert (result.values.loc[inc[inc].index] > 1.2).all()
        # Decreasing: trend < 0.8
        if dec.any():
            assert (result.values.loc[dec[dec].index] < 0.8).all()


# ============================================================
# OBVIndicator
# ============================================================


class TestOBVIndicator:
    def test_name(self):
        obv = OBVIndicator()
        assert obv.name == "obv"

    def test_first_value_equals_volume(self, sample_data):
        obv = OBVIndicator()
        result = obv.calculate(sample_data)
        assert result.values.iloc[0] == sample_data["volume"].iloc[0]

    def test_obv_increases_on_up_close(self, sample_data):
        obv = OBVIndicator()
        result = obv.calculate(sample_data)
        for i in range(1, len(sample_data)):
            if sample_data["close"].iloc[i] > sample_data["close"].iloc[i - 1]:
                assert result.values.iloc[i] == result.values.iloc[i - 1] + sample_data[
                    "volume"
                ].iloc[i]

    def test_obv_decreases_on_down_close(self, sample_data):
        obv = OBVIndicator()
        result = obv.calculate(sample_data)
        for i in range(1, len(sample_data)):
            if sample_data["close"].iloc[i] < sample_data["close"].iloc[i - 1]:
                assert result.values.iloc[i] == result.values.iloc[i - 1] - sample_data[
                    "volume"
                ].iloc[i]

    def test_obv_unchanged_on_flat_close(self):
        n = 10
        dates = pd.date_range("2024-01-01", periods=n)
        df = pd.DataFrame(
            {
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": [100.0] + [100.0] * (n - 1),
                "volume": 1_000_000,
            },
            index=dates,
        )
        obv = OBVIndicator()
        result = obv.calculate(df)
        # After first value, OBV should stay constant (close unchanged)
        for i in range(1, n):
            assert result.values.iloc[i] == result.values.iloc[i - 1]

    def test_obv_metadata(self, sample_data):
        obv = OBVIndicator()
        result = obv.calculate(sample_data)
        assert "obv_ma" in result.metadata
        assert "obv_trend" in result.metadata


# ============================================================
# IndicatorEngine.compute_all()
# ============================================================


class TestIndicatorEngine:
    def test_compute_all_returns_dataframe(self, sample_data):
        engine = IndicatorEngine()
        result = engine.compute_all(sample_data)
        assert isinstance(result, pd.DataFrame)

    def test_compute_all_preserves_original_columns(self, sample_data):
        engine = IndicatorEngine()
        result = engine.compute_all(sample_data)
        for col in ["open", "high", "low", "close", "volume"]:
            assert col in result.columns

    def test_compute_all_adds_expected_columns(self, sample_data):
        engine = IndicatorEngine()
        result = engine.compute_all(sample_data)
        expected_cols = [
            # Trend
            "slope_daily",
            "slope_weekly",
            "slope_monthly",
            "macd",
            "macd_signal",
            "macd_hist",
            "macd_golden",
            "ma_bullish",
            "ma20",
            "ma50",
            # Momentum
            "rsi",
            "momentum_score",
            # Volatility
            "atr",
            "atr_pct",
            "bb_upper",
            "bb_lower",
            "bb_position",
            "bb_width",
            "gap_pct",
            "gap_zscore",
            # Volume
            "volume_ratio",
            "volume_trend",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_compute_all_does_not_modify_original(self, sample_data):
        engine = IndicatorEngine()
        original_cols = set(sample_data.columns)
        engine.compute_all(sample_data)
        assert set(sample_data.columns) == original_cols

    def test_compute_all_numeric_columns(self, sample_data):
        """All indicator columns should be numeric."""
        engine = IndicatorEngine()
        result = engine.compute_all(sample_data)
        indicator_cols = [
            c for c in result.columns if c not in ["open", "high", "low", "close", "volume"]
        ]
        for col in indicator_cols:
            assert pd.api.types.is_numeric_dtype(result[col]), f"{col} is not numeric"

    def test_compute_all_row_count_unchanged(self, sample_data):
        engine = IndicatorEngine()
        result = engine.compute_all(sample_data)
        assert len(result) == len(sample_data)

    def test_compute_all_with_large_data(self, large_data):
        """Engine should handle 250+ rows (for SMA200)."""
        engine = IndicatorEngine()
        result = engine.compute_all(large_data)
        assert "ma200" in result.columns
        assert not result["ma200"].iloc[200:].isna().any()
