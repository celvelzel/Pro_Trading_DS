"""
Lobster Quant - Settings API Models
Pydantic schemas for application settings endpoints.

Aligned with:
  - lobster_quant/src/config/settings.py (Settings class)
  - frontend src/lib/types.ts (AppSettings, MarketSettings, etc.)
  - frontend src/stores/settingsStore.ts (SettingsState)
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


# ============================================================================
# Settings Sub-Schemas
# ============================================================================


class MarketSettings(BaseModel):
    """Market enable/disable configuration."""

    enableUS: bool = Field(default=True, description="Enable US stock market")
    enableHK: bool = Field(default=True, description="Enable HK stock market")
    enableA: bool = Field(default=False, description="Enable A-share market")


class DataSettings(BaseModel):
    """Data fetching and caching configuration."""

    dataYears: int = Field(
        default=3, ge=1, le=10, description="Years of historical data to fetch"
    )
    cacheTTL: int = Field(
        default=3600,
        ge=300,
        le=86400,
        description="Cache time-to-live in seconds",
    )


class ScoringWeights(BaseModel):
    """Signal scoring weights (must sum to ~1.0)."""

    trend: float = Field(
        default=0.40, ge=0.0, le=1.0, description="Weight for trend indicators"
    )
    momentum: float = Field(
        default=0.20, ge=0.0, le=1.0, description="Weight for momentum indicators"
    )
    volume: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Weight for volume indicators"
    )
    pattern: float = Field(
        default=0.25, ge=0.0, le=1.0, description="Weight for pattern indicators"
    )

    @model_validator(mode="after")
    def validate_weight_sum(self) -> "ScoringWeights":
        """Warn if weights don't sum to ~1.0 (soft validation)."""
        total = self.trend + self.momentum + self.volume + self.pattern
        if abs(total - 1.0) > 0.05:
            import warnings

            warnings.warn(
                f"Scoring weights sum to {total:.2f}, expected ~1.0",
                UserWarning,
                stacklevel=2,
            )
        return self


class BacktestSettings(BaseModel):
    """Backtest engine parameters."""

    holdingDays: int = Field(
        default=20, ge=5, le=100, description="Default holding period in days"
    )
    minScore: int = Field(
        default=20, ge=0, le=100, description="Minimum score to enter a trade"
    )
    lookbackDays: int = Field(
        default=500, ge=100, le=2000, description="Historical lookback window"
    )
    slippagePct: float = Field(
        default=0.001, ge=0.0, le=0.01, description="Slippage per trade"
    )
    commissionPct: float = Field(
        default=0.001, ge=0.0, le=0.01, description="Commission per trade"
    )


class OFFFilterSettings(BaseModel):
    """OFF (risk-off) filter parameters."""

    vixThreshold: float = Field(
        default=35.0, ge=10.0, le=100.0, description="VIX threshold for OFF signal"
    )
    atrPctThreshold: float = Field(
        default=0.05, ge=0.01, le=0.20, description="ATR percentage threshold"
    )
    gapThreshold: float = Field(
        default=0.08, ge=0.01, le=0.30, description="Gap percentage threshold"
    )
    minVolumeRatio: float = Field(
        default=0.05, ge=0.0, le=1.0, description="Minimum volume ratio"
    )
    ma200RecoveryDays: int = Field(
        default=60, ge=10, le=200, description="MA200 recovery lookback days"
    )


class IndicatorSettings(BaseModel):
    """Technical indicator parameters."""

    maShortPeriod: int = Field(default=20, ge=5, le=100)
    maLongPeriod: int = Field(default=200, ge=50, le=500)
    rsiPeriod: int = Field(default=14, ge=5, le=50)
    atrPeriod: int = Field(default=14, ge=5, le=50)
    macdFast: int = Field(default=12, ge=5, le=50)
    macdSlow: int = Field(default=26, ge=10, le=100)
    macdSignal: int = Field(default=9, ge=5, le=50)
    bbPeriod: int = Field(default=20, ge=5, le=100)
    bbStd: float = Field(default=2.0, ge=1.0, le=4.0)


# ============================================================================
# Composite Settings
# ============================================================================


class AppSettings(BaseModel):
    """Complete application settings.

    Groups all configuration into logical sections matching the frontend
    AppSettings interface and the Streamlit settings page layout.
    """

    markets: MarketSettings = Field(default_factory=MarketSettings)
    data: DataSettings = Field(default_factory=DataSettings)
    scoring: ScoringWeights = Field(default_factory=ScoringWeights)
    backtest: BacktestSettings = Field(default_factory=BacktestSettings)
    offFilter: OFFFilterSettings = Field(default_factory=OFFFilterSettings)
    indicators: IndicatorSettings = Field(default_factory=IndicatorSettings)
    benchmarkSymbol: str = Field(
        default="SPY", description="Benchmark symbol for market comparison"
    )


# ============================================================================
# Request / Response
# ============================================================================


class SettingsUpdateRequest(BaseModel):
    """Partial settings update request.

    All fields are optional — only provided fields will be updated.
    Nested objects are merged, not replaced.
    """

    markets: Optional[MarketSettings] = None
    data: Optional[DataSettings] = None
    scoring: Optional[ScoringWeights] = None
    backtest: Optional[BacktestSettings] = None
    offFilter: Optional[OFFFilterSettings] = None
    indicators: Optional[IndicatorSettings] = None
    benchmarkSymbol: Optional[str] = None


class SettingsResponse(BaseModel):
    """Response body for settings endpoints."""

    settings: AppSettings
    success: bool = True
    message: Optional[str] = None
