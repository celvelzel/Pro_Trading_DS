"""
Backtest API Router
Endpoints for strategy backtesting.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

router = APIRouter()


class BacktestRequest(BaseModel):
    symbol: str
    holdingDays: int = 10
    minScore: int = 60
    startDate: Optional[str] = None
    endDate: Optional[str] = None


class Trade(BaseModel):
    entryDate: str
    exitDate: str
    entryPrice: float
    exitPrice: float
    returnPercent: float
    holdingDays: int


class BacktestResult(BaseModel):
    totalTrades: int
    winRate: float
    totalReturn: float
    maxDrawdown: float
    sharpeRatio: float
    trades: List[Trade]
    equityCurve: List[dict]


@router.post("/run", response_model=BacktestResult)
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
        
        # Temporarily override settings
        original_holding = backtest_engine.holding_days
        original_min_score = backtest_engine.min_score
        
        backtest_engine.holding_days = request.holdingDays
        backtest_engine.min_score = request.minScore
        
        try:
            results = backtest_engine.run(df, score_series)
        finally:
            # Restore original settings
            backtest_engine.holding_days = original_holding
            backtest_engine.min_score = original_min_score
        
        # Convert trades to response format
        trades = []
        for trade in results.get('trades', []):
            trades.append(Trade(
                entryDate=str(trade.get('entry_date', '')),
                exitDate=str(trade.get('exit_date', '')),
                entryPrice=float(trade.get('entry_price', 0)),
                exitPrice=float(trade.get('exit_price', 0)),
                returnPercent=float(trade.get('return_pct', 0)),
                holdingDays=int(trade.get('holding_days', 0)),
            ))
        
        # Convert equity curve to response format
        equity_curve = []
        for date, value in results.get('equity_curve', {}).items():
            equity_curve.append({
                'date': str(date),
                'value': float(value),
            })
        
        return BacktestResult(
            totalTrades=int(results.get('total_trades', 0)),
            winRate=float(results.get('win_rate', 0)),
            totalReturn=float(results.get('total_return', 0)),
            maxDrawdown=float(results.get('max_drawdown', 0)),
            sharpeRatio=float(results.get('sharpe_ratio', 0)),
            trades=trades,
            equityCurve=equity_curve,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
