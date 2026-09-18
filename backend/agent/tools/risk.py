"""Thin typed adapter around the existing RiskEngine."""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from ..schemas import Citation
from .executor import ToolBusinessError
from .registry import ToolSpec, default_registry


class RiskInput(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    years: int = Field(default=1, ge=1, le=10)


class RiskOutput(BaseModel):
    symbol: str
    is_off: bool
    reasons: list[str]
    timestamp: str
    citations: list[Citation] = Field(default_factory=list)


def assess_risk(payload: RiskInput, engine_factory: Callable[[], Any] | None = None) -> RiskOutput:
    if engine_factory is None:
        from lobster_quant.src.core.data_engine import get_data_engine
        from lobster_quant.src.core.indicator_engine import get_indicator_engine
        from lobster_quant.src.core.risk_engine import get_risk_engine

        stock = get_data_engine().fetch_stock(payload.symbol.upper(), years=payload.years)
        indicator_engine = get_indicator_engine()
        risk_engine = get_risk_engine()
    else:
        engine = engine_factory()
        stock = engine.fetch_stock(payload.symbol.upper(), years=payload.years)
        indicator_engine = getattr(engine, "indicator_engine", None)
        risk_engine = getattr(engine, "risk_engine", None)
        if indicator_engine is None:
            from lobster_quant.src.core.indicator_engine import get_indicator_engine

            indicator_engine = get_indicator_engine()
        if risk_engine is None:
            from lobster_quant.src.core.risk_engine import get_risk_engine

            risk_engine = get_risk_engine()
    if stock is None or stock.daily is None or stock.daily.empty:
        raise ToolBusinessError(f"No market data available for {payload.symbol.upper()}")
    frame = indicator_engine.compute_all(stock.daily)
    status = risk_engine.get_latest_status(frame)
    return RiskOutput(
        symbol=stock.symbol,
        is_off=status.is_off,
        reasons=status.reasons,
        timestamp=status.timestamp.isoformat(),
        citations=[Citation(type="tool_result", ref_id=stock.symbol, label="risk assessment", field_path="is_off")],
    )


default_registry.register(
    ToolSpec(
        name="assess_risk",
        version="1",
        description="Assess the existing OFF risk filter for a symbol.",
        input_model=RiskInput,
        output_model=RiskOutput,
        handler=assess_risk,
        timeout_seconds=30,
    )
)
