"""
Signal Stats API Router.
Endpoints for signal win rate statistics and performance tracking.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

router = APIRouter()

DATA_DIR = "../lobster_quant/data"


@router.get("/stats")
async def get_signal_stats(
    lookback: str = Query(default="30d", description="Lookback period (e.g. 7d, 30d, 90d)"),
    strategy_id: Optional[str] = Query(default=None, description="Filter by strategy ID"),
    symbol: Optional[str] = Query(default=None, description="Filter by symbol"),
):
    """Get signal win rate statistics.

    Returns total signals, win rates by signal type, and average returns
    for 5-day, 10-day, and 20-day evaluation windows.
    """
    try:
        # Parse lookback period
        lookback_days = _parse_lookback(lookback)

        from lobster_quant.src.core.signal_tracker import SignalTracker

        tracker = SignalTracker(data_dir=DATA_DIR)
        stats = tracker.get_win_rate_stats(
            symbol=symbol,
            strategy_id=strategy_id,
            lookback_days=lookback_days,
        )

        return stats
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_signal_history(
    lookback: str = Query(default="30d", description="Lookback period"),
    strategy_id: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None),
    signal_type: Optional[str] = Query(default=None, description="Filter by signal type"),
    limit: int = Query(default=50, ge=1, le=500),
):
    """Get signal history with outcomes.

    Returns list of tracked signals with entry prices and actual returns.
    """
    try:
        lookback_days = _parse_lookback(lookback)

        from lobster_quant.src.core.signal_tracker import SignalTracker

        tracker = SignalTracker(data_dir=DATA_DIR)
        signals = tracker.get_signals(
            symbol=symbol,
            strategy_id=strategy_id,
            lookback_days=lookback_days,
            signal_type=signal_type,
        )

        # Limit results
        signals = signals[:limit]

        return [
            {
                "id": s.id,
                "symbol": s.symbol,
                "signalType": s.signal_type,
                "score": s.score,
                "probabilityUp": s.probability_up,
                "entryPrice": s.entry_price,
                "entryDate": s.entry_date,
                "strategyId": s.strategy_id,
                "price5d": s.price_5d,
                "price10d": s.price_10d,
                "price20d": s.price_20d,
                "return5d": round(s.return_5d * 100, 2) if s.return_5d is not None else None,
                "return10d": round(s.return_10d * 100, 2) if s.return_10d is not None else None,
                "return20d": round(s.return_20d * 100, 2) if s.return_20d is not None else None,
                "isWin5d": s.is_win_5d,
                "isWin10d": s.is_win_10d,
                "isWin20d": s.is_win_20d,
            }
            for s in signals
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record")
async def record_signal(
    symbol: str,
    signal_type: str,
    score: float,
    probability_up: float,
    entry_price: float,
    strategy_id: Optional[str] = None,
):
    """Record a new signal for tracking.

    Call this when the signal engine generates a new signal.
    """
    try:
        from lobster_quant.src.core.signal_tracker import SignalTracker

        tracker = SignalTracker(data_dir=DATA_DIR)
        signal_id = tracker.record_signal(
            symbol=symbol,
            signal_type=signal_type,
            score=score,
            probability_up=probability_up,
            entry_price=entry_price,
            strategy_id=strategy_id,
        )

        return {"signalId": signal_id, "status": "recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _parse_lookback(lookback: str) -> int:
    """Parse lookback string like '30d' into number of days."""
    lookback = lookback.strip().lower()
    if lookback.endswith("d"):
        try:
            days = int(lookback[:-1])
            if days <= 0 or days > 365:
                raise ValueError(f"Lookback must be between 1 and 365 days, got {days}")
            return days
        except ValueError:
            raise ValueError(f"Invalid lookback format: {lookback}. Use format like '7d', '30d'")
    raise ValueError(f"Invalid lookback format: {lookback}. Use format like '7d', '30d'")
