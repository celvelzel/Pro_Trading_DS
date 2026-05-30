"""
Signal History Store - JSON persistence for trading signal snapshots.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class SignalHistoryStore:
    """Manages signal history persistence to JSON files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.history_dir = self.data_dir / "signal_history"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create directories if they don't exist."""
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def _get_history_file(self, symbol: str) -> Path:
        """Get the history file path for a symbol."""
        return self.history_dir / f"{symbol}.json"

    def _load_history(self, symbol: str) -> list[dict[str, Any]]:
        """Load signal history for a symbol from JSON file."""
        file_path = self._get_history_file(symbol)
        if not file_path.exists():
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, IOError):
            return []

    def _save_history(self, symbol: str, history: list[dict[str, Any]]) -> None:
        """Save signal history for a symbol to JSON file."""
        self._ensure_dirs()
        file_path = self._get_history_file(symbol)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def get_history(self, symbol: str, days: int = 30) -> list[dict[str, Any]]:
        """Get signal history for a symbol within the specified number of days.

        Args:
            symbol: Stock symbol (e.g., AAPL, MSFT)
            days: Number of days of history to return

        Returns:
            List of signal history entries, newest first
        """
        history = self._load_history(symbol)
        if not history:
            return []

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        filtered = [entry for entry in history if entry.get("date", "") >= cutoff]

        # Sort by date descending (newest first)
        filtered.sort(key=lambda x: x.get("date", ""), reverse=True)
        return filtered

    def save_snapshot(self, symbol: str, score: int, signal_type: str, reasons: list[str]) -> None:
        """Save a signal snapshot for today.

        If an entry for today already exists, it will be updated.

        Args:
            symbol: Stock symbol
            score: Signal score (0-100)
            signal_type: Signal type (bullish, bearish, neutral)
            reasons: List of signal reasons
        """
        today = datetime.now().strftime("%Y-%m-%d")
        history = self._load_history(symbol)

        # Remove existing entry for today if present
        history = [entry for entry in history if entry.get("date") != today]

        # Add new entry
        entry = {
            "date": today,
            "score": score,
            "signalType": signal_type,
            "reasons": reasons,
        }
        history.append(entry)

        # Sort by date ascending for storage
        history.sort(key=lambda x: x.get("date", ""))

        self._save_history(symbol, history)

    def get_all_symbols(self) -> list[str]:
        """Get all symbols that have signal history.

        Returns:
            List of symbols with history files
        """
        if not self.history_dir.exists():
            return []

        return [f.stem for f in self.history_dir.glob("*.json")]

    def get_recent_changes(self, hours: int = 24) -> list[dict[str, Any]]:
        """Get symbols with signal changes in the last N hours.

        Compares today's snapshot with the most recent previous snapshot
        to detect signal type or significant score changes.

        Args:
            hours: Number of hours to look back (default 24)

        Returns:
            List of change records with symbol, previous/current signal info
        """
        cutoff = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d")
        changes = []

        for symbol in self.get_all_symbols():
            history = self._load_history(symbol)
            if len(history) < 2:
                continue

            # Sort by date descending
            history.sort(key=lambda x: x.get("date", ""), reverse=True)

            latest = history[0]
            previous = history[1]

            # Check if the latest entry is within the time window
            if latest.get("date", "") < cutoff:
                continue

            # Detect signal type change or significant score change (>10 points)
            type_changed = latest.get("signalType") != previous.get("signalType")
            score_diff = abs(latest.get("score", 0) - previous.get("score", 0))
            score_changed = score_diff > 10

            if type_changed or score_changed:
                changes.append({
                    "symbol": symbol,
                    "previousDate": previous.get("date"),
                    "previousScore": previous.get("score"),
                    "previousSignalType": previous.get("signalType"),
                    "currentDate": latest.get("date"),
                    "currentScore": latest.get("score"),
                    "currentSignalType": latest.get("signalType"),
                    "scoreChange": latest.get("score", 0) - previous.get("score", 0),
                    "reason": "signal_type_change" if type_changed else "significant_score_change",
                })

        return changes
