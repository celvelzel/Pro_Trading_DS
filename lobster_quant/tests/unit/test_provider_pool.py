"""
Tests for FallbackChain (formerly ProviderPool).
"""

from datetime import datetime
from unittest.mock import MagicMock, PropertyMock

import pytest

from src.data.circuit_breaker import CircuitState
from src.data.provider_pool import FallbackChain


class TestFallbackChain:
    """Test suite for FallbackChain."""

    def _make_provider(self, name: str) -> MagicMock:
        """Create a mock DataProvider with the given name."""
        provider = MagicMock()
        provider.name = name
        return provider

    # --- Provider addition ---

    def test_add_single_provider(self):
        """Should add provider to chain."""
        chain = FallbackChain("test")
        provider = self._make_provider("test_provider")

        chain.add_provider(provider, priority=1)
        assert chain.provider_count == 1

    def test_add_multiple_providers(self):
        """Should add multiple providers to chain."""
        chain = FallbackChain("test")

        chain.add_provider(self._make_provider("p1"), priority=1)
        chain.add_provider(self._make_provider("p2"), priority=2)
        chain.add_provider(self._make_provider("p3"), priority=3)

        assert chain.provider_count == 3

    def test_add_duplicate_provider_raises(self):
        """Should raise ValueError when adding duplicate provider name."""
        chain = FallbackChain("test")
        chain.add_provider(self._make_provider("dup"), priority=1)

        with pytest.raises(ValueError, match="already exists"):
            chain.add_provider(self._make_provider("dup"), priority=2)

    def test_priority_ordering(self):
        """Should return providers sorted by priority (lowest number first)."""
        chain = FallbackChain("test")

        chain.add_provider(self._make_provider("low_priority"), priority=2)
        chain.add_provider(self._make_provider("high_priority"), priority=1)

        available = chain.get_available_providers()
        assert len(available) == 2
        assert available[0].provider.name == "high_priority"
        assert available[1].provider.name == "low_priority"

    def test_priority_ordering_multiple_insertions(self):
        """Should maintain priority order after multiple insertions."""
        chain = FallbackChain("test")

        chain.add_provider(self._make_provider("mid"), priority=5)
        chain.add_provider(self._make_provider("first"), priority=1)
        chain.add_provider(self._make_provider("last"), priority=10)
        chain.add_provider(self._make_provider("second"), priority=2)

        available = chain.get_available_providers()
        names = [e.provider.name for e in available]
        assert names == ["first", "second", "mid", "last"]

    # --- Availability filtering ---

    def test_filter_unavailable_providers(self):
        """Should filter out providers with open circuit breakers."""
        chain = FallbackChain("test")

        chain.add_provider(self._make_provider("available"), priority=1)
        chain.add_provider(self._make_provider("unavailable"), priority=2)

        # Trip the second provider's circuit breaker
        cb = chain._providers[1].circuit_breaker
        cb._state = CircuitState.OPEN
        cb._last_failure_time = datetime.now()  # prevent auto-transition

        available = chain.get_available_providers()
        assert len(available) == 1
        assert available[0].provider.name == "available"

    def test_half_open_providers_are_available(self):
        """Should include providers in half-open state."""
        chain = FallbackChain("test")

        chain.add_provider(self._make_provider("half_open"), priority=1)

        # Set circuit breaker to half-open
        chain._providers[0].circuit_breaker._state = CircuitState.HALF_OPEN

        available = chain.get_available_providers()
        assert len(available) == 1

    def test_all_providers_unavailable(self):
        """Should return empty list when all providers are unavailable."""
        chain = FallbackChain("test")

        chain.add_provider(self._make_provider("p1"), priority=1)
        chain.add_provider(self._make_provider("p2"), priority=2)

        for entry in chain._providers:
            entry.circuit_breaker._state = CircuitState.OPEN
            entry.circuit_breaker._last_failure_time = datetime.now()

        available = chain.get_available_providers()
        assert len(available) == 0

    def test_empty_chain_returns_empty(self):
        """Should return empty list for chain with no providers."""
        chain = FallbackChain("test")
        assert chain.get_available_providers() == []

    # --- Status reporting ---

    def test_get_provider_status_structure(self):
        """Should return status dict with correct structure."""
        chain = FallbackChain("US")
        chain.add_provider(self._make_provider("alpha"), priority=1)

        status = chain.get_provider_status()
        assert status["market"] == "US"
        assert status["total_providers"] == 1
        assert status["available_providers"] == 1
        assert isinstance(status["providers"], list)
        assert len(status["providers"]) == 1

    def test_provider_status_entry_fields(self):
        """Should include all expected fields in provider status entry."""
        chain = FallbackChain("test")
        chain.add_provider(self._make_provider("p1"), priority=1)

        status = chain.get_provider_status()
        entry = status["providers"][0]

        assert entry["name"] == "p1"
        assert entry["priority"] == 1
        assert "circuit_breaker" in entry
        assert entry["success_count"] == 0
        assert entry["failure_count"] == 0
        assert entry["avg_response_time"] == 0.0
        assert entry["last_used"] is None
        assert "metrics_5min" in entry

    def test_status_reflects_available_count(self):
        """Should report correct available provider count."""
        chain = FallbackChain("test")

        chain.add_provider(self._make_provider("up"), priority=1)
        chain.add_provider(self._make_provider("down"), priority=2)

        # Trip one circuit breaker
        cb = chain._providers[1].circuit_breaker
        cb._state = CircuitState.OPEN
        cb._last_failure_time = datetime.now()

        status = chain.get_provider_status()
        assert status["total_providers"] == 2
        assert status["available_providers"] == 1

    def test_status_empty_chain(self):
        """Should handle empty chain status correctly."""
        chain = FallbackChain("HK")

        status = chain.get_provider_status()
        assert status["market"] == "HK"
        assert status["total_providers"] == 0
        assert status["available_providers"] == 0
        assert status["providers"] == []

    # --- Market property ---

    def test_market_property(self):
        """Should expose market identifier."""
        chain = FallbackChain("CN")
        assert chain.market == "CN"

    # --- Remove provider ---

    def test_remove_existing_provider(self):
        """Should remove provider and return True."""
        chain = FallbackChain("test")
        chain.add_provider(self._make_provider("removable"), priority=1)

        assert chain.remove_provider("removable") is True
        assert chain.provider_count == 0

    def test_remove_nonexistent_provider(self):
        """Should return False when provider not found."""
        chain = FallbackChain("test")
        assert chain.remove_provider("ghost") is False

    # --- Sliding window metrics ---

    def test_record_request_updates_counts(self):
        """record_request should update success/failure counts."""
        chain = FallbackChain("test")
        chain.add_provider(self._make_provider("p1"), priority=1)

        entry = chain._providers[0]
        entry.record_request(success=True, response_time=0.5)
        entry.record_request(success=True, response_time=0.3)
        entry.record_request(success=False, response_time=1.2)

        assert entry.success_count == 2
        assert entry.failure_count == 1
        assert entry.last_used is not None

    def test_avg_response_time(self):
        """avg_response_time should compute correctly."""
        chain = FallbackChain("test")
        chain.add_provider(self._make_provider("p1"), priority=1)

        entry = chain._providers[0]
        entry.record_request(success=True, response_time=1.0)
        entry.record_request(success=True, response_time=3.0)

        assert entry.avg_response_time == pytest.approx(2.0)

    def test_avg_response_time_empty_history(self):
        """avg_response_time should be 0 when no requests recorded."""
        chain = FallbackChain("test")
        chain.add_provider(self._make_provider("p1"), priority=1)

        assert chain._providers[0].avg_response_time == 0.0

    def test_get_windowed_metrics(self):
        """get_windowed_metrics should return correct structure."""
        chain = FallbackChain("test")
        chain.add_provider(self._make_provider("p1"), priority=1)

        entry = chain._providers[0]
        entry.record_request(success=True, response_time=0.5)
        entry.record_request(success=False, response_time=1.0)

        metrics = entry.get_windowed_metrics(window_minutes=5)
        assert metrics["total_calls"] == 2
        assert metrics["success_count"] == 1
        assert metrics["failure_count"] == 1
        assert metrics["success_rate"] == pytest.approx(0.5)
        assert metrics["window_minutes"] == 5

    def test_get_provider_metrics(self):
        """get_provider_metrics should find provider by name."""
        chain = FallbackChain("test")
        chain.add_provider(self._make_provider("p1"), priority=1)

        chain._providers[0].record_request(success=True, response_time=0.5)

        metrics = chain.get_provider_metrics("p1", window_minutes=5)
        assert metrics is not None
        assert metrics["total_calls"] == 1

    def test_get_provider_metrics_not_found(self):
        """get_provider_metrics should return None for unknown provider."""
        chain = FallbackChain("test")
        assert chain.get_provider_metrics("nonexistent") is None

    def test_status_includes_metrics_5min(self):
        """Provider status should include 5-minute windowed metrics."""
        chain = FallbackChain("test")
        chain.add_provider(self._make_provider("p1"), priority=1)

        chain._providers[0].record_request(success=True, response_time=0.5)

        status = chain.get_provider_status()
        entry = status["providers"][0]
        assert "metrics_5min" in entry
        assert entry["metrics_5min"]["total_calls"] == 1

    # --- Backward compatibility ---

    def test_provider_pool_alias(self):
        """ProviderPool should be an alias for FallbackChain."""
        from src.data.provider_pool import ProviderPool

        assert ProviderPool is FallbackChain
