"""
Strategy Manager - Business logic for strategy CRUD operations.
"""

from datetime import datetime
from typing import Any

from src.data.models import Strategy, StrategyParams
from src.storage.strategy_store import StrategyStore


class StrategyManager:
    """Manages strategies - CRUD operations and preset loading."""

    def __init__(self, data_dir: str = "data"):
        self.store = StrategyStore(data_dir)

    def list_strategies(self) -> list[Strategy]:
        """List all strategies (presets + custom)."""
        return self.store.list_strategies()

    def get_strategy(self, strategy_id: str) -> Strategy | None:
        """Get strategy by ID."""
        return self.store.get_strategy(strategy_id)

    def create_strategy(self, name: str, description: str, params: StrategyParams) -> Strategy:
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

    def update_strategy(self, strategy_id: str, **kwargs) -> Strategy | None:
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

    def get_presets(self) -> list[Strategy]:
        """Get all preset strategies."""
        return [s for s in self.list_strategies() if s.isPreset]

    def compare_strategies(
        self, strategy_ids: list[str], symbol: str, start_date: str, end_date: str
    ) -> dict[str, Any]:
        """Compare multiple strategies by running backtests.

        Args:
            strategy_ids: List of strategy IDs to compare
            symbol: Stock symbol to backtest
            start_date: Backtest start date (YYYY-MM-DD)
            end_date: Backtest end date (YYYY-MM-DD)

        Returns:
            Dictionary with comparison results:
            {
                "strategies": [...],
                "best_return": str,  # Strategy ID with highest return
                "best_sharpe": str,  # Strategy ID with highest Sharpe ratio
                "lowest_drawdown": str  # Strategy ID with lowest max drawdown
            }
        """
        results = []

        for strategy_id in strategy_ids:
            strategy = self.get_strategy(strategy_id)
            if strategy is None:
                continue

            # Run backtest for this strategy
            # Note: This will be implemented in Phase 3 when BacktestEngine is extended
            # For now, return a placeholder structure
            results.append(
                {
                    "id": strategy.id,
                    "name": strategy.name,
                    "metrics": None,  # Will be BacktestMetrics after Phase 3
                    "equity_curve": [],  # Will be List[EquityPoint] after Phase 3
                }
            )

        # Find best performers
        if not results:
            best_return_id = ""
            best_sharpe_id = ""
            lowest_drawdown_id = ""
        else:
            best_return = max(
                results,
                key=lambda x: x["metrics"].totalReturn if x["metrics"] else 0,
            )
            best_sharpe = max(
                results,
                key=lambda x: x["metrics"].sharpeRatio if x["metrics"] else 0,
            )
            lowest_drawdown = min(
                results,
                key=lambda x: x["metrics"].maxDrawdown if x["metrics"] else float("inf"),
            )
            best_return_id = best_return["id"]
            best_sharpe_id = best_sharpe["id"]
            lowest_drawdown_id = lowest_drawdown["id"]

        return {
            "strategies": results,
            "best_return": best_return_id,
            "best_sharpe": best_sharpe_id,
            "lowest_drawdown": lowest_drawdown_id,
        }
