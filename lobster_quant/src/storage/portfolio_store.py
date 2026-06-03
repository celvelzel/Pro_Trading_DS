"""
Portfolio Store - JSON persistence for real portfolio positions and P&L tracking.
Separate from simulation — this tracks actual holdings.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class PortfolioStore:
    """Manages portfolio position persistence to JSON files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.portfolio_dir = self.data_dir / "portfolio"
        self.positions_file = self.portfolio_dir / "positions.json"
        self.cash_file = self.portfolio_dir / "cash.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create directories if they don't exist."""
        self.portfolio_dir.mkdir(parents=True, exist_ok=True)

    def _load_positions(self) -> list[dict[str, Any]]:
        """Load all positions from disk."""
        if not self.positions_file.exists():
            return []
        try:
            with open(self.positions_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return []

    def _save_positions(self, positions: list[dict[str, Any]]) -> None:
        """Save positions to disk."""
        self._ensure_dirs()
        with open(self.positions_file, "w", encoding="utf-8") as f:
            json.dump(positions, f, indent=2, default=str)

    def _load_cash(self) -> dict[str, Any]:
        """Load cash balance from disk."""
        if not self.cash_file.exists():
            return {"balance": 100000.0, "updated_at": datetime.now().isoformat()}
        try:
            with open(self.cash_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception):
            return {"balance": 100000.0, "updated_at": datetime.now().isoformat()}

    def _save_cash(self, cash_data: dict[str, Any]) -> None:
        """Save cash balance to disk."""
        self._ensure_dirs()
        with open(self.cash_file, "w", encoding="utf-8") as f:
            json.dump(cash_data, f, indent=2, default=str)

    # =========================================================================
    # Position CRUD
    # =========================================================================

    def add_position(
        self,
        symbol: str,
        shares: int,
        cost_basis: float,
        strategy_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Add a new position to the portfolio."""
        positions = self._load_positions()

        # Check if position already exists for this symbol
        existing = next((p for p in positions if p["symbol"] == symbol.upper()), None)
        if existing:
            # Average up/down: merge into existing position
            total_cost = existing["cost_basis"] * existing["shares"] + cost_basis * shares
            total_shares = existing["shares"] + shares
            existing["cost_basis"] = round(total_cost / total_shares, 4)
            existing["shares"] = total_shares
            existing["updated_at"] = datetime.now().isoformat()
            self._save_positions(positions)
            return existing

        position = {
            "id": str(uuid.uuid4()),
            "symbol": symbol.upper(),
            "shares": shares,
            "cost_basis": cost_basis,
            "opened_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "strategy_id": strategy_id,
        }
        positions.append(position)
        self._save_positions(positions)
        return position

    def update_position(
        self,
        position_id: str,
        shares: Optional[int] = None,
        cost_basis: Optional[float] = None,
        strategy_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Update an existing position."""
        positions = self._load_positions()
        position = next((p for p in positions if p["id"] == position_id), None)

        if not position:
            return None

        if shares is not None:
            position["shares"] = shares
        if cost_basis is not None:
            position["cost_basis"] = cost_basis
        if strategy_id is not None:
            position["strategy_id"] = strategy_id

        position["updated_at"] = datetime.now().isoformat()
        self._save_positions(positions)
        return position

    def delete_position(self, position_id: str) -> bool:
        """Delete a position from the portfolio."""
        positions = self._load_positions()
        original_len = len(positions)
        positions = [p for p in positions if p["id"] != position_id]

        if len(positions) == original_len:
            return False

        self._save_positions(positions)
        return True

    def get_position(self, position_id: str) -> Optional[dict[str, Any]]:
        """Get a single position by ID."""
        positions = self._load_positions()
        return next((p for p in positions if p["id"] == position_id), None)

    def get_all_positions(self) -> list[dict[str, Any]]:
        """Get all positions."""
        return self._load_positions()

    # =========================================================================
    # Cash Management
    # =========================================================================

    def get_cash_balance(self) -> float:
        """Get current cash balance."""
        return self._load_cash()["balance"]

    def set_cash_balance(self, balance: float) -> dict[str, Any]:
        """Set cash balance."""
        cash_data = {"balance": round(balance, 2), "updated_at": datetime.now().isoformat()}
        self._save_cash(cash_data)
        return cash_data

    def adjust_cash(self, amount: float) -> float:
        """Adjust cash balance (positive = deposit, negative = withdrawal)."""
        cash_data = self._load_cash()
        cash_data["balance"] = round(cash_data["balance"] + amount, 2)
        cash_data["updated_at"] = datetime.now().isoformat()
        self._save_cash(cash_data)
        return cash_data["balance"]

    # =========================================================================
    # Portfolio Summary
    # =========================================================================

    def get_portfolio_summary(self, current_prices: dict[str, float]) -> dict[str, Any]:
        """
        Calculate portfolio summary with current market values.

        Args:
            current_prices: Map of symbol -> current price

        Returns:
            Summary with total cost, market value, P&L, etc.
        """
        positions = self._load_positions()
        cash = self.get_cash_balance()

        total_cost = 0.0
        total_market_value = 0.0
        position_details = []

        for pos in positions:
            symbol = pos["symbol"]
            shares = pos["shares"]
            cost_basis = pos["cost_basis"]
            current_price = current_prices.get(symbol) or cost_basis

            cost = cost_basis * shares
            market_value = current_price * shares
            pnl = market_value - cost
            pnl_pct = (pnl / cost * 100) if cost > 0 else 0.0

            total_cost += cost
            total_market_value += market_value

            position_details.append({
                **pos,
                "current_price": round(float(current_price), 2),
                "market_value": round(float(market_value), 2),
                "cost_total": round(float(cost), 2),
                "pnl": round(float(pnl), 2),
                "pnl_percent": round(float(pnl_pct), 2),
            })

        total_pnl = total_market_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

        return {
            "positions": position_details,
            "cash": round(cash, 2),
            "total_cost": round(total_cost, 2),
            "total_market_value": round(total_market_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl_pct, 2),
            "total_equity": round(total_market_value + cash, 2),
            "position_count": len(positions),
        }

    def get_pnl_by_strategy(self, current_prices: dict[str, float]) -> list[dict[str, Any]]:
        """Get P&L breakdown grouped by strategy."""
        positions = self._load_positions()
        strategy_map: dict[str, list[dict]] = {}

        for pos in positions:
            sid = pos.get("strategy_id") or "unassigned"
            if sid not in strategy_map:
                strategy_map[sid] = []
            strategy_map[sid].append(pos)

        results = []
        for strategy_id, group in strategy_map.items():
            total_cost = sum(p["cost_basis"] * p["shares"] for p in group)
            total_market = sum(
                (current_prices.get(p["symbol"]) or p["cost_basis"]) * p["shares"]
                for p in group
            )
            pnl = total_market - total_cost
            pnl_pct = (pnl / total_cost * 100) if total_cost > 0 else 0.0

            results.append({
                "strategy_id": strategy_id,
                "position_count": len(group),
                "total_cost": round(float(total_cost), 2),
                "total_market_value": round(float(total_market), 2),
                "pnl": round(float(pnl), 2),
                "pnl_percent": round(float(pnl_pct), 2),
            })

        # Sort by P&L descending
        results.sort(key=lambda x: x["pnl"], reverse=True)
        return results
