"""
Unit tests for lobster_quant.src.analysis.backtest.metrics module.
"""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from src.analysis.backtest.metrics import (
    calculate_max_drawdown,
    calculate_monthly_returns,
    calculate_period_win_rate,
    calculate_profit_loss_ratio,
    calculate_rolling_metrics,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_win_rate,
    calculate_yearly_returns,
)
from src.data.models import Trade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trade(return_pct: float) -> Trade:
    """Create a closed Trade stub with a given return_pct."""
    return Trade(
        symbol="TEST",
        buy_date=datetime(2024, 1, 1),
        buy_price=100.0,
        sell_date=datetime(2024, 1, 10),
        sell_price=100.0 * (1 + return_pct / 100),
        return_pct=return_pct,
    )


# ---------------------------------------------------------------------------
# Existing metrics (smoke)
# ---------------------------------------------------------------------------

class TestSharpeRatio:
    def test_positive_returns(self):
        returns = pd.Series([0.01, 0.02, 0.015, -0.005, 0.01])
        sharpe = calculate_sharpe_ratio(returns)
        assert sharpe > 0

    def test_empty_returns(self):
        assert calculate_sharpe_ratio(pd.Series(dtype=float)) == 0.0

    def test_zero_std(self):
        returns = pd.Series([0.01, 0.01, 0.01])
        assert calculate_sharpe_ratio(returns) == 0.0


class TestSortinoRatio:
    def test_positive_returns(self):
        returns = pd.Series([0.01, 0.02, 0.015, -0.005, 0.01])
        sortino = calculate_sortino_ratio(returns)
        assert sortino > 0

    def test_empty_returns(self):
        assert calculate_sortino_ratio(pd.Series(dtype=float)) == 0.0


class TestMaxDrawdown:
    def test_no_drawdown(self):
        curve = pd.Series([100, 110, 120, 130])
        assert calculate_max_drawdown(curve) == 0.0

    def test_simple_drawdown(self):
        curve = pd.Series([100, 120, 90, 110])
        dd = calculate_max_drawdown(curve)
        assert pytest.approx(dd, abs=1e-6) == 0.25  # 25% drawdown from 120 to 90

    def test_empty(self):
        assert calculate_max_drawdown(pd.Series(dtype=float)) == 0.0


class TestPeriodWinRate:
    def test_all_positive(self):
        returns = pd.Series([0.01, 0.02, 0.03])
        assert calculate_period_win_rate(returns) == 1.0

    def test_mixed(self):
        returns = pd.Series([0.01, -0.02, 0.03])
        assert pytest.approx(calculate_period_win_rate(returns)) == 2 / 3

    def test_empty(self):
        assert calculate_period_win_rate(pd.Series(dtype=float)) == 0.0


# ---------------------------------------------------------------------------
# New metrics – Trade-based
# ---------------------------------------------------------------------------

class TestWinRate:
    def test_all_winners(self):
        trades = [_make_trade(5), _make_trade(10), _make_trade(1)]
        assert calculate_win_rate(trades) == 100.0

    def test_all_losers(self):
        trades = [_make_trade(-5), _make_trade(-10)]
        assert calculate_win_rate(trades) == 0.0

    def test_mixed(self):
        trades = [_make_trade(5), _make_trade(-3), _make_trade(10), _make_trade(-1)]
        assert calculate_win_rate(trades) == 50.0

    def test_empty(self):
        assert calculate_win_rate([]) == 0.0


class TestProfitLossRatio:
    def test_symmetric(self):
        trades = [_make_trade(10), _make_trade(-10)]
        ratio = calculate_profit_loss_ratio(trades)
        assert pytest.approx(ratio, abs=1e-6) == 1.0

    def test_larger_wins(self):
        trades = [_make_trade(20), _make_trade(20), _make_trade(-5)]
        ratio = calculate_profit_loss_ratio(trades)
        # avg_win=20, avg_loss=5 → ratio=4.0
        assert pytest.approx(ratio, abs=1e-6) == 4.0

    def test_no_losses(self):
        trades = [_make_trade(5), _make_trade(10)]
        # avg_loss=0 → ratio=0 (guard against div-by-zero)
        assert calculate_profit_loss_ratio(trades) == 0

    def test_empty(self):
        assert calculate_profit_loss_ratio([]) == 0.0


# ---------------------------------------------------------------------------
# New metrics – Equity-curve decomposition
# ---------------------------------------------------------------------------

class TestMonthlyReturns:
    def test_single_month(self):
        equity = [100.0, 110.0]
        dates = ["2024-01-01", "2024-01-31"]
        result = calculate_monthly_returns(equity, dates)
        assert "2024-01" in result
        assert pytest.approx(result["2024-01"], abs=1e-2) == 10.0

    def test_two_months(self):
        equity = [100.0, 110.0, 121.0]
        dates = ["2024-01-15", "2024-01-31", "2024-02-28"]
        result = calculate_monthly_returns(equity, dates)
        assert "2024-01" in result
        assert "2024-02" in result
        # Jan: (110-100)/100 = 10%
        assert pytest.approx(result["2024-01"], abs=1e-2) == 10.0
        # Feb: last point is start=121, end=121 → 0% (single-point month)
        assert pytest.approx(result["2024-02"], abs=1e-2) == 0.0

    def test_empty(self):
        assert calculate_monthly_returns([], []) == {}

    def test_single_point(self):
        assert calculate_monthly_returns([100], ["2024-01-01"]) == {}


class TestYearlyReturns:
    def test_single_year(self):
        equity = [100.0, 120.0]
        dates = ["2024-01-01", "2024-12-31"]
        result = calculate_yearly_returns(equity, dates)
        assert "2024" in result
        assert pytest.approx(result["2024"], abs=1e-2) == 20.0

    def test_two_years(self):
        equity = [100.0, 120.0, 132.0]
        dates = ["2023-06-01", "2023-12-31", "2024-12-31"]
        result = calculate_yearly_returns(equity, dates)
        assert "2023" in result
        assert "2024" in result
        # 2023: (120-100)/100 = 20%
        assert pytest.approx(result["2023"], abs=1e-2) == 20.0
        # 2024: last point start=132, end=132 → 0% (single-point year)
        assert pytest.approx(result["2024"], abs=1e-2) == 0.0

    def test_empty(self):
        assert calculate_yearly_returns([], []) == {}


# ---------------------------------------------------------------------------
# New metrics – Rolling window
# ---------------------------------------------------------------------------

class TestRollingMetrics:
    def test_returns_keys(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = calculate_rolling_metrics(returns, window=22)
        assert set(result.keys()) == {"rolling_return", "rolling_volatility", "rolling_sharpe"}

    def test_correct_length(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = calculate_rolling_metrics(returns, window=22)
        # Each series should have same length as input (with NaN for initial window)
        for s in result.values():
            assert len(s) == 100

    def test_short_series_returns_empty(self):
        returns = pd.Series([0.01, 0.02])  # shorter than window
        result = calculate_rolling_metrics(returns, window=22)
        for s in result.values():
            assert len(s) == 0

    def test_rolling_volatility_nonnegative(self):
        returns = pd.Series(np.random.default_rng(42).normal(0.001, 0.02, 100))
        result = calculate_rolling_metrics(returns, window=22)
        vol = result["rolling_volatility"].dropna()
        assert (vol >= 0).all()
