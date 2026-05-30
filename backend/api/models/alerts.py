"""Alert API Models."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


AlertCondition = Literal[
    "score_above",
    "score_below",
    "price_above",
    "price_below",
    "signal_change",
]


class CreateAlertRuleRequest(BaseModel):
    """Create alert rule request."""
    symbol: str = Field(..., min_length=1, max_length=20)
    condition: AlertCondition
    threshold: float = Field(..., ge=0)
    enabled: bool = Field(default=True)


class UpdateAlertRuleRequest(BaseModel):
    """Update alert rule request."""
    symbol: Optional[str] = Field(None, min_length=1, max_length=20)
    condition: Optional[AlertCondition] = None
    threshold: Optional[float] = Field(None, ge=0)
    enabled: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    """Alert rule response."""
    id: str
    symbol: str
    condition: str
    threshold: float
    enabled: bool
    createdAt: str
    triggeredAt: Optional[str] = None


class TriggeredAlertResponse(BaseModel):
    """Triggered alert response."""
    id: str
    ruleId: str
    symbol: str
    condition: str
    threshold: float
    currentValue: float
    message: str
    triggeredAt: str
    read: bool


class AlertRulesListResponse(BaseModel):
    """List of alert rules."""
    rules: List[AlertRuleResponse]


class TriggeredAlertsResponse(BaseModel):
    """Triggered alerts response."""
    alerts: List[TriggeredAlertResponse]
    unreadCount: int


class MarkReadResponse(BaseModel):
    """Mark read response."""
    success: bool
