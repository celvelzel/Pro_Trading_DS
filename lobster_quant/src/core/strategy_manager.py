"""
Strategy Manager - Business logic for strategy CRUD operations.
"""

from datetime import datetime
from typing import List, Optional

from src.storage.strategy_store import StrategyStore
from src.data.models import Strategy, StrategyParams


class StrategyManager:
    """Manages strategies - CRUD operations and preset loading."""

    def __init__(self, data_dir: str = "data"):
        self.store = StrategyStore(data_dir)

    def list_strategies(self) -> List[Strategy]:
        """List all strategies (presets + custom)."""
        return self.store.list_strategies()

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get strategy by ID."""
        return self.store.get_strategy(strategy_id)

    def create_strategy(
        self, name: str, description: str, params: StrategyParams
    ) -> Strategy:
        """Create a new custom strategy.

        Args:
            name: Strategy name
            description: Strategy description
            params: Strategy parameters

        Returns:
            Created Strategy with generated ID
        """
        strategy_id = f"custom_{int(datetime.now().timestamp())}"

        strategy = Strategy(
            id=strategy_id,
            name=name,
            description=description,
            params=params,
            logic="default",
            isPreset=False,
            createdAt=datetime.now(),
        )

        self.store.save_strategy(strategy)
        return strategy

    def update_strategy(self, strategy_id: str, **kwargs) -> Optional[Strategy]:
        """Update an existing custom strategy.

        Args:
            strategy_id: Strategy ID to update
            **kwargs: Fields to update (name, description, params)

        Returns:
            Updated Strategy or None if not found/preset
        """
        strategy = self.store.get_strategy(strategy_id)
        if strategy is None or strategy.isPreset:
            return None

        if "name" in kwargs:
            strategy.name = kwargs["name"]
        if "description" in kwargs:
            strategy.description = kwargs["description"]
        if "params" in kwargs:
            strategy.params = kwargs["params"]

        strategy.updatedAt = datetime.now()
        self.store.save_strategy(strategy)
        return strategy

    def delete_strategy(self, strategy_id: str) -> bool:
        """Delete a custom strategy.

        Args:
            strategy_id: Strategy ID to delete

        Returns:
            True if deleted, False if not found or preset
        """
        try:
            return self.store.delete_strategy(strategy_id)
        except ValueError:
            return False

    def get_presets(self) -> List[Strategy]:
        """Get all preset strategies."""
        return [s for s in self.list_strategies() if s.isPreset]
