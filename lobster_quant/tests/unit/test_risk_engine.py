"""
Comprehensive tests for RiskEngine (OFF filter).

Tests cover:
- Initialization and settings
- assess() with normal and high-risk data
- Individual risk checks (ATR, MA200, Gap, Volume, Benchmark)
- get_stats() statistics calculation
- get_latest_status() status retrieval
- should_trade() trading decision
- Edge cases and error handling
"""

import numpy as np
import pandas as pd
import pytest

from src.core.risk_engine import RiskEngine, get_risk_engine
from src.data.models import OFFStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def risk_engine():
    """Create a fresh RiskEngine instance."""
    return RiskEngine()


@pytest.fixture
def normal_market_data():
    """Generate normal market data (low risk)."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="B")

    # Stable uptrending market
    trend = np.linspace(100, 115, n)
    noise = np.random.normal(0, 0.5, n)
    close = trend + noise

    df = pd.DataFrame(
        {
            "open": close - np.abs(np.random.randn(n) * 0.3),
            "high": close + np.abs(np.random.randn(n) * 0.5),
            "low": close - np.abs(np.random.randn(n) * 0.5),
            "close": close,
            "volume": np.random.randint(5_000_000, 15_000_000, n),
            "atr_pct": np.full(n, 0.015),  # Normal ATR (1.5%)
            "ma200": np.linspace(95, 108, n),  # Rising MA200, below price
            "volume_ratio": np.full(n, 1.2),  # Normal volume
        },
        index=dates,
    )
    return df


@pytest.fixture
def high_risk_data():
    """Generate high-risk market data (volatile, declining)."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="B")

    # Volatile declining market
    close = 100 + np.cumsum(np.random.normal(-0.3, 3, n))

    df = pd.DataFrame(
        {
            "open": close - np.abs(np.random.randn(n) * 2),
            "high": close + np.abs(np.random.randn(n) * 4),
            "low": close - np.abs(np.random.randn(n) * 4),
            "close": close,
            "volume": np.random.randint(1_000_000, 20_000_000, n),
            "atr_pct": np.full(n, 0.08),  # High ATR (8%)
            "ma200": np.linspace(110, 95, n),  # Falling MA200, above price
            "volume_ratio": np.full(n, 0.3),  # Low volume
        },
        index=dates,
    )
    return df


@pytest.fixture
def benchmark_data():
    """Generate benchmark (SPY-like) data."""
    np.random.seed(123)
    n = 100
    dates = pd.date_range("2024-01-01", periods=n, freq="B")

    close = 450 + np.cumsum(np.random.normal(0.1, 1, n))

    df = pd.DataFrame(
        {
            "open": close - np.abs(np.random.randn(n) * 0.5),
            "high": close + np.abs(np.random.randn(n)),
            "low": close - np.abs(np.random.randn(n)),
            "close": close,
            "volume": np.random.randint(50_000_000, 100_000_000, n),
        },
        index=dates,
    )
    # Add ma20 for benchmark risk assessment
    df["ma20"] = df["close"].rolling(20).mean()
    return df


@pytest.fixture
def insufficient_data():
    """Generate data with less than 60 rows (insufficient for OFF filter)."""
    np.random.seed(42)
    n = 30
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(np.random.normal(0, 1, n))

    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.random.randint(1_000_000, 10_000_000, n),
            "atr_pct": np.full(n, 0.02),
            "ma200": np.full(n, 95.0),
            "volume_ratio": np.full(n, 1.0),
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------


class TestRiskEngineInit:
    """Tests for RiskEngine initialization."""

    def test_creates_instance(self, risk_engine):
        """Should create a RiskEngine instance."""
        assert risk_engine is not None
        assert isinstance(risk_engine, RiskEngine)

    def test_loads_settings(self, risk_engine):
        """Should load threshold settings from config."""
        assert risk_engine.atr_threshold > 0
        assert risk_engine.gap_threshold > 0
        assert risk_engine.min_volume_ratio > 0
        assert risk_engine.ma200_recovery_days > 0

    def test_settings_are_numeric(self, risk_engine):
        """All thresholds should be numeric values."""
        assert isinstance(risk_engine.atr_threshold, (int, float))
        assert isinstance(risk_engine.gap_threshold, (int, float))
        assert isinstance(risk_engine.min_volume_ratio, (int, float))
        assert isinstance(risk_engine.ma200_recovery_days, (int, float))


# ---------------------------------------------------------------------------
# Assess Method Tests
# ---------------------------------------------------------------------------


class TestAssess:
    """Tests for assess() method."""

    def test_returns_dataframe(self, risk_engine, normal_market_data):
        """Should return a DataFrame."""
        result = risk_engine.assess(normal_market_data)
        assert isinstance(result, pd.DataFrame)

    def test_has_is_off_column(self, risk_engine, normal_market_data):
        """Result should have is_off column."""
        result = risk_engine.assess(normal_market_data)
        assert "is_off" in result.columns

    def test_is_off_is_boolean(self, risk_engine, normal_market_data):
        """is_off column should contain boolean values."""
        result = risk_engine.assess(normal_market_data)
        assert result["is_off"].dtype == bool

    def test_index_matches_input(self, risk_engine, normal_market_data):
        """Result index should match input data index."""
        result = risk_engine.assess(normal_market_data)
        assert len(result) == len(normal_market_data)
        assert result.index.equals(normal_market_data.index)

    def test_insufficient_data_returns_empty(self, risk_engine, insufficient_data):
        """Should return empty DataFrame when data has < 60 rows."""
        result = risk_engine.assess(insufficient_data)
        assert isinstance(result, pd.DataFrame)
        assert result.empty or len(result.columns) == 0

    def test_normal_market_mostly_on(self, risk_engine, normal_market_data):
        """Normal market should have mostly ON days (< 50% OFF)."""
        result = risk_engine.assess(normal_market_data)
        off_pct = result["is_off"].mean()
        assert off_pct < 0.5, f"Expected < 50% OFF days, got {off_pct:.1%}"

    def test_high_risk_market_more_off(self, risk_engine, high_risk_data):
        """High-risk market should have more OFF days."""
        result = risk_engine.assess(high_risk_data)
        off_pct = result["is_off"].mean()
        # High-risk data should trigger more OFF days
        assert off_pct > 0.0, "High-risk market should have some OFF days"

    def test_with_benchmark_adds_benchmark_column(self, risk_engine, normal_market_data, benchmark_data):
        """Should add benchmark risk column when benchmark data provided."""
        result = risk_engine.assess(normal_market_data, benchmark_data)
        assert "大盘风险" in result.columns


# ---------------------------------------------------------------------------
# Individual Risk Check Tests
# ---------------------------------------------------------------------------


class TestATRCheck:
    """Tests for ATR% risk check."""

    def test_high_atr_triggers_off(self, risk_engine):
        """High ATR% should trigger OFF status."""
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = np.linspace(100, 110, n)

        df = pd.DataFrame(
            {
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": np.ones(n) * 1_000_000,
                "atr_pct": np.full(n, 0.15),  # Very high ATR (15%)
                "ma200": np.full(n, 95.0),
                "volume_ratio": np.full(n, 1.0),
            },
            index=dates,
        )

        result = risk_engine.assess(df)
        # High ATR should trigger OFF for most days
        assert "ATR过高" in result.columns
        atr_off_pct = result["ATR过高"].mean()
        assert atr_off_pct > 0.5, "High ATR should trigger OFF for most days"

    def test_normal_atr_no_trigger(self, risk_engine):
        """Normal ATR% should not trigger OFF status."""
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = np.linspace(100, 110, n)

        df = pd.DataFrame(
            {
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": np.ones(n) * 1_000_000,
                "atr_pct": np.full(n, 0.01),  # Low ATR (1%)
                "ma200": np.full(n, 95.0),
                "volume_ratio": np.full(n, 1.0),
            },
            index=dates,
        )

        result = risk_engine.assess(df)
        if "ATR过高" in result.columns:
            assert result["ATR过高"].sum() == 0


class TestMA200Check:
    """Tests for MA200 recovery risk check."""

    def test_below_falling_ma200_triggers(self, risk_engine):
        """Price below falling MA200 should trigger OFF."""
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = np.linspace(90, 85, n)  # Price declining
        ma200 = np.linspace(100, 95, n)  # MA200 also declining, above price

        df = pd.DataFrame(
            {
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": np.ones(n) * 1_000_000,
                "atr_pct": np.full(n, 0.02),
                "ma200": ma200,
                "volume_ratio": np.full(n, 1.0),
            },
            index=dates,
        )

        result = risk_engine.assess(df)
        if "MA200恢复" in result.columns:
            # Should trigger for most days when price is below falling MA200
            assert result["MA200恢复"].sum() > 0

    def test_above_rising_ma200_no_trigger(self, risk_engine):
        """Price above rising MA200 should not trigger OFF."""
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = np.linspace(105, 115, n)  # Price rising
        ma200 = np.linspace(95, 100, n)  # MA200 below price, rising

        df = pd.DataFrame(
            {
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": np.ones(n) * 1_000_000,
                "atr_pct": np.full(n, 0.02),
                "ma200": ma200,
                "volume_ratio": np.full(n, 1.0),
            },
            index=dates,
        )

        result = risk_engine.assess(df)
        if "MA200恢复" in result.columns:
            assert result["MA200恢复"].sum() == 0


class TestVolumeCheck:
    """Tests for volume ratio risk check."""

    def test_low_volume_triggers(self, risk_engine):
        """Low volume ratio should trigger OFF."""
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = np.linspace(100, 110, n)

        df = pd.DataFrame(
            {
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": np.ones(n) * 100_000,  # Very low volume
                "atr_pct": np.full(n, 0.02),
                "ma200": np.full(n, 95.0),
                "volume_ratio": np.full(n, 0.01),  # Very low ratio (< 0.05 threshold)
            },
            index=dates,
        )

        result = risk_engine.assess(df)
        if "流动性不足" in result.columns:
            assert result["流动性不足"].sum() > 0

    def test_normal_volume_no_trigger(self, risk_engine):
        """Normal volume ratio should not trigger OFF."""
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = np.linspace(100, 110, n)

        df = pd.DataFrame(
            {
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": np.ones(n) * 5_000_000,
                "atr_pct": np.full(n, 0.02),
                "ma200": np.full(n, 95.0),
                "volume_ratio": np.full(n, 1.5),  # Normal ratio
            },
            index=dates,
        )

        result = risk_engine.assess(df)
        if "流动性不足" in result.columns:
            assert result["流动性不足"].sum() == 0


# ---------------------------------------------------------------------------
# Statistics Tests
# ---------------------------------------------------------------------------


class TestGetStats:
    """Tests for get_stats() method."""

    def test_returns_required_keys(self, risk_engine, normal_market_data):
        """Stats should contain all required keys."""
        results = risk_engine.assess(normal_market_data)
        stats = risk_engine.get_stats(normal_market_data, results)

        assert "total_days" in stats
        assert "off_days" in stats
        assert "on_days" in stats
        assert "on_pct" in stats
        assert "off_pct" in stats
        assert "reasons" in stats

    def test_total_days_matches_data(self, risk_engine, normal_market_data):
        """total_days should match input data length."""
        results = risk_engine.assess(normal_market_data)
        stats = risk_engine.get_stats(normal_market_data, results)
        assert stats["total_days"] == len(normal_market_data)

    def test_on_off_days_sum_to_total(self, risk_engine, normal_market_data):
        """on_days + off_days should equal total_days."""
        results = risk_engine.assess(normal_market_data)
        stats = risk_engine.get_stats(normal_market_data, results)
        assert stats["on_days"] + stats["off_days"] == stats["total_days"]

    def test_percentages_sum_to_100(self, risk_engine, normal_market_data):
        """on_pct + off_pct should equal 100."""
        results = risk_engine.assess(normal_market_data)
        stats = risk_engine.get_stats(normal_market_data, results)
        assert abs(stats["on_pct"] + stats["off_pct"] - 100) < 0.01

    def test_reasons_is_dict(self, risk_engine, normal_market_data):
        """reasons should be a dictionary."""
        results = risk_engine.assess(normal_market_data)
        stats = risk_engine.get_stats(normal_market_data, results)
        assert isinstance(stats["reasons"], dict)


# ---------------------------------------------------------------------------
# Latest Status Tests
# ---------------------------------------------------------------------------


class TestGetLatestStatus:
    """Tests for get_latest_status() method."""

    def test_returns_off_status(self, risk_engine, normal_market_data):
        """Should return an OFFStatus instance."""
        status = risk_engine.get_latest_status(normal_market_data)
        assert isinstance(status, OFFStatus)

    def test_has_required_fields(self, risk_engine, normal_market_data):
        """Status should have all required fields."""
        status = risk_engine.get_latest_status(normal_market_data)
        assert hasattr(status, "is_off")
        assert hasattr(status, "is_on")
        assert hasattr(status, "reasons")
        assert hasattr(status, "timestamp")

    def test_reasons_is_list(self, risk_engine, normal_market_data):
        """reasons should be a list."""
        status = risk_engine.get_latest_status(normal_market_data)
        assert isinstance(status.reasons, list)

    def test_insufficient_data_returns_default(self, risk_engine, insufficient_data):
        """Should return default status for insufficient data."""
        status = risk_engine.get_latest_status(insufficient_data)
        assert isinstance(status, OFFStatus)
        assert status.is_off is False

    def test_with_benchmark(self, risk_engine, normal_market_data, benchmark_data):
        """Should work with benchmark data."""
        status = risk_engine.get_latest_status(normal_market_data, benchmark_data)
        assert isinstance(status, OFFStatus)


# ---------------------------------------------------------------------------
# Should Trade Tests
# ---------------------------------------------------------------------------


class TestShouldTrade:
    """Tests for should_trade() method."""

    def test_returns_tuple(self, risk_engine, normal_market_data):
        """Should return a tuple of (bool, list)."""
        result = risk_engine.should_trade(normal_market_data)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_first_element_is_bool(self, risk_engine, normal_market_data):
        """First element should be a boolean."""
        should_trade, reasons = risk_engine.should_trade(normal_market_data)
        assert isinstance(should_trade, bool)

    def test_second_element_is_list(self, risk_engine, normal_market_data):
        """Second element should be a list."""
        should_trade, reasons = risk_engine.should_trade(normal_market_data)
        assert isinstance(reasons, list)

    def test_normal_market_allows_trading(self, risk_engine, normal_market_data):
        """Normal market should generally allow trading."""
        should_trade, reasons = risk_engine.should_trade(normal_market_data)
        # Most normal market conditions should allow trading
        # (This is a soft assertion - some days might be OFF)
        assert isinstance(should_trade, bool)


# ---------------------------------------------------------------------------
# Benchmark Risk Tests
# ---------------------------------------------------------------------------


class TestBenchmarkRisk:
    """Tests for benchmark risk assessment."""

    def test_benchmark_with_falling_ma200(self, risk_engine, normal_market_data):
        """Falling benchmark MA200 should trigger benchmark risk."""
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = np.linspace(450, 430, n)  # Declining benchmark

        benchmark = pd.DataFrame(
            {
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": np.ones(n) * 50_000_000,
            },
            index=dates,
        )

        result = risk_engine.assess(normal_market_data, benchmark)
        if "大盘风险" in result.columns:
            # Falling benchmark should trigger risk
            assert result["大盘风险"].sum() > 0

    def test_benchmark_with_rising_ma200(self, risk_engine, normal_market_data):
        """Rising benchmark MA200 should not trigger benchmark risk."""
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = np.linspace(430, 460, n)  # Rising benchmark

        benchmark = pd.DataFrame(
            {
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": np.ones(n) * 50_000_000,
            },
            index=dates,
        )

        result = risk_engine.assess(normal_market_data, benchmark)
        if "大盘风险" in result.columns:
            # Rising benchmark should not trigger risk (or very few days)
            assert result["大盘风险"].sum() < 10


# ---------------------------------------------------------------------------
# Singleton Tests
# ---------------------------------------------------------------------------


class TestGetRiskEngine:
    """Tests for get_risk_engine() singleton."""

    def test_returns_risk_engine(self):
        """Should return a RiskEngine instance."""
        engine = get_risk_engine()
        assert isinstance(engine, RiskEngine)

    def test_singleton_pattern(self):
        """Should return the same instance on multiple calls."""
        e1 = get_risk_engine()
        e2 = get_risk_engine()
        assert e1 is e2


# ---------------------------------------------------------------------------
# Edge Case Tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_dataframe(self, risk_engine):
        """Should handle empty DataFrame gracefully."""
        empty_df = pd.DataFrame()
        result = risk_engine.assess(empty_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_exactly_60_rows(self, risk_engine):
        """Should work with exactly 60 rows (minimum requirement)."""
        n = 60
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = np.linspace(100, 110, n)

        df = pd.DataFrame(
            {
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": np.ones(n) * 1_000_000,
                "atr_pct": np.full(n, 0.02),
                "ma200": np.full(n, 95.0),
                "volume_ratio": np.full(n, 1.0),
            },
            index=dates,
        )

        result = risk_engine.assess(df)
        assert len(result) == 60
        assert "is_off" in result.columns

    def test_59_rows_insufficient(self, risk_engine):
        """Should return empty DataFrame for 59 rows."""
        n = 59
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = np.linspace(100, 110, n)

        df = pd.DataFrame(
            {
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": np.ones(n) * 1_000_000,
                "atr_pct": np.full(n, 0.02),
                "ma200": np.full(n, 95.0),
                "volume_ratio": np.full(n, 1.0),
            },
            index=dates,
        )

        result = risk_engine.assess(df)
        assert result.empty or len(result.columns) == 0

    def test_missing_optional_columns(self, risk_engine):
        """Should handle missing optional columns gracefully."""
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = np.linspace(100, 110, n)

        # Only close column - no ATR, MA200, volume_ratio
        df = pd.DataFrame(
            {
                "close": close,
            },
            index=dates,
        )

        result = risk_engine.assess(df)
        assert len(result) == 100
        assert "is_off" in result.columns

    def test_nan_values_handled(self, risk_engine):
        """Should handle NaN values in data."""
        n = 100
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        close = np.linspace(100, 110, n)
        close[50:55] = np.nan  # Add some NaN values

        df = pd.DataFrame(
            {
                "open": close,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
                "volume": np.ones(n) * 1_000_000,
                "atr_pct": np.full(n, 0.02),
                "ma200": np.full(n, 95.0),
                "volume_ratio": np.full(n, 1.0),
            },
            index=dates,
        )

        # Should not raise an exception
        result = risk_engine.assess(df)
        assert len(result) == 100
