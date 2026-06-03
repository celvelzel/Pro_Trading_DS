"""
Lobster Quant - Walk-Forward Validation
Tests strategy parameter stability across rolling train/test windows.

Walk-forward analysis splits historical data into overlapping windows:
  - In-sample (IS): Training period for strategy signal generation
  - Out-of-sample (OOS): Testing period to validate generalization

If a strategy is robust, OOS performance should remain consistent with IS.
Degradation from IS to OOS suggests overfitting.
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from .engine import BacktestEngine
from .metrics import (
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_win_rate,
)
from ...data.models import BacktestResult, Trade
from ...utils.logging import get_logger

logger = get_logger()


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class WindowMetrics:
    """Metrics for a single walk-forward window (IS or OOS)."""

    total_trades: int = 0
    win_rate: float = 0.0
    avg_return: float = 0.0
    cumulative_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    profit_factor: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0


@dataclass
class WalkForwardWindow:
    """Results for a single walk-forward window."""

    window_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    is_metrics: WindowMetrics  # In-sample (training)
    oos_metrics: WindowMetrics  # Out-of-sample (testing)
    degradation: float = 0.0  # (IS_sharpe - OOS_sharpe) / IS_sharpe


@dataclass
class WalkForwardResult:
    """Complete walk-forward analysis result."""

    symbol: str
    train_months: int = 12
    test_months: int = 3
    step_months: int = 3
    total_windows: int = 0
    windows: list[WalkForwardWindow] = field(default_factory=list)

    # Aggregate metrics
    avg_is_sharpe: float = 0.0
    avg_oos_sharpe: float = 0.0
    avg_degradation: float = 0.0
    avg_oos_win_rate: float = 0.0
    avg_oos_return: float = 0.0
    consistency_ratio: float = 0.0  # Fraction of windows with OOS Sharpe > 0


# ============================================================================
# Walk-Forward Engine
# ============================================================================


class WalkForwardEngine:
    """Walk-forward validation engine.

    Splits historical data into rolling windows and compares in-sample
    vs out-of-sample performance to detect overfitting.

    Args:
        train_months: Number of months for the training (IS) period
        test_months: Number of months for the testing (OOS) period
        step_months: Number of months to advance between windows
        min_trades: Minimum trades required per window for valid results
    """

    def __init__(
        self,
        train_months: int = 12,
        test_months: int = 3,
        step_months: int = 3,
        min_trades: int = 2,
    ):
        self.train_months = train_months
        self.test_months = test_months
        self.step_months = step_months
        self.min_trades = min_trades

    def run(
        self,
        data: pd.DataFrame,
        score_series: pd.Series,
        symbol: str = "",
        engine_params: Optional[dict] = None,
    ) -> WalkForwardResult:
        """Run walk-forward analysis on historical data.

        Args:
            data: DataFrame with OHLCV and indicators
            score_series: Score values aligned with data index
            symbol: Stock symbol
            engine_params: Optional dict of BacktestEngine overrides
                (holdingDays, minScore, slippage, commission)

        Returns:
            WalkForwardResult with per-window IS/OOS metrics
        """
        if data.empty or score_series.empty:
            logger.warning("Walk-forward: empty data provided")
            return WalkForwardResult(symbol=symbol)

        # Ensure datetime index
        df = data.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        score_series = score_series.reindex(df.index)

        # Generate window boundaries
        windows = self._generate_windows(df.index)
        if not windows:
            logger.warning("Walk-forward: insufficient data for any window")
            return WalkForwardResult(symbol=symbol)

        logger.info(
            f"Walk-forward analysis for {symbol}: "
            f"{len(windows)} windows, "
            f"train={self.train_months}m, test={self.test_months}m, step={self.step_months}m"
        )

        # Run backtest for each window
        result = WalkForwardResult(
            symbol=symbol,
            train_months=self.train_months,
            test_months=self.test_months,
            step_months=self.step_months,
            total_windows=len(windows),
        )

        for idx, (train_start, train_end, test_start, test_end) in enumerate(windows):
            window_result = self._run_window(
                df, score_series, idx,
                train_start, train_end, test_start, test_end,
                engine_params,
            )
            if window_result is not None:
                result.windows.append(window_result)

        # Compute aggregate metrics
        self._compute_aggregates(result)

        logger.info(
            f"Walk-forward completed for {symbol}: "
            f"{len(result.windows)}/{len(windows)} valid windows, "
            f"consistency={result.consistency_ratio:.1%}"
        )

        return result

    def _generate_windows(
        self, index: pd.DatetimeIndex
    ) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
        """Generate rolling window boundaries.

        Returns:
            List of (train_start, train_end, test_start, test_end) tuples
        """
        # Use explicit conversion to avoid type issues
        start = pd.Timestamp(str(index[0]))
        end = pd.Timestamp(str(index[-1]))

        windows: list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]] = []
        current = start

        while True:
            train_start = current
            train_end = train_start + pd.DateOffset(months=self.train_months)
            test_start = train_end
            test_end = test_start + pd.DateOffset(months=self.test_months)

            # Check if we have enough data for this window
            if test_end > end:
                break

            # Check data exists in these ranges
            train_data = index[(index >= train_start) & (index <= train_end)]
            test_data = index[(index >= test_start) & (index <= test_end)]

            if len(train_data) >= 20 and len(test_data) >= 5:
                windows.append((train_start, train_end, test_start, test_end))  # type: ignore[arg-type]

            # Advance by step
            current = current + pd.DateOffset(months=self.step_months)

        return windows

    def _run_window(
        self,
        df: pd.DataFrame,
        score_series: pd.Series,
        window_index: int,
        train_start: pd.Timestamp,
        train_end: pd.Timestamp,
        test_start: pd.Timestamp,
        test_end: pd.Timestamp,
        engine_params: Optional[dict],
    ) -> Optional[WalkForwardWindow]:
        """Run backtest on IS and OOS periods for a single window."""
        # Slice data
        train_mask = (df.index >= train_start) & (df.index <= train_end)
        test_mask = (df.index >= test_start) & (df.index <= test_end)

        train_data = df.loc[train_mask]
        test_data = df.loc[test_mask]
        train_scores = score_series.loc[train_mask]
        test_scores = score_series.loc[test_mask]

        if len(train_data) < 50 or len(test_data) < 10:
            return None

        # Create engines with optional overrides
        train_engine = BacktestEngine()
        test_engine = BacktestEngine()

        if engine_params:
            self._apply_params(train_engine, engine_params)
            self._apply_params(test_engine, engine_params)

        # Run IS backtest
        is_result = train_engine.run(train_data, train_scores, symbol="")
        # Run OOS backtest
        oos_result = test_engine.run(test_data, test_scores, symbol="")

        # Validate minimum trades
        if is_result.total_trades < self.min_trades:
            logger.debug(f"Window {window_index}: IS has {is_result.total_trades} trades, skipping")
            return None

        # Extract metrics
        is_metrics = self._extract_metrics(is_result, train_engine.holding_days)
        oos_metrics = self._extract_metrics(oos_result, test_engine.holding_days)

        # Calculate degradation
        degradation = 0.0
        if is_metrics.sharpe_ratio > 0:
            degradation = (
                (is_metrics.sharpe_ratio - oos_metrics.sharpe_ratio)
                / is_metrics.sharpe_ratio
            )

        return WalkForwardWindow(
            window_index=window_index,
            train_start=str(train_start.date()),
            train_end=str(train_end.date()),
            test_start=str(test_start.date()),
            test_end=str(test_end.date()),
            is_metrics=is_metrics,
            oos_metrics=oos_metrics,
            degradation=round(degradation, 4),
        )

    def _extract_metrics(
        self, result: BacktestResult, holding_days: int
    ) -> WindowMetrics:
        """Extract WindowMetrics from a BacktestResult."""
        if result.total_trades == 0:
            return WindowMetrics()

        returns = pd.Series([t.return_pct for t in result.trades if t.return_pct is not None])

        if len(returns) == 0:
            return WindowMetrics(total_trades=result.total_trades)

        # Build equity curve for drawdown calculation
        returns_arr = np.array(returns.values, dtype=np.float64)
        equity = pd.Series(
            np.cumprod(np.add(1.0, returns_arr)),
            index=range(len(returns)),
        )

        return WindowMetrics(
            total_trades=result.total_trades,
            win_rate=round(float((returns > 0).mean()), 4),
            avg_return=round(float(returns.mean()), 6),
            cumulative_return=round(float(np.prod(np.add(1.0, returns_arr)) - 1), 6),
            max_drawdown=round(float(calculate_max_drawdown(equity)), 4),
            sharpe_ratio=round(float(calculate_sharpe_ratio(returns)), 4),
            sortino_ratio=round(float(calculate_sortino_ratio(returns)), 4),
            profit_factor=round(float(result.profit_factor), 4) if result.profit_factor else 0.0,
            best_trade=round(float(returns.max()), 6),
            worst_trade=round(float(returns.min()), 6),
        )

    def _compute_aggregates(self, result: WalkForwardResult) -> None:
        """Compute aggregate walk-forward metrics."""
        if not result.windows:
            return

        n = len(result.windows)
        is_sharpes = [w.is_metrics.sharpe_ratio for w in result.windows]
        oos_sharpes = [w.oos_metrics.sharpe_ratio for w in result.windows]
        oos_win_rates = [w.oos_metrics.win_rate for w in result.windows]
        oos_returns = [w.oos_metrics.cumulative_return for w in result.windows]
        degradations = [w.degradation for w in result.windows]

        result.avg_is_sharpe = round(float(np.mean(is_sharpes)), 4)
        result.avg_oos_sharpe = round(float(np.mean(oos_sharpes)), 4)
        result.avg_degradation = round(float(np.mean(degradations)), 4)
        result.avg_oos_win_rate = round(float(np.mean(oos_win_rates)), 4)
        result.avg_oos_return = round(float(np.mean(oos_returns)), 6)

        # Consistency: fraction of windows where OOS Sharpe > 0
        positive_oos = sum(1 for s in oos_sharpes if s > 0)
        result.consistency_ratio = round(positive_oos / n, 4)

    @staticmethod
    def _apply_params(engine: BacktestEngine, params: dict) -> None:
        """Apply parameter overrides to a BacktestEngine."""
        if "holdingDays" in params:
            engine.holding_days = params["holdingDays"]
        if "minScore" in params:
            engine.min_score = params["minScore"]
        if "slippage" in params:
            engine.slippage = params["slippage"]
        if "commission" in params:
            engine.commission = params["commission"]
