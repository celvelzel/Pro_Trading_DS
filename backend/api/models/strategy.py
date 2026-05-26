"""Strategy API Models."""
from typing import List, Optional
from pydantic import BaseModel, Field


class StrategyParamsRequest(BaseModel):
    """Strategy parameters request."""
    holdingDays: int = Field(default=20, ge=5, le=100)
    minScore: int = Field(default=60, ge=0, le=100)
    slippagePct: float = Field(default=0.001, ge=0.0, le=0.01)
    commissionPct: float = Field(default=0.001, ge=0.0, le=0.01)
    positionSizing: str = Field(default="fixed", pattern="^(fixed|dynamic)$")
    positionSize: float = Field(default=0.1, ge=0.01, le=1.0)
    initialCapital: float = Field(default=100000, ge=1000)
    maxPositions: int = Field(default=5, ge=1, le=20)


class CreateStrategyRequest(BaseModel):
    """Create strategy request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    params: StrategyParamsRequest


class UpdateStrategyRequest(BaseModel):
    """Update strategy request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    params: Optional[StrategyParamsRequest] = None


class StrategyResponse(BaseModel):
    """Strategy response."""
    id: str
    name: str
    description: str
    params: dict
    logic: str
    isPreset: bool
    createdAt: str
    updatedAt: Optional[str] = None


class CompareStrategiesRequest(BaseModel):
    """Compare strategies request."""
    strategyIds: List[str] = Field(..., min_length=2)
    symbol: str
    startDate: str
    endDate: str


class StrategyComparisonResponse(BaseModel):
    """Strategy comparison response."""
    strategies: List[dict]
    bestReturn: Optional[str] = None
    bestSharpe: Optional[str] = None
    lowestDrawdown: Optional[str] = None
