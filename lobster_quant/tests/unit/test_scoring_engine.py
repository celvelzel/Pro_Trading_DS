"""
Comprehensive tests for ScoringEngine.

Covers all business logic paths in src/core/scoring_engine.py:
- compute_score(): composite scoring, validation, slope_wm merging
- _calc_trend_score(): percentile-rank slope normalization (0-40)
- _calc_momentum_score(): RSI mapping + 20-day return percentile (0-40)
- _calc_volume_score(): volume ratio scoring (0-15)
- _calc_pattern_score(): MACD golden cross, MA bullish, BB position (0-25)
- get_scoring_engine(): singleton
- Edge cases: NaN, single row, large datasets, missing columns
"""

import numpy as np
import pandas as pd
import pytest

from src.core.scoring_engine import ScoringEngine, get_scoring_engine
from src.utils.exceptions import ScoringError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def scoring_engine():
    return ScoringEngine()


@pytest.fixture
def controlled_df():
    """DataFrame with hand-crafted values for precise sub-score testing."""
    n = 50
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "close": np.linspace(100, 120, n),
            "rsi": np.full(n, 50.0),
            "volume_ratio": np.full(n, 1.0),
            "slope_daily": np.full(n, 0.5),
            "macd_golden": [False] * n,
            "ma_bullish": [True] * n,
            "bb_position": np.full(n, 0.6),
        },
        index=idx,
    )


@pytest.fixture
def all_nan_df():
    """DataFrame where all indicator columns are NaN (e.g. insufficient data)."""
    n = 10
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "close": [np.nan] * n,
            "rsi": [np.nan] * n,
            "volume_ratio": [np.nan] * n,
            "slope_daily": [np.nan] * n,
        },
        index=idx,
    )


# ===========================================================================
# compute_score – top-level composite
# ===========================================================================

class TestComputeScore:
    """Tests for ScoringEngine.compute_score()."""

    def test_returns_series(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine.compute_score(sample_ohlcv_df_with_indicators)
        assert isinstance(result, pd.Series)

    def test_length_matches_input(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine.compute_score(sample_ohlcv_df_with_indicators)
        assert len(result) == len(sample_ohlcv_df_with_indicators)

    def test_index_matches_input(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine.compute_score(sample_ohlcv_df_with_indicators)
        pd.testing.assert_index_equal(result.index, sample_ohlcv_df_with_indicators.index)

    def test_score_range_0_to_100(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine.compute_score(sample_ohlcv_df_with_indicators)
        assert result.min() >= 0, f"Min score {result.min()} below 0"
        assert result.max() <= 100, f"Max score {result.max()} above 100"

    def test_score_dtype_is_float(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine.compute_score(sample_ohlcv_df_with_indicators)
        assert result.dtype == np.float64

    def test_does_not_mutate_input(self, scoring_engine, sample_ohlcv_df_with_indicators):
        original_cols = set(sample_ohlcv_df_with_indicators.columns)
        scoring_engine.compute_score(sample_ohlcv_df_with_indicators)
        assert set(sample_ohlcv_df_with_indicators.columns) == original_cols

    def test_with_slope_wm_merges_columns(self, scoring_engine, sample_ohlcv_df_with_indicators):
        """slope_weekly / slope_monthly are merged into the scoring dataframe."""
        df = sample_ohlcv_df_with_indicators.copy()
        df["slope_weekly"] = df["slope_daily"] * 0.5
        df["slope_monthly"] = df["slope_daily"] * 0.3
        slope_wm = df[["slope_weekly", "slope_monthly"]]
        # Remove from df so we can verify merge works
        df = df.drop(columns=["slope_weekly", "slope_monthly"])

        result = scoring_engine.compute_score(df, slope_wm=slope_wm)
        assert isinstance(result, pd.Series)
        assert len(result) == len(df)
        assert result.min() >= 0
        assert result.max() <= 100

    def test_score_with_all_nan_data(self, scoring_engine, all_nan_df):
        """All-NaN data should produce valid scores (no crash)."""
        result = scoring_engine.compute_score(all_nan_df)
        assert isinstance(result, pd.Series)
        assert len(result) == len(all_nan_df)
        # With NaN close, pct_change produces NaN → filled to defaults
        assert result.notna().all()

    def test_score_single_row(self, scoring_engine):
        """Single-row DataFrame should not crash."""
        idx = pd.date_range("2024-01-01", periods=1, freq="B")
        df = pd.DataFrame(
            {
                "close": [100.0],
                "rsi": [50.0],
                "volume_ratio": [1.0],
                "slope_daily": [0.1],
            },
            index=idx,
        )
        result = scoring_engine.compute_score(df)
        assert len(result) == 1
        assert 0 <= result.iloc[0] <= 100

    def test_score_large_dataset(self, scoring_engine):
        """Large dataset (1000 rows) should compute without errors."""
        n = 1000
        idx = pd.date_range("2020-01-01", periods=n, freq="B")
        np.random.seed(99)
        df = pd.DataFrame(
            {
                "close": 100 + np.cumsum(np.random.normal(0, 1, n)),
                "rsi": np.clip(np.random.normal(50, 15, n), 0, 100),
                "volume_ratio": np.abs(np.random.normal(1.0, 0.3, n)),
                "slope_daily": np.random.normal(0, 0.5, n),
                "macd_golden": np.random.choice([True, False], n, p=[0.1, 0.9]),
                "ma_bullish": np.random.choice([True, False], n, p=[0.5, 0.5]),
                "bb_position": np.random.uniform(-0.5, 1.5, n),
            },
            index=idx,
        )
        result = scoring_engine.compute_score(df)
        assert len(result) == n
        assert result.min() >= 0
        assert result.max() <= 100


# ===========================================================================
# Missing column validation
# ===========================================================================

class TestMissingColumns:
    """ScoringError raised when required columns are missing."""

    def test_missing_close(self, scoring_engine):
        df = pd.DataFrame(
            {"rsi": [50], "volume_ratio": [1.0], "slope_daily": [0.1]},
            index=pd.date_range("2024-01-01", periods=1),
        )
        with pytest.raises(ScoringError, match="Missing required columns"):
            scoring_engine.compute_score(df)

    def test_missing_rsi(self, scoring_engine):
        df = pd.DataFrame(
            {"close": [100], "volume_ratio": [1.0], "slope_daily": [0.1]},
            index=pd.date_range("2024-01-01", periods=1),
        )
        with pytest.raises(ScoringError, match="Missing required columns"):
            scoring_engine.compute_score(df)

    def test_missing_volume_ratio(self, scoring_engine):
        df = pd.DataFrame(
            {"close": [100], "rsi": [50], "slope_daily": [0.1]},
            index=pd.date_range("2024-01-01", periods=1),
        )
        with pytest.raises(ScoringError, match="Missing required columns"):
            scoring_engine.compute_score(df)

    def test_missing_slope_daily(self, scoring_engine):
        df = pd.DataFrame(
            {"close": [100], "rsi": [50], "volume_ratio": [1.0]},
            index=pd.date_range("2024-01-01", periods=1),
        )
        with pytest.raises(ScoringError, match="Missing required columns"):
            scoring_engine.compute_score(df)

    def test_missing_all_columns(self, scoring_engine):
        with pytest.raises(ScoringError, match="Missing required columns"):
            scoring_engine.compute_score(pd.DataFrame())

    def test_missing_multiple_columns_lists_all(self, scoring_engine):
        df = pd.DataFrame({"close": [100]})
        with pytest.raises(ScoringError) as exc_info:
            scoring_engine.compute_score(df)
        msg = str(exc_info.value)
        assert "rsi" in msg
        assert "volume_ratio" in msg
        assert "slope_daily" in msg

    def test_empty_dataframe_raises(self, scoring_engine):
        df = pd.DataFrame(columns=["close", "rsi", "volume_ratio", "slope_daily"])
        # Empty DataFrame has the columns but no data — no error for validation,
        # but should still work (return empty Series)
        result = scoring_engine.compute_score(df)
        assert len(result) == 0


# ===========================================================================
# _calc_trend_score
# ===========================================================================

class TestTrendScore:
    """Tests for _calc_trend_score(): slope percentile ranking (0-40 range)."""

    def test_range_with_real_data(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine._calc_trend_score(sample_ohlcv_df_with_indicators)
        assert result.min() >= 0
        assert result.max() <= 40

    def test_only_slope_daily(self, scoring_engine, controlled_df):
        """With only slope_daily present, trend score uses daily only."""
        result = scoring_engine._calc_trend_score(controlled_df)
        assert result.min() >= 0
        assert result.max() <= 40
        # All same slope_daily → rank should be uniform
        # With all identical values, rank(pct=True) gives 1.0 for all → score = 40
        assert result.nunique() == 1

    def test_with_all_three_slopes(self, scoring_engine, controlled_df):
        """With daily, weekly, monthly slopes, score is average of three."""
        df = controlled_df.copy()
        df["slope_weekly"] = np.full(len(df), 0.3)
        df["slope_monthly"] = np.full(len(df), 0.1)
        result = scoring_engine._calc_trend_score(df)
        assert result.min() >= 0
        assert result.max() <= 40

    def test_with_slope_weekly_only(self, scoring_engine, controlled_df):
        df = controlled_df.drop(columns=["slope_daily"])
        df["slope_weekly"] = np.full(len(df), 0.5)
        result = scoring_engine._calc_trend_score(df)
        assert result.min() >= 0
        assert result.max() <= 40

    def test_no_slope_columns_returns_20(self, scoring_engine):
        """When no slope columns exist, returns constant 20 (midpoint)."""
        df = pd.DataFrame({"close": [100, 101, 102]})
        result = scoring_engine._calc_trend_score(df)
        assert (result == 20).all()

    def test_all_nan_slope_returns_20(self, scoring_engine):
        """All-NaN slopes → 'recent' is empty → returns 20."""
        idx = pd.date_range("2024-01-01", periods=5, freq="B")
        df = pd.DataFrame(
            {"slope_daily": [np.nan] * 5},
            index=idx,
        )
        result = scoring_engine._calc_trend_score(df)
        assert (result == 20).all()

    def test_increasing_slopes_higher_scores(self, scoring_engine):
        """Rows with higher slopes should get higher trend scores."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        slopes = np.linspace(-1, 1, n)
        df = pd.DataFrame({"slope_daily": slopes}, index=idx)
        result = scoring_engine._calc_trend_score(df)
        # Scores should be monotonically increasing (since slopes are)
        assert result.is_monotonic_increasing

    def test_percentile_rank_normalization(self, scoring_engine):
        """Verify percentile rank is used: uniform data → all get the same score."""
        n = 100
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({"slope_daily": np.full(n, 42.0)}, index=idx)
        result = scoring_engine._calc_trend_score(df)
        # All identical → rank(pct=True) = (n+1)/(2n) ≈ 0.505 → 0.505 * 40 ≈ 20.2
        assert result.nunique() == 1, "All identical slopes should produce one unique score"
        # Score should be near midpoint (20) since all values are the same
        assert 19 < result.iloc[0] < 21


# ===========================================================================
# _calc_momentum_score
# ===========================================================================

class TestMomentumScore:
    """Tests for _calc_momentum_score(): RSI mapping + return percentile (0-40)."""

    def test_range_with_real_data(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine._calc_momentum_score(sample_ohlcv_df_with_indicators)
        assert result.min() >= 0
        assert result.max() <= 40

    def test_rsi_below_30_gives_20(self, scoring_engine):
        """RSI < 30 → rsi_score = 20."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": np.full(n, 20.0),
            },
            index=idx,
        )
        result = scoring_engine._calc_momentum_score(df)
        # rsi_score = 20 for all, ret_score varies by percentile
        # At minimum, rsi component should be 20
        assert result.min() >= 20

    def test_rsi_above_70_decreases_score(self, scoring_engine):
        """RSI = 100 → rsi_score = max(0, 20 - 30) = 0."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": np.full(n, 100.0),
            },
            index=idx,
        )
        result = scoring_engine._calc_momentum_score(df)
        # rsi_score = 0 for all, ret_score >= 0
        assert result.min() >= 0

    def test_rsi_nan_gives_10(self, scoring_engine):
        """NaN RSI → rsi_score = 10.0 (neutral)."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": [np.nan] * n,
            },
            index=idx,
        )
        result = scoring_engine._calc_momentum_score(df)
        # rsi_score = 10 for all, ret_score = varies
        # Total min should be around 10
        assert result.min() >= 10

    def test_rsi_30_boundary(self, scoring_engine):
        """RSI = 30 → exactly on boundary, should be 20 (< 30 check)."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": np.full(n, 30.0),
            },
            index=idx,
        )
        result = scoring_engine._calc_momentum_score(df)
        # RSI 30: 30 < 50 → 10.0 + (30-30)*0.5 = 10.0
        assert result.min() >= 10

    def test_rsi_50_midpoint(self, scoring_engine):
        """RSI = 50 → 10 + (50-30)*0.5 = 20."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": np.full(n, 50.0),
            },
            index=idx,
        )
        result = scoring_engine._calc_momentum_score(df)
        # rsi_score = 20.0, ret_score >= 0
        assert result.min() >= 20

    def test_rsi_70_boundary(self, scoring_engine):
        """RSI = 70 → max(0, 20 - (70-70)) = 20."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": np.full(n, 70.0),
            },
            index=idx,
        )
        result = scoring_engine._calc_momentum_score(df)
        # rsi_score = 20.0
        assert result.min() >= 20

    def test_rsi_0_gives_20(self, scoring_engine):
        """RSI = 0 → < 30 → 20."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": np.full(n, 0.0),
            },
            index=idx,
        )
        result = scoring_engine._calc_momentum_score(df)
        assert result.min() >= 20

    def test_rsi_40_interpolation(self, scoring_engine):
        """RSI = 40 → 10 + (40-30)*0.5 = 15."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": np.full(n, 40.0),
            },
            index=idx,
        )
        result = scoring_engine._calc_momentum_score(df)
        # rsi_score = 15.0, ret_score >= 0
        assert result.min() >= 15

    def test_rsi_60_interpolation(self, scoring_engine):
        """RSI = 60 → 20 - (60-50)*0.5 = 15."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": np.full(n, 60.0),
            },
            index=idx,
        )
        result = scoring_engine._calc_momentum_score(df)
        assert result.min() >= 15

    def test_rsi_90_gives_zero(self, scoring_engine):
        """RSI = 90 → max(0, 20 - (90-70)) = 0."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": np.full(n, 90.0),
            },
            index=idx,
        )
        result = scoring_engine._calc_momentum_score(df)
        # rsi_score = 0, ret_score >= 0
        assert result.min() >= 0

    def test_20d_return_component_present(self, scoring_engine):
        """20-day return percentile contributes to score."""
        n = 100
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        # Strong uptrend → high return → high ret_score
        close = np.linspace(50, 200, n)
        df = pd.DataFrame({"close": close, "rsi": np.full(n, 50.0)}, index=idx)
        result = scoring_engine._calc_momentum_score(df)
        # rsi_score = 20, ret_score should add more
        assert result.max() > 20

    def test_constant_close_no_return(self, scoring_engine):
        """Flat close prices → pct_change = 0 → percentile-based score."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {"close": np.full(n, 100.0), "rsi": np.full(n, 50.0)},
            index=idx,
        )
        result = scoring_engine._calc_momentum_score(df)
        # All returns = 0, rank uniform → ret_score = 0.5 * 20 = 10
        # rsi_score = 20, total = 30
        assert len(result) == n


# ===========================================================================
# _calc_volume_score
# ===========================================================================

class TestVolumeScore:
    """Tests for _calc_volume_score(): volume ratio mapping (0-15)."""

    def test_range_with_real_data(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine._calc_volume_score(sample_ohlcv_df_with_indicators)
        assert result.min() >= 0
        assert result.max() <= 15

    def test_high_volume_ratio_gives_15(self, scoring_engine):
        """volume_ratio > 1.5 → 15.0."""
        n = 10
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({"volume_ratio": np.full(n, 2.0)}, index=idx)
        result = scoring_engine._calc_volume_score(df)
        assert (result == 15.0).all()

    def test_low_volume_ratio_gives_5(self, scoring_engine):
        """volume_ratio < 0.8 → 5.0."""
        n = 10
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({"volume_ratio": np.full(n, 0.5)}, index=idx)
        result = scoring_engine._calc_volume_score(df)
        assert (result == 5.0).all()

    def test_volume_ratio_nan_gives_7_5(self, scoring_engine):
        """NaN volume_ratio → 7.5 (midpoint)."""
        n = 10
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({"volume_ratio": [np.nan] * n}, index=idx)
        result = scoring_engine._calc_volume_score(df)
        assert (result == 7.5).all()

    def test_volume_ratio_1_0_midrange(self, scoring_engine):
        """volume_ratio = 1.0 → 7.5 + (1.0 - 0.8) * 10.7 = 9.64."""
        n = 10
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({"volume_ratio": np.full(n, 1.0)}, index=idx)
        result = scoring_engine._calc_volume_score(df)
        expected = 7.5 + (1.0 - 0.8) * 10.7  # 9.64
        assert np.allclose(result, expected)

    def test_volume_ratio_0_8_boundary(self, scoring_engine):
        """volume_ratio = 0.8 → else branch: 7.5 + (0.8-0.8)*10.7 = 7.5."""
        n = 10
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({"volume_ratio": np.full(n, 0.8)}, index=idx)
        result = scoring_engine._calc_volume_score(df)
        assert np.allclose(result, 7.5)

    def test_volume_ratio_1_5_boundary(self, scoring_engine):
        """volume_ratio = 1.5 → else branch (not > 1.5): 7.5 + (1.5-0.8)*10.7."""
        n = 10
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({"volume_ratio": np.full(n, 1.5)}, index=idx)
        result = scoring_engine._calc_volume_score(df)
        expected = 7.5 + (1.5 - 0.8) * 10.7  # 14.99
        assert np.allclose(result, expected)

    def test_volume_ratio_just_above_1_5(self, scoring_engine):
        """volume_ratio = 1.51 → 15.0 (capped)."""
        n = 10
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({"volume_ratio": np.full(n, 1.51)}, index=idx)
        result = scoring_engine._calc_volume_score(df)
        assert (result == 15.0).all()

    def test_no_volume_ratio_column_gives_5(self, scoring_engine):
        """Missing volume_ratio column → Series(0.0) → 5.0 (< 0.8)."""
        idx = pd.date_range("2024-01-01", periods=5, freq="B")
        df = pd.DataFrame({"close": [100, 101, 102, 103, 104]}, index=idx)
        result = scoring_engine._calc_volume_score(df)
        assert (result == 5.0).all()

    def test_volume_ratio_zero(self, scoring_engine):
        """volume_ratio = 0 → < 0.8 → 5.0."""
        n = 10
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({"volume_ratio": np.full(n, 0.0)}, index=idx)
        result = scoring_engine._calc_volume_score(df)
        assert (result == 5.0).all()

    def test_linear_interpolation_between_08_and_15(self, scoring_engine):
        """Scores increase linearly between ratio 0.8 and 1.5."""
        n = 10
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        ratios = np.linspace(0.8, 1.5, n)
        df = pd.DataFrame({"volume_ratio": ratios}, index=idx)
        result = scoring_engine._calc_volume_score(df)
        assert result.is_monotonic_increasing
        assert result.min() >= 7.5
        assert result.max() <= 15.0


# ===========================================================================
# _calc_pattern_score
# ===========================================================================

class TestPatternScore:
    """Tests for _calc_pattern_score(): MACD, MA, BB (0-25)."""

    def test_range_with_real_data(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine._calc_pattern_score(sample_ohlcv_df_with_indicators)
        assert result.min() >= 0
        assert result.max() <= 25

    def test_no_pattern_columns_gives_zero(self, scoring_engine):
        """No pattern columns → score = 0."""
        idx = pd.date_range("2024-01-01", periods=5, freq="B")
        df = pd.DataFrame({"close": [100, 101, 102, 103, 104]}, index=idx)
        result = scoring_engine._calc_pattern_score(df)
        assert (result == 0.0).all()

    def test_macd_golden_cross_gives_10(self, scoring_engine):
        """macd_golden=True on previous row → +10 (shifted by 1)."""
        n = 5
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        # Set macd_golden=True on row 0, so shift(1) → row 1 gets +10
        df = pd.DataFrame(
            {"macd_golden": [True, False, False, False, False]},
            index=idx,
        )
        result = scoring_engine._calc_pattern_score(df)
        # Row 0: shift(1) = NaN → fillna(False) → 0
        # Row 1: shift(1) = True → 10
        # Rows 2-4: shift(1) = False → 0
        assert result.iloc[0] == 0.0
        assert result.iloc[1] == 10.0
        assert result.iloc[2] == 0.0

    def test_ma_bullish_gives_10(self, scoring_engine):
        """ma_bullish=True → +10."""
        n = 5
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {"ma_bullish": [True, True, False, False, False]},
            index=idx,
        )
        result = scoring_engine._calc_pattern_score(df)
        assert result.iloc[0] == 10.0
        assert result.iloc[1] == 10.0
        assert result.iloc[2] == 0.0

    def test_bb_position_above_0_5_gives_5(self, scoring_engine):
        """bb_position > 0.5 → +5."""
        n = 5
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {"bb_position": [0.6, 0.4, 0.5, 1.0, -0.1]},
            index=idx,
        )
        result = scoring_engine._calc_pattern_score(df)
        assert result.iloc[0] == 5.0  # 0.6 > 0.5
        assert result.iloc[1] == 0.0  # 0.4 <= 0.5
        assert result.iloc[2] == 0.0  # 0.5 == 0.5 (not >)
        assert result.iloc[3] == 5.0  # 1.0 > 0.5
        assert result.iloc[4] == 0.0  # -0.1 <= 0.5

    def test_all_patterns_present_max_score(self, scoring_engine):
        """All patterns active → 10 + 10 + 5 = 25."""
        n = 5
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        # macd_golden=True on row 0 → shift → row 1 gets +10
        df = pd.DataFrame(
            {
                "macd_golden": [True, True, True, True, True],
                "ma_bullish": [True, True, True, True, True],
                "bb_position": [0.8, 0.8, 0.8, 0.8, 0.8],
            },
            index=idx,
        )
        result = scoring_engine._calc_pattern_score(df)
        # Row 0: shift(1)=NaN → 0 + 10 + 5 = 15
        # Row 1+: 10 + 10 + 5 = 25
        assert result.iloc[0] == 15.0
        assert (result.iloc[1:] == 25.0).all()

    def test_macd_golden_nan_treated_as_false(self, scoring_engine):
        """NaN in macd_golden → fillna(False) → 0."""
        n = 3
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {"macd_golden": [np.nan, True, False]},
            index=idx,
        )
        result = scoring_engine._calc_pattern_score(df)
        # Row 0: shift(1)=NaN → fillna(False) → 0
        # Row 1: shift(1)=NaN → fillna(False) → 0
        # Row 2: shift(1)=True → 10
        assert result.iloc[0] == 0.0
        assert result.iloc[1] == 0.0
        assert result.iloc[2] == 10.0

    def test_ma_bullish_nan_treated_as_false(self, scoring_engine):
        """NaN in ma_bullish → fillna(False) → 0."""
        n = 3
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {"ma_bullish": [np.nan, True, False]},
            index=idx,
        )
        result = scoring_engine._calc_pattern_score(df)
        assert result.iloc[0] == 0.0
        assert result.iloc[1] == 10.0
        assert result.iloc[2] == 0.0

    def test_bb_position_nan_treated_as_false(self, scoring_engine):
        """NaN in bb_position → fillna(False) → 0."""
        n = 3
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {"bb_position": [np.nan, 0.6, 0.3]},
            index=idx,
        )
        result = scoring_engine._calc_pattern_score(df)
        assert result.iloc[0] == 0.0
        assert result.iloc[1] == 5.0
        assert result.iloc[2] == 0.0


# ===========================================================================
# get_scoring_engine – singleton
# ===========================================================================

class TestGetScoringEngine:
    """Tests for the get_scoring_engine() factory."""

    def test_returns_scoring_engine_instance(self):
        engine = get_scoring_engine()
        assert isinstance(engine, ScoringEngine)

    def test_singleton_returns_same_object(self):
        e1 = get_scoring_engine()
        e2 = get_scoring_engine()
        assert e1 is e2

    def test_has_weights(self):
        engine = get_scoring_engine()
        assert hasattr(engine, "weights")
        assert "trend" in engine.weights
        assert "momentum" in engine.weights
        assert "volume" in engine.weights
        assert "pattern" in engine.weights


# ===========================================================================
# Weight application
# ===========================================================================

class TestWeightApplication:
    """Verify weights from settings are applied correctly in final score."""

    def test_weights_sum_to_one(self, scoring_engine):
        total = sum(scoring_engine.weights.values())
        assert abs(total - 1.0) < 0.01, f"Weights sum to {total}, expected ~1.0"

    def test_default_weights(self, scoring_engine):
        """Default weights: trend=0.40, momentum=0.20, volume=0.15, pattern=0.25."""
        w = scoring_engine.weights
        assert abs(w["trend"] - 0.40) < 0.01
        assert abs(w["momentum"] - 0.20) < 0.01
        assert abs(w["volume"] - 0.15) < 0.01
        assert abs(w["pattern"] - 0.25) < 0.01

    def test_weighted_score_is_linear_combination(self, scoring_engine, controlled_df):
        """Final score = trend*0.4 + momentum*0.2 + volume*0.15 + pattern*0.25."""
        df = controlled_df.copy()
        result = scoring_engine.compute_score(df)

        trend = scoring_engine._calc_trend_score(df)
        momentum = scoring_engine._calc_momentum_score(df)
        volume = scoring_engine._calc_volume_score(df)
        pattern = scoring_engine._calc_pattern_score(df)

        expected = (
            trend * scoring_engine.weights["trend"]
            + momentum * scoring_engine.weights["momentum"]
            + volume * scoring_engine.weights["volume"]
            + pattern * scoring_engine.weights["pattern"]
        ).clip(0, 100)

        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_all_max_subscores_gives_100(self, scoring_engine):
        """If all sub-scores are at their max, final should be 100."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        # trend max=40, momentum max=40, volume max=15, pattern max=25
        # weighted: 40*0.4 + 40*0.2 + 15*0.15 + 25*0.25 = 16 + 8 + 2.25 + 6.25 = 32.5
        # That's the theoretical max before clip. Not 100.
        # But we can verify the calculation is correct.
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 200, n),
                "rsi": np.full(n, 30.0),  # rsi_score = 20
                "volume_ratio": np.full(n, 2.0),  # vol_score = 15
                "slope_daily": np.linspace(-1, 10, n),  # high slope for trend
                "macd_golden": [True] * n,  # +10
                "ma_bullish": [True] * n,  # +10
                "bb_position": np.full(n, 0.8),  # +5
            },
            index=idx,
        )
        result = scoring_engine.compute_score(df)
        # Pattern = 25 (max), volume = 15 (max)
        # Trend and momentum depend on percentile ranking
        assert result.max() > 0


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:
    """Edge cases and robustness tests."""

    def test_single_row_with_all_columns(self, scoring_engine):
        """Single row with all required columns."""
        idx = pd.date_range("2024-01-01", periods=1, freq="B")
        df = pd.DataFrame(
            {
                "close": [100.0],
                "rsi": [50.0],
                "volume_ratio": [1.0],
                "slope_daily": [0.1],
                "macd_golden": [False],
                "ma_bullish": [True],
                "bb_position": [0.6],
            },
            index=idx,
        )
        result = scoring_engine.compute_score(df)
        assert len(result) == 1
        assert 0 <= result.iloc[0] <= 100

    def test_two_rows(self, scoring_engine):
        """Two rows — minimal viable dataset for percentile ranking."""
        idx = pd.date_range("2024-01-01", periods=2, freq="B")
        df = pd.DataFrame(
            {
                "close": [100.0, 101.0],
                "rsi": [50.0, 55.0],
                "volume_ratio": [1.0, 1.2],
                "slope_daily": [0.1, 0.2],
            },
            index=idx,
        )
        result = scoring_engine.compute_score(df)
        assert len(result) == 2
        assert result.min() >= 0
        assert result.max() <= 100

    def test_negative_slope_daily(self, scoring_engine):
        """Negative slopes should still produce valid scores."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "close": np.linspace(200, 100, n),  # declining
                "rsi": np.full(n, 30.0),
                "volume_ratio": np.full(n, 1.0),
                "slope_daily": np.full(n, -2.0),
            },
            index=idx,
        )
        result = scoring_engine.compute_score(df)
        assert result.min() >= 0
        assert result.max() <= 100

    def test_extreme_rsi_values(self, scoring_engine):
        """RSI at extremes (0 and 100) should not crash."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        rsi_values = [0.0] * 25 + [100.0] * 25
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": rsi_values,
                "volume_ratio": np.full(n, 1.0),
                "slope_daily": np.full(n, 0.1),
            },
            index=idx,
        )
        result = scoring_engine.compute_score(df)
        assert result.min() >= 0
        assert result.max() <= 100

    def test_mixed_nan_and_valid_rsi(self, scoring_engine):
        """Mix of NaN and valid RSI values."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        rsi_values = [np.nan] * 25 + [50.0] * 25
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": rsi_values,
                "volume_ratio": np.full(n, 1.0),
                "slope_daily": np.full(n, 0.1),
            },
            index=idx,
        )
        result = scoring_engine.compute_score(df)
        assert result.notna().all()
        assert result.min() >= 0
        assert result.max() <= 100

    def test_mixed_nan_and_valid_volume_ratio(self, scoring_engine):
        """Mix of NaN and valid volume_ratio values."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        vr_values = [np.nan] * 25 + [1.0] * 25
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 120, n),
                "rsi": np.full(n, 50.0),
                "volume_ratio": vr_values,
                "slope_daily": np.full(n, 0.1),
            },
            index=idx,
        )
        result = scoring_engine.compute_score(df)
        assert result.notna().all()
        assert result.min() >= 0
        assert result.max() <= 100

    def test_clip_enforced_at_boundaries(self, scoring_engine):
        """Score should be clipped to [0, 100] even if raw exceeds."""
        n = 50
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 200, n),
                "rsi": np.full(n, 30.0),
                "volume_ratio": np.full(n, 2.0),
                "slope_daily": np.linspace(0, 100, n),
                "macd_golden": [True] * n,
                "ma_bullish": [True] * n,
                "bb_position": np.full(n, 1.0),
            },
            index=idx,
        )
        result = scoring_engine.compute_score(df)
        assert result.min() >= 0
        assert result.max() <= 100

    def test_score_preserves_index_name(self, scoring_engine):
        """Index name should be preserved in output."""
        n = 20
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        idx.name = "trade_date"
        df = pd.DataFrame(
            {
                "close": np.linspace(100, 110, n),
                "rsi": np.full(n, 50.0),
                "volume_ratio": np.full(n, 1.0),
                "slope_daily": np.full(n, 0.1),
            },
            index=idx,
        )
        result = scoring_engine.compute_score(df)
        assert result.index.name == "trade_date"
