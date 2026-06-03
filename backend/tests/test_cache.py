"""
Tests for backend.api.cache — in-memory response cache.
"""

import pytest
from api.cache import make_cache_key, cache_get, cache_set, cache_clear


@pytest.fixture(autouse=True)
def _clear_cache():
    """Clear all cache namespaces before each test."""
    cache_clear()
    yield
    cache_clear()


class TestMakeCacheKey:
    """Tests for make_cache_key."""

    def test_symbol_only(self):
        assert make_cache_key("AAPL") == "AAPL"

    def test_symbol_with_period(self):
        assert make_cache_key("AAPL", "1y") == "AAPL:1y"

    def test_symbol_with_5y(self):
        assert make_cache_key("AAPL", "5y") == "AAPL:5y"

    def test_symbol_with_1m(self):
        assert make_cache_key("MSFT", "1m") == "MSFT:1m"

    def test_same_symbol_different_periods_differ(self):
        key_1m = make_cache_key("AAPL", "1m")
        key_5y = make_cache_key("AAPL", "5y")
        assert key_1m != key_5y
        assert key_1m == "AAPL:1m"
        assert key_5y == "AAPL:5y"

    def test_period_none_returns_symbol_only(self):
        assert make_cache_key("TSLA", None) == "TSLA"

    def test_period_none_same_as_no_period(self):
        assert make_cache_key("TSLA", None) == make_cache_key("TSLA")


class TestCacheWithPeriod:
    """Integration tests verifying period-aware caching works end-to-end."""

    def test_different_periods_store_separate_values(self):
        """Same symbol with different periods should not collide."""
        cache_set("stocks", make_cache_key("AAPL", "1m"), {"period": "1m"})
        cache_set("stocks", make_cache_key("AAPL", "5y"), {"period": "5y"})

        val_1m = cache_get("stocks", make_cache_key("AAPL", "1m"), ttl=300)
        val_5y = cache_get("stocks", make_cache_key("AAPL", "5y"), ttl=300)

        assert val_1m == {"period": "1m"}
        assert val_5y == {"period": "5y"}

    def test_same_period_returns_same_value(self):
        """Same symbol and period should return cached value."""
        cache_set("stocks", make_cache_key("AAPL", "1y"), {"data": 42})
        result = cache_get("stocks", make_cache_key("AAPL", "1y"), ttl=300)
        assert result == {"data": 42}

    def test_no_period_backward_compatible(self):
        """Using make_cache_key(symbol) is backward compatible with old format."""
        cache_set("signals", make_cache_key("MSFT"), {"signal": "bullish"})
        result = cache_get("signals", make_cache_key("MSFT"), ttl=300)
        assert result == {"signal": "bullish"}
