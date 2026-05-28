"""
Lobster Quant - Fallback Chain (formerly Provider Pool)
Manages multiple data providers with priority-based fallback, circuit breaker
protection, and sliding-window metrics.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from .providers.base import DataProvider
from ..utils.logging import get_logger

logger = get_logger()

# Maximum number of request records kept per provider for sliding-window metrics
_MAX_HISTORY = 200


@dataclass
class RequestRecord:
    """A single request record for sliding-window metrics."""

    timestamp: datetime
    success: bool
    response_time: float


@dataclass
class ProviderEntry:
    """Entry in the fallback chain.

    Tracks a data provider along with its circuit breaker, priority,
    and sliding-window request history for monitoring and selection.

    Attributes:
        provider: The data source instance
        circuit_breaker: Circuit breaker protecting this provider
        priority: Priority level (1 = highest priority)
        _history: Sliding window of recent request records
        last_used: Timestamp of last usage (None if never used)
    """

    provider: DataProvider
    circuit_breaker: CircuitBreaker
    priority: int
    _history: deque = field(default_factory=lambda: deque(maxlen=_MAX_HISTORY))
    last_used: Optional[datetime] = None

    # ---- Sliding-window properties ----

    @property
    def success_count(self) -> int:
        """Number of successful requests in the history window."""
        return sum(1 for r in self._history if r.success)

    @property
    def failure_count(self) -> int:
        """Number of failed requests in the history window."""
        return sum(1 for r in self._history if not r.success)

    @property
    def avg_response_time(self) -> float:
        """Average response time across the history window."""
        if not self._history:
            return 0.0
        return sum(r.response_time for r in self._history) / len(self._history)

    def record_request(self, success: bool, response_time: float) -> None:
        """Record a request result in the sliding window.

        Args:
            success: Whether the request succeeded
            response_time: Request duration in seconds
        """
        self._history.append(
            RequestRecord(timestamp=datetime.now(), success=success, response_time=response_time)
        )
        self.last_used = datetime.now()

    def get_windowed_metrics(self, window_minutes: int = 5) -> Dict[str, Any]:
        """Get metrics scoped to a time window.

        Args:
            window_minutes: Look-back window in minutes

        Returns:
            Dictionary with windowed success/failure counts, avg response time, total calls
        """
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        windowed = [r for r in self._history if r.timestamp >= cutoff]

        if not windowed:
            return {
                "window_minutes": window_minutes,
                "total_calls": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
                "avg_response_time": 0.0,
            }

        successes = sum(1 for r in windowed if r.success)
        failures = len(windowed) - successes
        avg_time = sum(r.response_time for r in windowed) / len(windowed)

        return {
            "window_minutes": window_minutes,
            "total_calls": len(windowed),
            "success_count": successes,
            "failure_count": failures,
            "success_rate": round(successes / len(windowed), 3) if windowed else 0.0,
            "avg_response_time": round(avg_time, 3),
        }


class FallbackChain:
    """Chain of data providers with priority-based fallback.

    Manages multiple data providers for a given market, each protected
    by its own circuit breaker. Providers are selected by priority
    (lowest number = highest priority) and only if their circuit breaker
    allows requests.

    Usage::

        chain = FallbackChain("US")
        chain.add_provider(yfinance_provider, priority=1)
        chain.add_provider(fallback_provider, priority=2)

        # Get providers ordered by priority, filtered by availability
        available = chain.get_available_providers()

        # Get monitoring status
        status = chain.get_provider_status()
    """

    def __init__(self, market: str):
        """Initialize the fallback chain.

        Args:
            market: Market identifier (e.g., 'US', 'HK', 'CN')
        """
        self._market = market
        self._providers: List[ProviderEntry] = []

    @property
    def market(self) -> str:
        """Get the market identifier."""
        return self._market

    @property
    def provider_count(self) -> int:
        """Get total number of registered providers."""
        return len(self._providers)

    def add_provider(self, provider: DataProvider, priority: int) -> None:
        """Add a provider to the chain.

        Creates a circuit breaker for the provider and inserts it into
        the chain sorted by priority.

        Args:
            provider: The data provider instance to add
            priority: Priority level (1 = highest, higher numbers = lower priority)

        Raises:
            ValueError: If a provider with the same name already exists
        """
        existing_names = {e.provider.name for e in self._providers}
        if provider.name in existing_names:
            raise ValueError(f"Provider '{provider.name}' already exists in {self._market} chain")

        entry = ProviderEntry(
            provider=provider,
            circuit_breaker=CircuitBreaker(name=provider.name),
            priority=priority,
        )
        self._providers.append(entry)
        self._providers.sort(key=lambda x: x.priority)
        logger.info(
            f"Added provider '{provider.name}' to {self._market} chain (priority={priority})"
        )

    def remove_provider(self, name: str) -> bool:
        """Remove a provider from the chain by name.

        Args:
            name: Name of the provider to remove

        Returns:
            True if the provider was found and removed, False otherwise
        """
        for i, entry in enumerate(self._providers):
            if entry.provider.name == name:
                self._providers.pop(i)
                logger.info(f"Removed provider '{name}' from {self._market} chain")
                return True
        logger.warning(f"Provider '{name}' not found in {self._market} chain")
        return False

    def get_available_providers(self) -> List[ProviderEntry]:
        """Get list of available providers sorted by priority.

        Filters out providers whose circuit breaker is in OPEN state
        (not allowing requests), then returns the remaining providers
        ordered by priority (lowest number first).

        Returns:
            List of ProviderEntry instances that are currently available,
            sorted by priority ascending
        """
        available = [e for e in self._providers if e.circuit_breaker.is_available]
        return sorted(available, key=lambda x: x.priority)

    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers for monitoring.

        Returns a dictionary suitable for logging, dashboards, or
        health-check endpoints. Includes per-provider metrics with
        sliding-window statistics.

        Returns:
            Dictionary with market name and provider details list
        """
        return {
            "market": self._market,
            "total_providers": len(self._providers),
            "available_providers": len(
                [e for e in self._providers if e.circuit_breaker.is_available]
            ),
            "providers": [
                {
                    "name": e.provider.name,
                    "priority": e.priority,
                    "circuit_breaker": e.circuit_breaker.get_status(),
                    "success_count": e.success_count,
                    "failure_count": e.failure_count,
                    "avg_response_time": round(e.avg_response_time, 3),
                    "last_used": e.last_used.isoformat() if e.last_used else None,
                    "metrics_5min": e.get_windowed_metrics(5),
                }
                for e in self._providers
            ],
        }

    def get_provider_metrics(self, name: str, window_minutes: int = 5) -> Optional[Dict[str, Any]]:
        """Get windowed metrics for a specific provider.

        Args:
            name: Provider name
            window_minutes: Look-back window in minutes

        Returns:
            Metrics dictionary, or None if provider not found
        """
        for entry in self._providers:
            if entry.provider.name == name:
                return entry.get_windowed_metrics(window_minutes)
        return None


# Backward compatibility alias
ProviderPool = FallbackChain
