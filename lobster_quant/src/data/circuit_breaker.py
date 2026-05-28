"""
Lobster Quant - Circuit Breaker
Prevents cascading failures by tracking data source health.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import threading

from ..utils.logging import get_logger

logger = get_logger()


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Circuit tripped, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery, limited requests


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: int = 60  # Seconds before half-open attempt
    half_open_max_calls: int = 1  # Max calls in half-open state


class CircuitBreaker:
    """
    Circuit breaker for data source protection.

    States:
        CLOSED: Normal operation, all requests pass through
        OPEN: Circuit tripped, all requests fail fast
        HALF_OPEN: Testing recovery, limited requests allowed

    Transitions:
        CLOSED -> OPEN: When failures >= threshold
        OPEN -> HALF_OPEN: When recovery timeout elapsed
        HALF_OPEN -> CLOSED: On success
        HALF_OPEN -> OPEN: On failure
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker (e.g., provider name)
            config: Configuration overrides
        """
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_state_change: datetime = datetime.now()
        self._lock = threading.RLock()  # Reentrant lock to avoid deadlock

        logger.info(f"CircuitBreaker '{name}' initialized: state={self._state.value}")

    @property
    def name(self) -> str:
        """Get circuit breaker name."""
        return self._name

    @property
    def state(self) -> CircuitState:
        """
        Get current state, checking for automatic transitions.

        Returns:
            Current CircuitState
        """
        with self._lock:
            # Check if OPEN should transition to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state

    @property
    def is_available(self) -> bool:
        """
        Check if circuit breaker allows requests.

        Returns:
            True if requests are allowed (CLOSED or HALF_OPEN with available calls)
        """
        current_state = self.state  # This triggers state check

        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self._config.half_open_max_calls
        else:  # OPEN
            return False

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    @property
    def success_count(self) -> int:
        """Get current success count."""
        return self._success_count

    @property
    def last_failure_time(self) -> Optional[datetime]:
        """Get last failure timestamp."""
        return self._last_failure_time

    def record_success(self) -> None:
        """
        Record a successful call.

        Effects:
            - Resets failure count
            - Increments success count
            - Transitions HALF_OPEN -> CLOSED
        """
        with self._lock:
            self._failure_count = 0
            self._success_count += 1

            if self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.CLOSED)
                logger.info(
                    f"CircuitBreaker '{self._name}' recovered: "
                    f"HALF_OPEN -> CLOSED (success_count={self._success_count})"
                )

    def record_failure(self) -> None:
        """
        Record a failed call.

        Effects:
            - Increments failure count
            - Records failure timestamp
            - Transitions CLOSED -> OPEN if threshold reached
            - Transitions HALF_OPEN -> OPEN on any failure
        """
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            if self._state == CircuitState.CLOSED:
                if self._failure_count >= self._config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
                    logger.warning(
                        f"CircuitBreaker '{self._name}' tripped: "
                        f"CLOSED -> OPEN (failures={self._failure_count}, "
                        f"threshold={self._config.failure_threshold})"
                    )
            elif self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
                logger.warning(
                    f"CircuitBreaker '{self._name}' recovery failed: " f"HALF_OPEN -> OPEN"
                )

    def reset(self) -> None:
        """
        Manually reset circuit breaker to CLOSED state.

        Use with caution - only when you know the source is healthy.
        """
        with self._lock:
            old_state = self._state
            self._failure_count = 0
            self._half_open_calls = 0
            self._transition_to(CircuitState.CLOSED)
            logger.info(
                f"CircuitBreaker '{self._name}' manually reset: " f"{old_state.value} -> CLOSED"
            )

    def get_status(self) -> dict:
        """
        Get circuit breaker status for monitoring.

        Returns:
            Dictionary with status information
        """
        with self._lock:
            return {
                "name": self._name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure": (
                    self._last_failure_time.isoformat() if self._last_failure_time else None
                ),
                "is_available": self.is_available,
                "config": {
                    "failure_threshold": self._config.failure_threshold,
                    "recovery_timeout": self._config.recovery_timeout,
                    "half_open_max_calls": self._config.half_open_max_calls,
                },
            }

    def _should_attempt_reset(self) -> bool:
        """
        Check if enough time has passed to attempt recovery.

        Returns:
            True if recovery should be attempted
        """
        if self._last_failure_time is None:
            return True

        elapsed = datetime.now() - self._last_failure_time
        return elapsed >= timedelta(seconds=self._config.recovery_timeout)

    def _transition_to(self, new_state: CircuitState) -> None:
        """
        Transition to a new state.

        Args:
            new_state: Target state
        """
        old_state = self._state
        self._state = new_state
        self._last_state_change = datetime.now()

        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        elif new_state == CircuitState.CLOSED:
            self._half_open_calls = 0

        if old_state != new_state:
            logger.debug(
                f"CircuitBreaker '{self._name}' state change: "
                f"{old_state.value} -> {new_state.value}"
            )
