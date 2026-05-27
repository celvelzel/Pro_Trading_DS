"""
Tests for ProviderPool class.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, PropertyMock

from src.data.provider_pool import ProviderPool, ProviderEntry
from src.data.providers.base import DataProvider
from src.data.circuit_breaker import CircuitBreaker, CircuitState


class TestProviderPool:
    """Test suite for ProviderPool."""

    def _make_provider(self, name: str) -> MagicMock:
        """Create a mock DataProvider with the given name."""
        provider = MagicMock(spec=DataProvider)
        type(provider).name = PropertyMock(return_value=name)
        return provider

    # --- Provider addition ---

    def test_add_single_provider(self):
        """Should add provider to pool."""
        pool = ProviderPool("test")
        provider = self._make_provider("test_provider")

        pool.add_provider(provider, priority=1)
        assert pool.provider_count == 1

    def test_add_multiple_providers(self):
        """Should add multiple providers to pool."""
        pool = ProviderPool("test")

        pool.add_provider(self._make_provider("p1"), priority=1)
        pool.add_provider(self._make_provider("p2"), priority=2)
        pool.add_provider(self._make_provider("p3"), priority=3)

        assert pool.provider_count == 3

    def test_add_duplicate_provider_raises(self):
        """Should raise ValueError when adding duplicate provider name."""
        pool = ProviderPool("test")
        pool.add_provider(self._make_provider("dup"), priority=1)

        with pytest.raises(ValueError, match="already exists"):
            pool.add_provider(self._make_provider("dup"), priority=2)

    def test_priority_ordering(self):
        """Should return providers sorted by priority (lowest number first)."""
        pool = ProviderPool("test")

        pool.add_provider(self._make_provider("low_priority"), priority=2)
        pool.add_provider(self._make_provider("high_priority"), priority=1)

        available = pool.get_available_providers()
        assert len(available) == 2
        assert available[0].provider.name == "high_priority"
        assert available[1].provider.name == "low_priority"

    def test_priority_ordering_multiple_insertions(self):
        """Should maintain priority order after multiple insertions."""
        pool = ProviderPool("test")

        pool.add_provider(self._make_provider("mid"), priority=5)
        pool.add_provider(self._make_provider("first"), priority=1)
        pool.add_provider(self._make_provider("last"), priority=10)
        pool.add_provider(self._make_provider("second"), priority=2)

        available = pool.get_available_providers()
        names = [e.provider.name for e in available]
        assert names == ["first", "second", "mid", "last"]

    # --- Availability filtering ---

    def test_filter_unavailable_providers(self):
        """Should filter out providers with open circuit breakers."""
        pool = ProviderPool("test")

        pool.add_provider(self._make_provider("available"), priority=1)
        pool.add_provider(self._make_provider("unavailable"), priority=2)

        # Trip the second provider's circuit breaker
        cb = pool._providers[1].circuit_breaker
        cb._state = CircuitState.OPEN
        cb._last_failure_time = datetime.now()  # prevent auto-transition

        available = pool.get_available_providers()
        assert len(available) == 1
        assert available[0].provider.name == "available"

    def test_half_open_providers_are_available(self):
        """Should include providers in half-open state."""
        pool = ProviderPool("test")

        pool.add_provider(self._make_provider("half_open"), priority=1)

        # Set circuit breaker to half-open
        pool._providers[0].circuit_breaker._state = CircuitState.HALF_OPEN

        available = pool.get_available_providers()
        assert len(available) == 1

    def test_all_providers_unavailable(self):
        """Should return empty list when all providers are unavailable."""
        pool = ProviderPool("test")

        pool.add_provider(self._make_provider("p1"), priority=1)
        pool.add_provider(self._make_provider("p2"), priority=2)

        for entry in pool._providers:
            entry.circuit_breaker._state = CircuitState.OPEN
            entry.circuit_breaker._last_failure_time = datetime.now()

        available = pool.get_available_providers()
        assert len(available) == 0

    def test_empty_pool_returns_empty(self):
        """Should return empty list for pool with no providers."""
        pool = ProviderPool("test")
        assert pool.get_available_providers() == []

    # --- Status reporting ---

    def _make_cb_status(self, state: str = "closed", available: bool = True) -> dict:
        """Create a mock circuit breaker status dict."""
        return {
            "name": "test",
            "state": state,
            "failure_count": 0,
            "success_count": 0,
            "last_failure": None,
            "is_available": available,
            "config": {
                "failure_threshold": 5,
                "recovery_timeout": 60,
                "half_open_max_calls": 1,
            },
        }

    def test_get_provider_status_structure(self):
        """Should return status dict with correct structure."""
        pool = ProviderPool("US")

        pool.add_provider(self._make_provider("alpha"), priority=1)

        # Patch get_status to avoid deadlock in CircuitBreaker (non-reentrant lock)
        pool._providers[0].circuit_breaker.get_status = MagicMock(
            return_value=self._make_cb_status()
        )

        status = pool.get_provider_status()
        assert status["market"] == "US"
        assert status["total_providers"] == 1
        assert status["available_providers"] == 1
        assert isinstance(status["providers"], list)
        assert len(status["providers"]) == 1

    def test_provider_status_entry_fields(self):
        """Should include all expected fields in provider status entry."""
        pool = ProviderPool("test")

        pool.add_provider(self._make_provider("p1"), priority=1)

        pool._providers[0].circuit_breaker.get_status = MagicMock(
            return_value=self._make_cb_status()
        )

        status = pool.get_provider_status()
        entry = status["providers"][0]

        assert entry["name"] == "p1"
        assert entry["priority"] == 1
        assert "circuit_breaker" in entry
        assert entry["success_count"] == 0
        assert entry["failure_count"] == 0
        assert entry["avg_response_time"] == 0.0
        assert entry["last_used"] is None

    def test_status_reflects_available_count(self):
        """Should report correct available provider count."""
        pool = ProviderPool("test")

        pool.add_provider(self._make_provider("up"), priority=1)
        pool.add_provider(self._make_provider("down"), priority=2)

        # Trip one circuit breaker
        cb = pool._providers[1].circuit_breaker
        cb._state = CircuitState.OPEN
        cb._last_failure_time = datetime.now()

        pool._providers[0].circuit_breaker.get_status = MagicMock(
            return_value=self._make_cb_status()
        )
        pool._providers[1].circuit_breaker.get_status = MagicMock(
            return_value=self._make_cb_status(state="open", available=False)
        )

        status = pool.get_provider_status()
        assert status["total_providers"] == 2
        assert status["available_providers"] == 1

    def test_status_empty_pool(self):
        """Should handle empty pool status correctly."""
        pool = ProviderPool("HK")

        status = pool.get_provider_status()
        assert status["market"] == "HK"
        assert status["total_providers"] == 0
        assert status["available_providers"] == 0
        assert status["providers"] == []

    # --- Market property ---

    def test_market_property(self):
        """Should expose market identifier."""
        pool = ProviderPool("CN")
        assert pool.market == "CN"

    # --- Remove provider ---

    def test_remove_existing_provider(self):
        """Should remove provider and return True."""
        pool = ProviderPool("test")
        pool.add_provider(self._make_provider("removable"), priority=1)

        assert pool.remove_provider("removable") is True
        assert pool.provider_count == 0

    def test_remove_nonexistent_provider(self):
        """Should return False when provider not found."""
        pool = ProviderPool("test")
        assert pool.remove_provider("ghost") is False
