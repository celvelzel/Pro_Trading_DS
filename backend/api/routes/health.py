"""
Lobster Quant - Health API Routes
Endpoints for monitoring data source health and status.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from api.deps import get_data_engine_dep

router = APIRouter()


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
