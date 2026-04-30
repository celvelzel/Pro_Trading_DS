"""
Tests for ScoringEngine.
"""

import pytest
import pandas as pd
import numpy as np
from src.core.scoring_engine import ScoringEngine, get_scoring_engine
from src.utils.exceptions import ScoringError


@pytest.fixture
def scoring_engine():
    return ScoringEngine()


class TestScoringEngine:
    def test_compute_score_returns_series(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine.compute_score(sample_ohlcv_df_with_indicators)
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv_df_with_indicators)

    def test_score_range_0_100(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine.compute_score(sample_ohlcv_df_with_indicators)
        assert result.min() >= 0
        assert result.max() <= 100

    def test_score_with_missing_columns_raises(self, scoring_engine):
        df = pd.DataFrame({'close': [100, 101, 102]})
        with pytest.raises(ScoringError):
            scoring_engine.compute_score(df)

    def test_score_with_slope_wm(self, scoring_engine, sample_ohlcv_df_with_indicators):
        df = sample_ohlcv_df_with_indicators.copy()
        df['slope_weekly'] = df['slope_daily'] * 0.5
        df['slope_monthly'] = df['slope_daily'] * 0.3
        slope_wm = df[['slope_weekly', 'slope_monthly']]
        result = scoring_engine.compute_score(df, slope_wm=slope_wm)
        assert isinstance(result, pd.Series)

    def test_trend_score_range(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine._calc_trend_score(sample_ohlcv_df_with_indicators)
        assert result.min() >= 0
        assert result.max() <= 40

    def test_momentum_score_range(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine._calc_momentum_score(sample_ohlcv_df_with_indicators)
        assert result.min() >= 0
        assert result.max() <= 40

    def test_volume_score_range(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine._calc_volume_score(sample_ohlcv_df_with_indicators)
        assert result.min() >= 0
        assert result.max() <= 15

    def test_pattern_score_range(self, scoring_engine, sample_ohlcv_df_with_indicators):
        result = scoring_engine._calc_pattern_score(sample_ohlcv_df_with_indicators)
        assert result.min() >= 0
        assert result.max() <= 25


class TestGetScoringEngine:
    def test_returns_instance(self):
        engine = get_scoring_engine()
        assert isinstance(engine, ScoringEngine)

    def test_singleton(self):
        e1 = get_scoring_engine()
        e2 = get_scoring_engine()
        assert e1 is e2
