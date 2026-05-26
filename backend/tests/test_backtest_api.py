"""
Tests for Backtest API endpoints.
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


client = TestClient(app)

# Patch targets — routes use local imports from these modules
STRATEGY_MANAGER_PATCH = "lobster_quant.src.core.strategy_manager.StrategyManager"
DATA_ENGINE_PATCH = "lobster_quant.src.core.data_engine.get_data_engine"
INDICATOR_ENGINE_PATCH = "lobster_quant.src.core.indicator_engine.get_indicator_engine"
BACKTEST_ENGINE_PATCH = "lobster_quant.src.analysis.backtest.engine.BacktestEngine"
PORTFOLIO_BACKTEST_PATCH = "lobster_quant.src.analysis.backtest.portfolio.PortfolioBacktest"
BACKTEST_STORE_PATCH = "lobster_quant.src.storage.backtest_store.BacktestStore"


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
    }
    mock.logic = "default"
    mock.isPreset = False
    mock.createdAt = datetime(2024, 1, 1, 0, 0, 0)
    mock.updatedAt = None
    return mock


@pytest.fixture
def mock_backtest_result():
    """Create a mock backtest result."""
    result = MagicMock()
    result.symbol = "AAPL"
    result.total_trades = 5
    result.win_rate = 0.6
    result.cumulative_return = 0.15
    result.max_drawdown = 0.08
    result.sharpe_ratio = 1.2

    # Mock trades
    trade1 = MagicMock()
    trade1.buy_date = datetime(2024, 1, 15)
    trade1.sell_date = datetime(2024, 2, 15)
    trade1.buy_price = 150.0
    trade1.sell_price = 160.0
    trade1.return_pct = 0.0667
    trade1.holding_days = 31

    trade2 = MagicMock()
    trade2.buy_date = datetime(2024, 3, 1)
    trade2.sell_date = datetime(2024, 3, 21)
    trade2.buy_price = 165.0
    trade2.sell_price = 158.0
    trade2.return_pct = -0.0424
    trade2.holding_days = 20

    result.trades = [trade1, trade2]
    result.equity_curve = [1.0, 1.0667, 1.0212]

    # Mock metrics
    result.metrics = MagicMock()
    result.metrics.model_dump.return_value = {
        "totalTrades": 5,
        "winRate": 60.0,
        "totalReturn": 15.0,
        "maxDrawdown": 8.0,
        "sharpeRatio": 1.2,
    }

    return result


@pytest.fixture
def mock_stock_data():
    """Create mock stock data."""
    import pandas as pd

    stock_data = MagicMock()
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    stock_data.daily = pd.DataFrame({
        "open": [150.0] * 100,
        "high": [155.0] * 100,
        "low": [148.0] * 100,
        "close": [152.0] * 100,
        "volume": [1000000] * 100,
    }, index=dates)
    return stock_data


# ============================================================================
# Strategy Backtest Tests
# ============================================================================


class TestStrategyBacktest:
    """Tests for POST /backtest/strategy endpoint."""

    @patch(BACKTEST_ENGINE_PATCH)
    @patch(INDICATOR_ENGINE_PATCH)
    @patch(DATA_ENGINE_PATCH)
    @patch(STRATEGY_MANAGER_PATCH)
    def test_run_strategy_backtest_success(
        self, mock_manager_cls, mock_data_engine_cls,
        mock_indicator_engine_cls, mock_engine_cls,
        mock_strategy, mock_backtest_result, mock_stock_data
    ):
        """Test successful strategy backtest."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_manager.get_strategy.return_value = mock_strategy
        mock_manager_cls.return_value = mock_manager

        mock_data_engine = MagicMock()
        mock_data_engine.fetch_stock.return_value = mock_stock_data
        mock_data_engine_cls.return_value = mock_data_engine

        mock_indicator_engine = MagicMock()
        mock_indicator_engine.compute_all.return_value = mock_stock_data.daily
        mock_indicator_engine_cls.return_value = mock_indicator_engine

        mock_engine = MagicMock()
        mock_engine.run_with_strategy.return_value = mock_backtest_result
        mock_engine_cls.return_value = mock_engine

        # Make request
        response = client.post(
            "/api/backtest/backtest/strategy",
            params={
                "symbol": "AAPL",
                "strategy_id": "test_strategy_1"
            }
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["strategy_id"] == "test_strategy_1"
        assert data["strategy_name"] == "Test Strategy"
        assert data["symbol"] == "AAPL"
        assert "metrics" in data
        assert "trades" in data
        assert "equityCurve" in data

    @patch(STRATEGY_MANAGER_PATCH)
    def test_run_strategy_backtest_strategy_not_found(self, mock_manager_cls):
        """Test strategy backtest with non-existent strategy."""
        mock_manager = MagicMock()
        mock_manager.get_strategy.return_value = None
        mock_manager_cls.return_value = mock_manager

        response = client.post(
            "/api/backtest/backtest/strategy",
            params={
                "symbol": "AAPL",
                "strategy_id": "nonexistent"
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch(DATA_ENGINE_PATCH)
    @patch(STRATEGY_MANAGER_PATCH)
    def test_run_strategy_backtest_stock_not_found(
        self, mock_manager_cls, mock_data_engine_cls, mock_strategy
    ):
        """Test strategy backtest with non-existent stock."""
        mock_manager = MagicMock()
        mock_manager.get_strategy.return_value = mock_strategy
        mock_manager_cls.return_value = mock_manager

        mock_data_engine = MagicMock()
        mock_data_engine.fetch_stock.return_value = None
        mock_data_engine_cls.return_value = mock_data_engine

        response = client.post(
            "/api/backtest/backtest/strategy",
            params={
                "symbol": "INVALID",
                "strategy_id": "test_strategy_1"
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch(BACKTEST_ENGINE_PATCH)
    @patch(INDICATOR_ENGINE_PATCH)
    @patch(DATA_ENGINE_PATCH)
    @patch(STRATEGY_MANAGER_PATCH)
    def test_run_strategy_backtest_with_date_range(
        self, mock_manager_cls, mock_data_engine_cls,
        mock_indicator_engine_cls, mock_engine_cls,
        mock_strategy, mock_backtest_result, mock_stock_data
    ):
        """Test strategy backtest with date range filter."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_manager.get_strategy.return_value = mock_strategy
        mock_manager_cls.return_value = mock_manager

        mock_data_engine = MagicMock()
        mock_data_engine.fetch_stock.return_value = mock_stock_data
        mock_data_engine_cls.return_value = mock_data_engine

        mock_indicator_engine = MagicMock()
        mock_indicator_engine.compute_all.return_value = mock_stock_data.daily
        mock_indicator_engine_cls.return_value = mock_indicator_engine

        mock_engine = MagicMock()
        mock_engine.run_with_strategy.return_value = mock_backtest_result
        mock_engine_cls.return_value = mock_engine

        # Make request with date range
        response = client.post(
            "/api/backtest/backtest/strategy",
            params={
                "symbol": "AAPL",
                "strategy_id": "test_strategy_1",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"


# ============================================================================
# Portfolio Backtest Tests
# ============================================================================


class TestPortfolioBacktest:
    """Tests for POST /backtest/portfolio endpoint."""

    @patch(PORTFOLIO_BACKTEST_PATCH)
    @patch(STRATEGY_MANAGER_PATCH)
    def test_run_portfolio_backtest_success(
        self, mock_manager_cls, mock_portfolio_cls,
        mock_strategy, mock_backtest_result
    ):
        """Test successful portfolio backtest."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_manager.get_strategy.return_value = mock_strategy
        mock_manager_cls.return_value = mock_manager

        mock_portfolio = MagicMock()
        mock_portfolio.run.return_value = mock_backtest_result
        mock_portfolio_cls.return_value = mock_portfolio

        # Make request
        response = client.post(
            "/api/backtest/backtest/portfolio",
            params={
                "symbols": ["AAPL", "GOOGL", "MSFT"],
                "strategy_id": "test_strategy_1"
            }
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["strategy_id"] == "test_strategy_1"
        assert data["strategy_name"] == "Test Strategy"
        assert data["symbols"] == ["AAPL", "GOOGL", "MSFT"]
        assert "metrics" in data
        assert "trades" in data
        assert "equityCurve" in data

    @patch(STRATEGY_MANAGER_PATCH)
    def test_run_portfolio_backtest_strategy_not_found(self, mock_manager_cls):
        """Test portfolio backtest with non-existent strategy."""
        mock_manager = MagicMock()
        mock_manager.get_strategy.return_value = None
        mock_manager_cls.return_value = mock_manager

        response = client.post(
            "/api/backtest/backtest/portfolio",
            params={
                "symbols": ["AAPL"],
                "strategy_id": "nonexistent"
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch(PORTFOLIO_BACKTEST_PATCH)
    @patch(STRATEGY_MANAGER_PATCH)
    def test_run_portfolio_backtest_with_date_range(
        self, mock_manager_cls, mock_portfolio_cls,
        mock_strategy, mock_backtest_result
    ):
        """Test portfolio backtest with date range filter."""
        # Setup mocks
        mock_manager = MagicMock()
        mock_manager.get_strategy.return_value = mock_strategy
        mock_manager_cls.return_value = mock_manager

        mock_portfolio = MagicMock()
        mock_portfolio.run.return_value = mock_backtest_result
        mock_portfolio_cls.return_value = mock_portfolio

        # Make request with date range
        response = client.post(
            "/api/backtest/backtest/portfolio",
            params={
                "symbols": ["AAPL", "GOOGL"],
                "strategy_id": "test_strategy_1",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert len(data["symbols"]) == 2


# ============================================================================
# List Backtest Results Tests
# ============================================================================


class TestListBacktestResults:
    """Tests for GET /backtest/results endpoint."""

    @patch(BACKTEST_STORE_PATCH)
    def test_list_backtest_results_success(self, mock_store_cls):
        """Test successful listing of backtest results."""
        # Setup mocks
        mock_store = MagicMock()
        mock_result = MagicMock()
        mock_result.id = "result_20240101_120000"
        mock_result.strategy_id = "test_strategy_1"
        mock_result.symbol = "AAPL"
        mock_result.created_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_result.metrics = MagicMock()
        mock_result.metrics.model_dump.return_value = {
            "totalTrades": 5,
            "winRate": 60.0,
        }
        mock_store.list_results.return_value = [mock_result]
        mock_store_cls.return_value = mock_store

        # Make request
        response = client.get("/api/backtest/backtest/results")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "result_20240101_120000"
        assert data[0]["symbol"] == "AAPL"

    @patch(BACKTEST_STORE_PATCH)
    def test_list_backtest_results_with_strategy_filter(self, mock_store_cls):
        """Test listing backtest results filtered by strategy."""
        # Setup mocks
        mock_store = MagicMock()
        mock_result = MagicMock()
        mock_result.id = "result_20240101_120000"
        mock_result.strategy_id = "test_strategy_1"
        mock_result.symbol = "AAPL"
        mock_result.created_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_result.metrics = MagicMock()
        mock_result.metrics.model_dump.return_value = {"totalTrades": 5}
        mock_store.list_results.return_value = [mock_result]
        mock_store_cls.return_value = mock_store

        # Make request with strategy filter
        response = client.get(
            "/api/backtest/backtest/results",
            params={"strategy_id": "test_strategy_1"}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        mock_store.list_results.assert_called_once_with("test_strategy_1")

    @patch(BACKTEST_STORE_PATCH)
    def test_list_backtest_results_empty(self, mock_store_cls):
        """Test listing backtest results when none exist."""
        # Setup mocks
        mock_store = MagicMock()
        mock_store.list_results.return_value = []
        mock_store_cls.return_value = mock_store

        # Make request
        response = client.get("/api/backtest/backtest/results")

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


# ============================================================================
# Existing Endpoint Tests
# ============================================================================


class TestExistingBacktest:
    """Tests for existing POST /backtest/run endpoint."""

    @patch("lobster_quant.src.analysis.backtest.BacktestEngine")
    @patch("lobster_quant.src.analysis.signals.SignalGenerator")
    @patch(INDICATOR_ENGINE_PATCH)
    @patch(DATA_ENGINE_PATCH)
    def test_run_backtest_success(
        self, mock_data_engine_cls, mock_indicator_engine_cls,
        mock_signal_gen_cls, mock_engine_cls,
        mock_stock_data, mock_backtest_result
    ):
        """Test successful backtest run."""
        import pandas as pd

        # Setup mocks
        mock_data_engine = MagicMock()
        mock_data_engine.fetch_stock.return_value = mock_stock_data
        mock_data_engine_cls.return_value = mock_data_engine

        mock_indicator_engine = MagicMock()
        mock_indicator_engine.compute_all.return_value = mock_stock_data.daily
        mock_indicator_engine_cls.return_value = mock_indicator_engine

        mock_signal_gen = MagicMock()
        mock_signal_gen.calculate_score.return_value = 75.0
        mock_signal_gen_cls.return_value = mock_signal_gen

        mock_engine = MagicMock()
        mock_engine.holding_days = 20
        mock_engine.min_score = 60
        mock_engine.slippage = 0.001
        mock_engine.commission = 0.001
        mock_engine.run.return_value = mock_backtest_result
        mock_engine_cls.return_value = mock_engine

        # Make request
        response = client.post(
            "/api/backtest/run",
            json={
                "symbol": "AAPL",
                "holdingDays": 20,
                "minScore": 60,
            }
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert "totalTrades" in data
        assert "winRate" in data
        assert "trades" in data
        assert "equityCurve" in data

    @patch(DATA_ENGINE_PATCH)
    def test_run_backtest_stock_not_found(self, mock_data_engine_cls):
        """Test backtest with non-existent stock."""
        mock_data_engine = MagicMock()
        mock_data_engine.fetch_stock.return_value = None
        mock_data_engine_cls.return_value = mock_data_engine

        response = client.post(
            "/api/backtest/run",
            json={
                "symbol": "INVALID",
                "holdingDays": 20,
                "minScore": 60,
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
