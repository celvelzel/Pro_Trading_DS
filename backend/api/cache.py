"""
In-memory response cache with TTL support and LRU eviction.
No external dependencies — uses OrderedDict + time.time().
"""

import time
import hashlib
import logging
from collections import OrderedDict
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Maximum items per namespace before LRU eviction
_MAX_ITEMS: int = 1000

# Global cache store: {namespace: OrderedDict[key -> (timestamp, value)]}
_store: dict[str, OrderedDict[str, tuple[float, Any]]] = {}

# Hit/miss counters (per namespace)
_hits: dict[str, int] = {}
_misses: dict[str, int] = {}


def set_max_items(max_items: int) -> None:
    """Set the maximum number of items per namespace.

    Args:
        max_items: Maximum cache entries per namespace (must be > 0)
    """
    global _MAX_ITEMS
    if max_items <= 0:
        raise ValueError("max_items must be positive")
    _MAX_ITEMS = max_items
    logger.info(f"[cache] Max items per namespace set to {max_items}")


def get_stats() -> dict[str, dict[str, int]]:
    """Return hit/miss statistics per namespace.

    Returns:
        Dict of {namespace: {"hits": N, "misses": N}}
    """
    stats = {}
    all_ns = set(list(_hits.keys()) + list(_misses.keys()))
    for ns in all_ns:
        stats[ns] = {"hits": _hits.get(ns, 0), "misses": _misses.get(ns, 0)}
    return stats


def get_hit_rate(namespace: Optional[str] = None) -> float:
    """Return overall or per-namespace cache hit rate (0.0 – 1.0).

    Args:
        namespace: If provided, return hit rate for this namespace only.
                   Otherwise return the aggregate hit rate across all namespaces.

    Returns:
        Hit rate as a float between 0.0 and 1.0. Returns 0.0 when no requests.
    """
    if namespace:
        h = _hits.get(namespace, 0)
        m = _misses.get(namespace, 0)
    else:
        h = sum(_hits.values())
        m = sum(_misses.values())
    total = h + m
    return h / total if total > 0 else 0.0


def _namespace(namespace: str) -> OrderedDict[str, tuple[float, Any]]:
    """Get or create a cache namespace as an OrderedDict."""
    if namespace not in _store:
        _store[namespace] = OrderedDict()
    return _store[namespace]


def cache_get(namespace: str, key: str, ttl: float) -> Optional[Any]:
    """Get a cached value if it exists and hasn't expired.

    Moves accessed entries to the end (most-recently-used) for LRU eviction.

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
            # Hit — move to end (most recently used)
            ns.move_to_end(key)
            _hits[namespace] = _hits.get(namespace, 0) + 1
            logger.debug(f"[{namespace}] Cache hit for key={key}")
            return value
        else:
            # Expired — clean up
            del ns[key]
    # Miss
    _misses[namespace] = _misses.get(namespace, 0) + 1
    logger.debug(f"[{namespace}] Cache miss for key={key}")
    return None


def cache_set(namespace: str, key: str, value: Any) -> None:
    """Store a value in the cache with LRU eviction.

    When the namespace exceeds max_items, the least-recently-used
    entry is evicted automatically.

    Args:
        namespace: Cache namespace
        key: Cache key
        value: Value to cache
    """
    ns = _namespace(namespace)

    # If key already exists, update it and move to end
    if key in ns:
        ns.move_to_end(key)
        ns[key] = (time.time(), value)
        return

    # New key — evict LRU if at capacity
    if len(ns) >= _MAX_ITEMS:
        evicted_key, _ = ns.popitem(last=False)
        logger.info(f"[{namespace}] LRU evicted key={evicted_key} (capacity={_MAX_ITEMS})")

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
            _hits.pop(namespace, None)
            _misses.pop(namespace, None)
    else:
        for ns_name in _store:
            count += len(_store[ns_name])
        _store = {}
        _hits.clear()
        _misses.clear()
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


def make_cache_key(symbol: str, period: Optional[str] = None) -> str:
    """Build a deterministic cache key from symbol and optional period.

    Args:
        symbol: Stock symbol (e.g. "AAPL")
        period: Time period (e.g. "1y", "5y"). If None, returns just the symbol.

    Returns:
        Colon-joined cache key string (e.g. "AAPL:1y" or "AAPL")
    """
    if period:
        return f"{symbol}:{period}"
    return symbol


def cache_get_or_set(
    namespace: str,
    key: str,
    ttl: float,
    factory,
) -> Any:
    """Get from cache or compute, store, and return.

    Convenience wrapper that eliminates the get-check-set pattern in route handlers.

    Args:
        namespace: Cache namespace
        key: Cache key
        ttl: Time-to-live in seconds
        factory: Callable that returns the value to cache on miss

    Returns:
        Cached or freshly computed value
    """
    cached = cache_get(namespace, key, ttl)
    if cached is not None:
        return cached
    value = factory()
    cache_set(namespace, key, value)
    return value
