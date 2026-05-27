"""
Unit tests for SimulationScheduler.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.core.scheduler import SimulationScheduler


@pytest.fixture
def mock_scheduler():
    """Create a SimulationScheduler with mocked dependencies."""
    with (
        patch("src.core.scheduler.TradeSimulator") as MockSimulator,
        patch("src.core.scheduler.StrategyManager") as MockManager,
    ):

        scheduler = SimulationScheduler(data_dir="test_data")
        yield scheduler, MockSimulator, MockManager


class TestStockLists:
    """Tests for stock list constants and get_stock_list."""

    def test_us_stock_list_not_empty(self):
        assert len(SimulationScheduler.US_STOCK_LIST) > 0

    def test_hk_stock_list_not_empty(self):
        assert len(SimulationScheduler.HK_STOCK_LIST) > 0

    def test_a_stock_list_not_empty(self):
        assert len(SimulationScheduler.A_STOCK_LIST) > 0

    def test_get_stock_list_us(self, mock_scheduler):
        scheduler, _, _ = mock_scheduler
        result = scheduler.get_stock_list("US")
        assert result == SimulationScheduler.US_STOCK_LIST

    def test_get_stock_list_hk(self, mock_scheduler):
        scheduler, _, _ = mock_scheduler
        result = scheduler.get_stock_list("HK")
        assert result == SimulationScheduler.HK_STOCK_LIST

    def test_get_stock_list_a(self, mock_scheduler):
        scheduler, _, _ = mock_scheduler
        result = scheduler.get_stock_list("A")
        assert result == SimulationScheduler.A_STOCK_LIST

    def test_get_stock_list_unknown_defaults_to_us(self, mock_scheduler):
        scheduler, _, _ = mock_scheduler
        result = scheduler.get_stock_list("UNKNOWN")
        assert result == SimulationScheduler.US_STOCK_LIST

    def test_get_stock_list_default_is_us(self, mock_scheduler):
        scheduler, _, _ = mock_scheduler
        result = scheduler.get_stock_list()
        assert result == SimulationScheduler.US_STOCK_LIST


class TestRunDaily:
    """Tests for run_daily method."""

    def test_run_daily_already_running(self, mock_scheduler):
        scheduler, _, _ = mock_scheduler
        scheduler._running = True
        result = scheduler.run_daily()
        assert result == {"error": "Scheduler already running"}

    def test_run_daily_success(self, mock_scheduler):
        scheduler, _, MockManager = mock_scheduler

        # Mock strategy
        strategy = MagicMock()
        strategy.id = "test-strategy"
        strategy.name = "Test Strategy"
        MockManager.return_value.list_strategies.return_value = [strategy]

        # Mock simulator
        mock_snapshot = MagicMock()
        scheduler.simulator.run_daily.return_value = mock_snapshot

        result = scheduler.run_daily("US")

        assert "timestamp" in result
        assert result["market"] == "US"
        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "success"
        assert result["results"][0]["snapshot"] == mock_snapshot
        assert result["results"][0]["strategy_id"] == "test-strategy"
        assert result["results"][0]["strategy_name"] == "Test Strategy"
        assert result["results"][0]["error"] is None

    def test_run_daily_strategy_error(self, mock_scheduler):
        scheduler, _, MockManager = mock_scheduler

        # Mock strategy that raises
        strategy = MagicMock()
        strategy.id = "bad-strategy"
        strategy.name = "Bad Strategy"
        MockManager.return_value.list_strategies.return_value = [strategy]

        scheduler.simulator.run_daily.side_effect = RuntimeError("boom")

        result = scheduler.run_daily("US")

        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "error"
        assert result["results"][0]["snapshot"] is None
        assert "boom" in result["results"][0]["error"]

    def test_run_daily_resets_running_flag(self, mock_scheduler):
        scheduler, _, MockManager = mock_scheduler

        MockManager.return_value.list_strategies.side_effect = RuntimeError("fail")

        with pytest.raises(RuntimeError):
            scheduler.run_daily()

        assert scheduler._running is False

    def test_run_daily_multiple_strategies(self, mock_scheduler):
        scheduler, _, MockManager = mock_scheduler

        strategies = []
        for i in range(3):
            s = MagicMock()
            s.id = f"strat-{i}"
            s.name = f"Strategy {i}"
            strategies.append(s)

        MockManager.return_value.list_strategies.return_value = strategies
        scheduler.simulator.run_daily.return_value = MagicMock()

        result = scheduler.run_daily("HK")

        assert result["market"] == "HK"
        assert len(result["results"]) == 3
        for r in result["results"]:
            assert r["status"] == "success"

    def test_run_daily_mixed_success_and_error(self, mock_scheduler):
        scheduler, _, MockManager = mock_scheduler

        s1 = MagicMock()
        s1.id = "good"
        s1.name = "Good"
        s2 = MagicMock()
        s2.id = "bad"
        s2.name = "Bad"

        MockManager.return_value.list_strategies.return_value = [s1, s2]

        mock_snapshot = MagicMock()
        scheduler.simulator.run_daily.side_effect = [mock_snapshot, RuntimeError("fail")]

        result = scheduler.run_daily()

        assert result["results"][0]["status"] == "success"
        assert result["results"][1]["status"] == "error"


class TestRunStrategy:
    """Tests for run_strategy method."""

    def test_run_strategy_not_found(self, mock_scheduler):
        scheduler, _, MockManager = mock_scheduler
        MockManager.return_value.get_strategy.return_value = None

        result = scheduler.run_strategy("nonexistent")

        assert result == {"error": "Strategy nonexistent not found"}

    def test_run_strategy_success(self, mock_scheduler):
        scheduler, _, MockManager = mock_scheduler

        strategy = MagicMock()
        strategy.name = "My Strategy"
        MockManager.return_value.get_strategy.return_value = strategy

        mock_snapshot = MagicMock()
        scheduler.simulator.run_daily.return_value = mock_snapshot

        result = scheduler.run_strategy("my-strat", "US")

        assert result["status"] == "success"
        assert result["strategy_id"] == "my-strat"
        assert result["strategy_name"] == "My Strategy"
        assert result["market"] == "US"
        assert result["snapshot"] == mock_snapshot
        assert result["error"] is None

    def test_run_strategy_error(self, mock_scheduler):
        scheduler, _, MockManager = mock_scheduler

        strategy = MagicMock()
        strategy.name = "Fail Strategy"
        MockManager.return_value.get_strategy.return_value = strategy

        scheduler.simulator.run_daily.side_effect = RuntimeError("kaboom")

        result = scheduler.run_strategy("fail-strat", "A")

        assert result["status"] == "error"
        assert result["snapshot"] is None
        assert "kaboom" in result["error"]
        assert result["market"] == "A"

    def test_run_strategy_default_market(self, mock_scheduler):
        scheduler, _, MockManager = mock_scheduler

        strategy = MagicMock()
        strategy.name = "S"
        MockManager.return_value.get_strategy.return_value = strategy
        scheduler.simulator.run_daily.return_value = MagicMock()

        result = scheduler.run_strategy("s1")

        assert result["market"] == "US"
