"""
Alert Store - JSON persistence for alert rules and triggered alert history.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class AlertStore:
    """Manages alert rule persistence to JSON files."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.alerts_dir = self.data_dir / "alerts"
        self.rules_file = self.alerts_dir / "rules.json"
        self.history_file = self.alerts_dir / "triggered_history.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create directories if they don't exist."""
        self.alerts_dir.mkdir(parents=True, exist_ok=True)

    def _load_json(self, path: Path) -> Any:
        """Load JSON from file, return empty list if not exists."""
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _save_json(self, path: Path, data: Any) -> None:
        """Save data to JSON file."""
        self._ensure_dirs()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    # ========================================================================
    # Alert Rules CRUD
    # ========================================================================

    def list_rules(self) -> list[dict]:
        """List all alert rules."""
        return self._load_json(self.rules_file)

    def get_rule(self, rule_id: str) -> Optional[dict]:
        """Get alert rule by ID."""
        rules = self.list_rules()
        for rule in rules:
            if rule.get("id") == rule_id:
                return rule
        return None

    def create_rule(self, rule_data: dict) -> dict:
        """Create a new alert rule."""
        rules = self.list_rules()

        rule = {
            "id": str(uuid.uuid4()),
            "symbol": rule_data["symbol"].upper(),
            "condition": rule_data["condition"],
            "threshold": rule_data["threshold"],
            "enabled": rule_data.get("enabled", True),
            "createdAt": datetime.utcnow().isoformat(),
            "triggeredAt": None,
        }

        rules.append(rule)
        self._save_json(self.rules_file, rules)
        return rule

    def update_rule(self, rule_id: str, updates: dict) -> Optional[dict]:
        """Update an existing alert rule."""
        rules = self.list_rules()
        for i, rule in enumerate(rules):
            if rule.get("id") == rule_id:
                # Only update allowed fields
                if "symbol" in updates:
                    rules[i]["symbol"] = updates["symbol"].upper()
                if "condition" in updates:
                    rules[i]["condition"] = updates["condition"]
                if "threshold" in updates:
                    rules[i]["threshold"] = updates["threshold"]
                if "enabled" in updates:
                    rules[i]["enabled"] = updates["enabled"]

                self._save_json(self.rules_file, rules)
                return rules[i]
        return None

    def delete_rule(self, rule_id: str) -> bool:
        """Delete an alert rule."""
        rules = self.list_rules()
        original_len = len(rules)
        rules = [r for r in rules if r.get("id") != rule_id]

        if len(rules) < original_len:
            self._save_json(self.rules_file, rules)
            return True
        return False

    # ========================================================================
    # Triggered Alerts History
    # ========================================================================

    def get_triggered_history(self, limit: int = 50) -> list[dict]:
        """Get triggered alert history, newest first."""
        history = self._load_json(self.history_file)
        # Sort by triggeredAt descending
        history.sort(key=lambda x: x.get("triggeredAt", ""), reverse=True)
        return history[:limit]

    def add_triggered(self, triggered_data: dict) -> dict:
        """Record a triggered alert."""
        history = self._load_json(self.history_file)

        entry = {
            "id": str(uuid.uuid4()),
            "ruleId": triggered_data["ruleId"],
            "symbol": triggered_data["symbol"],
            "condition": triggered_data["condition"],
            "threshold": triggered_data["threshold"],
            "currentValue": triggered_data["currentValue"],
            "message": triggered_data["message"],
            "triggeredAt": datetime.utcnow().isoformat(),
            "read": False,
        }

        history.append(entry)
        # Keep last 200 entries max
        if len(history) > 200:
            history = history[-200:]
        self._save_json(self.history_file, history)
        return entry

    def mark_all_read(self) -> None:
        """Mark all triggered alerts as read."""
        history = self._load_json(self.history_file)
        for entry in history:
            entry["read"] = True
        self._save_json(self.history_file, history)

    def get_unread_count(self) -> int:
        """Get count of unread triggered alerts."""
        history = self._load_json(self.history_file)
        return sum(1 for entry in history if not entry.get("read", False))
