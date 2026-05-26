"""
Tests for Simulation API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure lobster_quant is importable
lobster_quant_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lobster_quant")
if os.path.exists(lobster_quant_path):
    sys.path.insert(0, lobster_quant_path)

from main import app
from api.models.simulation import (
    SimulationRequest,
    RunAllSimulationRequest,
    SimulatedTradeResponse,
    DailySnapshotResponse,
    SimulationResultResponse,
    PerformanceResponse,
)


client = TestClient(app)

# Patch targets
SCHEDULER_PATCH = "lobster_quant.src.core.scheduler.SimulationScheduler"
STORE_PATCH = "lobster_quant.src.storage.simulation_store.SimulationStore"


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_trade():
    """Create a mock SimulatedTrade object."""
    trade = MagicMock()
    trade.id = "trade_001"
    trade.strategyId = "test_strategy_1"
    trade.symbol = "AAPL"
    trade.entryDate = "2024-01-15"
    trade.entryPrice = 150.0
    trade.exitDate = "2024-02-15"
    trade.exitPrice = 165.0
    trade.shares = 10
    trade.status = "closed"
    trade.pnl = 150.0
    trade.pnlPercent = 10.0
    return trade


@pytest.fixture
def mock_open_trade():
    """Create a mock open SimulatedTrade object."""
    trade = MagicMock()
    trade.id = "trade_002"
    trade.strategyId = "test_strategy_1"
    trade.symbol = "TSLA"
    trade.entryDate = "2024-02-01"
    trade.entryPrice = 200.0
    trade.exitDate = None
    trade.exitPrice = None
    trade.shares = 5
    trade.status = "open"
    trade.pnl = None
    trade.pnlPercent = None
    return trade


@pytest.fixture
def mock_snapshot(mock_trade, mock_open_trade):
    """Create a mock DailySnapshot object."""
    snapshot = MagicMock()
    snapshot.date = "2024-02-15"
    snapshot.strategyId = "test_strategy_1"
    snapshot.selectedStocks = [{"symbol": "AAPL", "score": 85}]
    snapshot.openTrades = [mock_open_trade]
    snapshot.closedTrades = [mock_trade]
    snapshot.portfolioValue = 101500.0
    snapshot.cash = 50000.0
    snapshot.invested = 51500.0

    # model_dump for trades
    mock_open_trade.model_dump.return_value = {
        "id": "trade_002",
        "strategyId": "test_strategy_1",
        "symbol": "TSLA",
        "entryDate": "2024-02-01",
        "entryPrice": 200.0,
        "exitDate": None,
        "exitPrice": None,
        "shares": 5,
        "status": "open",
        "pnl": None,
        "pnlPercent": None,
    }
    mock_trade.model_dump.return_value = {
        "id": "trade_001",
        "strategyId": "test_strategy_1",
        "symbol": "AAPL",
        "entryDate": "2024-01-15",
        "entryPrice": 150.0,
        "exitDate": "2024-02-15",
        "exitPrice": 165.0,
        "shares": 10,
        "status": "closed",
        "pnl": 150.0,
        "pnlPercent": 10.0,
    }

    return snapshot


# ============================================================================
# Model Tests
# ============================================================================


class TestSimulationModels:
    """Test Pydantic models for simulation API."""

    def test_simulation_request(self):
        """Test SimulationRequest model."""
        req = SimulationRequest(strategyId="strat_1", market="US")
        assert req.strategyId == "strat_1"
        assert req.market == "US"

    def test_simulation_request_default_market(self):
        """Test SimulationRequest defaults to US market."""
        req = SimulationRequest(strategyId="strat_1")
        assert req.market == "US"

    def test_simulation_request_invalid_market(self):
        """Test SimulationRequest rejects invalid market."""
        with pytest.raises(Exception):
            SimulationRequest(strategyId="strat_1", market="INVALID")

    def test_run_all_simulation_request(self):
        """Test RunAllSimulationRequest model."""
        req = RunAllSimulationRequest(market="HK")
        assert req.market == "HK"

    def test_run_all_simulation_request_default(self):
        """Test RunAllSimulationRequest defaults to US."""
        req = RunAllSimulationRequest()
        assert req.market == "US"

    def test_simulated_trade_response(self):
        """Test SimulatedTradeResponse model."""
        resp = SimulatedTradeResponse(
            id="t1",
            strategyId="s1",
            symbol="AAPL",
            entryDate="2024-01-01",
            entryPrice=150.0,
            shares=10,
            status="open",
        )
        assert resp.id == "t1"
        assert resp.exitDate is None
        assert resp.pnl is None

    def test_daily_snapshot_response(self):
        """Test DailySnapshotResponse model."""
        resp = DailySnapshotResponse(
            date="2024-01-01",
            strategyId="s1",
            selectedStocks=[],
            openTrades=[],
            closedTrades=[],
            portfolioValue=100000.0,
            cash=100000.0,
            invested=0.0,
        )
        assert resp.portfolioValue == 100000.0

    def test_simulation_result_response(self):
        """Test SimulationResultResponse model."""
        resp = SimulationResultResponse(
            timestamp="2024-01-01T00:00:00",
            market="US",
            status="success",
        )
        assert resp.status == "success"
        assert resp.snapshot is None
        assert resp.error is None

    def test_performance_response(self):
        """Test PerformanceResponse model."""
        resp = PerformanceResponse(
            strategyId="s1",
            window="1M",
            totalReturn=10.5,
            volatility=5.2,
            sharpeRatio=1.8,
            maxDrawdown=3.0,
            winRate=60.0,
            totalTrades=10,
        )
        assert resp.sharpeRatio == 1.8
        assert resp.totalTrades == 10


# ============================================================================
# Endpoint Tests - POST /simulation/run
# ============================================================================


class TestRunSimulation:
    """Test POST /api/simulation/run endpoint."""

    @patch(SCHEDULER_PATCH)
    def test_run_simulation_success(self, mock_scheduler_cls, mock_snapshot):
        """Test successful simulation run."""
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler
        mock_scheduler.run_strategy.return_value = {
            "timestamp": "2024-02-15T10:00:00",
            "market": "US",
            "strategy_id": "test_strategy_1",
            "strategy_name": "Test Strategy",
            "status": "success",
            "snapshot": mock_snapshot,
        }

        resp = client.post("/api/simulation/run", json={
            "strategyId": "test_strategy_1",
            "market": "US",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["strategyId"] == "test_strategy_1"
        assert data["strategyName"] == "Test Strategy"
        assert data["snapshot"] is not None
        assert data["snapshot"]["portfolioValue"] == 101500.0

    @patch(SCHEDULER_PATCH)
    def test_run_simulation_error_in_result(self, mock_scheduler_cls):
        """Test simulation returns error in result."""
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler
        mock_scheduler.run_strategy.return_value = {
            "error": "Strategy not found"
        }

        resp = client.post("/api/simulation/run", json={
            "strategyId": "nonexistent",
            "market": "US",
        })

        assert resp.status_code == 400
        assert "Strategy not found" in resp.json()["detail"]

    @patch(SCHEDULER_PATCH)
    def test_run_simulation_exception(self, mock_scheduler_cls):
        """Test simulation raises unexpected exception."""
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler
        mock_scheduler.run_strategy.side_effect = RuntimeError("Unexpected error")

        resp = client.post("/api/simulation/run", json={
            "strategyId": "test_strategy_1",
            "market": "US",
        })

        assert resp.status_code == 500
        assert "Unexpected error" in resp.json()["detail"]

    def test_run_simulation_invalid_market(self):
        """Test simulation with invalid market."""
        resp = client.post("/api/simulation/run", json={
            "strategyId": "test_strategy_1",
            "market": "INVALID",
        })

        assert resp.status_code == 422  # Validation error

    @patch(SCHEDULER_PATCH)
    def test_run_simulation_no_snapshot(self, mock_scheduler_cls):
        """Test simulation run with no snapshot in result."""
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler
        mock_scheduler.run_strategy.return_value = {
            "timestamp": "2024-02-15T10:00:00",
            "market": "US",
            "strategy_id": "test_strategy_1",
            "strategy_name": "Test Strategy",
            "status": "success",
        }

        resp = client.post("/api/simulation/run", json={
            "strategyId": "test_strategy_1",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshot"] is None


# ============================================================================
# Endpoint Tests - POST /simulation/run-all
# ============================================================================


class TestRunAllSimulations:
    """Test POST /api/simulation/run-all endpoint."""

    @patch(SCHEDULER_PATCH)
    def test_run_all_success(self, mock_scheduler_cls, mock_snapshot):
        """Test successful run-all simulation."""
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler
        mock_scheduler.run_daily.return_value = {
            "timestamp": "2024-02-15T10:00:00",
            "market": "US",
            "results": [
                {
                    "strategy_id": "strat_1",
                    "strategy_name": "Strategy 1",
                    "status": "success",
                    "snapshot": mock_snapshot,
                    "error": None,
                },
                {
                    "strategy_id": "strat_2",
                    "strategy_name": "Strategy 2",
                    "status": "success",
                    "snapshot": None,
                    "error": None,
                },
            ],
        }

        resp = client.post("/api/simulation/run-all", json={"market": "US"})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["strategyId"] == "strat_1"
        assert data[1]["strategyId"] == "strat_2"

    @patch(SCHEDULER_PATCH)
    def test_run_all_error(self, mock_scheduler_cls):
        """Test run-all returns error."""
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler
        mock_scheduler.run_daily.return_value = {
            "error": "Scheduler already running"
        }

        resp = client.post("/api/simulation/run-all", json={"market": "US"})

        assert resp.status_code == 400
        assert "Scheduler already running" in resp.json()["detail"]

    @patch(SCHEDULER_PATCH)
    def test_run_all_exception(self, mock_scheduler_cls):
        """Test run-all raises unexpected exception."""
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler
        mock_scheduler.run_daily.side_effect = RuntimeError("Boom")

        resp = client.post("/api/simulation/run-all", json={"market": "US"})

        assert resp.status_code == 500

    def test_run_all_default_market(self):
        """Test run-all with default market."""
        with patch(SCHEDULER_PATCH) as mock_cls:
            mock_scheduler = MagicMock()
            mock_cls.return_value = mock_scheduler
            mock_scheduler.run_daily.return_value = {
                "timestamp": "2024-02-15T10:00:00",
                "market": "US",
                "results": [],
            }

            resp = client.post("/api/simulation/run-all", json={})

            assert resp.status_code == 200
            assert resp.json() == []


# ============================================================================
# Endpoint Tests - GET /simulation/trades
# ============================================================================


class TestListTrades:
    """Test GET /api/simulation/trades endpoint."""

    @patch(STORE_PATCH)
    def test_list_trades_success(self, mock_store_cls, mock_trade, mock_open_trade):
        """Test listing trades successfully."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        mock_store.get_trades.return_value = [mock_trade, mock_open_trade]

        resp = client.get("/api/simulation/trades?strategy_id=test_strategy_1")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["id"] == "trade_001"
        assert data[0]["status"] == "closed"
        assert data[1]["id"] == "trade_002"
        assert data[1]["status"] == "open"

    @patch(STORE_PATCH)
    def test_list_trades_with_status_filter(self, mock_store_cls, mock_trade):
        """Test listing trades with status filter."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        mock_store.get_trades.return_value = [mock_trade]

        resp = client.get("/api/simulation/trades?strategy_id=test_strategy_1&status=closed")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "closed"
        mock_store.get_trades.assert_called_once_with("test_strategy_1", "closed")

    @patch(STORE_PATCH)
    def test_list_trades_empty(self, mock_store_cls):
        """Test listing trades returns empty list."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        mock_store.get_trades.return_value = []

        resp = client.get("/api/simulation/trades?strategy_id=test_strategy_1")

        assert resp.status_code == 200
        assert resp.json() == []

    @patch(STORE_PATCH)
    def test_list_trades_exception(self, mock_store_cls):
        """Test listing trades raises exception."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        mock_store.get_trades.side_effect = RuntimeError("DB error")

        resp = client.get("/api/simulation/trades?strategy_id=test_strategy_1")

        assert resp.status_code == 500


# ============================================================================
# Endpoint Tests - GET /simulation/snapshots
# ============================================================================


class TestListSnapshots:
    """Test GET /api/simulation/snapshots endpoint."""

    @patch(STORE_PATCH)
    def test_list_snapshots_success(self, mock_store_cls, mock_snapshot):
        """Test listing snapshots successfully."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        mock_store.get_snapshots.return_value = [mock_snapshot]

        resp = client.get("/api/simulation/snapshots?strategy_id=test_strategy_1")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["date"] == "2024-02-15"
        assert data[0]["portfolioValue"] == 101500.0

    @patch(STORE_PATCH)
    def test_list_snapshots_with_days(self, mock_store_cls, mock_snapshot):
        """Test listing snapshots with custom days parameter."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        mock_store.get_snapshots.return_value = [mock_snapshot]

        resp = client.get("/api/simulation/snapshots?strategy_id=test_strategy_1&days=7")

        assert resp.status_code == 200
        mock_store.get_snapshots.assert_called_once_with("test_strategy_1", 7)

    @patch(STORE_PATCH)
    def test_list_snapshots_empty(self, mock_store_cls):
        """Test listing snapshots returns empty list."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        mock_store.get_snapshots.return_value = []

        resp = client.get("/api/simulation/snapshots?strategy_id=test_strategy_1")

        assert resp.status_code == 200
        assert resp.json() == []

    @patch(STORE_PATCH)
    def test_list_snapshots_exception(self, mock_store_cls):
        """Test listing snapshots raises exception."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        mock_store.get_snapshots.side_effect = RuntimeError("IO error")

        resp = client.get("/api/simulation/snapshots?strategy_id=test_strategy_1")

        assert resp.status_code == 500


# ============================================================================
# Endpoint Tests - GET /simulation/performance
# ============================================================================


class TestGetPerformance:
    """Test GET /api/simulation/performance endpoint."""

    @patch(STORE_PATCH)
    def test_get_performance_success(self, mock_store_cls):
        """Test getting performance metrics successfully."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        # Create mock trades with pnlPercent
        trades = []
        for i, pnl in enumerate([10.0, -5.0, 8.0, -2.0, 15.0]):
            t = MagicMock()
            t.pnlPercent = pnl
            trades.append(t)

        mock_store.get_trades.return_value = trades

        resp = client.get("/api/simulation/performance?strategy_id=test_strategy_1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["strategyId"] == "test_strategy_1"
        assert data["window"] == "1M"
        assert data["totalTrades"] == 5
        assert data["winRate"] == 60.0  # 3 out of 5 positive
        assert data["totalReturn"] == 26.0  # sum of pnlPercent

    @patch(STORE_PATCH)
    def test_get_performance_no_trades(self, mock_store_cls):
        """Test getting performance with no trades."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        mock_store.get_trades.return_value = []

        resp = client.get("/api/simulation/performance?strategy_id=test_strategy_1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["totalReturn"] == 0
        assert data["totalTrades"] == 0
        assert data["winRate"] == 0

    @patch(STORE_PATCH)
    def test_get_performance_custom_window(self, mock_store_cls):
        """Test getting performance with custom window."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        t = MagicMock()
        t.pnlPercent = 5.0
        mock_store.get_trades.return_value = [t]

        resp = client.get("/api/simulation/performance?strategy_id=s1&window=3M")

        assert resp.status_code == 200
        assert resp.json()["window"] == "3M"

    @patch(STORE_PATCH)
    def test_get_performance_all_winning(self, mock_store_cls):
        """Test performance with all winning trades."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        trades = []
        for pnl in [10.0, 5.0, 8.0]:
            t = MagicMock()
            t.pnlPercent = pnl
            trades.append(t)

        mock_store.get_trades.return_value = trades

        resp = client.get("/api/simulation/performance?strategy_id=s1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["winRate"] == 100.0
        assert data["totalReturn"] == 23.0

    @patch(STORE_PATCH)
    def test_get_performance_all_losing(self, mock_store_cls):
        """Test performance with all losing trades."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store

        trades = []
        for pnl in [-10.0, -5.0, -3.0]:
            t = MagicMock()
            t.pnlPercent = pnl
            trades.append(t)

        mock_store.get_trades.return_value = trades

        resp = client.get("/api/simulation/performance?strategy_id=s1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["winRate"] == 0.0
        assert data["totalReturn"] == -18.0

    @patch(STORE_PATCH)
    def test_get_performance_exception(self, mock_store_cls):
        """Test performance raises exception."""
        mock_store = MagicMock()
        mock_store_cls.return_value = mock_store
        mock_store.get_trades.side_effect = RuntimeError("Store error")

        resp = client.get("/api/simulation/performance?strategy_id=s1")

        assert resp.status_code == 500


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestSnapshotToResponse:
    """Test _snapshot_to_response helper."""

    def test_snapshot_none(self):
        """Test converting None snapshot."""
        from api.routes.simulation import _snapshot_to_response

        result = _snapshot_to_response(None)
        assert result is None

    def test_snapshot_conversion(self, mock_snapshot):
        """Test converting snapshot to response."""
        from api.routes.simulation import _snapshot_to_response

        result = _snapshot_to_response(mock_snapshot)
        assert result is not None
        assert result.date == "2024-02-15"
        assert result.strategyId == "test_strategy_1"
        assert result.portfolioValue == 101500.0
        assert result.cash == 50000.0
        assert len(result.openTrades) == 1
        assert len(result.closedTrades) == 1
