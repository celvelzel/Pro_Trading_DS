"""
Lobster Quant - Data Cache
Persistent disk cache with TTL support, LRU memory cache, and parquet for DataFrames.
"""

import hashlib
import json
import pickle
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ..utils.exceptions import CacheError
from ..utils.logging import get_logger

logger = get_logger()

# Auto-cleanup runs every N set() calls
_CLEANUP_INTERVAL = 100


class DataCache:
    """Persistent data cache with TTL support and LRU memory eviction.

    Features:
        - LRU memory cache with configurable max items
        - Parquet storage for DataFrames (safe, version-tolerant)
        - Pickle fallback for complex objects (StockData, etc.)
        - Backward compatibility with old pickle-only caches
        - Probabilistic auto-cleanup of expired entries
    """

    def __init__(
        self,
        cache_dir: str = "./data/cache",
        default_ttl: int = 3600,
        max_memory_items: int = 500,
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._max_memory_items = max_memory_items
        self._memory_cache: OrderedDict[str, Any] = OrderedDict()
        self._memory_meta: dict[str, dict] = {}  # key -> {cached_at, ttl}
        self._set_counter: int = 0
        logger.info(f"Cache initialized at {self.cache_dir} (max_memory_items={max_memory_items})")

    # ------------------------------------------------------------------
    # Key / path helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.md5(key.encode()).hexdigest()

    def _meta_path(self, key: str) -> Path:
        return self.cache_dir / f"{self._hash_key(key)}.meta.json"

    def _data_path(self, key: str, extension: str) -> Path:
        return self.cache_dir / f"{self._hash_key(key)}.{extension}"

    # ------------------------------------------------------------------
    # TTL validation
    # ------------------------------------------------------------------

    @staticmethod
    def _is_expired(cached_at: str, ttl: int) -> bool:
        try:
            return datetime.now() - datetime.fromisoformat(cached_at) > timedelta(seconds=ttl)
        except Exception:
            return True  # Treat unparseable metadata as expired

    # ------------------------------------------------------------------
    # Memory cache helpers (LRU)
    # ------------------------------------------------------------------

    def _memory_get(self, key: str) -> Optional[Any]:
        """Get from memory cache. Returns None if missing or expired."""
        if key not in self._memory_cache:
            return None
        meta = self._memory_meta.get(key)
        if meta and self._is_expired(meta["cached_at"], meta.get("ttl", self.default_ttl)):
            self._memory_cache.pop(key, None)
            self._memory_meta.pop(key, None)
            return None
        # Move to end (most-recently-used)
        self._memory_cache.move_to_end(key)
        return self._memory_cache[key]

    def _memory_set(self, key: str, data: Any, cached_at: str, ttl: int) -> None:
        """Store in memory cache with LRU eviction."""
        if key in self._memory_cache:
            self._memory_cache.move_to_end(key)
        self._memory_cache[key] = data
        self._memory_meta[key] = {"cached_at": cached_at, "ttl": ttl}
        # Evict oldest if over limit
        while len(self._memory_cache) > self._max_memory_items:
            evicted_key, _ = self._memory_cache.popitem(last=False)
            self._memory_meta.pop(evicted_key, None)

    # ------------------------------------------------------------------
    # Disk serialization
    # ------------------------------------------------------------------

    def _write_disk(self, key: str, data: Any, ttl: int) -> None:
        """Write data to disk in the appropriate format."""
        cached_at = datetime.now().isoformat()
        meta = {
            "cached_at": cached_at,
            "ttl": ttl,
            "key": key,
        }

        if isinstance(data, pd.DataFrame):
            data_path = self._data_path(key, "parquet")
            data.to_parquet(data_path, index=True)
            meta["format"] = "parquet"
            meta["type"] = "DataFrame"
        else:
            data_path = self._data_path(key, "pkl")
            with open(data_path, "wb") as f:
                pickle.dump(data, f)
            meta["format"] = "pickle"
            meta["type"] = type(data).__name__

        with open(self._meta_path(key), "w") as f:
            json.dump(meta, f)

    def _read_disk(self, key: str) -> Optional[Any]:
        """Read data from disk. Returns None if not found, expired, or unreadable."""
        meta_path = self._meta_path(key)

        # New format: metadata JSON exists
        if meta_path.exists():
            try:
                with open(meta_path, "r") as f:
                    meta = json.load(f)

                if self._is_expired(meta["cached_at"], meta.get("ttl", self.default_ttl)):
                    return None

                fmt = meta.get("format", "pickle")
                if fmt == "parquet":
                    data_path = self._data_path(key, "parquet")
                    if data_path.exists():
                        return pd.read_parquet(data_path)
                elif fmt == "pickle":
                    data_path = self._data_path(key, "pkl")
                    if data_path.exists():
                        with open(data_path, "rb") as f:
                            return pickle.load(f)
            except Exception as e:
                logger.warning(f"Cache read error for {key}: {e}")
            return None

        # Backward compatibility: old pickle-only format (.pkl without .meta.json)
        legacy_path = self._data_path(key, "pkl")
        if legacy_path.exists():
            try:
                with open(legacy_path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Legacy cache read error for {key}: {e}")

        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        """Get data from cache if not expired.

        Checks memory first, then disk. Validates TTL at both levels.

        Args:
            key: Cache key

        Returns:
            Cached data or None if not found/expired
        """
        # 1. Memory cache
        result = self._memory_get(key)
        if result is not None:
            logger.debug(f"Memory cache hit: {key}")
            return result

        # 2. Disk cache
        result = self._read_disk(key)
        if result is not None:
            logger.debug(f"Disk cache hit: {key}")
            # Promote to memory
            cached_at = datetime.now().isoformat()
            self._memory_set(key, result, cached_at, self.default_ttl)
            return result

        return None

    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Store data in both memory and disk cache.

        DataFrames are stored as parquet; other objects as pickle.

        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (uses default if not specified)

        Raises:
            CacheError: If disk write fails
        """
        ttl = ttl if ttl is not None else self.default_ttl
        cached_at = datetime.now().isoformat()

        try:
            # Memory
            self._memory_set(key, data, cached_at, ttl)
            # Disk
            self._write_disk(key, data, ttl)
            logger.debug(f"Cache set: {key}")

            # Probabilistic auto-cleanup
            self._set_counter += 1
            if self._set_counter % _CLEANUP_INTERVAL == 0:
                self.cleanup_expired()

        except Exception as e:
            raise CacheError(f"Failed to cache data for {key}: {e}")

    def delete(self, key: str) -> bool:
        """Delete data from both memory and disk cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        # Memory
        self._memory_cache.pop(key, None)
        self._memory_meta.pop(key, None)

        # Disk — try all possible extensions
        deleted = False
        meta_path = self._meta_path(key)
        if meta_path.exists():
            meta_path.unlink()
            deleted = True

        for ext in ("parquet", "pkl"):
            data_path = self._data_path(key, ext)
            if data_path.exists():
                data_path.unlink()
                deleted = True

        return deleted

    def clear(self) -> int:
        """Clear all cached data.

        Returns:
            Number of data files cleared
        """
        self._memory_cache.clear()
        self._memory_meta.clear()

        count = 0
        for pattern in ("*.parquet", "*.pkl", "*.meta.json"):
            for f in self.cache_dir.glob(pattern):
                f.unlink()
                if not pattern.startswith("*.meta"):
                    count += 1

        logger.info(f"Cache cleared: {count} items removed")
        return count

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with memory items, disk items, and total size
        """
        data_files = list(self.cache_dir.glob("*.parquet")) + list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in data_files)

        return {
            "memory_items": len(self._memory_cache),
            "disk_items": len(data_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir),
        }

    def cleanup_expired(self) -> int:
        """Remove expired cache entries from disk.

        Returns:
            Number of items removed
        """
        removed = 0
        for meta_file in self.cache_dir.glob("*.meta.json"):
            try:
                with open(meta_file, "r") as f:
                    meta = json.load(f)

                if self._is_expired(meta["cached_at"], meta.get("ttl", self.default_ttl)):
                    key_hash = meta_file.stem.replace(".meta", "")
                    # Remove data file (could be parquet or pkl)
                    for ext in ("parquet", "pkl"):
                        data_file = self.cache_dir / f"{key_hash}.{ext}"
                        if data_file.exists():
                            data_file.unlink()
                    meta_file.unlink()
                    removed += 1
            except Exception as e:
                logger.warning(f"Error cleaning up cache file {meta_file}: {e}")

        if removed > 0:
            logger.info(f"Cleaned up {removed} expired cache entries")

        return removed
