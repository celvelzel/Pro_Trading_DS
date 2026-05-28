"""
Comprehensive unit tests for StrategyManager.

Covers all business logic paths:
  - list_strategies: empty, custom, presets, mixed
  - get_strategy: existing, nonexistent
  - create_strategy: custom_ prefix, field mapping, persistence
  - update_strategy: name, description, params, nonexistent→None, preset→None
  - delete_strategy: custom→True, nonexistent→False, preset→False
  - get_presets: empty, filters correctly
  - compare_strategies: single, multiple, skips nonexistent, empty, structure
"""

import json
import time
from datetime import datetime

import pytest

from src.core.strategy_manager import StrategyManager
from src.data.models import Strategy, StrategyParams
from src.storage.strategy_store import StrategyStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_params():
    """Default StrategyParams for tests."""
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
def manager(tmp_path):
    """StrategyManager backed by an isolated tmp_path."""
    return StrategyManager(data_dir=str(tmp_path))


@pytest.fixture
def created_strategy(manager, sample_params):
    """A pre-created custom strategy (persists to disk)."""
    return manager.create_strategy(
        name="Test Strategy",
        description="A test strategy",
        params=sample_params,
    )


def _write_preset_json(store: StrategyStore, strategy_id: str, name: str, params: StrategyParams):
    """Helper: write a preset JSON directly into the presets directory."""
    preset = Strategy(
        id=strategy_id,
        name=name,
        description=f"Preset {name}",
        params=params,
        logic="default",
        isPreset=True,
        createdAt=datetime.now(),
    )
    preset_file = store.presets_dir / f"{strategy_id}.json"
    preset_file.write_text(json.dumps(preset.model_dump(), default=str), encoding="utf-8")
    return preset


# ===========================================================================
# list_strategies
# ===========================================================================


class TestListStrategies:
    """Tests for StrategyManager.list_strategies."""

    def test_empty_when_no_strategies_exist(self, manager):
        result = manager.list_strategies()
        assert result == []

    def test_lists_created_custom_strategy(self, manager, created_strategy):
        result = manager.list_strategies()
        assert len(result) == 1
        assert result[0].id == created_strategy.id
        assert result[0].name == "Test Strategy"

    def test_lists_multiple_strategies(self, manager, sample_params):
        s1 = manager.create_strategy(name="A", description="D", params=sample_params)
        time.sleep(1.1)
        s2 = manager.create_strategy(name="B", description="D", params=sample_params)
        result = manager.list_strategies()
        ids = [s.id for s in result]
        assert len(result) == 2
        assert s1.id in ids
        assert s2.id in ids

    def test_includes_presets(self, manager, created_strategy, tmp_path, sample_params):
        store = StrategyStore(str(tmp_path))
        _write_preset_json(store, "preset_1", "Preset One", sample_params)

        result = manager.list_strategies()
        ids = [s.id for s in result]
        assert created_strategy.id in ids
        assert "preset_1" in ids
        assert len(result) == 2

    def test_returns_strategy_objects(self, manager, created_strategy):
        result = manager.list_strategies()
        assert isinstance(result, list)
        for s in result:
            assert isinstance(s, Strategy)


# ===========================================================================
# get_strategy
# ===========================================================================


class TestGetStrategy:
    """Tests for StrategyManager.get_strategy."""

    def test_returns_existing_custom_strategy(self, manager, created_strategy):
        result = manager.get_strategy(created_strategy.id)
        assert result is not None
        assert result.id == created_strategy.id
        assert result.name == "Test Strategy"
        assert result.description == "A test strategy"

    def test_returns_none_for_nonexistent(self, manager):
        assert manager.get_strategy("does_not_exist") is None

    def test_returns_none_for_empty_string(self, manager):
        assert manager.get_strategy("") is None

    def test_can_retrieve_preset(self, manager, tmp_path, sample_params):
        store = StrategyStore(str(tmp_path))
        _write_preset_json(store, "preset_get", "Gettable Preset", sample_params)

        result = manager.get_strategy("preset_get")
        assert result is not None
        assert result.id == "preset_get"
        assert result.isPreset is True

    def test_retrieved_fields_match_created(self, manager, sample_params):
        original = manager.create_strategy(
            name="FieldCheck", description="Desc", params=sample_params
        )
        retrieved = manager.get_strategy(original.id)
        assert retrieved.name == original.name
        assert retrieved.description == original.description
        assert retrieved.params.holdingDays == original.params.holdingDays
        assert retrieved.logic == original.logic
        assert retrieved.isPreset == original.isPreset


# ===========================================================================
# create_strategy
# ===========================================================================


class TestCreateStrategy:
    """Tests for StrategyManager.create_strategy."""

    def test_generates_id_with_custom_prefix(self, manager, sample_params):
        strategy = manager.create_strategy(name="X", description="D", params=sample_params)
        assert strategy.id.startswith("custom_")

    def test_sets_all_provided_fields(self, manager, sample_params):
        strategy = manager.create_strategy(
            name="Full", description="Complete", params=sample_params
        )
        assert strategy.name == "Full"
        assert strategy.description == "Complete"
        assert strategy.params == sample_params

    def test_sets_ispreset_false(self, manager, sample_params):
        strategy = manager.create_strategy(name="X", description="D", params=sample_params)
        assert strategy.isPreset is False

    def test_sets_logic_to_default(self, manager, sample_params):
        strategy = manager.create_strategy(name="X", description="D", params=sample_params)
        assert strategy.logic == "default"

    def test_sets_created_at(self, manager, sample_params):
        before = datetime.now()
        strategy = manager.create_strategy(name="X", description="D", params=sample_params)
        assert strategy.createdAt is not None
        assert strategy.createdAt >= before

    def test_persists_to_disk(self, manager, sample_params):
        strategy = manager.create_strategy(name="Persist", description="D", params=sample_params)
        retrieved = manager.get_strategy(strategy.id)
        assert retrieved is not None
        assert retrieved.name == "Persist"

    def test_multiple_creates_yield_unique_ids(self, manager, sample_params):
        s1 = manager.create_strategy(name="A", description="D", params=sample_params)
        time.sleep(1.1)
        s2 = manager.create_strategy(name="B", description="D", params=sample_params)
        assert s1.id != s2.id

    def test_created_strategy_appears_in_list(self, manager, sample_params):
        strategy = manager.create_strategy(name="Listed", description="D", params=sample_params)
        result = manager.list_strategies()
        assert any(s.id == strategy.id for s in result)

    def test_params_round_trip(self, manager):
        custom_params = StrategyParams(
            holdingDays=50,
            minScore=80,
            slippagePct=0.005,
            commissionPct=0.003,
            positionSizing="dynamic",
            positionSize=0.25,
            initialCapital=500000,
            maxPositions=10,
        )
        strategy = manager.create_strategy(name="Custom", description="D", params=custom_params)
        retrieved = manager.get_strategy(strategy.id)
        assert retrieved.params.holdingDays == 50
        assert retrieved.params.minScore == 80
        assert retrieved.params.slippagePct == 0.005
        assert retrieved.params.positionSizing == "dynamic"
        assert retrieved.params.maxPositions == 10


# ===========================================================================
# update_strategy
# ===========================================================================


class TestUpdateStrategy:
    """Tests for StrategyManager.update_strategy."""

    def test_update_name(self, manager, created_strategy):
        result = manager.update_strategy(created_strategy.id, name="New Name")
        assert result is not None
        assert result.name == "New Name"

    def test_update_description(self, manager, created_strategy):
        result = manager.update_strategy(created_strategy.id, description="New desc")
        assert result is not None
        assert result.description == "New desc"

    def test_update_params(self, manager, created_strategy, sample_params):
        new_params = sample_params.model_copy(update={"holdingDays": 30})
        result = manager.update_strategy(created_strategy.id, params=new_params)
        assert result is not None
        assert result.params.holdingDays == 30

    def test_update_multiple_fields_at_once(self, manager, created_strategy, sample_params):
        new_params = sample_params.model_copy(update={"minScore": 70})
        result = manager.update_strategy(
            created_strategy.id,
            name="Multi",
            description="Updated",
            params=new_params,
        )
        assert result is not None
        assert result.name == "Multi"
        assert result.description == "Updated"
        assert result.params.minScore == 70

    def test_sets_updated_at_timestamp(self, manager, created_strategy):
        result = manager.update_strategy(created_strategy.id, name="Timestamped")
        assert result.updatedAt is not None

    def test_persists_updated_changes(self, manager, created_strategy):
        manager.update_strategy(created_strategy.id, name="Persisted")
        retrieved = manager.get_strategy(created_strategy.id)
        assert retrieved.name == "Persisted"

    def test_returns_none_for_nonexistent_id(self, manager):
        result = manager.update_strategy("nonexistent", name="X")
        assert result is None

    def test_returns_none_for_empty_id(self, manager):
        result = manager.update_strategy("", name="X")
        assert result is None

    def test_returns_none_for_preset_strategy(self, manager, tmp_path, sample_params):
        store = StrategyStore(str(tmp_path))
        _write_preset_json(store, "preset_upd", "Preset", sample_params)

        result = manager.update_strategy("preset_upd", name="Hacked")
        assert result is None

    def test_preset_not_modified_by_update_attempt(self, manager, tmp_path, sample_params):
        store = StrategyStore(str(tmp_path))
        _write_preset_json(store, "preset_safe", "Original", sample_params)

        manager.update_strategy("preset_safe", name="Hacked")
        preset = manager.get_strategy("preset_safe")
        assert preset.name == "Original"

    def test_update_preserves_unspecified_fields(self, manager, created_strategy):
        original_desc = created_strategy.description
        original_params = created_strategy.params
        result = manager.update_strategy(created_strategy.id, name="Only Name")
        assert result.description == original_desc
        assert result.params == original_params

    def test_update_with_no_kwargs_returns_strategy(self, manager, created_strategy):
        """Calling update with no field kwargs should still set updatedAt and save."""
        result = manager.update_strategy(created_strategy.id)
        assert result is not None
        assert result.name == created_strategy.name
        assert result.updatedAt is not None

    def test_update_with_unknown_kwargs_ignored(self, manager, created_strategy):
        """Unknown kwargs should be silently ignored."""
        result = manager.update_strategy(created_strategy.id, unknown_field="value")
        assert result is not None
        assert result.name == created_strategy.name


# ===========================================================================
# delete_strategy
# ===========================================================================


class TestDeleteStrategy:
    """Tests for StrategyManager.delete_strategy."""

    def test_deletes_existing_custom_strategy(self, manager, created_strategy):
        result = manager.delete_strategy(created_strategy.id)
        assert result is True

    def test_deleted_strategy_no_longer_retrievable(self, manager, created_strategy):
        manager.delete_strategy(created_strategy.id)
        assert manager.get_strategy(created_strategy.id) is None

    def test_deleted_strategy_removed_from_list(self, manager, created_strategy):
        manager.delete_strategy(created_strategy.id)
        result = manager.list_strategies()
        assert all(s.id != created_strategy.id for s in result)

    def test_returns_false_for_nonexistent_id(self, manager):
        assert manager.delete_strategy("nonexistent") is False

    def test_returns_false_for_empty_string(self, manager):
        assert manager.delete_strategy("") is False

    def test_returns_false_for_preset_strategy(self, manager, tmp_path, sample_params):
        store = StrategyStore(str(tmp_path))
        _write_preset_json(store, "preset_del", "Preset", sample_params)

        result = manager.delete_strategy("preset_del")
        assert result is False

    def test_preset_not_deleted(self, manager, tmp_path, sample_params):
        store = StrategyStore(str(tmp_path))
        _write_preset_json(store, "preset_undeleted", "Preset", sample_params)

        manager.delete_strategy("preset_undeleted")
        preset = manager.get_strategy("preset_undeleted")
        assert preset is not None
        assert preset.name == "Preset"

    def test_delete_does_not_affect_other_strategies(self, manager, sample_params):
        s1 = manager.create_strategy(name="A", description="D", params=sample_params)
        time.sleep(1.1)
        s2 = manager.create_strategy(name="B", description="D", params=sample_params)

        manager.delete_strategy(s1.id)
        remaining = manager.list_strategies()
        assert len(remaining) == 1
        assert remaining[0].id == s2.id


# ===========================================================================
# get_presets
# ===========================================================================


class TestGetPresets:
    """Tests for StrategyManager.get_presets."""

    def test_empty_when_no_presets(self, manager):
        assert manager.get_presets() == []

    def test_returns_only_presets(self, manager, tmp_path, sample_params):
        store = StrategyStore(str(tmp_path))
        _write_preset_json(store, "p1", "Preset A", sample_params)
        _write_preset_json(store, "p2", "Preset B", sample_params)

        presets = manager.get_presets()
        assert len(presets) == 2
        assert all(s.isPreset for s in presets)

    def test_excludes_custom_strategies(self, manager, created_strategy, tmp_path, sample_params):
        store = StrategyStore(str(tmp_path))
        _write_preset_json(store, "p_only", "Only Preset", sample_params)

        presets = manager.get_presets()
        assert len(presets) == 1
        assert presets[0].id == "p_only"
        assert presets[0].isPreset is True

    def test_all_results_are_strategy_instances(self, manager, tmp_path, sample_params):
        store = StrategyStore(str(tmp_path))
        _write_preset_json(store, "p_type", "Type Check", sample_params)

        for s in manager.get_presets():
            assert isinstance(s, Strategy)


# ===========================================================================
# compare_strategies
# ===========================================================================


class TestCompareStrategies:
    """Tests for StrategyManager.compare_strategies."""

    def test_single_strategy(self, manager, created_strategy):
        result = manager.compare_strategies(
            [created_strategy.id], "AAPL", "2024-01-01", "2024-12-31"
        )
        assert len(result["strategies"]) == 1
        assert result["strategies"][0]["id"] == created_strategy.id
        assert result["strategies"][0]["name"] == "Test Strategy"

    def test_multiple_strategies(self, manager, sample_params):
        s1 = manager.create_strategy(name="S1", description="D1", params=sample_params)
        time.sleep(1.1)
        s2 = manager.create_strategy(name="S2", description="D2", params=sample_params)

        result = manager.compare_strategies(
            [s1.id, s2.id], "AAPL", "2024-01-01", "2024-12-31"
        )
        assert len(result["strategies"]) == 2
        ids = [s["id"] for s in result["strategies"]]
        assert s1.id in ids
        assert s2.id in ids

    def test_skips_nonexistent_ids(self, manager, created_strategy):
        result = manager.compare_strategies(
            [created_strategy.id, "nonexistent"], "AAPL", "2024-01-01", "2024-12-31"
        )
        assert len(result["strategies"]) == 1
        assert result["strategies"][0]["id"] == created_strategy.id

    def test_all_nonexistent_returns_empty(self, manager):
        result = manager.compare_strategies(
            ["fake1", "fake2"], "AAPL", "2024-01-01", "2024-12-31"
        )
        assert result["strategies"] == []

    def test_empty_ids_returns_empty(self, manager):
        result = manager.compare_strategies([], "AAPL", "2024-01-01", "2024-12-31")
        assert result["strategies"] == []

    def test_returns_correct_top_level_keys(self, manager, created_strategy):
        result = manager.compare_strategies(
            [created_strategy.id], "AAPL", "2024-01-01", "2024-12-31"
        )
        assert set(result.keys()) == {"strategies", "best_return", "best_sharpe", "lowest_drawdown"}

    def test_returns_correct_strategy_keys(self, manager, created_strategy):
        result = manager.compare_strategies(
            [created_strategy.id], "AAPL", "2024-01-01", "2024-12-31"
        )
        for s in result["strategies"]:
            assert set(s.keys()) == {"id", "name", "metrics", "equity_curve"}

    def test_placeholder_metrics_are_none(self, manager, created_strategy):
        result = manager.compare_strategies(
            [created_strategy.id], "AAPL", "2024-01-01", "2024-12-31"
        )
        assert result["strategies"][0]["metrics"] is None
        assert result["strategies"][0]["equity_curve"] == []

    def test_best_fields_empty_string_when_no_results(self, manager):
        result = manager.compare_strategies(
            ["nonexistent"], "AAPL", "2024-01-01", "2024-12-31"
        )
        assert result["best_return"] == ""
        assert result["best_sharpe"] == ""
        assert result["lowest_drawdown"] == ""

    def test_best_fields_populated_when_results_exist(self, manager, created_strategy):
        result = manager.compare_strategies(
            [created_strategy.id], "AAPL", "2024-01-01", "2024-12-31"
        )
        # With metrics=None, the key comparison defaults to 0, so the only result wins
        assert result["best_return"] == created_strategy.id
        assert result["best_sharpe"] == created_strategy.id
        assert result["lowest_drawdown"] == created_strategy.id
