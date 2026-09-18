"""Thin typed adapter around the existing DataEngine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel, Field

from ..schemas import Citation
from .executor import ToolBusinessError, ToolExecutionError
from .registry import ToolSpec, default_registry


class MarketSnapshotInput(BaseModel):
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9.\-]+$")
    years: int = Field(default=1, ge=1, le=10)


class MarketSnapshotOutput(BaseModel):
    symbol: str
    price: float
    timestamp: datetime
    rows: int
    source: str
    start_date: str
    end_date: str
    change_pct: float | None = None
    citations: list[Citation] = Field(default_factory=list)


def get_market_snapshot(payload: MarketSnapshotInput, engine_factory: Callable[[], Any] | None = None) -> MarketSnapshotOutput:
    if engine_factory is None:
        from lobster_quant.src.core.data_engine import get_data_engine

        engine_factory = get_data_engine
    stock = engine_factory().fetch_stock(payload.symbol.upper(), years=payload.years)
    if stock is None or stock.daily is None or stock.daily.empty:
        raise ToolBusinessError(f"No market data available for {payload.symbol.upper()}")
    frame = stock.daily
    close = frame["close"].astype(float)
    previous = float(close.iloc[-2]) if len(close) > 1 else None
    price = float(close.iloc[-1])
    return MarketSnapshotOutput(
        symbol=stock.symbol,
        price=price,
        timestamp=datetime.now(),
        rows=len(frame),
        source=stock.source,
        start_date=frame.index[0].isoformat(),
        end_date=frame.index[-1].isoformat(),
        change_pct=((price - previous) / previous * 100) if previous else None,
        citations=[
            Citation(type="tool_result", ref_id=stock.symbol, label="market snapshot", field_path="price")
        ],
    )


default_registry.register(
    ToolSpec(
        name="get_market_snapshot",
        version="1",
        description="Return a bounded latest market snapshot from the configured data engine.",
        input_model=MarketSnapshotInput,
        output_model=MarketSnapshotOutput,
        handler=get_market_snapshot,
        timeout_seconds=20,
    )
)
