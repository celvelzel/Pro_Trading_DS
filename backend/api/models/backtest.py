"""
Lobster Quant - Backtest API Models
Pydantic schemas for strategy backtesting endpoints.

Aligned with:
  - lobster_quant/src/data/models.py (Trade, BacktestResult)
  - lobster_quant/src/config/settings.py (backtest_* parameters)
  - frontend src/lib/types.ts (BacktestParams, BacktestResult, Trade, EquityPoint)
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    """Request body for running a strategy backtest.

    Parameters mirror the Streamlit backtest page and BacktestEngine config.
    """

    symbol: str = Field(..., min_length=1, description="Stock symbol to backtest")
    holdingDays: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Number of days to hold each position",
    )
    minScore: int = Field(
        default=60,
        ge=0,
        le=100,
        description="Minimum signal score to enter a trade",
    )
    startDate: Optional[str] = Field(
        default=None,
        description="Backtest start date (YYYY-MM-DD). Defaults to lookback window.",
    )
    endDate: Optional[str] = Field(
        default=None,
        description="Backtest end date (YYYY-MM-DD). Defaults to latest data.",
    )
    lookbackDays: Optional[int] = Field(
        default=None,
        ge=100,
        le=2000,
        description="Historical lookback window in days. Overrides startDate/endDate.",
    )
    slippagePct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=0.01,
        description="Slippage percentage per trade (e.g. 0.001 = 0.1%)",
    )
    commissionPct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=0.01,
        description="Commission percentage per trade (e.g. 0.001 = 0.1%)",
    )


class BacktestTrade(BaseModel):
    """Single trade record from a backtest run.

    Field names use camelCase to match the frontend TypeScript interface.
    """

    entryDate: str = Field(..., description="Trade entry date (YYYY-MM-DD)")
    exitDate: str = Field(..., description="Trade exit date (YYYY-MM-DD)")
    entryPrice: float = Field(..., gt=0, description="Entry price")
    exitPrice: float = Field(..., gt=0, description="Exit price")
    returnPercent: float = Field(
        ..., description="Trade return as percentage (e.g. 5.2 = +5.2%)"
    )
    holdingDays: int = Field(..., ge=0, description="Actual holding period in days")


class EquityPoint(BaseModel):
    """Single point on the equity curve."""

    date: str = Field(..., description="Date (YYYY-MM-DD)")
    value: float = Field(..., description="Portfolio value (normalized to 1.0 start)")


class BacktestResponse(BaseModel):
    """Response body for a completed backtest.

    Mirrors the frontend BacktestResult interface and includes all metrics
    computed by BacktestEngine + metrics.py.
    """

    totalTrades: int = Field(..., ge=0, description="Total number of trades executed")
    winRate: float = Field(
        ..., ge=0, le=100, description="Win rate as percentage (e.g. 65.0 = 65%)"
    )
    totalReturn: float = Field(
        ..., description="Cumulative return as percentage (e.g. 12.5 = +12.5%)"
    )
    maxDrawdown: float = Field(
        ..., ge=0, le=100, description="Maximum drawdown as percentage"
    )
    sharpeRatio: float = Field(..., description="Annualized Sharpe ratio")
    trades: List[BacktestTrade] = Field(
        default_factory=list, description="Individual trade records"
    )
    equityCurve: List[EquityPoint] = Field(
        default_factory=list, description="Equity curve data points"
    )


# ============================================================================
# Walk-Forward Validation Models
# ============================================================================


class WalkForwardRequest(BaseModel):
    """Request body for walk-forward validation analysis."""

    symbol: str = Field(..., min_length=1, description="Stock symbol to analyze")
    trainMonths: int = Field(
        default=12, ge=3, le=36,
        description="Training period length in months",
    )
    testMonths: int = Field(
        default=3, ge=1, le=12,
        description="Testing period length in months",
    )
    stepMonths: int = Field(
        default=3, ge=1, le=12,
        description="Months to advance between windows",
    )
    holdingDays: int = Field(
        default=20, ge=5, le=100,
        description="Number of days to hold each position",
    )
    minScore: int = Field(
        default=60, ge=0, le=100,
        description="Minimum signal score to enter a trade",
    )


class WindowMetricsResponse(BaseModel):
    """Metrics for a single period (IS or OOS) within a walk-forward window."""

    totalTrades: int = Field(..., ge=0)
    winRate: float = Field(..., description="Win rate as fraction (0-1)")
    avgReturn: float = Field(..., description="Average trade return as fraction")
    cumulativeReturn: float = Field(..., description="Cumulative return as fraction")
    maxDrawdown: float = Field(..., description="Max drawdown as fraction (0-1)")
    sharpeRatio: float = Field(..., description="Annualized Sharpe ratio")
    sortinoRatio: float = Field(..., description="Annualized Sortino ratio")
    profitFactor: float = Field(..., description="Profit factor")
    bestTrade: float = Field(..., description="Best single trade return")
    worstTrade: float = Field(..., description="Worst single trade return")


class WalkForwardWindowResponse(BaseModel):
    """Results for a single walk-forward window."""

    windowIndex: int = Field(..., ge=0)
    trainStart: str = Field(..., description="Training period start date")
    trainEnd: str = Field(..., description="Training period end date")
    testStart: str = Field(..., description="Testing period start date")
    testEnd: str = Field(..., description="Testing period end date")
    isMetrics: WindowMetricsResponse = Field(..., description="In-sample metrics")
    oosMetrics: WindowMetricsResponse = Field(..., description="Out-of-sample metrics")
    degradation: float = Field(..., description="Sharpe degradation ratio")


class WalkForwardResponse(BaseModel):
    """Response body for walk-forward validation analysis."""

    symbol: str
    trainMonths: int
    testMonths: int
    stepMonths: int
    totalWindows: int = Field(..., ge=0)
    windows: List[WalkForwardWindowResponse] = Field(default_factory=list)
    avgIsSharpe: float = Field(..., description="Average in-sample Sharpe ratio")
    avgOosSharpe: float = Field(..., description="Average out-of-sample Sharpe ratio")
    avgDegradation: float = Field(..., description="Average degradation ratio")
    avgOosWinRate: float = Field(..., description="Average OOS win rate")
    avgOosReturn: float = Field(..., description="Average OOS cumulative return")
    consistencyRatio: float = Field(..., description="Fraction of windows with OOS Sharpe > 0")
