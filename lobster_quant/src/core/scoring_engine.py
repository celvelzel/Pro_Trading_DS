"""
Lobster Quant - Scoring Engine
Multi-factor scoring from technical indicators, ported from legacy scoring.py.
"""

from typing import Optional
import pandas as pd
import numpy as np

from ..config.settings import get_settings
from ..utils.logging import get_logger
from ..utils.exceptions import ScoringError

logger = get_logger()


class ScoringEngine:
    """Multi-factor scoring engine (0-100 scale).

    Computes a composite score from four weighted factors:
    - Trend (40%): Daily/weekly/monthly MA slope strength
    - Momentum (20%): RSI + 20-day return percentile
    - Volume (15%): Volume ratio confirmation
    - Pattern (25%): MACD golden cross, MA alignment, Bollinger position
    """

    def __init__(self):
        self.settings = get_settings()
        self.weights = self.settings.scoring_weights

    def compute_score(
        self,
        df: pd.DataFrame,
        slope_wm: Optional[pd.DataFrame] = None,
    ) -> pd.Series:
        """Compute rolling composite score (0-100) for all rows.

        Args:
            df: DataFrame with computed technical indicators.
                Required columns: close, rsi, volume_ratio, macd_golden,
                ma_bullish, bb_position, slope_daily.
            slope_wm: Optional DataFrame with slope_weekly and slope_monthly,
                same index as df.

        Returns:
            Series of scores (0-100) aligned to df index.

        Raises:
            ScoringError: If required columns are missing.
        """
        df = df.copy()
        if slope_wm is not None:
            df["slope_weekly"] = slope_wm["slope_weekly"]
            df["slope_monthly"] = slope_wm["slope_monthly"]

        required = ["close", "rsi", "volume_ratio", "slope_daily"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ScoringError(
                f"Missing required columns for scoring: {missing}"
            )

        # 1. Trend strength (40%) — daily/weekly/monthly slope composite
        df["trend_score"] = self._calc_trend_score(df)

        # 2. Momentum signals (20%)
        df["momentum_score"] = self._calc_momentum_score(df)

        # 3. Volume confirmation (15%)
        df["volume_score"] = self._calc_volume_score(df)

        # 4. Technical patterns (25%)
        df["pattern_score"] = self._calc_pattern_score(df)

        # Weighted total
        total = (
            df["trend_score"] * self.weights["trend"]
            + df["momentum_score"] * self.weights["momentum"]
            + df["volume_score"] * self.weights["volume"]
            + df["pattern_score"] * self.weights["pattern"]
        )

        return total.clip(0, 100)

    # ── Private helpers ──────────────────────────────────────────

    def _calc_trend_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate trend strength score (0-40 range before weighting).

        Normalizes MA slopes via percentile rank over the last 500 observations.
        """
        scores: dict[str, pd.Series] = {}

        for col in ["slope_daily", "slope_weekly", "slope_monthly"]:
            if col in df.columns:
                recent = df[col].dropna().iloc[-500:]
                if len(recent) > 0:
                    pct = df[col].rank(pct=True)
                    scores[f"{col}_score"] = pct.fillna(0.5) * 40
                else:
                    scores[f"{col}_score"] = pd.Series(20, index=df.index)

        # Average of available slope scores
        available = [k for k in ["slope_daily_score", "slope_weekly_score", "slope_monthly_score"]
                     if k in scores]
        if available:
            result = sum(scores[k] for k in available) / len(available)
        else:
            result = pd.Series(20, index=df.index)

        return result

    def _calc_momentum_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate momentum score (0-40 range before weighting).

        Combines RSI mapping and 20-day return percentile.
        """

        def _rsi_to_score(rsi: float) -> float:
            if pd.isna(rsi):
                return 10.0
            if rsi < 30:
                return 20.0
            if rsi < 50:
                return 10.0 + (rsi - 30) * 0.5
            if rsi < 70:
                return 20.0 - (rsi - 50) * 0.5
            return max(0.0, 20.0 - (rsi - 70))

        rsi_score = df["rsi"].apply(_rsi_to_score)

        # 20-day return percentile
        df_copy = df.copy()
        df_copy["ret_20d"] = df["close"].pct_change(20)
        ret_recent = df_copy["ret_20d"].dropna().iloc[-500:]
        if len(ret_recent) > 0:
            ret_pct = ret_recent.rank(pct=True)
            ret_score = ret_pct.reindex(df.index, method="ffill").fillna(0.5) * 20
        else:
            ret_score = pd.Series(10.0, index=df.index)

        return rsi_score + ret_score

    def _calc_volume_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate volume score (0-15 range before weighting)."""

        def _vol_to_score(vr: float) -> float:
            if pd.isna(vr):
                return 7.5
            if vr > 1.5:
                return 15.0
            if vr < 0.8:
                return 5.0
            return 7.5 + (vr - 0.8) * 10.7

        vr = df.get("volume_ratio")
        if vr is None or not isinstance(vr, pd.Series):
            vr = pd.Series(0.0, index=df.index)
        return vr.apply(_vol_to_score)  # type: ignore[return-value]

    def _calc_pattern_score(self, df: pd.DataFrame) -> pd.Series:
        """Calculate pattern score (0-25 range before weighting).

        Components:
        - MACD golden cross: +10
        - MA bullish alignment (MA20 > MA50 > MA200): +10
        - Price above Bollinger mid-band: +5
        """
        score = pd.Series(0.0, index=df.index)

        # MACD golden cross (use shifted signal to avoid lookahead)
        if "macd_golden" in df.columns:
            score += df["macd_golden"].shift(1).fillna(False).astype(int) * 10

        # MA bullish alignment
        if "ma_bullish" in df.columns:
            score += df["ma_bullish"].fillna(False).astype(int) * 10

        # Bollinger position (above midline)
        if "bb_position" in df.columns:
            score += (df["bb_position"] > 0.5).fillna(False).astype(int) * 5

        return score


# Global singleton
_scoring_engine: Optional[ScoringEngine] = None


def get_scoring_engine() -> ScoringEngine:
    """Get global ScoringEngine singleton."""
    global _scoring_engine
    if _scoring_engine is None:
        _scoring_engine = ScoringEngine()
    return _scoring_engine