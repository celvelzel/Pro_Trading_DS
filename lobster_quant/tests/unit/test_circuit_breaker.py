"""
Tests for CircuitBreaker class.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.data.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState

# Fixed base time for deterministic tests
BASE_TIME = datetime(2025, 1, 1, 12, 0, 0)


@pytest.fixture
def default_cb():
    """Circuit breaker with default config."""
    return CircuitBreaker("test")


@pytest.fixture
def cb_3_threshold():
    """Circuit breaker with threshold=3, recovery=60s."""
    config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60)
    return CircuitBreaker("test", config=config)


@pytest.fixture
def cb_1_threshold():
    """Circuit breaker with threshold=1, recovery=60s."""
    config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=60)
    return CircuitBreaker("test", config=config)


class TestInitialState:
    """Tests for initial circuit breaker state."""

    def test_initial_state_is_closed(self, default_cb):
        assert default_cb.state == CircuitState.CLOSED

    def test_initial_is_available(self, default_cb):
        assert default_cb.is_available is True

    def test_initial_failure_count_is_zero(self, default_cb):
        assert default_cb.failure_count == 0

    def test_initial_success_count_is_zero(self, default_cb):
        assert default_cb.success_count == 0

    def test_name_stored(self):
        cb = CircuitBreaker("my_source")
        assert cb.name == "my_source"


class TestClosedToOpenTransition:
    """Tests for CLOSED -> OPEN transition."""

    def test_below_threshold_stays_closed(self, cb_3_threshold):
        cb_3_threshold.record_failure()
        cb_3_threshold.record_failure()
        assert cb_3_threshold.state == CircuitState.CLOSED
        assert cb_3_threshold.is_available is True

    def test_at_threshold_opens(self, cb_3_threshold):
        for _ in range(3):
            cb_3_threshold.record_failure()
        assert cb_3_threshold.state == CircuitState.OPEN
        assert cb_3_threshold.is_available is False

    def test_failure_count_tracks_correctly(self, cb_3_threshold):
        cb_3_threshold.record_failure()
        cb_3_threshold.record_failure()
        cb_3_threshold.record_failure()
        assert cb_3_threshold.failure_count == 3

    def test_last_failure_time_set(self, default_cb):
        default_cb.record_failure()
        assert default_cb.last_failure_time is not None


class TestOpenToHalfOpenTransition:
    """Tests for OPEN -> HALF_OPEN transition."""

    def test_stays_open_before_timeout(self, cb_3_threshold):
        """State remains OPEN when recovery timeout has not elapsed."""
        with patch("src.data.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = BASE_TIME
            for _ in range(3):
                cb_3_threshold.record_failure()
            assert cb_3_threshold._state == CircuitState.OPEN

            # 30s later — not enough (timeout=60)
            mock_dt.now.return_value = BASE_TIME + timedelta(seconds=30)
            assert cb_3_threshold.state == CircuitState.OPEN

    def test_transitions_to_half_open_after_timeout(self, cb_3_threshold):
        """State transitions to HALF_OPEN after recovery timeout."""
        with patch("src.data.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = BASE_TIME
            for _ in range(3):
                cb_3_threshold.record_failure()
            assert cb_3_threshold._state == CircuitState.OPEN

            # 61s later — enough for timeout=60
            mock_dt.now.return_value = BASE_TIME + timedelta(seconds=61)
            assert cb_3_threshold.state == CircuitState.HALF_OPEN

    def test_half_open_is_available_within_limit(self, cb_3_threshold):
        """HALF_OPEN state allows requests within half_open_max_calls."""
        with patch("src.data.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = BASE_TIME
            for _ in range(3):
                cb_3_threshold.record_failure()

            mock_dt.now.return_value = BASE_TIME + timedelta(seconds=61)
            assert cb_3_threshold.state == CircuitState.HALF_OPEN
            assert cb_3_threshold.is_available is True

    def test_exact_timeout_boundary(self, cb_3_threshold):
        """Exactly at timeout boundary should transition."""
        with patch("src.data.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = BASE_TIME
            for _ in range(3):
                cb_3_threshold.record_failure()

            # Exactly 60s — should be >= timeout
            mock_dt.now.return_value = BASE_TIME + timedelta(seconds=60)
            assert cb_3_threshold.state == CircuitState.HALF_OPEN


class TestHalfOpenToClosedTransition:
    """Tests for HALF_OPEN -> CLOSED transition."""

    def test_success_closes_circuit(self, cb_1_threshold):
        """Recording success in HALF_OPEN transitions to CLOSED."""
        with patch("src.data.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = BASE_TIME
            cb_1_threshold.record_failure()
            assert cb_1_threshold._state == CircuitState.OPEN

            mock_dt.now.return_value = BASE_TIME + timedelta(seconds=61)
            assert cb_1_threshold.state == CircuitState.HALF_OPEN

            cb_1_threshold.record_success()
            assert cb_1_threshold.state == CircuitState.CLOSED
            assert cb_1_threshold.is_available is True

    def test_success_resets_failure_count(self, cb_1_threshold):
        """Success in HALF_OPEN resets failure count."""
        with patch("src.data.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = BASE_TIME
            cb_1_threshold.record_failure()

            mock_dt.now.return_value = BASE_TIME + timedelta(seconds=61)
            assert cb_1_threshold.state == CircuitState.HALF_OPEN

            cb_1_threshold.record_success()
            assert cb_1_threshold.failure_count == 0

    def test_success_increments_success_count(self, cb_1_threshold):
        """Success in HALF_OPEN increments success count."""
        with patch("src.data.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = BASE_TIME
            cb_1_threshold.record_failure()

            mock_dt.now.return_value = BASE_TIME + timedelta(seconds=61)
            assert cb_1_threshold.state == CircuitState.HALF_OPEN

            cb_1_threshold.record_success()
            assert cb_1_threshold.success_count == 1


class TestHalfOpenToOpenTransition:
    """Tests for HALF_OPEN -> OPEN transition."""

    def test_failure_reopens_circuit(self, cb_1_threshold):
        """Recording failure in HALF_OPEN transitions back to OPEN."""
        with patch("src.data.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = BASE_TIME
            cb_1_threshold.record_failure()

            mock_dt.now.return_value = BASE_TIME + timedelta(seconds=61)
            assert cb_1_threshold.state == CircuitState.HALF_OPEN

            cb_1_threshold.record_failure()
            assert cb_1_threshold._state == CircuitState.OPEN
            assert cb_1_threshold.is_available is False


class TestManualReset:
    """Tests for manual reset."""

    def test_reset_from_open(self, cb_3_threshold):
        """Manual reset from OPEN returns to CLOSED."""
        for _ in range(3):
            cb_3_threshold.record_failure()
        assert cb_3_threshold._state == CircuitState.OPEN

        cb_3_threshold.reset()
        assert cb_3_threshold.state == CircuitState.CLOSED
        assert cb_3_threshold.failure_count == 0
        assert cb_3_threshold.is_available is True

    def test_reset_from_half_open(self, cb_1_threshold):
        """Manual reset from HALF_OPEN returns to CLOSED."""
        with patch("src.data.circuit_breaker.datetime") as mock_dt:
            mock_dt.now.return_value = BASE_TIME
            cb_1_threshold.record_failure()

            mock_dt.now.return_value = BASE_TIME + timedelta(seconds=61)
            assert cb_1_threshold.state == CircuitState.HALF_OPEN

            cb_1_threshold.reset()
            assert cb_1_threshold.state == CircuitState.CLOSED


class TestSuccessRecording:
    """Tests for success recording in CLOSED state."""

    def test_success_in_closed_stays_closed(self, default_cb):
        default_cb.record_success()
        assert default_cb.state == CircuitState.CLOSED
        assert default_cb.success_count == 1

    def test_success_resets_failure_count_in_closed(self, default_cb):
        default_cb.record_failure()
        default_cb.record_failure()
        default_cb.record_success()
        assert default_cb.failure_count == 0


class TestGetStatus:
    """Tests for get_status method."""

    def test_status_contains_expected_keys(self, default_cb):
        status = default_cb.get_status()
        assert "name" in status
        assert "state" in status
        assert "failure_count" in status
        assert "success_count" in status
        assert "last_failure" in status
        assert "is_available" in status
        assert "config" in status

    def test_status_values(self, default_cb):
        status = default_cb.get_status()
        assert status["name"] == "test"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["success_count"] == 0
        assert status["is_available"] is True

    def test_status_after_failure(self, default_cb):
        default_cb.record_failure()
        status = default_cb.get_status()
        assert status["failure_count"] == 1
        assert status["last_failure"] is not None


class TestEdgeCases:
    """Edge case tests."""

    def test_custom_config(self):
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=120,
            half_open_max_calls=3,
        )
        cb = CircuitBreaker("custom", config=config)
        assert cb.state == CircuitState.CLOSED

    def test_zero_threshold_opens_immediately(self):
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config=config)
        cb.record_failure()
        assert cb._state == CircuitState.OPEN

    def test_multiple_cycles(self, cb_1_threshold):
        """Test circuit breaker survives multiple open/close cycles."""
        with patch("src.data.circuit_breaker.datetime") as mock_dt:
            # Cycle 1: open and recover
            mock_dt.now.return_value = BASE_TIME
            cb_1_threshold.record_failure()
            assert cb_1_threshold._state == CircuitState.OPEN

            mock_dt.now.return_value = BASE_TIME + timedelta(seconds=61)
            assert cb_1_threshold.state == CircuitState.HALF_OPEN

            cb_1_threshold.record_success()
            assert cb_1_threshold.state == CircuitState.CLOSED

            # Cycle 2: open and recover again
            mock_dt.now.return_value = BASE_TIME + timedelta(seconds=120)
            cb_1_threshold.record_failure()
            assert cb_1_threshold._state == CircuitState.OPEN

            mock_dt.now.return_value = BASE_TIME + timedelta(seconds=181)
            assert cb_1_threshold.state == CircuitState.HALF_OPEN

            cb_1_threshold.record_success()
            assert cb_1_threshold.state == CircuitState.CLOSED

    def test_failure_below_threshold_resets_on_success(self, cb_3_threshold):
        """Failures below threshold are cleared by a success."""
        cb_3_threshold.record_failure()
        cb_3_threshold.record_success()
        assert cb_3_threshold.failure_count == 0
        assert cb_3_threshold.state == CircuitState.CLOSED
