"""
Lobster Quant - Backtest Engine
Enhanced backtesting with slippage, commission, and risk management.
"""

from typing import Any

import numpy as np
import pandas as pd

from ...config.settings import get_settings
from ...data.models import BacktestMetrics, BacktestResult, Strategy, Trade
from ...utils.logging import get_logger

logger = get_logger()


class BacktestEngine:
    """Enhanced backtest engine.

    Features:
    - Fixed holding period
    - Slippage simulation
    - Commission calculation
    - Risk management (stop loss)
    - Comprehensive metrics
    """

    def __init__(self):
        self.settings = get_settings()
        self.holding_days = self.settings.backtest_holding_days
        self.min_score = self.settings.backtest_min_score
        self.slippage = self.settings.backtest_slippage_pct
        self.commission = self.settings.backtest_commission_pct

    def run(self, data: pd.DataFrame, score_series: pd.Series, symbol: str = "") -> BacktestResult:
        """Run backtest on historical data.

        Args:
            data: DataFrame with OHLCV and indicators
            score_series: Score values aligned with data index
            symbol: Stock symbol

        Returns:
            BacktestResult with trades and metrics
        """
        if len(data) < self.holding_days + 50:
            logger.warning(f"Insufficient data for backtest: {len(data)} rows")
            return BacktestResult(symbol=symbol)

        # Align score with data
        df = data.copy()
        df["score"] = score_series.reindex(df.index)
        df = df.dropna(subset=["close", "score"])

        if len(df) < self.holding_days:
            return BacktestResult(symbol=symbol)

        # Calculate entry signals
        # Defensive: compute ma20 if not provided by IndicatorEngine
        if "ma20" not in df.columns:
            df["ma20"] = pd.to_numeric(df["close"], errors="coerce").rolling(window=20).mean()
        close = pd.to_numeric(df["close"], errors="coerce")
        ma20 = pd.to_numeric(df["ma20"], errors="coerce")
        ma20_slope = (
            pd.to_numeric(df["ma20_slope"], errors="coerce")
            if "ma20_slope" in df.columns
            else ma20.diff()
        )
        df["ma20_slope"] = ma20_slope

        score = pd.to_numeric(df["score"], errors="coerce")
        df["entry_signal"] = (close > ma20) & (ma20_slope > 0) & (score >= self.min_score)

        # Generate trades
        trades = self._generate_trades(df, symbol)

        # Calculate metrics
        result = self._calculate_metrics(trades, symbol)

        logger.info(f"Backtest completed for {symbol}: {result.total_trades} trades")
        return result

    def _generate_trades(self, df: pd.DataFrame, symbol: str) -> list[Trade]:
        """Generate trades from entry signals."""
        trades = []
        blocked_until = None

        signals = df.index[df["entry_signal"]].tolist()

        for date in signals:
            # Skip if in holding period
            if blocked_until is not None and date < blocked_until:
                continue

            idx = df.index.get_loc(date)
            if idx + self.holding_days >= len(df):
                break  # Not enough data for full holding period

            # Entry
            buy_price = df.at[date, "close"]
            buy_price = self._apply_slippage(buy_price, "buy")

            # Exit
            sell_idx = idx + self.holding_days
            sell_date = df.index[sell_idx]
            sell_price = df.at[sell_date, "close"]
            sell_price = self._apply_slippage(sell_price, "sell")

            # Calculate returns
            gross_return = (sell_price - buy_price) / buy_price

            # Apply commission (round trip)
            commission_cost = self.commission * 2
            net_return = gross_return - commission_cost

            trade = Trade(
                symbol=symbol,
                buy_date=date,
                buy_price=buy_price,
                sell_date=sell_date,
                sell_price=sell_price,
                return_pct=net_return,
                holding_days=self.holding_days,
            )

            trades.append(trade)
            blocked_until = sell_date

        return trades

    def _apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to price.

        Args:
            price: Original price
            side: 'buy' or 'sell'

        Returns:
            Price with slippage applied
        """
        if side == "buy":
            # Buy at slightly higher price
            return price * (1 + self.slippage)
        else:
            # Sell at slightly lower price
            return price * (1 - self.slippage)

    def _calculate_metrics(self, trades: list[Trade], symbol: str) -> BacktestResult:
        """Calculate backtest metrics."""
        if not trades:
            return BacktestResult(symbol=symbol)

        returns = [t.return_pct for t in trades if t.return_pct is not None]

        if not returns:
            return BacktestResult(symbol=symbol, trades=trades)

        # Basic metrics
        win_rate = sum(1 for r in returns if r > 0) / len(returns)
        avg_return = np.mean(returns)

        # Profit factor
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]

        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0.0001
        profit_factor = avg_win / avg_loss if avg_loss > 0 else float("inf")

        # Cumulative return
        cum_return = np.prod([1 + r for r in returns]) - 1

        # Max drawdown
        equity_curve = [1.0]
        for r in returns:
            equity_curve.append(equity_curve[-1] * (1 + r))

        peak = equity_curve[0]
        max_dd = 0
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd

        # Sharpe ratio (simplified, assuming risk-free rate = 0)
        if len(returns) > 1:
            sharpe = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252 / self.holding_days)
        else:
            sharpe = None

        return BacktestResult(
            symbol=symbol,
            trades=trades,
            total_trades=len(trades),
            win_rate=win_rate,
            avg_return=avg_return,
            profit_factor=profit_factor,
            max_drawdown=max_dd,
            cumulative_return=cum_return,
            best_trade=max(returns),
            worst_trade=min(returns),
            sharpe_ratio=sharpe,
            start_date=trades[0].buy_date if trades else None,
            end_date=trades[-1].sell_date if trades else None,
        )

    def get_trade_summary(self, result: BacktestResult) -> dict[str, Any]:
        """Get human-readable trade summary."""
        return {
            "symbol": result.symbol,
            "total_trades": result.total_trades,
            "win_rate": f"{result.win_rate*100:.1f}%",
            "avg_return": f"{result.avg_return*100:.2f}%",
            "profit_factor": f"{result.profit_factor:.2f}",
            "max_drawdown": f"{result.max_drawdown*100:.1f}%",
            "cumulative_return": f"{result.cumulative_return*100:.1f}%",
            "sharpe_ratio": f"{result.sharpe_ratio:.2f}" if result.sharpe_ratio else "N/A",
            "best_trade": f"{result.best_trade*100:.2f}%",
            "worst_trade": f"{result.worst_trade*100:.2f}%",
        }

    def run_with_strategy(
        self, data: pd.DataFrame, strategy: Strategy, symbol: str = ""
    ) -> BacktestResult:
        """Run backtest using a Strategy object's parameters.

        Args:
            data: DataFrame with OHLCV and indicators
            strategy: Strategy object with parameters
            symbol: Stock symbol

        Returns:
            BacktestResult with enhanced BacktestMetrics
        """
        # Temporarily override engine settings with strategy params
        original_holding = self.holding_days
        original_min_score = self.min_score
        original_slippage = self.slippage
        original_commission = self.commission

        try:
            self.holding_days = strategy.params.holdingDays
            self.min_score = strategy.params.minScore
            self.slippage = strategy.params.slippagePct
            self.commission = strategy.params.commissionPct

            # Generate score series using scoring engine
            from src.core.signal_engine import get_signal_engine

            signal_engine = get_signal_engine()

            # Calculate scores for each row
            score_series = pd.Series(index=data.index, dtype=float)
            for i in range(len(data)):
                try:
                    score_series.iloc[i] = signal_engine.scoring_engine.compute_score(
                        data.iloc[: i + 1]
                    ).iloc[-1]
                except Exception:
                    score_series.iloc[i] = 0

            # Run existing backtest
            result = self.run(data, score_series, symbol)

            # Enhance metrics with new fields
            result.metrics = self._calculate_enhanced_metrics(result)

            return result

        finally:
            # Restore original settings
            self.holding_days = original_holding
            self.min_score = original_min_score
            self.slippage = original_slippage
            self.commission = original_commission

    def _calculate_enhanced_metrics(self, result: BacktestResult) -> BacktestMetrics:
        """Calculate enhanced metrics from backtest result."""
        trades = result.trades
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

        # Calculate win/loss stats
        winning = [t for t in trades if t.return_pct is not None and t.return_pct > 0]
        losing = [t for t in trades if t.return_pct is not None and t.return_pct <= 0]

        win_rate = len(winning) / len(trades) * 100 if trades else 0
        avg_win = sum(t.return_pct for t in winning) / len(winning) if winning else 0
        avg_loss = sum(t.return_pct for t in losing) / len(losing) if losing else 0
        profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        avg_holding = sum(t.holding_days for t in trades) / len(trades) if trades else 0

        # Calculate equity curve metrics
        equity_curve = result.equity_curve
        if equity_curve and len(equity_curve) > 1:
            values = equity_curve
            total_return = (values[-1] - values[0]) / values[0] * 100 if values[0] else 0

            # Calculate volatility from daily returns
            returns = pd.Series(values).pct_change().dropna()
            volatility = returns.std() * np.sqrt(252) * 100 if len(returns) > 1 else 0

            # Calculate max drawdown
            peak = pd.Series(values).expanding().max()
            drawdown = (pd.Series(values) - peak) / peak
            max_drawdown = abs(drawdown.min()) * 100

            # Calculate Sharpe ratio
            sharpe = (
                (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
            )

            # Annualized return (assuming 252 trading days per year)
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
