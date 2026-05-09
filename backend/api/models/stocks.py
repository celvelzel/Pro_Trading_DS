"""
Lobster Quant - Stock API Models
Pydantic schemas for stock data, indicators, signals, options, and risk endpoints.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


# ============================================================================
# OHLCV / Price Data
# ============================================================================


class Candle(BaseModel):
    """Single OHLCV candlestick."""

    time: int = Field(..., description="Unix timestamp in seconds")
    open: float = Field(..., ge=0)
    high: float = Field(..., ge=0)
    low: float = Field(..., ge=0)
    close: float = Field(..., ge=0)
    volume: float = Field(..., ge=0)


class StockData(BaseModel):
    """Complete stock data with price summary and candle history."""

    symbol: str
    name: str
    price: float = Field(..., ge=0)
    change: float
    changePercent: float
    volume: int = Field(..., ge=0)
    candles: List[Candle]


# ============================================================================
# Technical Indicators
# ============================================================================


class MACDData(BaseModel):
    """MACD indicator values."""

    value: float
    signal: float
    histogram: float


class Indicators(BaseModel):
    """Technical indicator snapshot for a stock."""

    rsi: float = Field(..., ge=0, le=100)
    macd: MACDData
    ma20: float
    ma200: float
    atr: float = Field(..., ge=0)
    atrPercent: float = Field(..., ge=0)


# ============================================================================
# Trading Signals
# ============================================================================

SignalType = Literal["bullish", "bearish", "neutral"]


class Signal(BaseModel):
    """Trading signal with score and reasoning."""

    type: SignalType
    score: int = Field(..., ge=0, le=100)
    probability: int = Field(..., ge=0, le=100)
    reasons: List[str]


# ============================================================================
# Options Analysis
# ============================================================================


class OptionsAnalysis(BaseModel):
    """Options chain analysis summary."""

    maxPain: float
    putCallRatio: float
    support: List[float]
    resistance: List[float]


# ============================================================================
# Risk Assessment
# ============================================================================

RiskStatus = Literal["on", "off"]


class RiskAssessment(BaseModel):
    """Market risk filter status."""

    status: RiskStatus
    statusText: str
    reasons: List[str]
    onPercent: float = Field(..., ge=0, le=100)
    offPercent: float = Field(..., ge=0, le=100)
