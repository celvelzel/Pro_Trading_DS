"""
Simple in-memory response cache with TTL support.
No external dependencies — uses dict + time.time().
"""

import time
import hashlib
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Global cache store: {namespace: {key: (timestamp, value)}}
_store: dict[str, dict[str, tuple[float, Any]]] = {}


def _namespace(namespace: str) -> dict[str, tuple[float, Any]]:
    """Get or create a cache namespace."""
    if namespace not in _store:
        _store[namespace] = {}
    return _store[namespace]


def cache_get(namespace: str, key: str, ttl: float) -> Optional[Any]:
    """Get a cached value if it exists and hasn't expired.

    Args:
        namespace: Cache namespace (e.g. "scanner", "backtest")
        key: Cache key (e.g. "US:70")
        ttl: Time-to-live in seconds

    Returns:
        Cached value or None if miss/expired
    """
    ns = _namespace(namespace)
    if key in ns:
        timestamp, value = ns[key]
        if time.time() - timestamp < ttl:
            logger.info(f"[{namespace}] Cache hit for key={key}")
            return value
        else:
            # Expired — clean up
            del ns[key]
    return None


def cache_set(namespace: str, key: str, value: Any) -> None:
    """Store a value in the cache.

    Args:
        namespace: Cache namespace
        key: Cache key
        value: Value to cache
    """
    ns = _namespace(namespace)
    ns[key] = (time.time(), value)


def cache_clear(namespace: Optional[str] = None) -> int:
    """Clear cache entries.

    Args:
        namespace: If provided, clear only this namespace. Otherwise clear all.

    Returns:
        Number of entries cleared
    """
    global _store
    count = 0
    if namespace:
        if namespace in _store:
            count = len(_store[namespace])
            del _store[namespace]
    else:
        for ns_name in _store:
            count += len(_store[ns_name])
        _store = {}
    logger.info(f"[cache] Cleared {count} entries" + (f" in namespace '{namespace}'" if namespace else ""))
    return count


def make_params_hash(**kwargs) -> str:
    """Create a short hash from keyword arguments for cache key construction.

    Args:
        **kwargs: Parameters to hash

    Returns:
        8-character hex hash string
    """
    # Sort keys for deterministic hashing
    param_str = "&".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return hashlib.md5(param_str.encode()).hexdigest()[:8]
