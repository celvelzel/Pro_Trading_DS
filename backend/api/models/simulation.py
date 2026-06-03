"""Simulation API Models."""
from typing import List, Optional
from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    """Run simulation request."""
    strategyId: str
    market: str = Field(default="US", pattern="^(US|HK|A)$")


class RunAllSimulationRequest(BaseModel):
    """Run all strategies simulation."""
    market: str = Field(default="US", pattern="^(US|HK|A)$")


class SimulatedTradeResponse(BaseModel):
    """Simulated trade response."""
    id: str
    strategyId: str
    symbol: str
    entryDate: str
    entryPrice: float
    exitDate: Optional[str] = None
    exitPrice: Optional[float] = None
    shares: int
    status: str
    pnl: Optional[float] = None
    pnlPercent: Optional[float] = None


class DailySnapshotResponse(BaseModel):
    """Daily snapshot response."""
    date: str
    strategyId: str
    selectedStocks: List[dict]
    openTrades: List[dict]
    closedTrades: List[dict]
    portfolioValue: float
    cash: float
    invested: float


class SimulationResultResponse(BaseModel):
    """Simulation result response."""
    timestamp: str
    market: str
    strategyId: Optional[str] = None
    strategyName: Optional[str] = None
    status: str
    snapshot: Optional[DailySnapshotResponse] = None
    error: Optional[str] = None


class PerformanceResponse(BaseModel):
    """Performance metrics response."""
    strategyId: str
    window: str
    totalReturn: float
    volatility: float
    sharpeRatio: float
    maxDrawdown: float
    winRate: float
    totalTrades: int


class AddFromAlertRequest(BaseModel):
    """Request to add a trade from a triggered alert."""
    symbol: str
    alert_id: str
    side: str = Field(default="buy", pattern="^(buy|sell)$")
