"""
Lobster Quant - Signal Tracker
Records trading signals and calculates win rates based on actual price movement.

Win rate = % of signals where price moved in the predicted direction after N days.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from ..utils.logging import get_logger

logger = get_logger()


@dataclass
class TrackedSignal:
    """A recorded signal with entry price and outcome tracking."""

    id: str
    symbol: str
    signal_type: str  # 强烈推荐, 推荐, 持有, 观望
    score: float
    probability_up: float
    entry_price: float
    entry_date: str  # ISO format
    strategy_id: Optional[str] = None

    # Outcome fields (filled after evaluation window)
    price_5d: Optional[float] = None
    price_10d: Optional[float] = None
    price_20d: Optional[float] = None
    return_5d: Optional[float] = None
    return_10d: Optional[float] = None
    return_20d: Optional[float] = None
    is_win_5d: Optional[bool] = None
    is_win_10d: Optional[bool] = None
    is_win_20d: Optional[bool] = None

    @property
    def is_bullish(self) -> bool:
        return self.signal_type in ("强烈推荐", "推荐")

    @property
    def is_bearish(self) -> bool:
        return self.signal_type in ("观望",)

    @property
    def expected_direction(self) -> int:
        """Expected price direction: 1=up, -1=down, 0=neutral."""
        if self.signal_type == "强烈推荐":
            return 1
        elif self.signal_type == "推荐":
            return 1
        elif self.signal_type == "观望":
            return -1
        return 0  # 持有


class SignalTracker:
    """Records signals and evaluates win rates after N days.

    Storage: JSON files per signal in data/signal_records/
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.records_dir = self.data_dir / "signal_records"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.records_dir.mkdir(parents=True, exist_ok=True)

    def record_signal(
        self,
        symbol: str,
        signal_type: str,
        score: float,
        probability_up: float,
        entry_price: float,
        strategy_id: Optional[str] = None,
    ) -> str:
        """Record a new signal. Returns signal ID."""
        self._ensure_dirs()

        signal_id = f"sig_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{symbol}"
        signal = TrackedSignal(
            id=signal_id,
            symbol=symbol,
            signal_type=signal_type,
            score=score,
            probability_up=probability_up,
            entry_price=entry_price,
            entry_date=datetime.now().isoformat(),
            strategy_id=strategy_id,
        )

        file_path = self.records_dir / f"{signal_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(signal), f, indent=2, ensure_ascii=False)

        logger.info(f"Recorded signal: {signal_id} | {symbol} | {signal_type} @ {entry_price}")
        return signal_id

    def update_outcome(
        self,
        signal_id: str,
        current_prices: dict[str, float],
    ) -> Optional[TrackedSignal]:
        """Update signal with actual prices at 5d/10d/20d marks.

        Args:
            signal_id: Signal ID to update
            current_prices: {"5d": price, "10d": price, "20d": price}

        Returns:
            Updated TrackedSignal or None if not found
        """
        file_path = self.records_dir / f"{signal_id}.json"
        if not file_path.exists():
            logger.warning(f"Signal not found: {signal_id}")
            return None

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        signal = TrackedSignal(**data)
        entry_price = signal.entry_price

        for period, price in current_prices.items():
            if price is None or price <= 0:
                continue

            attr_price = f"price_{period}"
            attr_return = f"return_{period}"
            attr_win = f"is_win_{period}"

            if hasattr(signal, attr_price):
                setattr(signal, attr_price, price)
                ret = (price - entry_price) / entry_price
                setattr(signal, attr_return, round(ret, 6))

                # Win = price moved in expected direction
                direction = signal.expected_direction
                if direction == 1:
                    setattr(signal, attr_win, ret > 0)
                elif direction == -1:
                    setattr(signal, attr_win, ret < 0)
                else:
                    setattr(signal, attr_win, None)

        # Save updated signal
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(signal), f, indent=2, ensure_ascii=False)

        return signal

    def get_signals(
        self,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None,
        lookback_days: Optional[int] = None,
        signal_type: Optional[str] = None,
    ) -> list[TrackedSignal]:
        """Get tracked signals with optional filters."""
        signals = []

        cutoff = None
        if lookback_days:
            cutoff = datetime.now() - timedelta(days=lookback_days)

        for file in self.records_dir.glob("sig_*.json"):
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)
                signal = TrackedSignal(**data)

                # Apply filters
                if symbol and signal.symbol != symbol:
                    continue
                if strategy_id and signal.strategy_id != strategy_id:
                    continue
                if signal_type and signal.signal_type != signal_type:
                    continue
                if cutoff:
                    entry_dt = datetime.fromisoformat(signal.entry_date)
                    if entry_dt < cutoff:
                        continue

                signals.append(signal)
            except Exception:
                continue

        # Sort by entry date descending
        signals.sort(key=lambda s: s.entry_date, reverse=True)
        return signals

    def get_win_rate_stats(
        self,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None,
        lookback_days: int = 30,
    ) -> dict[str, Any]:
        """Calculate win rate statistics.

        Returns:
            {
                "total_signals": int,
                "evaluated_5d": int,
                "evaluated_10d": int,
                "evaluated_20d": int,
                "win_rate_5d": float,  # 0-100
                "win_rate_10d": float,
                "win_rate_20d": float,
                "avg_return_5d": float,  # percentage
                "avg_return_10d": float,
                "avg_return_20d": float,
                "by_signal_type": {
                    "强烈推荐": {"count": int, "win_rate_5d": float, ...},
                    ...
                }
            }
        """
        signals = self.get_signals(
            symbol=symbol,
            strategy_id=strategy_id,
            lookback_days=lookback_days,
        )

        total = len(signals)
        if total == 0:
            return {
                "total_signals": 0,
                "lookback_days": lookback_days,
                "evaluated_5d": 0,
                "evaluated_10d": 0,
                "evaluated_20d": 0,
                "win_rate_5d": 0.0,
                "win_rate_10d": 0.0,
                "win_rate_20d": 0.0,
                "avg_return_5d": 0.0,
                "avg_return_10d": 0.0,
                "avg_return_20d": 0.0,
                "by_signal_type": {},
            }

        # Aggregate stats
        stats: dict[str, Any] = {
            "total_signals": total,
            "lookback_days": lookback_days,
        }

        for period in ("5d", "10d", "20d"):
            win_attr = f"is_win_{period}"
            ret_attr = f"return_{period}"

            evaluated = [s for s in signals if getattr(s, win_attr) is not None]
            wins = [s for s in evaluated if getattr(s, win_attr) is True]
            returns = [getattr(s, ret_attr) for s in evaluated if getattr(s, ret_attr) is not None]

            stats[f"evaluated_{period}"] = len(evaluated)
            stats[f"win_rate_{period}"] = (
                round(len(wins) / len(evaluated) * 100, 1) if evaluated else 0.0
            )
            stats[f"avg_return_{period}"] = (
                round(sum(returns) / len(returns) * 100, 2) if returns else 0.0
            )

        # Breakdown by signal type
        by_type: dict[str, dict] = {}
        for sig_type in ("强烈推荐", "推荐", "持有", "观望"):
            type_signals = [s for s in signals if s.signal_type == sig_type]
            if not type_signals:
                continue

            type_stats: dict[str, Any] = {"count": len(type_signals)}
            for period in ("5d", "10d", "20d"):
                win_attr = f"is_win_{period}"
                ret_attr = f"return_{period}"

                evaluated = [s for s in type_signals if getattr(s, win_attr) is not None]
                wins = [s for s in evaluated if getattr(s, win_attr) is True]
                returns = [
                    getattr(s, ret_attr)
                    for s in evaluated
                    if getattr(s, ret_attr) is not None
                ]

                type_stats[f"win_rate_{period}"] = (
                    round(len(wins) / len(evaluated) * 100, 1) if evaluated else 0.0
                )
                type_stats[f"avg_return_{period}"] = (
                    round(sum(returns) / len(returns) * 100, 2) if returns else 0.0
                )

            by_type[sig_type] = type_stats

        stats["by_signal_type"] = by_type
        return stats


# Global singleton
_signal_tracker: SignalTracker | None = None


def get_signal_tracker() -> SignalTracker:
    """Get global SignalTracker singleton."""
    global _signal_tracker
    if _signal_tracker is None:
        _signal_tracker = SignalTracker()
    return _signal_tracker
