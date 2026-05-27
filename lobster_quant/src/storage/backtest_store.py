"""
Backtest Store - JSON persistence for backtest results.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class BacktestStore:
    """Manages backtest result persistence to JSON files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.results_dir = self.data_dir / "backtest_results"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create directories if they don't exist."""
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def _get_backtest_result_class(self):
        """Lazy import to avoid triggering broken data/__init__.py."""
        from src.data.models import BacktestResult

        return BacktestResult

    def save_result(self, result: Any) -> str:
        """Save backtest result, return result ID."""
        self._ensure_dirs()

        # Generate result ID based on timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_id = f"result_{timestamp}"

        # Save to file
        file_path = self.results_dir / f"{result_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2, default=str)

        return result_id

    def get_result(self, result_id: str) -> Any | None:
        """Get backtest result by ID."""
        BacktestResult = self._get_backtest_result_class()

        file_path = self.results_dir / f"{result_id}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return BacktestResult(**data)
        except Exception:
            return None

    def list_results(self, strategy_id: str | None = None) -> list[Any]:
        """List backtest results, optionally filtered by strategy."""
        BacktestResult = self._get_backtest_result_class()
        results = []

        for file in self.results_dir.glob("*.json"):
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)
                result = BacktestResult(**data)

                # Filter by strategy if specified
                if strategy_id:
                    result_strategy_id = getattr(result, "strategy_id", None)
                    if result_strategy_id and result_strategy_id != strategy_id:
                        continue

                results.append(result)
            except Exception:
                continue

        # Sort by start_date (newest first)
        results.sort(key=lambda r: r.start_date or datetime.min, reverse=True)
        return results
