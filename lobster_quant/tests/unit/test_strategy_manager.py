"""
Unit tests for StrategyManager.
"""

import shutil
import tempfile
from datetime import datetime

import pytest

from src.core.strategy_manager import StrategyManager
from src.data.models import Strategy, StrategyParams


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def manager(temp_dir):
    """Create a StrategyManager with temp directory."""
    return StrategyManager(data_dir=temp_dir)


@pytest.fixture
def sample_params():
    """Create sample strategy parameters."""
    return StrategyParams(
        holdingDays=20,
        minScore=60,
        slippagePct=0.001,
        commissionPct=0.001,
        positionSizing="fixed",
        positionSize=0.1,
        initialCapital=100000,
        maxPositions=5,
    )


@pytest.fixture
def created_strategy(manager, sample_params):
    """Create and return a custom strategy."""
    return manager.create_strategy(
        name="Test Strategy",
        description="A test strategy",
        params=sample_params,
    )


class TestListStrategies:
    """Tests for list_strategies."""

    def test_empty_list(self, manager):
        """Should return empty list when no strategies exist."""
        result = manager.list_strategies()
        assert result == []

    def test_lists_created_strategies(self, manager, created_strategy):
        """Should list created strategies."""
        result = manager.list_strategies()
        assert len(result) == 1
        assert result[0].id == created_strategy.id


class TestGetStrategy:
    """Tests for get_strategy."""

    def test_get_existing(self, manager, created_strategy):
        """Should retrieve an existing strategy."""
        result = manager.get_strategy(created_strategy.id)
        assert result is not None
        assert result.id == created_strategy.id
        assert result.name == "Test Strategy"

    def test_get_nonexistent(self, manager):
        """Should return None for nonexistent strategy."""
        result = manager.get_strategy("nonexistent_id")
        assert result is None


class TestCreateStrategy:
    """Tests for create_strategy."""

    def test_creates_with_generated_id(self, manager, sample_params):
        """Should generate a strategy ID with custom_ prefix."""
        strategy = manager.create_strategy(
            name="My Strategy",
            description="Description",
            params=sample_params,
        )
        assert strategy.id.startswith("custom_")
        assert strategy.name == "My Strategy"
        assert strategy.description == "Description"
        assert strategy.isPreset is False
        assert strategy.logic == "default"
        assert strategy.createdAt is not None

    def test_created_strategy_is_persisted(self, manager, sample_params):
        """Should persist the created strategy."""
        strategy = manager.create_strategy(
            name="Persisted",
            description="Test",
            params=sample_params,
        )
        retrieved = manager.get_strategy(strategy.id)
        assert retrieved is not None
        assert retrieved.name == "Persisted"

    def test_multiple_creates_have_unique_ids(self, manager, sample_params):
        """Should generate unique IDs for each strategy."""
        import time

        s1 = manager.create_strategy(name="S1", description="D1", params=sample_params)
        time.sleep(1.1)  # Ensure different timestamp
        s2 = manager.create_strategy(name="S2", description="D2", params=sample_params)
        assert s1.id != s2.id


class TestUpdateStrategy:
    """Tests for update_strategy."""

    def test_update_name(self, manager, created_strategy):
        """Should update strategy name."""
        result = manager.update_strategy(created_strategy.id, name="Updated Name")
        assert result is not None
        assert result.name == "Updated Name"
        assert result.updatedAt is not None

    def test_update_description(self, manager, created_strategy):
        """Should update strategy description."""
        result = manager.update_strategy(created_strategy.id, description="New description")
        assert result is not None
        assert result.description == "New description"

    def test_update_params(self, manager, created_strategy, sample_params):
        """Should update strategy params."""
        new_params = sample_params.model_copy(update={"holdingDays": 30})
        result = manager.update_strategy(created_strategy.id, params=new_params)
        assert result is not None
        assert result.params.holdingDays == 30

    def test_update_multiple_fields(self, manager, created_strategy, sample_params):
        """Should update multiple fields at once."""
        new_params = sample_params.model_copy(update={"minScore": 70})
        result = manager.update_strategy(
            created_strategy.id,
            name="Multi Update",
            description="Updated desc",
            params=new_params,
        )
        assert result is not None
        assert result.name == "Multi Update"
        assert result.description == "Updated desc"
        assert result.params.minScore == 70

    def test_update_nonexistent_returns_none(self, manager):
        """Should return None when updating nonexistent strategy."""
        result = manager.update_strategy("nonexistent", name="X")
        assert result is None

    def test_update_preset_returns_none(self, manager, temp_dir, sample_params):
        """Should return None when attempting to update a preset."""
        # Create a preset strategy directly via store
        from src.storage.strategy_store import StrategyStore

        store = StrategyStore(temp_dir)
        preset = Strategy(
            id="preset_test",
            name="Preset",
            description="A preset",
            params=sample_params,
            logic="default",
            isPreset=True,
            createdAt=datetime.now(),
        )
        # Save preset directly to presets dir
        import json

        preset_file = store.presets_dir / "preset_test.json"
        with open(preset_file, "w") as f:
            json.dump(preset.model_dump(), f, default=str)

        result = manager.update_strategy("preset_test", name="Hacked")
        assert result is None

    def test_updated_changes_persist(self, manager, created_strategy):
        """Should persist updated changes."""
        manager.update_strategy(created_strategy.id, name="Persisted Update")
        retrieved = manager.get_strategy(created_strategy.id)
        assert retrieved.name == "Persisted Update"


class TestDeleteStrategy:
    """Tests for delete_strategy."""

    def test_delete_existing_custom(self, manager, created_strategy):
        """Should delete an existing custom strategy."""
        result = manager.delete_strategy(created_strategy.id)
        assert result is True
        assert manager.get_strategy(created_strategy.id) is None

    def test_delete_nonexistent(self, manager):
        """Should return False when deleting nonexistent strategy."""
        result = manager.delete_strategy("nonexistent")
        assert result is False

    def test_delete_preset_returns_false(self, manager, temp_dir, sample_params):
        """Should return False when attempting to delete a preset."""
        from src.storage.strategy_store import StrategyStore

        store = StrategyStore(temp_dir)
        preset = Strategy(
            id="preset_del",
            name="Preset",
            description="A preset",
            params=sample_params,
            logic="default",
            isPreset=True,
            createdAt=datetime.now(),
        )
        import json

        preset_file = store.presets_dir / "preset_del.json"
        with open(preset_file, "w") as f:
            json.dump(preset.model_dump(), f, default=str)

        result = manager.delete_strategy("preset_del")
        assert result is False


class TestGetPresets:
    """Tests for get_presets."""

    def test_empty_presets(self, manager):
        """Should return empty list when no presets exist."""
        assert manager.get_presets() == []

    def test_filters_only_presets(self, manager, created_strategy, temp_dir, sample_params):
        """Should return only preset strategies."""
        from src.storage.strategy_store import StrategyStore

        store = StrategyStore(temp_dir)
        preset = Strategy(
            id="preset_only",
            name="Preset Only",
            description="A preset",
            params=sample_params,
            logic="default",
            isPreset=True,
            createdAt=datetime.now(),
        )
        import json

        preset_file = store.presets_dir / "preset_only.json"
        with open(preset_file, "w") as f:
            json.dump(preset.model_dump(), f, default=str)

        presets = manager.get_presets()
        assert len(presets) == 1
        assert presets[0].id == "preset_only"
        assert presets[0].isPreset is True


class TestCompareStrategies:
    """Tests for compare_strategies."""

    def test_compare_single_strategy(self, manager, created_strategy):
        """Should return results for a single valid strategy."""
        result = manager.compare_strategies(
            [created_strategy.id], "AAPL", "2024-01-01", "2024-12-31"
        )
        assert "strategies" in result
        assert "best_return" in result
        assert "best_sharpe" in result
        assert "lowest_drawdown" in result
        assert len(result["strategies"]) == 1
        assert result["strategies"][0]["id"] == created_strategy.id
        assert result["strategies"][0]["name"] == "Test Strategy"

    def test_compare_multiple_strategies(self, manager, sample_params):
        """Should return results for multiple strategies and pick best."""
        s1 = manager.create_strategy(name="S1", description="D1", params=sample_params)
        s2 = manager.create_strategy(name="S2", description="D2", params=sample_params)

        result = manager.compare_strategies([s1.id, s2.id], "AAPL", "2024-01-01", "2024-12-31")
        assert len(result["strategies"]) == 2
        ids = [s["id"] for s in result["strategies"]]
        assert s1.id in ids
        assert s2.id in ids

    def test_compare_skips_nonexistent(self, manager, created_strategy):
        """Should skip strategy IDs that don't exist."""
        result = manager.compare_strategies(
            [created_strategy.id, "nonexistent"], "AAPL", "2024-01-01", "2024-12-31"
        )
        assert len(result["strategies"]) == 1
        assert result["strategies"][0]["id"] == created_strategy.id

    def test_compare_all_nonexistent_returns_empty(self, manager):
        """Should return empty strategies when all IDs are nonexistent."""
        result = manager.compare_strategies(["fake1", "fake2"], "AAPL", "2024-01-01", "2024-12-31")
        assert result["strategies"] == []

    def test_compare_empty_ids_returns_empty(self, manager):
        """Should return empty strategies when given empty list."""
        result = manager.compare_strategies([], "AAPL", "2024-01-01", "2024-12-31")
        assert result["strategies"] == []

    def test_compare_placeholder_metrics_are_none(self, manager, created_strategy):
        """Should return None for metrics (placeholder until Phase 3)."""
        result = manager.compare_strategies(
            [created_strategy.id], "AAPL", "2024-01-01", "2024-12-31"
        )
        assert result["strategies"][0]["metrics"] is None
        assert result["strategies"][0]["equity_curve"] == []

    def test_compare_returns_correct_structure(self, manager, created_strategy):
        """Should return dictionary with all required keys."""
        result = manager.compare_strategies(
            [created_strategy.id], "AAPL", "2024-01-01", "2024-12-31"
        )
        assert isinstance(result, dict)
        assert set(result.keys()) == {
            "strategies",
            "best_return",
            "best_sharpe",
            "lowest_drawdown",
        }
        for s in result["strategies"]:
            assert set(s.keys()) == {"id", "name", "metrics", "equity_curve"}
