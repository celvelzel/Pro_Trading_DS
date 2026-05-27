"""
Lobster Quant - Health API Routes
Endpoints for monitoring data source health and status.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

router = APIRouter()


@router.get("/data-sources")
async def get_data_sources_status() -> Dict[str, Any]:
    """
    Get status of all data source pools.

    Returns:
        JSON object with status of each market's provider pool
    """
    try:
        from src.core.data_engine import DataEngine

        engine = DataEngine()
        return engine.get_provider_status()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get data source status: {str(e)}"
        )


@router.get("/data-sources/{market}")
async def get_market_status(market: str) -> Dict[str, Any]:
    """
    Get status of a specific market's provider pool.

    Args:
        market: Market identifier (us_stock, hk_stock, a_stock)

    Returns:
        JSON object with market's provider pool status
    """
    try:
        from src.core.data_engine import DataEngine

        engine = DataEngine()
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
