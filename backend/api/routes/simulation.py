"""Simulation API Router."""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from api.models.simulation import (
    SimulationRequest, RunAllSimulationRequest,
    SimulatedTradeResponse, DailySnapshotResponse,
    SimulationResultResponse, PerformanceResponse
)

router = APIRouter()


@router.post("/run", response_model=SimulationResultResponse)
async def run_simulation(request: SimulationRequest):
    """Run simulation for a specific strategy."""
    try:
        from lobster_quant.src.core.scheduler import SimulationScheduler

        scheduler = SimulationScheduler()
        result = scheduler.run_strategy(request.strategyId, request.market)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return SimulationResultResponse(
            timestamp=result["timestamp"],
            market=result["market"],
            strategyId=result.get("strategy_id"),
            strategyName=result.get("strategy_name"),
            status=result["status"],
            snapshot=_snapshot_to_response(result.get("snapshot")),
            error=result.get("error")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-all", response_model=List[SimulationResultResponse])
async def run_all_simulations(request: RunAllSimulationRequest):
    """Run simulation for all strategies."""
    try:
        from lobster_quant.src.core.scheduler import SimulationScheduler

        scheduler = SimulationScheduler()
        result = scheduler.run_daily(request.market)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return [
            SimulationResultResponse(
                timestamp=result["timestamp"],
                market=result["market"],
                strategyId=r.get("strategy_id"),
                strategyName=r.get("strategy_name"),
                status=r["status"],
                snapshot=_snapshot_to_response(r.get("snapshot")),
                error=r.get("error")
            )
            for r in result["results"]
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades", response_model=List[SimulatedTradeResponse])
async def list_trades(strategy_id: str, status: Optional[str] = None):
    """List simulated trades."""
    try:
        from lobster_quant.src.storage.simulation_store import SimulationStore

        store = SimulationStore()
        trades = store.get_trades(strategy_id, status)

        return [
            SimulatedTradeResponse(
                id=t.id,
                strategyId=t.strategyId,
                symbol=t.symbol,
                entryDate=t.entryDate,
                entryPrice=t.entryPrice,
                exitDate=t.exitDate,
                exitPrice=t.exitPrice,
                shares=t.shares,
                status=t.status,
                pnl=t.pnl,
                pnlPercent=t.pnlPercent
            )
            for t in trades
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshots", response_model=List[DailySnapshotResponse])
async def list_snapshots(strategy_id: str, days: int = 30):
    """List daily snapshots."""
    try:
        from lobster_quant.src.storage.simulation_store import SimulationStore

        store = SimulationStore()
        snapshots = store.get_snapshots(strategy_id, days)

        return [_snapshot_to_response(s) for s in snapshots]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance(strategy_id: str, window: str = "1M"):
    """Get performance metrics."""
    try:
        from lobster_quant.src.storage.simulation_store import SimulationStore
        import pandas as pd

        store = SimulationStore()

        # Get closed trades for the strategy
        trades = store.get_trades(strategy_id, status="closed")

        if not trades:
            return PerformanceResponse(
                strategyId=strategy_id,
                window=window,
                totalReturn=0,
                volatility=0,
                sharpeRatio=0,
                maxDrawdown=0,
                winRate=0,
                totalTrades=0
            )

        # Calculate metrics from SimulatedTrade pnlPercent values
        returns_list: List[float] = [
            t.pnlPercent for t in trades if t.pnlPercent is not None
        ]
        returns_series = pd.Series(returns_list, dtype=float)

        # Win rate: percentage of trades with positive pnlPercent
        winning = [r for r in returns_list if r > 0]
        win_rate = len(winning) / len(trades) * 100 if trades else 0.0

        # Total return
        total_return: float = sum(returns_list) if returns_list else 0.0

        # Volatility
        volatility: float = float(returns_series.std()) if len(returns_series) > 1 else 0.0  # type: ignore[arg-type]

        # Sharpe ratio (simplified, annualized)
        sharpe: float = 0.0
        if volatility > 0 and len(returns_series) > 1:
            sharpe = float(returns_series.mean() / volatility * (252 ** 0.5))

        # Max drawdown (simplified - from cumulative returns)
        max_drawdown: float = 0.0
        if len(returns_series) > 0:
            cumulative = returns_series.div(100).add(1).cumprod()
            peak = cumulative.expanding().max()
            drawdown = cumulative.sub(peak).div(peak)
            dd_min = drawdown.min()
            max_drawdown = abs(float(dd_min)) * 100 if len(drawdown) > 0 else 0.0

        return PerformanceResponse(
            strategyId=strategy_id,
            window=window,
            totalReturn=round(total_return, 2),
            volatility=round(volatility, 2),
            sharpeRatio=round(sharpe, 2),
            maxDrawdown=round(max_drawdown, 2),
            winRate=round(win_rate, 2),
            totalTrades=len(trades)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _snapshot_to_response(snapshot) -> Optional[DailySnapshotResponse]:
    """Convert DailySnapshot to response model."""
    if snapshot is None:
        return None

    return DailySnapshotResponse(
        date=snapshot.date,
        strategyId=snapshot.strategyId,
        selectedStocks=snapshot.selectedStocks,
        openTrades=[t.model_dump() if hasattr(t, 'model_dump') else t.dict() for t in snapshot.openTrades],
        closedTrades=[t.model_dump() if hasattr(t, 'model_dump') else t.dict() for t in snapshot.closedTrades],
        portfolioValue=snapshot.portfolioValue,
        cash=snapshot.cash,
        invested=snapshot.invested
    )
