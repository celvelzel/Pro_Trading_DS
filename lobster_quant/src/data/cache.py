"""
Lobster Quant - Data Cache
Persistent disk cache with TTL support.
"""

import json
import pickle
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Any
import pandas as pd

from src.utils.logging import get_logger
from src.utils.exceptions import CacheError

logger = get_logger()


class DataCache:
    """Persistent data cache with TTL support.
    
    Stores DataFrames and other data to disk to avoid repeated API calls.
    """
    
    def __init__(self, cache_dir: str = "./data/cache", default_ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._memory_cache: dict[str, Any] = {}
        logger.info(f"Cache initialized at {self.cache_dir}")
    
    def _get_cache_key(self, key: str) -> str:
        """Generate a safe filename from key."""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{self._get_cache_key(key)}.pkl"
    
    def _get_meta_path(self, key: str) -> Path:
        """Get the metadata file path for a cache key."""
        return self.cache_dir / f"{self._get_cache_key(key)}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """Get data from cache if not expired.
        
        Args:
            key: Cache key
        
        Returns:
            Cached data or None if not found/expired
        """
        # Check memory cache first
        if key in self._memory_cache:
            # Check TTL for memory cache too
            meta_path = self._get_meta_path(key)
            if meta_path.exists():
                try:
                    with open(meta_path, 'r') as f:
                        meta = json.load(f)
                    cached_time = datetime.fromisoformat(meta['cached_at'])
                    ttl = meta.get('ttl', self.default_ttl)
                    if datetime.now() - cached_time > timedelta(seconds=ttl):
                        # Expired — remove from memory and disk
                        self._memory_cache.pop(key, None)
                        return None
                except Exception:
                    pass
            logger.debug(f"Memory cache hit: {key}")
            return self._memory_cache[key]
        
        cache_path = self._get_cache_path(key)
        meta_path = self._get_meta_path(key)
        
        if not cache_path.exists() or not meta_path.exists():
            return None
        
        try:
            # Check TTL
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            cached_time = datetime.fromisoformat(meta['cached_at'])
            ttl = meta.get('ttl', self.default_ttl)
            
            if datetime.now() - cached_time > timedelta(seconds=ttl):
                logger.debug(f"Cache expired: {key}")
                return None
            
            # Load data
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            
            # Store in memory cache
            self._memory_cache[key] = data
            
            logger.debug(f"Disk cache hit: {key}")
            return data
            
        except Exception as e:
            logger.warning(f"Cache read error for {key}: {e}")
            return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Store data in cache.
        
        Args:
            key: Cache key
            data: Data to cache
            ttl: Time to live in seconds (uses default if not specified)
        """
        cache_path = self._get_cache_path(key)
        meta_path = self._get_meta_path(key)
        
        try:
            # Store in memory
            self._memory_cache[key] = data
            
            # Store on disk
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
            
            # Store metadata
            meta = {
                'cached_at': datetime.now().isoformat(),
                'ttl': ttl if ttl is not None else self.default_ttl,
                'key': key,
                'type': type(data).__name__
            }
            with open(meta_path, 'w') as f:
                json.dump(meta, f)
            
            logger.debug(f"Cache set: {key}")
            
        except Exception as e:
            raise CacheError(f"Failed to cache data for {key}: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete data from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if deleted, False if not found
        """
        cache_path = self._get_cache_path(key)
        meta_path = self._get_meta_path(key)
        
        # Remove from memory
        self._memory_cache.pop(key, None)
        
        # Remove from disk
        deleted = False
        if cache_path.exists():
            cache_path.unlink()
            deleted = True
        if meta_path.exists():
            meta_path.unlink()
            deleted = True
        
        return deleted
    
    def clear(self) -> int:
        """Clear all cached data.
        
        Returns:
            Number of items cleared
        """
        self._memory_cache.clear()
        
        count = 0
        for file in self.cache_dir.glob("*.pkl"):
            file.unlink()
            count += 1
        for file in self.cache_dir.glob("*.json"):
            file.unlink()
        
        logger.info(f"Cache cleared: {count} items removed")
        return count
    
    def get_stats(self) -> dict:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        pkl_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in pkl_files)
        
        return {
            'memory_items': len(self._memory_cache),
            'disk_items': len(pkl_files),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_dir': str(self.cache_dir)
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries.
        
        Returns:
            Number of items removed
        """
        removed = 0
        for meta_file in self.cache_dir.glob("*.json"):
            try:
                with open(meta_file, 'r') as f:
                    meta = json.load(f)
                
                cached_time = datetime.fromisoformat(meta['cached_at'])
                ttl = meta.get('ttl', self.default_ttl)
                
                if datetime.now() - cached_time > timedelta(seconds=ttl):
                    # Remove both files
                    key_hash = meta_file.stem
                    pkl_file = self.cache_dir / f"{key_hash}.pkl"
                    if pkl_file.exists():
                        pkl_file.unlink()
                    meta_file.unlink()
                    removed += 1
                    
            except Exception as e:
                logger.warning(f"Error cleaning up cache file {meta_file}: {e}")
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} expired cache entries")
        
        return removed

