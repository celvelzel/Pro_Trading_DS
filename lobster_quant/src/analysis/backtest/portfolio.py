"""
Lobster Quant - Portfolio Backtest
Multi-stock portfolio backtest engine with result aggregation.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

from src.analysis.backtest.engine import BacktestEngine
from src.analysis.backtest.metrics import (
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_profit_loss_ratio,
)
from src.core.data_engine import get_data_engine
from src.core.indicator_engine import get_indicator_engine
from src.data.models import BacktestMetrics, BacktestResult, Strategy, Trade
from src.utils.logging import get_logger

logger = get_logger()

# Maximum parallel workers for portfolio backtest
MAX_WORKERS = 4


@dataclass
class EquityPoint:
    """Single point on an equity curve."""

    date: object  # Timestamp or comparable date type
    equity: float


class PortfolioBacktest:
    """Multi-stock portfolio backtest engine.

    Runs a strategy across multiple stocks, aggregates trades and
    equity curves, and computes portfolio-level metrics.
    """

    def __init__(self, max_workers: int = MAX_WORKERS):
        self.backtest_engine = BacktestEngine()
        self.data_engine = get_data_engine()
        self.indicator_engine = get_indicator_engine()
        self.max_workers = max_workers

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        symbols: List[str],
        strategy: Strategy,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> BacktestResult:
        """Run portfolio backtest on multiple stocks.

        Args:
            symbols: List of stock symbols.
            strategy: Strategy to use for backtesting.
            start_date: Backtest start date (YYYY-MM-DD).
            end_date: Backtest end date (YYYY-MM-DD).

        Returns:
            BacktestResult with aggregated portfolio metrics.
        """
        results: List[BacktestResult] = []

        for symbol in symbols:
            try:
                # Fetch stock data
                stock_data = self.data_engine.fetch_stock(symbol)
                if stock_data is None:
                    logger.warning(f"No data returned for {symbol}, skipping")
                    continue

                # Compute indicators
                df = self.indicator_engine.compute_all(stock_data.daily)

                # Filter by date range if specified
                if start_date:
                    df = df[df.index >= start_date]
                if end_date:
                    df = df[df.index <= end_date]

                # Run backtest for this stock
                result = self.backtest_engine.run_with_strategy(df, strategy, symbol)
                results.append(result)

            except Exception as e:
                logger.warning(f"Backtest failed for {symbol}: {e}")
                continue

        # Aggregate results
        return self._aggregate_results(results, strategy, symbols)

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------

    def _aggregate_results(
        self,
        results: List[BacktestResult],
        strategy: Strategy,
        symbols: List[str],
    ) -> BacktestResult:
        """Aggregate multiple backtest results into a single portfolio result."""
        if not results:
            return BacktestResult(symbol=", ".join(symbols))

        # Collect all trades
        all_trades: List[Trade] = []
        for r in results:
            all_trades.extend(r.trades)

        # Build per-stock equity curves (list[float] from BacktestResult.equity_curve)
        equity_curves: List[List[float]] = [
            r.equity_curve for r in results if r.equity_curve and len(r.equity_curve) > 1
        ]
        aggregated_equity = self._aggregate_equity_curves(equity_curves)

        # Calculate portfolio-level metrics
        metrics = self._calculate_portfolio_metrics(all_trades, aggregated_equity)

        # Determine date range
        start = min((r.start_date for r in results if r.start_date), default=None)
        end = max((r.end_date for r in results if r.end_date), default=None)

        return BacktestResult(
            symbol=", ".join(symbols),
            trades=all_trades,
            metrics=metrics,
            win_rate=metrics.winRate / 100 if metrics else 0,
            avg_return=metrics.avgWin / 100 if metrics else 0,
            profit_factor=metrics.profitLossRatio if metrics else 0,
            max_drawdown=metrics.maxDrawdown / 100 if metrics else 0,
            cumulative_return=metrics.totalReturn / 100 if metrics else 0,
            sharpe_ratio=metrics.sharpeRatio if metrics else None,
            start_date=start,
            end_date=end,
        )

    def _aggregate_equity_curves(self, curves: List[List[float]]) -> List[float]:
        """Aggregate multiple equity curves by averaging aligned values.

        Each curve is a list of floats where index 0 = initial capital
        and subsequent indices correspond to sequential trade outcomes.
        The curves are aligned by index position (equal-weight assumption).
        """
        if not curves:
            return []

        max_len = max(len(c) for c in curves)
        aggregated: List[float] = []

        for i in range(max_len):
            values = [c[i] for c in curves if i < len(c)]
            if values:
                aggregated.append(sum(values) / len(values))

        return aggregated

    def _calculate_portfolio_metrics(
        self,
        trades: List[Trade],
        equity_curve: List[float],
    ) -> BacktestMetrics:
        """Calculate portfolio-level metrics from aggregated data."""
        if not trades:
            return BacktestMetrics(
                totalReturn=0,
                annualizedReturn=0,
                volatility=0,
                sharpeRatio=0,
                maxDrawdown=0,
                winRate=0,
                profitLossRatio=0,
                totalTrades=0,
                winningTrades=0,
                losingTrades=0,
                avgHoldingDays=0,
                avgWin=0,
                avgLoss=0,
            )

        # Trade-level statistics using unified metrics functions
        closed_trades = [t for t in trades if t.return_pct is not None]
        trade_returns: List[float] = [t.return_pct for t in closed_trades]  # type: ignore[misc]
        winning = [r for r in trade_returns if r > 0]
        losing = [r for r in trade_returns if r <= 0]

        total = len(closed_trades) if closed_trades else len(trades)
        win_rate = calculate_win_rate(trades)
        avg_win = sum(winning) / len(winning) if winning else 0.0
        avg_loss = sum(losing) / len(losing) if losing else 0.0
        profit_loss_ratio = calculate_profit_loss_ratio(trades)
        avg_holding = (
            sum(t.holding_days for t in trades) / len(trades) if trades else 0
        )

        # Equity-curve-level metrics using unified metrics functions
        if equity_curve and len(equity_curve) > 1:
            equity_series = pd.Series(equity_curve)
            daily_returns = equity_series.pct_change().dropna()

            total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0] * 100 if equity_curve[0] else 0
            volatility = daily_returns.std() * np.sqrt(252) * 100 if len(daily_returns) > 1 else 0
            max_drawdown = calculate_max_drawdown(equity_series) * 100
            sharpe = calculate_sharpe_ratio(daily_returns)

            days = len(equity_curve)
            annualized = ((1 + total_return / 100) ** (252 / days) - 1) * 100 if days > 0 else 0
        else:
            total_return = 0
            volatility = 0
            max_drawdown = 0
            sharpe = 0
            annualized = 0

        return BacktestMetrics(
            totalReturn=round(total_return, 2),
            annualizedReturn=round(annualized, 2),
            volatility=round(volatility, 2),
            sharpeRatio=round(sharpe, 2),
            maxDrawdown=round(max_drawdown, 2),
            winRate=round(win_rate, 2),
            profitLossRatio=round(profit_loss_ratio, 2),
            totalTrades=len(trades),
            winningTrades=len(winning),
            losingTrades=len(losing),
            avgHoldingDays=round(avg_holding, 1),
            avgWin=round(avg_win, 2),
            avgLoss=round(avg_loss, 2),
        )
