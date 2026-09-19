"""
Lobster Quant - Health API Routes
Endpoints for monitoring data source health and status.
"""

import os

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from api.deps import get_data_engine_dep

router = APIRouter()


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def readiness() -> dict:
    checks: dict[str, dict[str, str]] = {}
    try:
        from sqlalchemy import text
        from db.session import sync_engine

        with sync_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = {"status": "ready"}
    except Exception:
        checks["database"] = {"status": "not_ready", "code": "DATABASE_UNAVAILABLE"}
    configured = bool(os.getenv("AI_API_KEY", "").strip())
    checks["ai_provider"] = {
        "status": "ready" if configured else "not_ready",
        "code": "" if configured else "AI_PROVIDER_NOT_CONFIGURED",
    }
    checks["redis"] = {"status": "configured" if os.getenv("REDIS_URL") else "inline_local_mode"}
    return {
        "status": "ready" if checks["database"]["status"] == "ready" else "not_ready",
        "checks": checks,
    }


@router.get("/data-sources")
async def get_data_sources_status() -> Dict[str, Any]:
    """
    Get status of all data source pools.

    Returns:
        JSON object with status of each market's fallback chain
    """
    try:
        engine = get_data_engine_dep()
        return engine.get_provider_status()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get data source status: {str(e)}"
        )


@router.get("/data-sources/{market}")
async def get_market_status(market: str) -> Dict[str, Any]:
    """
    Get status of a specific market's fallback chain.

    Args:
        market: Market identifier (us_stock, hk_stock, a_stock)

    Returns:
        JSON object with market's fallback chain status
    """
    try:
        engine = get_data_engine_dep()
        status = engine.get_provider_status()

        if market not in status:
            raise HTTPException(
                status_code=404,
                detail=f"Market '{market}' not found"
            )

        return status[market]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get market status: {str(e)}"
        )
