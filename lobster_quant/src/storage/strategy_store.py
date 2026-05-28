"""
Strategy Store - JSON persistence for trading strategies.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class StrategyStore:
    """Manages strategy persistence to JSON files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.strategies_dir = self.data_dir / "strategies"
        self.presets_dir = self.strategies_dir / "presets"
        self.custom_dir = self.strategies_dir / "custom"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create directories if they don't exist."""
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        self.custom_dir.mkdir(parents=True, exist_ok=True)

    def _get_strategy_class(self):
        """Lazy import to avoid triggering broken data/__init__.py."""
        from ..data.models import Strategy

        return Strategy

    def list_strategies(self) -> list[Any]:
        """List all strategies (presets + custom)."""
        strategy_cls = self._get_strategy_class()
        strategies = []

        # Load presets
        for file in self.presets_dir.glob("*.json"):
            try:
                strategy = self._load_from_file(file, strategy_cls)
                if strategy:
                    strategies.append(strategy)
            except Exception:
                continue

        # Load custom strategies
        for file in self.custom_dir.glob("*.json"):
            try:
                strategy = self._load_from_file(file, strategy_cls)
                if strategy:
                    strategies.append(strategy)
            except Exception:
                continue

        return strategies

    def get_strategy(self, strategy_id: str) -> Any | None:
        """Get strategy by ID."""
        strategy_cls = self._get_strategy_class()

        # Check presets first
        preset_file = self.presets_dir / f"{strategy_id}.json"
        if preset_file.exists():
            return self._load_from_file(preset_file, strategy_cls)

        # Check custom strategies
        custom_file = self.custom_dir / f"{strategy_id}.json"
        if custom_file.exists():
            return self._load_from_file(custom_file, strategy_cls)

        return None

    def save_strategy(self, strategy: Any) -> None:
        """Save a custom strategy."""
        if strategy.isPreset:
            raise ValueError("Cannot save preset strategies. Presets are read-only.")

        self._ensure_dirs()
        file_path = self.custom_dir / f"{strategy.id}.json"

        # Update timestamp
        strategy.updatedAt = datetime.now()

        # Save to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(strategy.model_dump(), f, indent=2, default=str)

    def delete_strategy(self, strategy_id: str) -> bool:
        """Delete a custom strategy (presets cannot be deleted)."""
        # Check if it's a preset
        preset_file = self.presets_dir / f"{strategy_id}.json"
        if preset_file.exists():
            raise ValueError("Cannot delete preset strategies.")

        # Delete custom strategy
        custom_file = self.custom_dir / f"{strategy_id}.json"
        if custom_file.exists():
            custom_file.unlink()
            return True

        return False

    def _load_from_file(self, file_path: Path, model_class: Any) -> Any | None:
        """Load a strategy from a JSON file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return model_class(**data)
        except Exception:
            return None
