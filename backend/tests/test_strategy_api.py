"""
Tests for Strategy API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure lobster_quant is importable
lobster_quant_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lobster_quant")
if os.path.exists(lobster_quant_path):
    sys.path.insert(0, lobster_quant_path)

from main import app
from api.models.strategy import (
    StrategyParamsRequest,
    CreateStrategyRequest,
    UpdateStrategyRequest,
    StrategyResponse,
    CompareStrategiesRequest,
    StrategyComparisonResponse,
)


client = TestClient(app)

# Patch targets — routes use local imports from these modules
MANAGER_PATCH = "lobster_quant.src.core.strategy_manager.StrategyManager"
PARAMS_PATCH = "lobster_quant.src.data.models.StrategyParams"


@pytest.fixture
def mock_strategy():
    """Create a mock strategy object."""
    mock = MagicMock()
    mock.id = "test_strategy_1"
    mock.name = "Test Strategy"
    mock.description = "A test strategy"
    mock.params = MagicMock()
    mock.params.model_dump.return_value = {
        "holdingDays": 20,
        "minScore": 60,
        "slippagePct": 0.001,
        "commissionPct": 0.001,
        "positionSizing": "fixed",
        "positionSize": 0.1,
        "initialCapital": 100000,
        "maxPositions": 5,
    }
    mock.logic = "default"
    mock.isPreset = False
    mock.createdAt = datetime(2024, 1, 1, 0, 0, 0)
    mock.updatedAt = None
    return mock


@pytest.fixture
def mock_preset_strategy():
    """Create a mock preset strategy object."""
    mock = MagicMock()
    mock.id = "preset_conservative"
    mock.name = "Conservative"
    mock.description = "Conservative strategy"
    mock.params = MagicMock()
    mock.params.model_dump.return_value = {
        "holdingDays": 30,
        "minScore": 70,
        "slippagePct": 0.001,
        "commissionPct": 0.001,
        "positionSizing": "fixed",
        "positionSize": 0.05,
        "initialCapital": 100000,
        "maxPositions": 3,
    }
    mock.logic = "conservative"
    mock.isPreset = True
    mock.createdAt = datetime(2024, 1, 1, 0, 0, 0)
    mock.updatedAt = None
    return mock


# ============================================================================
# Model Tests
# ============================================================================


class TestStrategyParamsRequest:
    """Tests for StrategyParamsRequest model."""

    def test_default_values(self):
        """Should have correct default values."""
        params = StrategyParamsRequest()
        assert params.holdingDays == 20
        assert params.minScore == 60
        assert params.slippagePct == 0.001
        assert params.commissionPct == 0.001
        assert params.positionSizing == "fixed"
        assert params.positionSize == 0.1
        assert params.initialCapital == 100000
        assert params.maxPositions == 5

    def test_custom_values(self):
        """Should accept custom values."""
        params = StrategyParamsRequest(
            holdingDays=30,
            minScore=70,
            slippagePct=0.002,
            commissionPct=0.002,
            positionSizing="dynamic",
            positionSize=0.2,
            initialCapital=200000,
            maxPositions=10,
        )
        assert params.holdingDays == 30
        assert params.minScore == 70
        assert params.slippagePct == 0.002
        assert params.commissionPct == 0.002
        assert params.positionSizing == "dynamic"
        assert params.positionSize == 0.2
        assert params.initialCapital == 200000
        assert params.maxPositions == 10

    def test_invalid_holding_days_too_low(self):
        """Should reject holdingDays below 5."""
        with pytest.raises(Exception):
            StrategyParamsRequest(holdingDays=4)

    def test_invalid_holding_days_too_high(self):
        """Should reject holdingDays above 100."""
        with pytest.raises(Exception):
            StrategyParamsRequest(holdingDays=101)

    def test_invalid_position_sizing(self):
        """Should reject invalid positionSizing."""
        with pytest.raises(Exception):
            StrategyParamsRequest(positionSizing="invalid")

    def test_valid_position_sizing_fixed(self):
        """Should accept fixed positionSizing."""
        params = StrategyParamsRequest(positionSizing="fixed")
        assert params.positionSizing == "fixed"

    def test_valid_position_sizing_dynamic(self):
        """Should accept dynamic positionSizing."""
        params = StrategyParamsRequest(positionSizing="dynamic")
        assert params.positionSizing == "dynamic"


class TestCreateStrategyRequest:
    """Tests for CreateStrategyRequest model."""

    def test_valid_request(self):
        """Should accept valid request."""
        request = CreateStrategyRequest(
            name="My Strategy",
            description="A custom strategy",
            params=StrategyParamsRequest(),
        )
        assert request.name == "My Strategy"
        assert request.description == "A custom strategy"

    def test_missing_name(self):
        """Should reject missing name."""
        with pytest.raises(Exception):
            CreateStrategyRequest(params=StrategyParamsRequest())

    def test_empty_name(self):
        """Should reject empty name."""
        with pytest.raises(Exception):
            CreateStrategyRequest(name="", params=StrategyParamsRequest())

    def test_name_too_long(self):
        """Should reject name over 100 characters."""
        with pytest.raises(Exception):
            CreateStrategyRequest(
                name="x" * 101,
                params=StrategyParamsRequest(),
            )

    def test_default_description(self):
        """Should have empty default description."""
        request = CreateStrategyRequest(
            name="Test",
            params=StrategyParamsRequest(),
        )
        assert request.description == ""


class TestUpdateStrategyRequest:
    """Tests for UpdateStrategyRequest model."""

    def test_partial_update(self):
        """Should accept partial updates."""
        request = UpdateStrategyRequest(name="New Name")
        assert request.name == "New Name"
        assert request.description is None
        assert request.params is None

    def test_all_none(self):
        """Should accept all None values."""
        request = UpdateStrategyRequest()
        assert request.name is None
        assert request.description is None
        assert request.params is None


class TestStrategyResponse:
    """Tests for StrategyResponse model."""

    def test_response_model(self):
        """Should create valid response."""
        response = StrategyResponse(
            id="test_1",
            name="Test",
            description="Description",
            params={"holdingDays": 20},
            logic="default",
            isPreset=False,
            createdAt="2024-01-01T00:00:00",
        )
        assert response.id == "test_1"
        assert response.updatedAt is None

    def test_response_with_updated_at(self):
        """Should accept updatedAt."""
        response = StrategyResponse(
            id="test_1",
            name="Test",
            description="Description",
            params={},
            logic="default",
            isPreset=False,
            createdAt="2024-01-01T00:00:00",
            updatedAt="2024-01-02T00:00:00",
        )
        assert response.updatedAt == "2024-01-02T00:00:00"


class TestCompareStrategiesRequest:
    """Tests for CompareStrategiesRequest model."""

    def test_valid_request(self):
        """Should accept valid request."""
        request = CompareStrategiesRequest(
            strategyIds=["s1", "s2"],
            symbol="AAPL",
            startDate="2023-01-01",
            endDate="2023-12-31",
        )
        assert len(request.strategyIds) == 2

    def test_minimum_two_strategies(self):
        """Should require at least 2 strategy IDs."""
        with pytest.raises(Exception):
            CompareStrategiesRequest(
                strategyIds=["s1"],
                symbol="AAPL",
                startDate="2023-01-01",
                endDate="2023-12-31",
            )


class TestStrategyComparisonResponse:
    """Tests for StrategyComparisonResponse model."""

    def test_response_model(self):
        """Should create valid response."""
        response = StrategyComparisonResponse(
            strategies=[{"id": "s1"}, {"id": "s2"}],
            bestReturn="s1",
            bestSharpe="s2",
            lowestDrawdown="s1",
        )
        assert len(response.strategies) == 2
        assert response.bestReturn == "s1"

    def test_optional_fields(self):
        """Should accept None for optional fields."""
        response = StrategyComparisonResponse(strategies=[])
        assert response.bestReturn is None
        assert response.bestSharpe is None
        assert response.lowestDrawdown is None


# ============================================================================
# Endpoint Tests
# ============================================================================


class TestListStrategiesEndpoint:
    """Tests for GET /api/strategy/strategies."""

    @patch(MANAGER_PATCH)
    def test_list_strategies_empty(self, MockManager):
        """Should return empty list when no strategies exist."""
        MockManager.return_value.list_strategies.return_value = []
        response = client.get("/api/strategy/strategies")
        assert response.status_code == 200
        assert response.json() == []

    @patch(MANAGER_PATCH)
    def test_list_strategies_with_data(self, MockManager, mock_strategy):
        """Should return list of strategies."""
        MockManager.return_value.list_strategies.return_value = [mock_strategy]
        response = client.get("/api/strategy/strategies")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "test_strategy_1"
        assert data[0]["name"] == "Test Strategy"

    @patch(MANAGER_PATCH)
    def test_list_strategies_multiple(self, MockManager, mock_strategy, mock_preset_strategy):
        """Should return multiple strategies."""
        MockManager.return_value.list_strategies.return_value = [mock_strategy, mock_preset_strategy]
        response = client.get("/api/strategy/strategies")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @patch(MANAGER_PATCH)
    def test_list_strategies_error(self, MockManager):
        """Should return 500 on error."""
        MockManager.return_value.list_strategies.side_effect = Exception("DB error")
        response = client.get("/api/strategy/strategies")
        assert response.status_code == 500


class TestGetStrategyEndpoint:
    """Tests for GET /api/strategy/strategies/{strategy_id}."""

    @patch(MANAGER_PATCH)
    def test_get_existing_strategy(self, MockManager, mock_strategy):
        """Should return strategy by ID."""
        MockManager.return_value.get_strategy.return_value = mock_strategy
        response = client.get("/api/strategy/strategies/test_strategy_1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_strategy_1"
        assert data["name"] == "Test Strategy"
        assert data["isPreset"] is False

    @patch(MANAGER_PATCH)
    def test_get_preset_strategy(self, MockManager, mock_preset_strategy):
        """Should return preset strategy by ID."""
        MockManager.return_value.get_strategy.return_value = mock_preset_strategy
        response = client.get("/api/strategy/strategies/preset_conservative")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "preset_conservative"
        assert data["isPreset"] is True

    @patch(MANAGER_PATCH)
    def test_get_nonexistent_strategy(self, MockManager):
        """Should return 404 for nonexistent strategy."""
        MockManager.return_value.get_strategy.return_value = None
        response = client.get("/api/strategy/strategies/nonexistent")
        assert response.status_code == 404

    @patch(MANAGER_PATCH)
    def test_get_strategy_error(self, MockManager):
        """Should return 500 on error."""
        MockManager.return_value.get_strategy.side_effect = Exception("DB error")
        response = client.get("/api/strategy/strategies/test_strategy_1")
        assert response.status_code == 500


class TestCreateStrategyEndpoint:
    """Tests for POST /api/strategy/strategies."""

    @patch(PARAMS_PATCH)
    @patch(MANAGER_PATCH)
    def test_create_strategy(self, MockManager, MockParams, mock_strategy):
        """Should create a new strategy."""
        MockManager.return_value.create_strategy.return_value = mock_strategy
        response = client.post(
            "/api/strategy/strategies",
            json={
                "name": "Test Strategy",
                "description": "A test strategy",
                "params": {
                    "holdingDays": 20,
                    "minScore": 60,
                    "slippagePct": 0.001,
                    "commissionPct": 0.001,
                    "positionSizing": "fixed",
                    "positionSize": 0.1,
                    "initialCapital": 100000,
                    "maxPositions": 5,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test_strategy_1"
        assert data["name"] == "Test Strategy"

    @patch(PARAMS_PATCH)
    @patch(MANAGER_PATCH)
    def test_create_strategy_minimal(self, MockManager, MockParams, mock_strategy):
        """Should create strategy with only required fields."""
        MockManager.return_value.create_strategy.return_value = mock_strategy
        response = client.post(
            "/api/strategy/strategies",
            json={
                "name": "Minimal Strategy",
                "params": {},
            },
        )
        assert response.status_code == 200

    def test_create_strategy_missing_name(self):
        """Should reject request without name."""
        response = client.post(
            "/api/strategy/strategies",
            json={
                "params": {
                    "holdingDays": 20,
                    "minScore": 60,
                },
            },
        )
        assert response.status_code == 422

    @patch(MANAGER_PATCH)
    def test_create_strategy_error(self, MockManager):
        """Should return 500 on error."""
        MockManager.return_value.create_strategy.side_effect = Exception("DB error")
        response = client.post(
            "/api/strategy/strategies",
            json={
                "name": "Test Strategy",
                "params": {},
            },
        )
        assert response.status_code == 500


class TestUpdateStrategyEndpoint:
    """Tests for PUT /api/strategy/strategies/{strategy_id}."""

    @patch(MANAGER_PATCH)
    def test_update_strategy_name(self, MockManager, mock_strategy):
        """Should update strategy name."""
        mock_strategy.name = "Updated Name"
        MockManager.return_value.update_strategy.return_value = mock_strategy
        response = client.put(
            "/api/strategy/strategies/test_strategy_1",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    @patch(MANAGER_PATCH)
    def test_update_strategy_description(self, MockManager, mock_strategy):
        """Should update strategy description."""
        mock_strategy.description = "New description"
        MockManager.return_value.update_strategy.return_value = mock_strategy
        response = client.put(
            "/api/strategy/strategies/test_strategy_1",
            json={"description": "New description"},
        )
        assert response.status_code == 200

    @patch(MANAGER_PATCH)
    def test_update_strategy_not_found(self, MockManager):
        """Should return 404 for nonexistent strategy."""
        MockManager.return_value.update_strategy.return_value = None
        response = client.put(
            "/api/strategy/strategies/nonexistent",
            json={"name": "New Name"},
        )
        assert response.status_code == 404

    @patch(MANAGER_PATCH)
    def test_update_strategy_preset(self, MockManager):
        """Should return 404 for preset strategy."""
        MockManager.return_value.update_strategy.return_value = None
        response = client.put(
            "/api/strategy/strategies/preset_conservative",
            json={"name": "New Name"},
        )
        assert response.status_code == 404

    @patch(MANAGER_PATCH)
    def test_update_strategy_error(self, MockManager):
        """Should return 500 on error."""
        MockManager.return_value.update_strategy.side_effect = Exception("DB error")
        response = client.put(
            "/api/strategy/strategies/test_strategy_1",
            json={"name": "New Name"},
        )
        assert response.status_code == 500


class TestDeleteStrategyEndpoint:
    """Tests for DELETE /api/strategy/strategies/{strategy_id}."""

    @patch(MANAGER_PATCH)
    def test_delete_strategy(self, MockManager):
        """Should delete a custom strategy."""
        MockManager.return_value.delete_strategy.return_value = True
        response = client.delete("/api/strategy/strategies/test_strategy_1")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test_strategy_1" in data["message"]

    @patch(MANAGER_PATCH)
    def test_delete_nonexistent_strategy(self, MockManager):
        """Should return 404 for nonexistent strategy."""
        MockManager.return_value.delete_strategy.return_value = False
        response = client.delete("/api/strategy/strategies/nonexistent")
        assert response.status_code == 404

    @patch(MANAGER_PATCH)
    def test_delete_preset_strategy(self, MockManager):
        """Should return 404 for preset strategy."""
        MockManager.return_value.delete_strategy.return_value = False
        response = client.delete("/api/strategy/strategies/preset_conservative")
        assert response.status_code == 404

    @patch(MANAGER_PATCH)
    def test_delete_strategy_error(self, MockManager):
        """Should return 500 on error."""
        MockManager.return_value.delete_strategy.side_effect = Exception("DB error")
        response = client.delete("/api/strategy/strategies/test_strategy_1")
        assert response.status_code == 500


class TestCompareStrategiesEndpoint:
    """Tests for POST /api/strategy/strategies/compare."""

    @patch(MANAGER_PATCH)
    def test_compare_strategies(self, MockManager):
        """Should compare multiple strategies."""
        MockManager.return_value.compare_strategies.return_value = {
            "strategies": [
                {"id": "strategy_1", "name": "Strategy 1", "totalReturn": 0.15},
                {"id": "strategy_2", "name": "Strategy 2", "totalReturn": 0.20},
            ],
            "best_return": "strategy_2",
            "best_sharpe": "strategy_1",
            "lowest_drawdown": "strategy_1",
        }
        response = client.post(
            "/api/strategy/strategies/compare",
            json={
                "strategyIds": ["strategy_1", "strategy_2"],
                "symbol": "AAPL",
                "startDate": "2023-01-01",
                "endDate": "2023-12-31",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["strategies"]) == 2
        assert data["bestReturn"] == "strategy_2"
        assert data["bestSharpe"] == "strategy_1"
        assert data["lowestDrawdown"] == "strategy_1"

    def test_compare_strategies_single_id(self):
        """Should reject comparison with single strategy."""
        response = client.post(
            "/api/strategy/strategies/compare",
            json={
                "strategyIds": ["strategy_1"],
                "symbol": "AAPL",
                "startDate": "2023-01-01",
                "endDate": "2023-12-31",
            },
        )
        assert response.status_code == 422

    @patch(MANAGER_PATCH)
    def test_compare_strategies_error(self, MockManager):
        """Should return 500 on error."""
        MockManager.return_value.compare_strategies.side_effect = Exception("Error")
        response = client.post(
            "/api/strategy/strategies/compare",
            json={
                "strategyIds": ["strategy_1", "strategy_2"],
                "symbol": "AAPL",
                "startDate": "2023-01-01",
                "endDate": "2023-12-31",
            },
        )
        assert response.status_code == 500
