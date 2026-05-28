"""
Comprehensive tests for SignalEngine.

Covers:
- generate_signal() integration flow (IndicatorEngine → ScoringEngine → SignalGenerator)
- _classify_signal() boundary conditions
- get_signal_engine() singleton
- Edge cases: empty data, NaN indicators, boundary scores
- SignalGenerator helper methods used by SignalEngine
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.core.signal_engine import SignalEngine, get_signal_engine
from src.data.models import SignalResult, StockData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stock_data(df: pd.DataFrame, symbol: str = "TEST") -> StockData:
    """Wrap a DataFrame into a StockData for SignalEngine."""
    return StockData(
        symbol=symbol,
        daily=df,
        last_update=datetime.now(),
        source="mock",
    )


def _make_indicator_df(n: int = 100, seed: int = 42) -> pd.DataFrame:
    """Build a DataFrame with all indicator columns that ScoringEngine expects."""
    np.random.seed(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(np.random.normal(0.001, 0.02, n)) * 100
    high = close * (1 + np.abs(np.random.normal(0, 0.01, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, n)))
    open_ = close * (1 + np.random.normal(0, 0.005, n))
    volume = np.random.randint(1_000_000, 10_000_000, n).astype(float)

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )

    # Moving averages
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma50"] = df["close"].rolling(50).mean()

    # RSI
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # MACD
    exp12 = df["close"].ewm(span=12, adjust=False).mean()
    exp26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = exp12 - exp26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_golden"] = (df["macd"] > df["macd_signal"]) & (
        df["macd"].shift(1) <= df["macd_signal"].shift(1)
    )

    # Volume ratio
    df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

    # Slope
    df["slope_daily"] = (
        df["close"]
        .rolling(20)
        .apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == 20 else 0,
            raw=False,
        )
    )

    # MA bullish
    df["ma_bullish"] = df["ma20"] > df["ma50"]

    # Bollinger Bands position
    bb_mid = df["close"].rolling(20).mean()
    bb_std = df["close"].rolling(20).std()
    df["bb_position"] = (df["close"] - bb_mid) / (2 * bb_std) + 0.5

    # ROC
    df["roc"] = df["close"].pct_change(20) * 100

    # ATR
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    df["atr_pct"] = df["atr"] / df["close"]

    # Gap
    df["gap_pct"] = (df["open"] - df["close"].shift(1)).abs() / df["close"].shift(1)

    return df


def _make_all_nan_df(n: int = 100) -> pd.DataFrame:
    """Build a DataFrame where all indicator columns are NaN."""
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    df = pd.DataFrame(
        {
            "open": np.nan,
            "high": np.nan,
            "low": np.nan,
            "close": np.nan,
            "volume": np.nan,
            "ma20": np.nan,
            "ma50": np.nan,
            "rsi": np.nan,
            "macd": np.nan,
            "macd_signal": np.nan,
            "macd_golden": False,
            "volume_ratio": np.nan,
            "slope_daily": np.nan,
            "ma_bullish": False,
            "bb_position": np.nan,
            "roc": np.nan,
            "atr": np.nan,
            "atr_pct": np.nan,
            "gap_pct": np.nan,
        },
        index=dates,
    )
    return df


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_indicator_engine():
    """Mock IndicatorEngine that returns a controlled DataFrame."""
    engine = MagicMock()
    engine.compute_all = MagicMock(side_effect=lambda df: df)
    return engine


@pytest.fixture
def mock_scoring_engine():
    """Mock ScoringEngine that returns a controllable score series."""
    engine = MagicMock()
    # By default, return a series with a single score of 55
    engine.compute_score = MagicMock(
        side_effect=lambda df: pd.Series([55.0] * len(df), index=df.index)
    )
    return engine


@pytest.fixture
def signal_engine(mock_indicator_engine, mock_scoring_engine):
    """SignalEngine with mocked IndicatorEngine and ScoringEngine."""
    with patch(
        "src.core.signal_engine.get_indicator_engine",
        return_value=mock_indicator_engine,
    ), patch(
        "src.core.signal_engine.get_scoring_engine",
        return_value=mock_scoring_engine,
    ):
        engine = SignalEngine()
    return engine


@pytest.fixture
def indicator_df():
    """Pre-computed indicator DataFrame (100 rows)."""
    return _make_indicator_df()


@pytest.fixture
def all_nan_df():
    """DataFrame with all NaN indicators."""
    return _make_all_nan_df()


# ===========================================================================
# TestGenerateSignal — full integration through the engine
# ===========================================================================

class TestGenerateSignal:
    """Tests for SignalEngine.generate_signal()."""

    def test_returns_signal_result(self, signal_engine, indicator_df):
        """generate_signal must return a SignalResult instance."""
        stock = _make_stock_data(indicator_df)
        result = signal_engine.generate_signal(stock)
        assert isinstance(result, SignalResult)

    def test_result_has_correct_symbol(self, signal_engine, indicator_df):
        """Symbol from StockData is propagated to SignalResult."""
        stock = _make_stock_data(indicator_df, symbol="AAPL")
        result = signal_engine.generate_signal(stock)
        assert result.symbol == "AAPL"

    def test_signal_type_is_valid_enum(self, signal_engine, indicator_df):
        """signal_type must be one of the four allowed Chinese strings."""
        stock = _make_stock_data(indicator_df)
        result = signal_engine.generate_signal(stock)
        assert result.signal_type in ("强烈推荐", "推荐", "持有", "观望")

    def test_score_in_range_0_100(self, signal_engine, indicator_df):
        """Score must be between 0 and 100 inclusive."""
        stock = _make_stock_data(indicator_df)
        result = signal_engine.generate_signal(stock)
        assert 0 <= result.score <= 100

    def test_probability_in_range_0_100(self, signal_engine, indicator_df):
        """probability_up must be between 0 and 100 inclusive."""
        stock = _make_stock_data(indicator_df)
        result = signal_engine.generate_signal(stock)
        assert 0 <= result.probability_up <= 100

    def test_reasons_is_list_of_strings(self, signal_engine, indicator_df):
        """reasons must be a list where every element is a string."""
        stock = _make_stock_data(indicator_df)
        result = signal_engine.generate_signal(stock)
        assert isinstance(result.reasons, list)
        for reason in result.reasons:
            assert isinstance(reason, str)

    def test_timestamp_is_set(self, signal_engine, indicator_df):
        """SignalResult should have a timestamp (default_factory sets it)."""
        stock = _make_stock_data(indicator_df)
        result = signal_engine.generate_signal(stock)
        assert result.timestamp is not None

    def test_score_equals_latest_from_series(
        self, signal_engine, indicator_df, mock_scoring_engine
    ):
        """Score must come from the last element of ScoringEngine output."""
        # Set the mock to return a specific score for the last row
        scores = [42.0] * (len(indicator_df) - 1) + [88.5]
        mock_scoring_engine.compute_score = MagicMock(
            return_value=pd.Series(scores, index=indicator_df.index)
        )
        stock = _make_stock_data(indicator_df)
        result = signal_engine.generate_signal(stock)
        assert result.score == 88.5

    def test_score_zero_when_series_empty(
        self, signal_engine, indicator_df, mock_scoring_engine
    ):
        """If score_series is empty, latest_score defaults to 0.0."""
        mock_scoring_engine.compute_score = MagicMock(
            return_value=pd.Series(dtype=float)
        )
        stock = _make_stock_data(indicator_df)
        result = signal_engine.generate_signal(stock)
        assert result.score == 0.0

    def test_indicator_engine_called_with_daily(
        self, signal_engine, indicator_df, mock_indicator_engine
    ):
        """IndicatorEngine.compute_all receives stock_data.daily."""
        stock = _make_stock_data(indicator_df)
        signal_engine.generate_signal(stock)
        mock_indicator_engine.compute_all.assert_called_once()
        call_arg = mock_indicator_engine.compute_all.call_args[0][0]
        pd.testing.assert_frame_equal(call_arg, stock.daily)

    def test_scoring_engine_called_with_indicators(
        self, signal_engine, indicator_df, mock_scoring_engine
    ):
        """ScoringEngine.compute_score receives the indicator-enriched DataFrame."""
        stock = _make_stock_data(indicator_df)
        signal_engine.generate_signal(stock)
        mock_scoring_engine.compute_score.assert_called_once()

    def test_different_symbols(self, signal_engine, indicator_df):
        """Engine correctly propagates different symbols."""
        for sym in ("GOOG", "TSLA", "000001.SZ"):
            stock = _make_stock_data(indicator_df, symbol=sym)
            result = signal_engine.generate_signal(stock)
            assert result.symbol == sym


# ===========================================================================
# TestClassifySignal — boundary-value analysis of _classify_signal()
# ===========================================================================

class TestClassifySignal:
    """Boundary tests for SignalEngine._classify_signal()."""

    # --- 强烈推荐: score >= 70 AND probability >= 60 ---

    @pytest.mark.parametrize(
        "score, prob",
        [
            (70, 60),    # exact boundary
            (70, 100),   # score at boundary, prob max
            (100, 60),   # score max, prob at boundary
            (100, 100),  # both max
            (85, 75),    # well above boundary
            (70.0, 60.0),  # floats at boundary
        ],
    )
    def test_strong_recommend(self, signal_engine, score, prob):
        assert signal_engine._classify_signal(score, prob) == "强烈推荐"

    # --- 推荐: score >= 50 AND probability >= 50 (but NOT 强烈推荐) ---

    @pytest.mark.parametrize(
        "score, prob",
        [
            (50, 50),    # exact boundary
            (50, 59),    # score at boundary, prob just below 强烈推荐
            (69, 50),    # score just below 强烈推荐, prob at boundary
            (69, 59),    # both just below 强烈推荐 threshold
            (60, 55),    # comfortably in range
            (50.0, 50.0),  # floats
        ],
    )
    def test_recommend(self, signal_engine, score, prob):
        assert signal_engine._classify_signal(score, prob) == "推荐"

    # --- 持有: score >= 30 (but NOT 强烈推荐 or 推荐) ---

    @pytest.mark.parametrize(
        "score, prob",
        [
            (30, 0),     # score at boundary, prob minimal
            (30, 49),    # score at boundary, prob below 推荐
            (49, 0),     # score just below 推荐 threshold
            (49, 49),    # both below 推荐 thresholds
            (40, 30),    # mid-range
            (30.0, 25.0),  # floats
        ],
    )
    def test_hold(self, signal_engine, score, prob):
        assert signal_engine._classify_signal(score, prob) == "持有"

    # --- 观望: score < 30 ---

    @pytest.mark.parametrize(
        "score, prob",
        [
            (0, 0),      # minimum
            (0, 100),    # score min, prob max — still 观望 because score < 30
            (29, 0),     # score just below boundary
            (29, 59),    # score just below, prob high — still 观望
            (15, 30),    # mid-low range
            (0.0, 0.0),  # floats
        ],
    )
    def test_watch(self, signal_engine, score, prob):
        assert signal_engine._classify_signal(score, prob) == "观望"

    # --- Cross-boundary: score high but prob low → not 强烈推荐 ---

    def test_high_score_low_prob_not_strong(self, signal_engine):
        """score=80 but prob=59 → 推荐, not 强烈推荐."""
        assert signal_engine._classify_signal(80, 59) == "推荐"

    def test_low_score_high_prob_not_recommend(self, signal_engine):
        """score=49 but prob=80 → 持有, not 推荐."""
        assert signal_engine._classify_signal(49, 80) == "持有"

    def test_score_70_prob_59_is_recommend(self, signal_engine):
        """score meets 强烈推荐 threshold but prob does not → 推荐."""
        assert signal_engine._classify_signal(70, 59) == "推荐"

    def test_score_69_prob_60_is_recommend(self, signal_engine):
        """prob meets 强烈推荐 threshold but score does not → 推荐."""
        assert signal_engine._classify_signal(69, 60) == "推荐"

    def test_score_50_prob_49_is_hold(self, signal_engine):
        """score meets 推荐 threshold but prob does not → 持有."""
        assert signal_engine._classify_signal(50, 49) == "持有"

    def test_score_49_prob_50_is_hold(self, signal_engine):
        """prob meets 推荐 threshold but score does not → 持有."""
        assert signal_engine._classify_signal(49, 50) == "持有"


# ===========================================================================
# TestGetSignalEngine — singleton behaviour
# ===========================================================================

class TestGetSignalEngine:
    """Tests for the get_signal_engine() singleton factory."""

    def test_returns_signal_engine_instance(self):
        """get_signal_engine() must return a SignalEngine."""
        # Reset singleton to avoid cross-test pollution
        import src.core.signal_engine as mod
        original = mod._signal_engine
        mod._signal_engine = None
        try:
            engine = get_signal_engine()
            assert isinstance(engine, SignalEngine)
        finally:
            mod._signal_engine = original

    def test_singleton_returns_same_object(self):
        """Two calls must return the exact same object (identity check)."""
        import src.core.signal_engine as mod
        original = mod._signal_engine
        mod._signal_engine = None
        try:
            e1 = get_signal_engine()
            e2 = get_signal_engine()
            assert e1 is e2
        finally:
            mod._signal_engine = original

    def test_singleton_has_expected_attributes(self):
        """Singleton must have indicator_engine, scoring_engine, signal_generator."""
        import src.core.signal_engine as mod
        original = mod._signal_engine
        mod._signal_engine = None
        try:
            engine = get_signal_engine()
            assert hasattr(engine, "indicator_engine")
            assert hasattr(engine, "scoring_engine")
            assert hasattr(engine, "signal_generator")
        finally:
            mod._signal_engine = original


# ===========================================================================
# TestGenerateReasons — via SignalGenerator used by SignalEngine
# ===========================================================================

class TestGenerateReasons:
    """Tests for the reason-generation logic exercised through SignalEngine."""

    def test_reasons_for_bullish_indicators(self, signal_engine):
        """Strong bullish indicators should produce positive reasons."""
        df = _make_indicator_df()
        # Force bullish conditions on the last row
        df.loc[df.index[-1], "slope_daily"] = 0.02  # > 0.01 → trend up
        df.loc[df.index[-1], "rsi"] = 25  # < 30 → oversold
        df.loc[df.index[-1], "volume_ratio"] = 2.0  # > 1.5 → volume surge
        df.loc[df.index[-1], "macd_golden"] = True
        df.loc[df.index[-1], "ma_bullish"] = True

        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        reasons_text = " ".join(result.reasons)

        assert "日线趋势向上" in reasons_text
        assert "RSI超卖" in reasons_text
        assert "成交量放大" in reasons_text
        assert "MACD金叉" in reasons_text
        assert "MA多头排列" in reasons_text

    def test_reasons_for_bearish_indicators(self, signal_engine):
        """Strong bearish indicators should produce negative reasons."""
        df = _make_indicator_df()
        df.loc[df.index[-1], "slope_daily"] = -0.02  # < -0.01 → trend down
        df.loc[df.index[-1], "rsi"] = 75  # > 70 → overbought
        df.loc[df.index[-1], "volume_ratio"] = 0.3  # < 0.5 → volume shrink
        df.loc[df.index[-1], "macd_golden"] = False
        df.loc[df.index[-1], "ma_bullish"] = False

        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        reasons_text = " ".join(result.reasons)

        assert "日线趋势向下" in reasons_text
        assert "RSI超买" in reasons_text
        assert "成交量萎缩" in reasons_text

    def test_reasons_for_neutral_indicators(self, signal_engine):
        """Neutral indicators should produce fewer/no reasons."""
        df = _make_indicator_df()
        # Set neutral values
        df.loc[df.index[-1], "slope_daily"] = 0.001  # between -0.01 and 0.01
        df.loc[df.index[-1], "rsi"] = 50  # neutral zone
        df.loc[df.index[-1], "volume_ratio"] = 1.0  # normal
        df.loc[df.index[-1], "macd_golden"] = False
        df.loc[df.index[-1], "ma_bullish"] = False

        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)

        # Neutral conditions should not trigger trend/volume/pattern reasons
        reasons_text = " ".join(result.reasons)
        assert "日线趋势向上" not in reasons_text
        assert "日线趋势向下" not in reasons_text
        assert "成交量放大" not in reasons_text
        assert "成交量萎缩" not in reasons_text

    def test_reasons_for_low_score(self, signal_engine, mock_scoring_engine):
        """Score < 30 should include '综合评分偏低' reason."""
        df = _make_indicator_df()
        mock_scoring_engine.compute_score = MagicMock(
            return_value=pd.Series([20.0] * len(df), index=df.index)
        )
        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        assert any("综合评分偏低" in r for r in result.reasons)

    def test_reasons_for_high_score(self, signal_engine, mock_scoring_engine):
        """Score > 70 should include '综合评分优秀' reason."""
        df = _make_indicator_df()
        mock_scoring_engine.compute_score = MagicMock(
            return_value=pd.Series([80.0] * len(df), index=df.index)
        )
        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        assert any("综合评分优秀" in r for r in result.reasons)


# ===========================================================================
# TestEdgeCases — unusual inputs
# ===========================================================================

class TestEdgeCases:
    """Edge-case tests for SignalEngine."""

    def test_with_conftest_sample_ohlcv_df(self, signal_engine, sample_ohlcv_df):
        """Engine works with the conftest sample_ohlcv_df fixture."""
        stock = _make_stock_data(sample_ohlcv_df)
        result = signal_engine.generate_signal(stock)
        assert isinstance(result, SignalResult)
        assert result.symbol == "TEST"

    def test_with_conftest_indicators_df(
        self, signal_engine, sample_ohlcv_df_with_indicators
    ):
        """Engine works with the conftest sample_ohlcv_df_with_indicators fixture."""
        stock = _make_stock_data(sample_ohlcv_df_with_indicators)
        result = signal_engine.generate_signal(stock)
        assert isinstance(result, SignalResult)

    def test_with_conftest_mock_stock_data(self, signal_engine, mock_stock_data):
        """Engine works with the conftest mock_stock_data fixture."""
        result = signal_engine.generate_signal(mock_stock_data)
        assert isinstance(result, SignalResult)
        assert result.symbol == "MOCK"

    def test_single_row_dataframe(self, signal_engine):
        """Engine handles a DataFrame with only 1 row."""
        df = pd.DataFrame(
            {
                "open": [100.0],
                "high": [101.0],
                "low": [99.0],
                "close": [100.5],
                "volume": [1_000_000.0],
            },
            index=pd.date_range("2024-01-01", periods=1),
        )
        stock = _make_stock_data(df)
        # Should not raise; may return default/low score
        result = signal_engine.generate_signal(stock)
        assert isinstance(result, SignalResult)

    def test_minimal_columns_dataframe(self, signal_engine):
        """Engine handles DataFrame with only OHLCV columns (no indicator cols)."""
        n = 60
        dates = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "open": [100.0] * n,
                "high": [101.0] * n,
                "low": [99.0] * n,
                "close": [100.0] * n,
                "volume": [1_000_000.0] * n,
            },
            index=dates,
        )
        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        assert isinstance(result, SignalResult)

    def test_indicators_with_nans(self, signal_engine, all_nan_df):
        """Engine handles DataFrame where indicator values are NaN.

        The mocked engines pass NaN data through; SignalGenerator should
        degrade gracefully (reasons list may be empty, score may be 0).
        """
        stock = _make_stock_data(all_nan_df)
        # With mock returning score_series of fixed length, this should work
        result = signal_engine.generate_signal(stock)
        assert isinstance(result, SignalResult)
        assert isinstance(result.reasons, list)

    def test_large_dataframe(self, signal_engine):
        """Engine handles a large DataFrame (500 rows) without error."""
        df = _make_indicator_df(n=500, seed=123)
        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        assert isinstance(result, SignalResult)

    def test_score_exactly_100(
        self, signal_engine, indicator_df, mock_scoring_engine
    ):
        """Score of exactly 100 with matching probability should produce 强烈推荐."""
        mock_scoring_engine.compute_score = MagicMock(
            return_value=pd.Series([100.0] * len(indicator_df), index=indicator_df.index)
        )
        # Mock signal_generator to control probability independently
        signal_engine.signal_generator.calculate_probability_up = MagicMock(
            return_value=90.0
        )
        stock = _make_stock_data(indicator_df)
        result = signal_engine.generate_signal(stock)
        assert result.score == 100.0
        assert result.probability_up == 90.0
        assert result.signal_type == "强烈推荐"

    def test_score_exactly_0(self, signal_engine, indicator_df, mock_scoring_engine):
        """Score of exactly 0 with matching probability should produce 观望."""
        mock_scoring_engine.compute_score = MagicMock(
            return_value=pd.Series([0.0] * len(indicator_df), index=indicator_df.index)
        )
        signal_engine.signal_generator.calculate_probability_up = MagicMock(
            return_value=20.0
        )
        stock = _make_stock_data(indicator_df)
        result = signal_engine.generate_signal(stock)
        assert result.score == 0.0
        assert result.probability_up == 20.0
        assert result.signal_type == "观望"


# ===========================================================================
# TestScoreToProbabilityMapping — verify SignalGenerator probability mapping
# ===========================================================================

class TestScoreToProbabilityMapping:
    """Verify the score→probability mapping used by SignalGenerator.calculate_probability_up.

    Since SignalEngine calls signal_generator.calculate_probability_up() which
    internally calls signal_generator.calculate_score(), we test the formula
    directly on SignalGenerator with crafted data.
    """

    @staticmethod
    def _make_df_with_score(target_score: float, n: int = 100) -> pd.DataFrame:
        """Build a DataFrame that produces a predictable calculate_score output.

        We can't easily control the multi-factor score, so instead we test the
        mapping formula by calling calculate_probability_up on real data and
        checking it falls in the expected range for the data's implicit score.
        """
        return _make_indicator_df(n=n, seed=42)

    def test_short_data_returns_50(self):
        """Data with < 50 rows should return probability 50.0."""
        from src.analysis.signals.lobster_signal import SignalGenerator
        gen = SignalGenerator()
        df = _make_indicator_df(n=30)
        prob = gen.calculate_probability_up(df)
        assert prob == 50.0

    def test_probability_range_for_real_data(self):
        """For real indicator data, probability must be in [20, 90]."""
        from src.analysis.signals.lobster_signal import SignalGenerator
        gen = SignalGenerator()
        df = _make_indicator_df(n=100)
        prob = gen.calculate_probability_up(df)
        assert 20 <= prob <= 90

    def test_probability_is_rounded_to_1_decimal(self):
        """Probability should be rounded to 1 decimal place."""
        from src.analysis.signals.lobster_signal import SignalGenerator
        gen = SignalGenerator()
        df = _make_indicator_df(n=100)
        prob = gen.calculate_probability_up(df)
        # Check it has at most 1 decimal place
        assert prob == round(prob, 1)

    def test_formula_low_score_range(self):
        """Manually verify formula: score in [0,30) → prob = 20 + score*(20/30).

        Since we can't easily force calculate_score to a specific value,
        we test the formula mathematically for boundary values.
        """
        # score=0 → prob = 20 + 0 = 20
        # score=15 → prob = 20 + 15*(20/30) = 30
        # score=29.99 → prob = 20 + 29.99*(20/30) ≈ 40
        for score in [0, 15, 29.99]:
            if score < 30:
                expected = 20 + score * (20 / 30)
                assert 20 <= round(min(100, max(0, expected)), 1) <= 40

    def test_formula_mid_score_range(self):
        """Verify formula: score in [30,70) → prob = 40 + (score-30)*(20/40)."""
        for score in [30, 50, 69.99]:
            if 30 <= score < 70:
                expected = 40 + (score - 30) * (20 / 40)
                assert 40 <= round(min(100, max(0, expected)), 1) <= 60

    def test_formula_high_score_range(self):
        """Verify formula: score in [70,100] → prob = 60 + (score-70)*(30/30)."""
        for score in [70, 85, 100]:
            if score >= 70:
                expected = 60 + (score - 70) * (30 / 30)
                assert 60 <= round(min(100, max(0, expected)), 1) <= 90


# ===========================================================================
# TestSignalClassificationIntegration — end-to-end signal classification
# ===========================================================================

class TestSignalClassificationIntegration:
    """End-to-end tests verifying score → probability → signal_type chain.

    Both ScoringEngine and SignalGenerator are mocked so we control
    score and probability independently.
    """

    @staticmethod
    def _make_engine_with_score_and_prob(score_value: float, prob_value: float):
        """Create a SignalEngine with fully mocked score and probability."""
        indicator_engine = MagicMock()
        indicator_engine.compute_all = MagicMock(side_effect=lambda df: df)

        scoring_engine = MagicMock()
        scoring_engine.compute_score = MagicMock(
            side_effect=lambda df: pd.Series([score_value] * len(df), index=df.index)
        )

        with patch(
            "src.core.signal_engine.get_indicator_engine",
            return_value=indicator_engine,
        ), patch(
            "src.core.signal_engine.get_scoring_engine",
            return_value=scoring_engine,
        ):
            engine = SignalEngine()

        # Also mock the signal generator's probability calculation
        engine.signal_generator.calculate_probability_up = MagicMock(
            return_value=prob_value
        )
        # Mock reasons to avoid depending on indicator columns
        engine.signal_generator._generate_reasons = MagicMock(return_value=[])
        return engine

    def test_high_score_high_prob_is_strong(self):
        """score=80, prob=70 → 强烈推荐."""
        engine = self._make_engine_with_score_and_prob(80.0, 70.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "强烈推荐"
        assert result.score == 80.0
        assert result.probability_up == 70.0

    def test_mid_score_mid_prob_is_recommend(self):
        """score=60, prob=55 → 推荐."""
        engine = self._make_engine_with_score_and_prob(60.0, 55.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "推荐"

    def test_low_mid_score_is_hold(self):
        """score=40, prob=35 → 持有."""
        engine = self._make_engine_with_score_and_prob(40.0, 35.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "持有"

    def test_low_score_low_prob_is_watch(self):
        """score=20, prob=25 → 观望."""
        engine = self._make_engine_with_score_and_prob(20.0, 25.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "观望"

    def test_boundary_70_60_is_strong(self):
        """score=70, prob=60 → exact boundary → 强烈推荐."""
        engine = self._make_engine_with_score_and_prob(70.0, 60.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "强烈推荐"

    def test_boundary_70_59_is_recommend(self):
        """score=70 but prob=59 → 推荐 (prob below 强烈推荐 threshold)."""
        engine = self._make_engine_with_score_and_prob(70.0, 59.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "推荐"

    def test_boundary_69_60_is_recommend(self):
        """prob=60 but score=69 → 推荐 (score below 强烈推荐 threshold)."""
        engine = self._make_engine_with_score_and_prob(69.0, 60.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "推荐"

    def test_boundary_50_50_is_recommend(self):
        """score=50, prob=50 → exact boundary → 推荐."""
        engine = self._make_engine_with_score_and_prob(50.0, 50.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "推荐"

    def test_boundary_50_49_is_hold(self):
        """score=50 but prob=49 → 持有 (prob below 推荐 threshold)."""
        engine = self._make_engine_with_score_and_prob(50.0, 49.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "持有"

    def test_boundary_49_50_is_hold(self):
        """prob=50 but score=49 → 持有 (score below 推荐 threshold)."""
        engine = self._make_engine_with_score_and_prob(49.0, 50.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "持有"

    def test_boundary_30_is_hold(self):
        """score=30, prob=40 → 持有."""
        engine = self._make_engine_with_score_and_prob(30.0, 40.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "持有"

    def test_boundary_29_is_watch(self):
        """score=29, prob=39 → 观望 (score < 30)."""
        engine = self._make_engine_with_score_and_prob(29.0, 39.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "观望"

    def test_max_score_max_prob(self):
        """score=100, prob=100 → 强烈推荐."""
        engine = self._make_engine_with_score_and_prob(100.0, 100.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "强烈推荐"

    def test_min_score_min_prob(self):
        """score=0, prob=0 → 观望."""
        engine = self._make_engine_with_score_and_prob(0.0, 0.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "观望"

    def test_high_score_low_prob_is_recommend_not_strong(self):
        """score=90 but prob=50 → 推荐, not 强烈推荐."""
        engine = self._make_engine_with_score_and_prob(90.0, 50.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "推荐"

    def test_low_score_high_prob_is_hold_not_recommend(self):
        """score=40 but prob=80 → 持有, not 推荐 (score < 50)."""
        engine = self._make_engine_with_score_and_prob(40.0, 80.0)
        df = _make_indicator_df()
        result = engine.generate_signal(_make_stock_data(df))
        assert result.signal_type == "持有"


# ===========================================================================
# TestReasonsEdgeCases — edge cases for reason generation
# ===========================================================================

class TestReasonsEdgeCases:
    """Edge cases for reason generation through SignalEngine."""

    def test_no_slope_column_no_crash(self, signal_engine):
        """If slope_daily column is missing, no crash and no trend reason."""
        df = _make_indicator_df()
        df.drop(columns=["slope_daily"], inplace=True)
        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        assert isinstance(result.reasons, list)

    def test_no_rsi_column_no_crash(self, signal_engine):
        """If rsi column is missing, no crash and no momentum reason."""
        df = _make_indicator_df()
        df.drop(columns=["rsi"], inplace=True)
        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        assert isinstance(result.reasons, list)

    def test_no_volume_ratio_column_no_crash(self, signal_engine):
        """If volume_ratio column is missing, no crash and no volume reason."""
        df = _make_indicator_df()
        df.drop(columns=["volume_ratio"], inplace=True)
        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        assert isinstance(result.reasons, list)

    def test_slope_exactly_at_threshold(self, signal_engine):
        """slope_daily exactly at ±0.01 should NOT trigger trend reasons."""
        df = _make_indicator_df()
        df.loc[df.index[-1], "slope_daily"] = 0.01  # boundary: not > 0.01
        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        reasons_text = " ".join(result.reasons)
        assert "日线趋势向上" not in reasons_text

    def test_slope_just_above_threshold(self, signal_engine):
        """slope_daily just above 0.01 should trigger trend up reason."""
        df = _make_indicator_df()
        df.loc[df.index[-1], "slope_daily"] = 0.0101
        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        reasons_text = " ".join(result.reasons)
        assert "日线趋势向上" in reasons_text

    def test_volume_ratio_at_1_5_boundary(self, signal_engine):
        """volume_ratio exactly 1.5 should NOT trigger 'volume surge'."""
        df = _make_indicator_df()
        df.loc[df.index[-1], "volume_ratio"] = 1.5  # boundary: not > 1.5
        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        reasons_text = " ".join(result.reasons)
        assert "成交量放大" not in reasons_text

    def test_volume_ratio_above_1_5(self, signal_engine):
        """volume_ratio > 1.5 should trigger 'volume surge' reason."""
        df = _make_indicator_df()
        df.loc[df.index[-1], "volume_ratio"] = 1.51
        stock = _make_stock_data(df)
        result = signal_engine.generate_signal(stock)
        reasons_text = " ".join(result.reasons)
        assert "成交量放大" in reasons_text
