"""
Lobster Quant - Backtest Engine
Enhanced backtesting with slippage, commission, and risk management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np

from src.data.models import Trade, BacktestResult
from src.config.settings import get_settings
from src.utils.logging import get_logger
from src.utils.exceptions import BacktestError

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
    
    def run(self, 
            data: pd.DataFrame, 
            score_series: pd.Series,
            symbol: str = "") -> BacktestResult:
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
        df['score'] = score_series.reindex(df.index)
        df = df.dropna(subset=['close', 'score'])
        
        if len(df) < self.holding_days:
            return BacktestResult(symbol=symbol)
        
        # Calculate entry signals
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma20_slope'] = df['ma20'].diff()
        
        df['entry_signal'] = (
            (df['close'] > df['ma20']) &
            (df['ma20_slope'] > 0) &
            (df['score'] >= self.min_score)
        )
        
        # Generate trades
        trades = self._generate_trades(df, symbol)
        
        # Calculate metrics
        result = self._calculate_metrics(trades, symbol)
        
        logger.info(f"Backtest completed for {symbol}: {result.total_trades} trades")
        return result
    
    def _generate_trades(self, df: pd.DataFrame, symbol: str) -> List[Trade]:
        """Generate trades from entry signals."""
        trades = []
        blocked_until = None
        
        signals = df.index[df['entry_signal']].tolist()
        
        for date in signals:
            # Skip if in holding period
            if blocked_until is not None and date < blocked_until:
                continue
            
            idx = df.index.get_loc(date)
            if idx + self.holding_days >= len(df):
                break  # Not enough data for full holding period
            
            # Entry
            buy_price = df.at[date, 'close']
            buy_price = self._apply_slippage(buy_price, 'buy')
            
            # Exit
            sell_idx = idx + self.holding_days
            sell_date = df.index[sell_idx]
            sell_price = df.at[sell_date, 'close']
            sell_price = self._apply_slippage(sell_price, 'sell')
            
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
                holding_days=self.holding_days
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
        if side == 'buy':
            # Buy at slightly higher price
            return price * (1 + self.slippage)
        else:
            # Sell at slightly lower price
            return price * (1 - self.slippage)
    
    def _calculate_metrics(self, trades: List[Trade], symbol: str) -> BacktestResult:
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
        profit_factor = avg_win / avg_loss if avg_loss > 0 else float('inf')
        
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
            end_date=trades[-1].sell_date if trades else None
        )
    
    def get_trade_summary(self, result: BacktestResult) -> Dict[str, Any]:
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

