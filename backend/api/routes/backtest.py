"""
Backtest API Router
Endpoints for strategy backtesting.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from api.models.backtest import BacktestRequest, BacktestTrade, EquityPoint, BacktestResponse

router = APIRouter()


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """
    Run strategy backtest.

    Args:
        request: Backtest parameters

    Returns:
        Backtest results with trades and equity curve
    """
    try:
        from lobster_quant.src.core.data_engine import get_data_engine
        from lobster_quant.src.core.indicator_engine import get_indicator_engine
        from lobster_quant.src.analysis.signals import SignalGenerator
        from lobster_quant.src.analysis.backtest import BacktestEngine
        import pandas as pd

        data_engine = get_data_engine()
        indicator_engine = get_indicator_engine()

        stock_data = data_engine.fetch_stock(request.symbol)
        if stock_data is None:
            raise HTTPException(status_code=404, detail=f"Stock {request.symbol} not found")

        df = indicator_engine.compute_all(stock_data.daily)

        # Generate score series
        signal_gen = SignalGenerator()
        score_series = pd.Series(
            [signal_gen.calculate_score(df.iloc[:i+1]) for i in range(len(df))],
            index=df.index
        )

        # Run backtest
        backtest_engine = BacktestEngine()

        # Apply optional overrides from request
        original_holding = backtest_engine.holding_days
        original_min_score = backtest_engine.min_score
        original_slippage = backtest_engine.slippage
        original_commission = backtest_engine.commission

        backtest_engine.holding_days = request.holdingDays
        backtest_engine.min_score = request.minScore
        if request.slippagePct is not None:
            backtest_engine.slippage = request.slippagePct
        if request.commissionPct is not None:
            backtest_engine.commission = request.commissionPct

        try:
            results = backtest_engine.run(df, score_series)
        finally:
            # Restore original settings
            backtest_engine.holding_days = original_holding
            backtest_engine.min_score = original_min_score
            backtest_engine.slippage = original_slippage
            backtest_engine.commission = original_commission

        # Convert trades to response format
        trades = []
        for trade in results.trades:
            trades.append(BacktestTrade(
                entryDate=str(trade.buy_date.date()) if trade.buy_date else "",
                exitDate=str(trade.sell_date.date()) if trade.sell_date else "",
                entryPrice=trade.buy_price,
                exitPrice=trade.sell_price or 0.0,
                returnPercent=round((trade.return_pct or 0.0) * 100, 2),
                holdingDays=trade.holding_days,
            ))

        # Convert equity curve to response format
        equity_curve = []
        eq_values = results.equity_curve
        for i, val in enumerate(eq_values):
            equity_curve.append(EquityPoint(
                date=f"day_{i}",
                value=round(val, 4),
            ))

        return BacktestResponse(
            totalTrades=results.total_trades,
            winRate=round(results.win_rate * 100, 1),
            totalReturn=round(results.cumulative_return * 100, 2),
            maxDrawdown=round(results.max_drawdown * 100, 2),
            sharpeRatio=round(results.sharpe_ratio or 0.0, 2),
            trades=trades,
            equityCurve=equity_curve,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
