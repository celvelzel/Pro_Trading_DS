"""
Simulation Store - JSON persistence for simulated trades and snapshots.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class SimulationStore:
    """Manages simulation data persistence to JSON files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.simulation_dir = self.data_dir / "simulation"
        self.trades_dir = self.simulation_dir / "trades"
        self.snapshots_dir = self.simulation_dir / "snapshots"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create directories if they don't exist."""
        self.trades_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def _get_model_classes(self):
        """Lazy import to avoid triggering broken data/__init__.py."""
        from src.data.models import DailySnapshot, SimulatedTrade

        return SimulatedTrade, DailySnapshot

    def save_trade(self, trade: Any) -> None:
        """Save a simulated trade."""
        self._ensure_dirs()

        # Create strategy-specific directory
        strategy_trades_dir = self.trades_dir / trade.strategyId
        strategy_trades_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename based on month
        month_str = datetime.now().strftime("%Y%m")
        file_path = strategy_trades_dir / f"trades_{month_str}.json"

        # Load existing trades or create new list
        trades = []
        if file_path.exists():
            try:
                with open(file_path, encoding="utf-8") as f:
                    trades = json.load(f)
            except Exception:
                trades = []

        # Update or add trade
        trade_dict = trade.model_dump()
        existing_index = next((i for i, t in enumerate(trades) if t.get("id") == trade.id), None)

        if existing_index is not None:
            trades[existing_index] = trade_dict
        else:
            trades.append(trade_dict)

        # Save to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(trades, f, indent=2, default=str)

    def get_trades(self, strategy_id: str, status: str | None = None) -> list[Any]:
        """Get trades for a strategy, optionally filtered by status."""
        SimulatedTrade, _ = self._get_model_classes()

        strategy_trades_dir = self.trades_dir / strategy_id
        if not strategy_trades_dir.exists():
            return []

        trades = []
        for file in strategy_trades_dir.glob("trades_*.json"):
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)
                for trade_data in data:
                    trade = SimulatedTrade(**trade_data)
                    if status is None or trade.status == status:
                        trades.append(trade)
            except Exception:
                continue

        # Sort by entry date (newest first)
        trades.sort(key=lambda t: t.entryDate, reverse=True)
        return trades

    def save_snapshot(self, snapshot: Any) -> None:
        """Save daily snapshot."""
        self._ensure_dirs()

        # Create strategy-specific directory
        strategy_snapshots_dir = self.snapshots_dir / snapshot.strategyId
        strategy_snapshots_dir.mkdir(parents=True, exist_ok=True)

        # Save to file with date in filename
        file_path = strategy_snapshots_dir / f"snapshot_{snapshot.date}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(snapshot.model_dump(), f, indent=2, default=str)

    def get_snapshots(self, strategy_id: str, days: int = 30) -> list[Any]:
        """Get recent snapshots for a strategy."""
        _, DailySnapshot = self._get_model_classes()

        strategy_snapshots_dir = self.snapshots_dir / strategy_id
        if not strategy_snapshots_dir.exists():
            return []

        snapshots = []
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        for file in strategy_snapshots_dir.glob("snapshot_*.json"):
            try:
                # Extract date from filename
                date_str = file.stem.replace("snapshot_", "")
                if date_str >= cutoff_date:
                    with open(file, encoding="utf-8") as f:
                        data = json.load(f)
                    snapshots.append(DailySnapshot(**data))
            except Exception:
                continue

        # Sort by date (newest first)
        snapshots.sort(key=lambda s: s.date, reverse=True)
        return snapshots
