"""
Lobster Quant - Data Models
Standardized data structures using Pydantic v2.
"""

from datetime import datetime
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, ConfigDict
import pandas as pd
import numpy as np


class OHLCV(BaseModel):
    """Single candlestick data point."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    timestamp: datetime
    open: float = Field(..., ge=0)
    high: float = Field(..., ge=0)
    low: float = Field(..., ge=0)
    close: float = Field(..., ge=0)
    volume: float = Field(..., ge=0)
    
    @property
    def range(self) -> float:
        return self.high - self.low
    
    @property
    def body(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def is_bullish(self) -> bool:
        return self.close >= self.open


class StockData(BaseModel):
    """Complete stock data container with daily/weekly/monthly timeframes."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    symbol: str
    daily: pd.DataFrame
    weekly: Optional[pd.DataFrame] = None
    monthly: Optional[pd.DataFrame] = None
    last_update: datetime = Field(default_factory=datetime.now)
    source: str = "unknown"
    
    def get_latest_price(self) -> Optional[float]:
        """Get the most recent closing price."""
        if self.daily is not None and not self.daily.empty:
            return float(self.daily['close'].iloc[-1])
        return None
    
    def get_latest_date(self) -> Optional[datetime]:
        """Get the most recent data date."""
        if self.daily is not None and not self.daily.empty:
            idx = self.daily.index[-1]
            return idx if isinstance(idx, datetime) else pd.to_datetime(idx)
        return None


class IndicatorValue(BaseModel):
    """Single indicator value at a point in time."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    name: str
    value: Any
    timestamp: datetime
    
    def as_float(self) -> Optional[float]:
        """Safely convert value to float."""
        try:
            return float(self.value)
        except (TypeError, ValueError):
            return None


class SignalResult(BaseModel):
    """Trading signal result."""
    symbol: str
    signal_type: Literal["强烈推荐", "推荐", "持有", "观望", "sell", "neutral"] = "观望"
    score: float = Field(..., ge=0, le=100)
    probability_up: float = Field(default=50.0, ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @property
    def is_bullish(self) -> bool:
        return self.signal_type in ["强烈推荐", "推荐"]
    
    @property
    def is_bearish(self) -> bool:
        return self.signal_type in ["sell"]
    
    @property
    def strength(self) -> str:
        """Signal strength description."""
        if self.score >= 80:
            return "强"
        elif self.score >= 60:
            return "中"
        elif self.score >= 40:
            return "弱"
        return "无"


class OFFStatus(BaseModel):
    """OFF filter status for a single day."""
    timestamp: datetime
    is_off: bool
    reasons: list[str] = Field(default_factory=list)
    
    @property
    def is_on(self) -> bool:
        return not self.is_off
    
    @property
    def status_text(self) -> str:
        return "OFF" if self.is_off else "ON"
    
    @property
    def status_emoji(self) -> str:
        return "❌" if self.is_off else "✅"


class Trade(BaseModel):
    """Single backtest trade record."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    symbol: str
    buy_date: datetime
    buy_price: float = Field(..., gt=0)
    sell_date: Optional[datetime] = None
    sell_price: Optional[float] = None
    return_pct: Optional[float] = None
    holding_days: int = 0
    
    @property
    def is_closed(self) -> bool:
        return self.sell_date is not None and self.sell_price is not None
    
    @property
    def pnl(self) -> Optional[float]:
        if not self.is_closed:
            return None
        return (self.sell_price - self.buy_price) / self.buy_price


class BacktestResult(BaseModel):
    """Complete backtest result summary."""
    symbol: str
    trades: list[Trade] = Field(default_factory=list)
    @property
    def total_trades(self) -> int:
        return len(self.trades)
    win_rate: float = 0.0
    avg_return: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    cumulative_return: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    sharpe_ratio: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    @property
    def winning_trades(self) -> int:
        return sum(1 for t in self.trades if t.pnl is not None and t.pnl > 0)
    
    @property
    def losing_trades(self) -> int:
        return sum(1 for t in self.trades if t.pnl is not None and t.pnl <= 0)
    
    @property
    def equity_curve(self) -> list[float]:
        """Generate equity curve from trades."""
        curve = [1.0]
        for trade in self.trades:
            if trade.pnl is not None:
                curve.append(curve[-1] * (1 + trade.pnl))
        return curve


class MarketSnapshot(BaseModel):
    """Single stock snapshot for scanner display."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    code: str
    price: float
    score: float = 0.0
    slope_daily: Optional[float] = None
    slope_weekly: Optional[float] = None
    slope_monthly: Optional[float] = None
    rsi: Optional[float] = None
    volume_ratio: Optional[float] = None
    tags: list[str] = Field(default_factory=list)
    signal: Optional[str] = None
    market: Literal["us_stock", "hk_stock", "a_stock"] = "us_stock"
    
    @property
    def trend_direction(self) -> str:
        """Overall trend direction based on slopes."""
        slopes = [s for s in [self.slope_daily, self.slope_weekly, self.slope_monthly] if s is not None]
        if not slopes:
            return "unknown"
        avg = sum(slopes) / len(slopes)
        if avg > 0.02:
            return "strong_up"
        elif avg > 0:
            return "up"
        elif avg > -0.02:
            return "down"
        return "strong_down"


class OptionsData(BaseModel):
    """Options chain data."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    symbol: str
    expiration: str
    calls: list[dict] = Field(default_factory=list)
    puts: list[dict] = Field(default_factory=list)
    current_price: Optional[float] = None
    
    @property
    def put_call_ratio(self) -> Optional[float]:
        """Calculate put/call ratio by volume."""
        call_vol = sum(c.get("volume", 0) or 0 for c in self.calls)
        put_vol = sum(p.get("volume", 0) or 0 for p in self.puts)
        if call_vol == 0:
            return None
        return put_vol / call_vol
    
    @property
    def max_pain_strike(self) -> Optional[float]:
        """Calculate max pain strike."""
        if not self.calls or not self.puts or self.current_price is None:
            return None
        
        all_strikes = set()
        for c in self.calls:
            if "strike" in c and c.get("openInterest", 0) > 0:
                all_strikes.add(c["strike"])
        for p in self.puts:
            if "strike" in p and p.get("openInterest", 0) > 0:
                all_strikes.add(p["strike"])
        
        if not all_strikes:
            return None
        
        min_loss = float("inf")
        max_pain = None
        
        for strike in all_strikes:
            put_loss = sum(
                max(0, p.get("strike", 0) - self.current_price) * (p.get("openInterest", 0) or 0)
                for p in self.puts
            )
            call_loss = sum(
                max(0, self.current_price - c.get("strike", 0)) * (c.get("openInterest", 0) or 0)
                for c in self.calls
            )
            total_loss = put_loss + call_loss
            if total_loss < min_loss:
                min_loss = total_loss
                max_pain = strike
        
        return max_pain


class HealthStatus(BaseModel):
    """System health check result."""
    status: Literal["healthy", "degraded", "unhealthy"] = "healthy"
    checks: dict[str, bool] = Field(default_factory=dict)
    latency_ms: dict[str, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    
    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"
