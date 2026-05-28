"""
Unit tests for storage layer.
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.data.models import BacktestResult, DailySnapshot, SimulatedTrade, Strategy, StrategyParams
from src.storage import BacktestStore, SimulationStore, StrategyStore


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_strategy():
    """Create a sample strategy for testing."""
    return Strategy(
        id="test_strategy_001",
        name="Test Strategy",
        description="A test strategy",
        params=StrategyParams(
            holdingDays=20,
            minScore=60,
            slippagePct=0.001,
            commissionPct=0.001,
            positionSizing="fixed",
            positionSize=0.1,
            initialCapital=100000,
            maxPositions=5,
        ),
        logic="default",
        isPreset=False,
        createdAt=datetime.now(),
    )


@pytest.fixture
def sample_backtest_result():
    """Create a sample backtest result for testing."""
    return BacktestResult(
        symbol="AAPL",
        win_rate=0.6,
        avg_return=0.05,
        profit_factor=1.5,
        max_drawdown=0.1,
        cumulative_return=0.25,
        best_trade=0.15,
        worst_trade=-0.05,
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 5, 26),
    )


@pytest.fixture
def sample_trade():
    """Create a sample simulated trade for testing."""
    return SimulatedTrade(
        id="trade_001",
        strategyId="test_strategy_001",
        symbol="AAPL",
        entryDate="2026-05-20",
        entryPrice=150.0,
        shares=100,
        status="open",
    )


@pytest.fixture
def sample_snapshot():
    """Create a sample daily snapshot for testing."""
    return DailySnapshot(
        date="2026-05-26",
        strategyId="test_strategy_001",
        selectedStocks=[{"symbol": "AAPL", "score": 85}],
        openTrades=[],
        closedTrades=[],
        portfolioValue=100000.0,
        cash=50000.0,
        invested=50000.0,
    )


class TestStrategyStore:
    """Tests for StrategyStore."""

    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates required directories."""
        _ = StrategyStore(data_dir=temp_dir)
        assert Path(temp_dir, "strategies", "presets").exists()
        assert Path(temp_dir, "strategies", "custom").exists()

    def test_save_and_get_strategy(self, temp_dir, sample_strategy):
        """Test saving and retrieving a strategy."""
        store = StrategyStore(data_dir=temp_dir)
        store.save_strategy(sample_strategy)

        retrieved = store.get_strategy("test_strategy_001")
        assert retrieved is not None
        assert retrieved.id == "test_strategy_001"
        assert retrieved.name == "Test Strategy"

    def test_list_strategies(self, temp_dir, sample_strategy):
        """Test listing all strategies."""
        store = StrategyStore(data_dir=temp_dir)
        store.save_strategy(sample_strategy)

        strategies = store.list_strategies()
        assert len(strategies) >= 1
        assert any(s.id == "test_strategy_001" for s in strategies)

    def test_delete_strategy(self, temp_dir, sample_strategy):
        """Test deleting a custom strategy."""
        store = StrategyStore(data_dir=temp_dir)
        store.save_strategy(sample_strategy)

        result = store.delete_strategy("test_strategy_001")
        assert result is True

        retrieved = store.get_strategy("test_strategy_001")
        assert retrieved is None

    def test_delete_nonexistent_strategy(self, temp_dir):
        """Test deleting a non-existent strategy."""
        store = StrategyStore(data_dir=temp_dir)
        result = store.delete_strategy("nonexistent")
        assert result is False

    def test_cannot_save_preset(self, temp_dir):
        """Test that preset strategies cannot be saved."""
        store = StrategyStore(data_dir=temp_dir)

        preset = Strategy(
            id="preset_001",
            name="Preset",
            description="A preset strategy",
            params=StrategyParams(),
            isPreset=True,
            createdAt=datetime.now(),
        )

        with pytest.raises(ValueError, match="Cannot save preset strategies"):
            store.save_strategy(preset)

    def test_cannot_delete_preset(self, temp_dir):
        """Test that preset strategies cannot be deleted."""
        store = StrategyStore(data_dir=temp_dir)

        # Create a preset file manually
        preset_file = Path(temp_dir, "strategies", "presets", "preset_001.json")
        preset_file.write_text('{"id": "preset_001", "isPreset": true}')

        with pytest.raises(ValueError, match="Cannot delete preset strategies"):
            store.delete_strategy("preset_001")


class TestBacktestStore:
    """Tests for BacktestStore."""

    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates required directories."""
        _ = BacktestStore(data_dir=temp_dir)
        assert Path(temp_dir, "backtest_results").exists()

    def test_save_and_get_result(self, temp_dir, sample_backtest_result):
        """Test saving and retrieving a backtest result."""
        store = BacktestStore(data_dir=temp_dir)
        result_id = store.save_result(sample_backtest_result)

        assert result_id is not None
        assert result_id.startswith("result_")

        retrieved = store.get_result(result_id)
        assert retrieved is not None
        assert retrieved.symbol == "AAPL"

    def test_list_results(self, temp_dir, sample_backtest_result):
        """Test listing backtest results."""
        store = BacktestStore(data_dir=temp_dir)
        store.save_result(sample_backtest_result)

        results = store.list_results()
        assert len(results) >= 1

    def test_get_nonexistent_result(self, temp_dir):
        """Test getting a non-existent result."""
        store = BacktestStore(data_dir=temp_dir)
        result = store.get_result("nonexistent")
        assert result is None


class TestSimulationStore:
    """Tests for SimulationStore."""

    def test_init_creates_directories(self, temp_dir):
        """Test that initialization creates required directories."""
        _ = SimulationStore(data_dir=temp_dir)
        assert Path(temp_dir, "simulation", "trades").exists()
        assert Path(temp_dir, "simulation", "snapshots").exists()

    def test_save_and_get_trades(self, temp_dir, sample_trade):
        """Test saving and retrieving trades."""
        store = SimulationStore(data_dir=temp_dir)
        store.save_trade(sample_trade)

        trades = store.get_trades("test_strategy_001")
        assert len(trades) == 1
        assert trades[0].id == "trade_001"

    def test_get_trades_by_status(self, temp_dir, sample_trade):
        """Test filtering trades by status."""
        store = SimulationStore(data_dir=temp_dir)
        store.save_trade(sample_trade)

        # Get open trades
        open_trades = store.get_trades("test_strategy_001", status="open")
        assert len(open_trades) == 1

        # Get closed trades (should be empty)
        closed_trades = store.get_trades("test_strategy_001", status="closed")
        assert len(closed_trades) == 0

    def test_save_and_get_snapshots(self, temp_dir, sample_snapshot):
        """Test saving and retrieving snapshots."""
        store = SimulationStore(data_dir=temp_dir)
        store.save_snapshot(sample_snapshot)

        snapshots = store.get_snapshots("test_strategy_001")
        assert len(snapshots) == 1
        assert snapshots[0].date == "2026-05-26"

    def test_update_trade(self, temp_dir, sample_trade):
        """Test updating an existing trade."""
        store = SimulationStore(data_dir=temp_dir)
        store.save_trade(sample_trade)

        # Update trade
        sample_trade.status = "closed"
        sample_trade.exitDate = "2026-05-26"
        sample_trade.exitPrice = 160.0
        sample_trade.pnl = 1000.0
        store.save_trade(sample_trade)

        trades = store.get_trades("test_strategy_001")
        assert len(trades) == 1
        assert trades[0].status == "closed"

    def test_get_trades_nonexistent_strategy(self, temp_dir):
        """Test getting trades for non-existent strategy."""
        store = SimulationStore(data_dir=temp_dir)
        trades = store.get_trades("nonexistent")
        assert trades == []

    def test_get_snapshots_nonexistent_strategy(self, temp_dir):
        """Test getting snapshots for non-existent strategy."""
        store = SimulationStore(data_dir=temp_dir)
        snapshots = store.get_snapshots("nonexistent")
        assert snapshots == []
