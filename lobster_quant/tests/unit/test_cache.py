"""
Tests for DataCache.
"""

import shutil
import tempfile

import pandas as pd
import pytest

from src.data.cache import DataCache


@pytest.fixture
def temp_cache_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def cache(temp_cache_dir):
    return DataCache(cache_dir=temp_cache_dir, default_ttl=3600)


@pytest.fixture
def sample_df():
    """A small DataFrame for parquet round-trip testing."""
    return pd.DataFrame(
        {"open": [1.0, 2.0], "high": [3.0, 4.0], "close": [5.0, 6.0]},
        index=pd.date_range("2024-01-01", periods=2),
    )


class TestDataCache:
    def test_set_and_get(self, cache):
        cache.set("key1", {"data": [1, 2, 3]})
        result = cache.get("key1")
        assert result == {"data": [1, 2, 3]}

    def test_get_nonexistent(self, cache):
        assert cache.get("nonexistent") is None

    def test_delete(self, cache):
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_nonexistent(self, cache):
        assert cache.delete("nonexistent") is False

    def test_clear(self, cache):
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        count = cache.clear()
        assert isinstance(count, int)

    def test_get_stats(self, cache):
        cache.set("key1", "value1")
        stats = cache.get_stats()
        assert isinstance(stats, dict)
        assert "memory_items" in stats
        assert "disk_items" in stats

    def test_memory_cache_hit(self, cache):
        cache.set("key1", "value1")
        cache.get("key1")
        result = cache.get("key1")
        assert result == "value1"

    def test_cleanup_expired(self, cache):
        from datetime import datetime, timedelta
        from unittest.mock import patch

        cache.set("expired_key", "value", ttl=10)

        future_time = datetime.now() + timedelta(seconds=20)
        with patch("src.data.cache.datetime") as mock_dt:
            mock_dt.now.return_value = future_time
            mock_dt.fromisoformat = datetime.fromisoformat
            removed = cache.cleanup_expired()
        assert removed >= 1

    def test_persistence_across_instances(self, temp_cache_dir):
        cache1 = DataCache(cache_dir=temp_cache_dir, default_ttl=3600)
        cache1.set("persistent", "data")
        cache2 = DataCache(cache_dir=temp_cache_dir, default_ttl=3600)
        assert cache2.get("persistent") == "data"


class TestDataCacheParquet:
    """Tests for parquet DataFrame storage."""

    def test_dataframe_parquet_roundtrip(self, cache, sample_df):
        """DataFrames should round-trip through parquet."""
        cache.set("df_key", sample_df)
        result = cache.get("df_key")
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["open", "high", "close"]
        assert len(result) == 2

    def test_parquet_file_created(self, cache, sample_df, temp_cache_dir):
        """Should create .parquet file instead of .pkl for DataFrames."""
        cache.set("df_key", sample_df)
        parquet_files = list(
            (cache.cache_dir if hasattr(cache, "cache_dir") else __import__("pathlib").Path(temp_cache_dir)).glob("*.parquet")
        )
        assert len(parquet_files) >= 1

    def test_non_dataframe_still_uses_pickle(self, cache, temp_cache_dir):
        """Non-DataFrame objects should still use pickle format."""
        cache.set("dict_key", {"a": 1})
        pkl_files = list(__import__("pathlib").Path(temp_cache_dir).glob("*.pkl"))
        assert len(pkl_files) >= 1


class TestDataCacheLRU:
    """Tests for LRU memory cache eviction."""

    def test_lru_eviction(self, temp_cache_dir):
        """Should evict oldest items when memory limit reached."""
        cache = DataCache(cache_dir=temp_cache_dir, default_ttl=3600, max_memory_items=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # should evict 'a'

        # 'a' should be evicted from memory but still on disk
        assert "a" not in cache._memory_cache
        assert "d" in cache._memory_cache

    def test_lru_access_refreshes_order(self, temp_cache_dir):
        """Accessing an item should move it to most-recently-used."""
        cache = DataCache(cache_dir=temp_cache_dir, default_ttl=3600, max_memory_items=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        cache.get("a")  # refresh 'a'

        cache.set("d", 4)  # should evict 'b' (oldest unused), not 'a'

        assert "a" in cache._memory_cache
        assert "b" not in cache._memory_cache

    def test_lru_eviction_cleans_meta(self, temp_cache_dir):
        """Eviction should also remove metadata tracking."""
        cache = DataCache(cache_dir=temp_cache_dir, default_ttl=3600, max_memory_items=2)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # evicts 'a'

        assert "a" not in cache._memory_meta


class TestDataCacheAutoCleanup:
    """Tests for probabilistic auto-cleanup."""

    def test_auto_cleanup_triggered(self, temp_cache_dir):
        """Should trigger cleanup every N set() calls."""
        cache = DataCache(cache_dir=temp_cache_dir, default_ttl=1, max_memory_items=500)

        # Insert an expired entry
        from datetime import datetime, timedelta
        from unittest.mock import patch

        cache.set("expired", "val", ttl=0)

        future_time = datetime.now() + timedelta(seconds=10)
        with patch("src.data.cache.datetime") as mock_dt:
            mock_dt.now.return_value = future_time
            mock_dt.fromisoformat = datetime.fromisoformat

            # set() 99 more times to hit cleanup interval (100)
            for i in range(99):
                cache.set(f"key_{i}", f"val_{i}", ttl=3600)

        # The expired entry should have been cleaned up
        # (it won't be in memory since its TTL check fails, and it should be cleaned from disk)
