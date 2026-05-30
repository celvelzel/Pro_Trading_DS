"""
Cache API Router
Endpoint for clearing in-memory response caches.
"""

from fastapi import APIRouter
from api.cache import cache_clear
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
