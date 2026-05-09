"""
Lobster Quant - Scanner API Models
Pydantic schemas for stock scanning and screening endpoints.
"""

from typing import List, Literal
from pydantic import BaseModel, Field

from .stocks import SignalType


class ScanRequest(BaseModel):
    """Request body for stock scanning."""

    market: Literal["US", "HK", "A"] = Field(
        ..., description="Market to scan: US, HK, or A"
    )
    minScore: int = Field(
        default=60, ge=0, le=100, description="Minimum signal score threshold"
    )


class StockResult(BaseModel):
    """Single stock scan result."""

    symbol: str
    name: str
    price: float = Field(..., ge=0)
    change: float
    changePercent: float
    score: int = Field(..., ge=0, le=100)
    signalType: SignalType
    probability: int = Field(default=50, ge=0, le=100)
    reasons: List[str]


class ScanResponse(BaseModel):
    """Response body for stock scanning."""

    results: List[StockResult]
    total: int = Field(..., ge=0)
    market: str
    minScore: int = Field(..., ge=0, le=100)
