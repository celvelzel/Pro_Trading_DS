"""
Backtest API Router - Enhanced with strategy support.
Endpoints for strategy backtesting, portfolio backtesting, and result management.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional


from api.models.backtest import (
    BacktestRequest,
    BacktestTrade,
    EquityPoint,
    BacktestResponse,
    WalkForwardRequest,
)
from api.deps import get_data_engine_dep, get_indicator_engine_dep

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
        from lobster_quant.src.analysis.signals import SignalGenerator
        from lobster_quant.src.analysis.backtest import BacktestEngine
        import pandas as pd

        data_engine = get_data_engine_dep()
        indicator_engine = get_indicator_engine_dep()

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


@router.post("/backtest/strategy", response_model=dict)
async def run_strategy_backtest(
    symbol: str,
    strategy_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Run backtest with a specific strategy.

    Args:
        symbol: Stock symbol to backtest
        strategy_id: ID of the strategy to use
        start_date: Backtest start date (YYYY-MM-DD)
        end_date: Backtest end date (YYYY-MM-DD)

    Returns:
        Backtest results with strategy info, metrics, trades, and equity curve
    """
    try:
        from lobster_quant.src.core.strategy_manager import StrategyManager
        from lobster_quant.src.analysis.backtest.engine import BacktestEngine

        # Get strategy
        manager = StrategyManager()
        strategy = manager.get_strategy(strategy_id)
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")

        # Fetch and prepare data
        data_engine = get_data_engine_dep()
        indicator_engine = get_indicator_engine_dep()

        stock_data = data_engine.fetch_stock(symbol)
        if stock_data is None:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")

        df = indicator_engine.compute_all(stock_data.daily)

        # Filter by date range if specified
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]

        # Run backtest with strategy
        engine = BacktestEngine()
        result = engine.run_with_strategy(df, strategy, symbol)

        return {
            "strategy_id": strategy_id,
            "strategy_name": strategy.name,
            "symbol": symbol,
            "metrics": result.metrics.model_dump() if result.metrics else None,
            "trades": [
                {
                    "entryDate": str(t.buy_date.date()) if t.buy_date else "",
                    "exitDate": str(t.sell_date.date()) if t.sell_date else "",
                    "entryPrice": t.buy_price,
                    "exitPrice": t.sell_price or 0.0,
                    "returnPercent": round((t.return_pct or 0.0) * 100, 2),
                    "holdingDays": t.holding_days
                }
                for t in result.trades
            ],
            "equityCurve": result.equity_curve
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backtest/portfolio", response_model=dict)
async def run_portfolio_backtest(
    symbols: List[str] = Query(..., description="List of stock symbols"),
    strategy_id: str = Query(..., description="Strategy ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Run portfolio backtest on multiple stocks.

    Args:
        symbols: List of stock symbols to backtest
        strategy_id: ID of the strategy to use
        start_date: Backtest start date (YYYY-MM-DD)
        end_date: Backtest end date (YYYY-MM-DD)

    Returns:
        Portfolio backtest results with aggregated metrics
    """
    try:
        from lobster_quant.src.core.strategy_manager import StrategyManager
        from lobster_quant.src.analysis.backtest.portfolio import PortfolioBacktest

        # Get strategy
        manager = StrategyManager()
        strategy = manager.get_strategy(strategy_id)
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")

        # Run portfolio backtest
        portfolio = PortfolioBacktest()
        result = portfolio.run(symbols, strategy, start_date, end_date)

        return {
            "strategy_id": strategy_id,
            "strategy_name": strategy.name,
            "symbols": symbols,
            "metrics": result.metrics.model_dump() if result.metrics else None,
            "trades": [
                {
                    "entryDate": str(t.buy_date.date()) if t.buy_date else "",
                    "exitDate": str(t.sell_date.date()) if t.sell_date else "",
                    "entryPrice": t.buy_price,
                    "exitPrice": t.sell_price or 0.0,
                    "returnPercent": round((t.return_pct or 0.0) * 100, 2),
                    "holdingDays": t.holding_days
                }
                for t in result.trades
            ],
            "equityCurve": result.equity_curve
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backtest/results", response_model=List[dict])
async def list_backtest_results(strategy_id: Optional[str] = None):
    """List backtest results.

    Args:
        strategy_id: Optional filter by strategy ID

    Returns:
        List of backtest result summaries
    """
    try:
        from lobster_quant.src.storage.backtest_store import BacktestStore

        store = BacktestStore()
        results = store.list_results(strategy_id)

        return [
            {
                "id": r.id if hasattr(r, 'id') else None,
                "strategyId": r.strategy_id if hasattr(r, 'strategy_id') else None,
                "symbol": r.symbol,
                "metrics": r.metrics.model_dump() if r.metrics else None,
                "createdAt": str(r.created_at) if hasattr(r, 'created_at') else None
            }
            for r in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backtest/walk-forward", response_model=dict)
async def run_walk_forward(request: WalkForwardRequest):
    """Run walk-forward validation analysis.

    Splits historical data into rolling train/test windows and compares
    in-sample vs out-of-sample performance to detect overfitting.

    Args:
        request: Walk-forward parameters

    Returns:
        Walk-forward results with per-window IS/OOS metrics and aggregates
    """
    try:
        from lobster_quant.src.analysis.signals import SignalGenerator
        from lobster_quant.src.analysis.backtest.walk_forward import WalkForwardEngine
        import pandas as pd

        data_engine = get_data_engine_dep()
        indicator_engine = get_indicator_engine_dep()

        stock_data = data_engine.fetch_stock(request.symbol)
        if stock_data is None:
            raise HTTPException(
                status_code=404,
                detail=f"Stock {request.symbol} not found",
            )

        df = indicator_engine.compute_all(stock_data.daily)

        # Generate score series
        signal_gen = SignalGenerator()
        score_series = pd.Series(
            [signal_gen.calculate_score(df.iloc[:i + 1]) for i in range(len(df))],
            index=df.index,
        )

        # Run walk-forward analysis
        engine = WalkForwardEngine(
            train_months=request.trainMonths,
            test_months=request.testMonths,
            step_months=request.stepMonths,
        )

        result = engine.run(
            data=df,
            score_series=score_series,
            symbol=request.symbol,
            engine_params={
                "holdingDays": request.holdingDays,
                "minScore": request.minScore,
            },
        )

        # Convert to response format
        windows = []
        for w in result.windows:
            windows.append({
                "windowIndex": w.window_index,
                "trainStart": w.train_start,
                "trainEnd": w.train_end,
                "testStart": w.test_start,
                "testEnd": w.test_end,
                "isMetrics": {
                    "totalTrades": w.is_metrics.total_trades,
                    "winRate": w.is_metrics.win_rate,
                    "avgReturn": w.is_metrics.avg_return,
                    "cumulativeReturn": w.is_metrics.cumulative_return,
                    "maxDrawdown": w.is_metrics.max_drawdown,
                    "sharpeRatio": w.is_metrics.sharpe_ratio,
                    "sortinoRatio": w.is_metrics.sortino_ratio,
                    "profitFactor": w.is_metrics.profit_factor,
                    "bestTrade": w.is_metrics.best_trade,
                    "worstTrade": w.is_metrics.worst_trade,
                },
                "oosMetrics": {
                    "totalTrades": w.oos_metrics.total_trades,
                    "winRate": w.oos_metrics.win_rate,
                    "avgReturn": w.oos_metrics.avg_return,
                    "cumulativeReturn": w.oos_metrics.cumulative_return,
                    "maxDrawdown": w.oos_metrics.max_drawdown,
                    "sharpeRatio": w.oos_metrics.sharpe_ratio,
                    "sortinoRatio": w.oos_metrics.sortino_ratio,
                    "profitFactor": w.oos_metrics.profit_factor,
                    "bestTrade": w.oos_metrics.best_trade,
                    "worstTrade": w.oos_metrics.worst_trade,
                },
                "degradation": w.degradation,
            })

        return {
            "symbol": result.symbol,
            "trainMonths": result.train_months,
            "testMonths": result.test_months,
            "stepMonths": result.step_months,
            "totalWindows": result.total_windows,
            "windows": windows,
            "avgIsSharpe": result.avg_is_sharpe,
            "avgOosSharpe": result.avg_oos_sharpe,
            "avgDegradation": result.avg_degradation,
            "avgOosWinRate": result.avg_oos_win_rate,
            "avgOosReturn": result.avg_oos_return,
            "consistencyRatio": result.consistency_ratio,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
