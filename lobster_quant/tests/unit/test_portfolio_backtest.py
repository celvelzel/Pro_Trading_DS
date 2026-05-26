"""
Tests for PortfolioBacktest - multi-stock portfolio backtest engine.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.core.portfolio_backtest import PortfolioBacktest, EquityPoint
from src.data.models import (
    BacktestMetrics,
    BacktestResult,
    Strategy,
    StrategyParams,
    Trade,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_strategy():
    """Create a sample Strategy for testing."""
    return Strategy(
        id="test_portfolio_strategy",
        name="Portfolio Test Strategy",
        description="Strategy for portfolio backtest tests",
        params=StrategyParams(
            holdingDays=15,
            minScore=55,
            slippagePct=0.002,
            commissionPct=0.001,
            positionSizing="fixed",
            positionSize=0.1,
            initialCapital=100000,
            maxPositions=5,
        ),
        logic="default",
        isPreset=False,
        createdAt=datetime(2023, 1, 1),
    )


@pytest.fixture
def sample_trades_a():
    """Sample trades for stock A."""
    return [
        Trade(
            symbol="AAA",
            buy_date=datetime(2023, 1, 1),
            buy_price=100.0,
            sell_date=datetime(2023, 1, 20),
            sell_price=110.0,
            return_pct=0.10,
            holding_days=15,
        ),
        Trade(
            symbol="AAA",
            buy_date=datetime(2023, 2, 1),
            buy_price=110.0,
            sell_date=datetime(2023, 2, 20),
            sell_price=105.0,
            return_pct=-0.045,
            holding_days=15,
        ),
    ]


@pytest.fixture
def sample_trades_b():
    """Sample trades for stock B."""
    return [
        Trade(
            symbol="BBB",
            buy_date=datetime(2023, 1, 5),
            buy_price=200.0,
            sell_date=datetime(2023, 1, 25),
            sell_price=220.0,
            return_pct=0.10,
            holding_days=15,
        ),
    ]


@pytest.fixture
def backtest_result_a(sample_trades_a):
    """BacktestResult for stock A."""
    return BacktestResult(
        symbol="AAA",
        trades=sample_trades_a,
        win_rate=0.5,
        avg_return=0.0275,
        profit_factor=2.2,
        max_drawdown=0.045,
        cumulative_return=0.05,
        best_trade=0.10,
        worst_trade=-0.045,
        sharpe_ratio=1.5,
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 2, 20),
    )


@pytest.fixture
def backtest_result_b(sample_trades_b):
    """BacktestResult for stock B."""
    return BacktestResult(
        symbol="BBB",
        trades=sample_trades_b,
        win_rate=1.0,
        avg_return=0.10,
        profit_factor=float("inf"),
        max_drawdown=0.0,
        cumulative_return=0.10,
        best_trade=0.10,
        worst_trade=0.10,
        sharpe_ratio=2.0,
        start_date=datetime(2023, 1, 5),
        end_date=datetime(2023, 1, 25),
    )


@pytest.fixture
def sample_ohlcv_df():
    """Generate a sample OHLCV DataFrame with indicators."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(np.random.normal(0.001, 0.02, n)) * 100
    high = close * (1 + np.abs(np.random.normal(0, 0.01, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, n)))
    open_ = close * (1 + np.random.normal(0, 0.005, n))
    volume = np.random.randint(1_000_000, 10_000_000, n)

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
    # Add required indicator columns
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma20_slope"] = df["ma20"].diff()
    return df


# ---------------------------------------------------------------------------
# Unit tests – construction
# ---------------------------------------------------------------------------


class TestPortfolioBacktestInit:
    """Tests for PortfolioBacktest construction."""

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_init_creates_engines(self, mock_bt, mock_data, mock_ind):
        pb = PortfolioBacktest()
        mock_bt.assert_called_once()
        mock_data.assert_called_once()
        mock_ind.assert_called_once()
        assert pb.backtest_engine is mock_bt.return_value
        assert pb.data_engine is mock_data.return_value
        assert pb.indicator_engine is mock_ind.return_value


# ---------------------------------------------------------------------------
# Unit tests – run()
# ---------------------------------------------------------------------------


class TestPortfolioBacktestRun:
    """Tests for the run() method."""

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_run_empty_symbols(self, mock_bt_cls, mock_data_cls, mock_ind_cls, sample_strategy):
        """Running with no symbols returns an empty BacktestResult."""
        pb = PortfolioBacktest()
        result = pb.run([], sample_strategy)

        assert isinstance(result, BacktestResult)
        assert result.symbol == ""
        assert result.trades == []

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_run_single_stock(
        self,
        mock_bt_cls,
        mock_data_cls,
        mock_ind_cls,
        sample_strategy,
        backtest_result_a,
        sample_ohlcv_df,
    ):
        """Running with a single stock delegates to BacktestEngine."""
        mock_data_engine = MagicMock()
        mock_ind_engine = MagicMock()
        mock_bt_engine = MagicMock()

        mock_data_cls.return_value = mock_data_engine
        mock_ind_cls.return_value = mock_ind_engine
        mock_bt_cls.return_value = mock_bt_engine

        # Mock data fetch
        stock_data = MagicMock()
        stock_data.daily = sample_ohlcv_df
        mock_data_engine.fetch_stock.return_value = stock_data

        # Mock indicator computation
        mock_ind_engine.compute_all.return_value = sample_ohlcv_df

        # Mock backtest result
        mock_bt_engine.run_with_strategy.return_value = backtest_result_a

        pb = PortfolioBacktest()
        result = pb.run(["AAA"], sample_strategy)

        mock_data_engine.fetch_stock.assert_called_once_with("AAA")
        mock_ind_engine.compute_all.assert_called_once()
        mock_bt_engine.run_with_strategy.assert_called_once()
        assert "AAA" in result.symbol
        assert len(result.trades) == 2

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_run_multiple_stocks(
        self,
        mock_bt_cls,
        mock_data_cls,
        mock_ind_cls,
        sample_strategy,
        backtest_result_a,
        backtest_result_b,
        sample_ohlcv_df,
    ):
        """Running with multiple stocks aggregates results."""
        mock_data_engine = MagicMock()
        mock_ind_engine = MagicMock()
        mock_bt_engine = MagicMock()

        mock_data_cls.return_value = mock_data_engine
        mock_ind_cls.return_value = mock_ind_engine
        mock_bt_cls.return_value = mock_bt_engine

        stock_data = MagicMock()
        stock_data.daily = sample_ohlcv_df
        mock_data_engine.fetch_stock.return_value = stock_data

        mock_ind_engine.compute_all.return_value = sample_ohlcv_df

        mock_bt_engine.run_with_strategy.side_effect = [
            backtest_result_a,
            backtest_result_b,
        ]

        pb = PortfolioBacktest()
        result = pb.run(["AAA", "BBB"], sample_strategy)

        assert mock_data_engine.fetch_stock.call_count == 2
        assert "AAA" in result.symbol
        assert "BBB" in result.symbol
        # 2 trades from A + 1 trade from B = 3
        assert len(result.trades) == 3

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_run_skips_failed_stock(
        self,
        mock_bt_cls,
        mock_data_cls,
        mock_ind_cls,
        sample_strategy,
        backtest_result_b,
        sample_ohlcv_df,
    ):
        """Stocks that fail are skipped; successful ones still contribute."""
        mock_data_engine = MagicMock()
        mock_ind_engine = MagicMock()
        mock_bt_engine = MagicMock()

        mock_data_cls.return_value = mock_data_engine
        mock_ind_cls.return_value = mock_ind_engine
        mock_bt_cls.return_value = mock_bt_engine

        stock_data = MagicMock()
        stock_data.daily = sample_ohlcv_df

        # First call fails, second succeeds
        mock_data_engine.fetch_stock.side_effect = [None, stock_data]
        mock_ind_engine.compute_all.return_value = sample_ohlcv_df
        mock_bt_engine.run_with_strategy.return_value = backtest_result_b

        pb = PortfolioBacktest()
        result = pb.run(["FAIL", "BBB"], sample_strategy)

        assert "BBB" in result.symbol
        assert len(result.trades) == 1

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_run_applies_date_filter(
        self,
        mock_bt_cls,
        mock_data_cls,
        mock_ind_cls,
        sample_strategy,
        backtest_result_a,
        sample_ohlcv_df,
    ):
        """start_date and end_date filter the DataFrame before backtest."""
        mock_data_engine = MagicMock()
        mock_ind_engine = MagicMock()
        mock_bt_engine = MagicMock()

        mock_data_cls.return_value = mock_data_engine
        mock_ind_cls.return_value = mock_ind_engine
        mock_bt_cls.return_value = mock_bt_engine

        stock_data = MagicMock()
        stock_data.daily = sample_ohlcv_df
        mock_data_engine.fetch_stock.return_value = stock_data
        mock_ind_engine.compute_all.return_value = sample_ohlcv_df
        mock_bt_engine.run_with_strategy.return_value = backtest_result_a

        pb = PortfolioBacktest()
        pb.run(
            ["AAA"],
            sample_strategy,
            start_date="2023-03-01",
            end_date="2023-06-01",
        )

        # Verify the DataFrame passed to run_with_strategy was filtered
        call_args = mock_bt_engine.run_with_strategy.call_args
        passed_df = call_args[0][0]
        assert passed_df.index.min() >= pd.Timestamp("2023-03-01")
        assert passed_df.index.max() <= pd.Timestamp("2023-06-01")


# ---------------------------------------------------------------------------
# Unit tests – _aggregate_equity_curves
# ---------------------------------------------------------------------------


class TestAggregateEquityCurves:
    """Tests for equity curve aggregation."""

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_empty_curves(self, mock_bt, mock_data, mock_ind):
        pb = PortfolioBacktest()
        assert pb._aggregate_equity_curves([]) == []

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_single_curve(self, mock_bt, mock_data, mock_ind):
        pb = PortfolioBacktest()
        curve = [1.0, 1.05, 1.10]
        result = pb._aggregate_equity_curves([curve])
        assert result == [1.0, 1.05, 1.10]

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_two_curves_average(self, mock_bt, mock_data, mock_ind):
        pb = PortfolioBacktest()
        c1 = [1.0, 1.10, 1.20]
        c2 = [1.0, 0.90, 0.95]
        result = pb._aggregate_equity_curves([c1, c2])
        assert len(result) == 3
        assert result[0] == pytest.approx(1.0)
        assert result[1] == pytest.approx(1.0)
        assert result[2] == pytest.approx(1.075)

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_different_length_curves(self, mock_bt, mock_data, mock_ind):
        """Curves of different lengths are padded by averaging available values."""
        pb = PortfolioBacktest()
        c1 = [1.0, 1.10, 1.20, 1.30]
        c2 = [1.0, 0.90]
        result = pb._aggregate_equity_curves([c1, c2])

        assert len(result) == 4
        # Index 0: avg(1.0, 1.0) = 1.0
        assert result[0] == pytest.approx(1.0)
        # Index 1: avg(1.10, 0.90) = 1.0
        assert result[1] == pytest.approx(1.0)
        # Index 2: only c1 contributes
        assert result[2] == pytest.approx(1.20)
        # Index 3: only c1 contributes
        assert result[3] == pytest.approx(1.30)


# ---------------------------------------------------------------------------
# Unit tests – _calculate_portfolio_metrics
# ---------------------------------------------------------------------------


class TestCalculatePortfolioMetrics:
    """Tests for portfolio-level metrics calculation."""

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_no_trades(self, mock_bt, mock_data, mock_ind):
        pb = PortfolioBacktest()
        metrics = pb._calculate_portfolio_metrics([], [])

        assert isinstance(metrics, BacktestMetrics)
        assert metrics.totalTrades == 0
        assert metrics.winRate == 0
        assert metrics.totalReturn == 0

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_with_trades_and_curve(self, mock_bt, mock_data, mock_ind):
        pb = PortfolioBacktest()
        trades = [
            Trade(
                symbol="X",
                buy_date=datetime(2023, 1, 1),
                buy_price=100.0,
                sell_date=datetime(2023, 1, 20),
                sell_price=110.0,
                return_pct=0.10,
                holding_days=15,
            ),
            Trade(
                symbol="X",
                buy_date=datetime(2023, 2, 1),
                buy_price=110.0,
                sell_date=datetime(2023, 2, 20),
                sell_price=105.0,
                return_pct=-0.045,
                holding_days=15,
            ),
            Trade(
                symbol="Y",
                buy_date=datetime(2023, 1, 5),
                buy_price=200.0,
                sell_date=datetime(2023, 1, 25),
                sell_price=220.0,
                return_pct=0.10,
                holding_days=15,
            ),
        ]
        curve = [1.0, 1.10, 1.05, 1.15]

        metrics = pb._calculate_portfolio_metrics(trades, curve)

        assert metrics.totalTrades == 3
        assert metrics.winningTrades == 2
        assert metrics.losingTrades == 1
        assert metrics.winRate == pytest.approx(66.67, abs=0.01)
        assert metrics.avgHoldingDays == 15.0
        assert metrics.totalReturn > 0
        assert metrics.maxDrawdown > 0

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_all_winning_trades(self, mock_bt, mock_data, mock_ind):
        pb = PortfolioBacktest()
        trades = [
            Trade(
                symbol="W",
                buy_date=datetime(2023, 1, 1),
                buy_price=100.0,
                sell_date=datetime(2023, 1, 20),
                sell_price=110.0,
                return_pct=0.10,
                holding_days=15,
            ),
        ]
        curve = [1.0, 1.10]

        metrics = pb._calculate_portfolio_metrics(trades, curve)

        assert metrics.winRate == 100.0
        assert metrics.winningTrades == 1
        assert metrics.losingTrades == 0
        assert metrics.avgWin == pytest.approx(0.10, abs=0.01)
        assert metrics.avgLoss == 0

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_trades_without_equity_curve(self, mock_bt, mock_data, mock_ind):
        """Metrics degrade gracefully when equity curve is empty."""
        pb = PortfolioBacktest()
        trades = [
            Trade(
                symbol="Z",
                buy_date=datetime(2023, 1, 1),
                buy_price=100.0,
                sell_date=datetime(2023, 1, 20),
                sell_price=110.0,
                return_pct=0.10,
                holding_days=15,
            ),
        ]

        metrics = pb._calculate_portfolio_metrics(trades, [])

        assert metrics.totalTrades == 1
        assert metrics.winRate == 100.0
        assert metrics.totalReturn == 0  # no curve → no return calc
        assert metrics.volatility == 0


# ---------------------------------------------------------------------------
# Unit tests – _aggregate_results
# ---------------------------------------------------------------------------


class TestAggregateResults:
    """Tests for the _aggregate_results helper."""

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_empty_results(self, mock_bt, mock_data, mock_ind, sample_strategy):
        pb = PortfolioBacktest()
        result = pb._aggregate_results([], sample_strategy, ["A", "B"])

        assert result.symbol == "A, B"
        assert result.trades == []

    @patch("src.core.portfolio_backtest.get_indicator_engine")
    @patch("src.core.portfolio_backtest.get_data_engine")
    @patch("src.core.portfolio_backtest.BacktestEngine")
    def test_aggregates_dates(self, mock_bt, mock_data, mock_ind, sample_strategy):
        pb = PortfolioBacktest()
        r1 = BacktestResult(
            symbol="A",
            trades=[],
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 6, 1),
        )
        r2 = BacktestResult(
            symbol="B",
            trades=[],
            start_date=datetime(2023, 3, 1),
            end_date=datetime(2023, 12, 1),
        )

        result = pb._aggregate_results([r1, r2], sample_strategy, ["A", "B"])

        assert result.start_date == datetime(2023, 1, 1)
        assert result.end_date == datetime(2023, 12, 1)


# ---------------------------------------------------------------------------
# EquityPoint dataclass
# ---------------------------------------------------------------------------


class TestEquityPoint:
    """Tests for the EquityPoint dataclass."""

    def test_creation(self):
        ep = EquityPoint(date="2023-01-01", equity=100.0)
        assert ep.date == "2023-01-01"
        assert ep.equity == 100.0

    def test_equality(self):
        ep1 = EquityPoint(date="2023-01-01", equity=100.0)
        ep2 = EquityPoint(date="2023-01-01", equity=100.0)
        assert ep1 == ep2
