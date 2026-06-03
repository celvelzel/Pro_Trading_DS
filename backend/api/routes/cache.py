"""
Cache API Router
Endpoints for in-memory response cache management and stats.
"""

from fastapi import APIRouter
from api.cache import cache_clear, get_stats, get_hit_rate
from lobster_quant.src.utils.logging import get_logger

logger = get_logger()

router = APIRouter()


@router.post("/clear")
async def clear_cache():
    """
    Clear all in-memory response caches.

    Returns:
        Status with number of entries cleared
    """
    entries = cache_clear()
    logger.info(f"[cache/clear] Cleared {entries} cache entries")
    return {"status": "cleared", "entries": entries}


@router.get("/stats")
async def cache_stats():
    """
    Return cache hit/miss statistics and overall hit rate.

    Returns:
        {
            "overall_hit_rate": float (0.0-1.0),
            "namespaces": {namespace: {"hits": int, "misses": int}}
        }
    """
    stats = get_stats()
    overall_hit_rate = get_hit_rate()
    return {"overall_hit_rate": overall_hit_rate, "namespaces": stats}
