"""
Tests for DataCache.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from src.data.cache import DataCache


@pytest.fixture
def temp_cache_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def cache(temp_cache_dir):
    return DataCache(cache_dir=temp_cache_dir, default_ttl=3600)


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
        assert 'memory_items' in stats
        assert 'disk_items' in stats

    def test_memory_cache_hit(self, cache):
        cache.set("key1", "value1")
        cache.get("key1")
        result = cache.get("key1")
        assert result == "value1"

    def test_cleanup_expired(self, cache):
        from unittest.mock import patch
        from datetime import datetime, timedelta
        
        cache.set("expired_key", "value", ttl=10)
        
        future_time = datetime.now() + timedelta(seconds=20)
        with patch('src.data.cache.datetime') as mock_dt:
            mock_dt.now.return_value = future_time
            mock_dt.fromisoformat = datetime.fromisoformat
            removed = cache.cleanup_expired()
        assert removed >= 1

    def test_persistence_across_instances(self, temp_cache_dir):
        cache1 = DataCache(cache_dir=temp_cache_dir, default_ttl=3600)
        cache1.set("persistent", "data")
        cache2 = DataCache(cache_dir=temp_cache_dir, default_ttl=3600)
        assert cache2.get("persistent") == "data"
