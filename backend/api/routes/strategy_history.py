"""
Strategy History API Router.
Endpoints for fetching backtest history, simulation history, and signal/alert history
for a specific strategy.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import os

router = APIRouter()

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "..", "lobster_quant", "data",
)


# ---------------------------------------------------------------------------
# Backtest History
# ---------------------------------------------------------------------------


@router.get("/{strategy_id}/backtests")
async def get_strategy_backtests(strategy_id: str):
    """Get backtest history for a specific strategy."""
    try:
        from lobster_quant.src.storage.backtest_store import BacktestStore

        store = BacktestStore(data_dir=DATA_DIR)
        results = store.list_results(strategy_id=strategy_id)

        return [
            {
                "id": getattr(r, "id", None) or f"bt_{i}",
                "symbol": getattr(r, "symbol", "N/A"),
                "startDate": str(getattr(r, "start_date", "")),
                "endDate": str(getattr(r, "end_date", "")),
                "totalTrades": getattr(r, "total_trades", 0),
                "winRate": round(getattr(r, "win_rate", 0) * 100, 1),
                "totalReturn": round(getattr(r, "cumulative_return", 0) * 100, 2),
                "maxDrawdown": round(getattr(r, "max_drawdown", 0) * 100, 2),
                "sharpeRatio": round(getattr(r, "sharpe_ratio", 0) or 0, 2),
                "createdAt": str(getattr(r, "created_at", "")),
            }
            for i, r in enumerate(results)
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Simulation History
# ---------------------------------------------------------------------------


@router.get("/{strategy_id}/simulations")
async def get_strategy_simulations(
    strategy_id: str,
    days: int = Query(default=30, ge=1, le=365),
):
    """Get simulation history (trades + snapshots) for a specific strategy."""
    try:
        from lobster_quant.src.storage.simulation_store import SimulationStore

        store = SimulationStore(data_dir=DATA_DIR)
        trades = store.get_trades(strategy_id)
        snapshots = store.get_snapshots(strategy_id, days=days)

        return {
            "trades": [
                {
                    "id": t.id,
                    "symbol": t.symbol,
                    "entryDate": t.entryDate,
                    "entryPrice": t.entryPrice,
                    "exitDate": t.exitDate,
                    "exitPrice": t.exitPrice,
                    "shares": t.shares,
                    "status": t.status,
                    "pnl": t.pnl,
                    "pnlPercent": t.pnlPercent,
                }
                for t in trades
            ],
            "snapshots": [
                {
                    "date": s.date,
                    "portfolioValue": s.portfolioValue,
                    "cash": s.cash,
                    "invested": s.invested,
                    "openTrades": len(s.openTrades) if hasattr(s, "openTrades") else 0,
                    "closedTrades": len(s.closedTrades) if hasattr(s, "closedTrades") else 0,
                }
                for s in snapshots
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Signal / Alert History
# ---------------------------------------------------------------------------


@router.get("/{strategy_id}/signals")
async def get_strategy_signals(strategy_id: str):
    """Get signal/alert history triggered by this strategy.

    Falls back to an empty list if AlertStore is not available.
    """
    try:
        # Verify strategy exists
        from lobster_quant.src.core.strategy_manager import StrategyManager

        manager = StrategyManager(data_dir=DATA_DIR)
        strategy = manager.get_strategy(strategy_id)
        if strategy is None:
            raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")

        # Try to get triggered alerts from the alert store
        try:
            from lobster_quant.src.storage.alert_store import AlertStore

            store = AlertStore(data_dir=DATA_DIR)
            triggered = store.get_triggered_alerts()
            # Filter alerts that might be related to this strategy
            # (alerts are per-symbol, so we return all as strategy context)
            return [
                {
                    "id": a.get("id", ""),
                    "ruleId": a.get("ruleId", ""),
                    "symbol": a.get("symbol", ""),
                    "condition": a.get("condition", ""),
                    "threshold": a.get("threshold", 0),
                    "currentValue": a.get("currentValue", 0),
                    "message": a.get("message", ""),
                    "triggeredAt": a.get("triggeredAt", ""),
                    "read": a.get("read", False),
                }
                for a in triggered
            ]
        except (ImportError, FileNotFoundError, Exception):
            # AlertStore may not exist yet or have no data
            return []

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
