"""Portfolio API Models."""
from typing import List, Optional
from pydantic import BaseModel, Field


class PositionResponse(BaseModel):
    """Portfolio position response."""
    id: str
    symbol: str
    shares: int
    cost_basis: float
    opened_at: str
    updated_at: str
    strategy_id: Optional[str] = None
    # Computed fields (populated when prices available)
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None


class AddPositionRequest(BaseModel):
    """Add a new position."""
    symbol: str = Field(..., min_length=1, max_length=20)
    shares: int = Field(..., gt=0)
    cost_basis: float = Field(..., gt=0)
    strategy_id: Optional[str] = None


class UpdatePositionRequest(BaseModel):
    """Update an existing position."""
    shares: Optional[int] = Field(None, gt=0)
    cost_basis: Optional[float] = Field(None, gt=0)
    strategy_id: Optional[str] = None


class CashBalanceResponse(BaseModel):
    """Cash balance response."""
    balance: float
    updated_at: str


class SetCashRequest(BaseModel):
    """Set cash balance."""
    balance: float = Field(..., ge=0)


class AdjustCashRequest(BaseModel):
    """Adjust cash balance."""
    amount: float


class PositionDetailResponse(BaseModel):
    """Position with P&L details."""
    id: str
    symbol: str
    shares: int
    cost_basis: float
    opened_at: str
    updated_at: str
    strategy_id: Optional[str] = None
    current_price: float
    market_value: float
    cost_total: float
    pnl: float
    pnl_percent: float


class PortfolioSummaryResponse(BaseModel):
    """Portfolio summary response."""
    positions: List[PositionDetailResponse]
    cash: float
    total_cost: float
    total_market_value: float
    total_pnl: float
    total_pnl_percent: float
    total_equity: float
    position_count: int


class PnlByStrategyResponse(BaseModel):
    """P&L breakdown by strategy."""
    strategy_id: str
    position_count: int
    total_cost: float
    total_market_value: float
    pnl: float
    pnl_percent: float


class PortfolioPnlResponse(BaseModel):
    """Full P&L response."""
    strategies: List[PnlByStrategyResponse]
    total_pnl: float
    total_pnl_percent: float
