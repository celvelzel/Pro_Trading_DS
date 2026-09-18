"""Thin typed adapter around the existing IndicatorEngine."""

from __future__ import annotations

import math
from typing import Any, Callable

from pydantic import BaseModel, Field

from ..schemas import Citation
from .executor import ToolBusinessError
from .registry import ToolSpec, default_registry


class IndicatorsInput(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    years: int = Field(default=1, ge=1, le=10)


class IndicatorsOutput(BaseModel):
    symbol: str
    timestamp: str
    values: dict[str, float | bool | None]
    citations: list[Citation] = Field(default_factory=list)


def _safe_value(value: Any) -> float | bool | None:
    if isinstance(value, bool):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def calculate_indicators(payload: IndicatorsInput, engine_factory: Callable[[], Any] | None = None) -> IndicatorsOutput:
    if engine_factory is None:
        from lobster_quant.src.core.data_engine import get_data_engine
        from lobster_quant.src.core.indicator_engine import get_indicator_engine

        stock = get_data_engine().fetch_stock(payload.symbol.upper(), years=payload.years)
        indicator_engine = get_indicator_engine()
    else:
        engine = engine_factory()
        stock = engine.fetch_stock(payload.symbol.upper(), years=payload.years)
        indicator_engine = getattr(engine, "indicator_engine", None)
        if indicator_engine is None:
            from lobster_quant.src.core.indicator_engine import get_indicator_engine

            indicator_engine = get_indicator_engine()
    if stock is None or stock.daily is None or stock.daily.empty:
        raise ToolBusinessError(f"No market data available for {payload.symbol.upper()}")
    frame = indicator_engine.compute_all(stock.daily)
    latest = frame.iloc[-1]
    values = {key: _safe_value(value) for key, value in latest.items() if key not in {"open", "high", "low", "close", "volume"}}
    return IndicatorsOutput(
        symbol=stock.symbol,
        timestamp=frame.index[-1].isoformat(),
        values=values,
        citations=[Citation(type="tool_result", ref_id=stock.symbol, label="indicators", field_path="values")],
    )


default_registry.register(
    ToolSpec(
        name="calculate_indicators",
        version="1",
        description="Calculate the existing technical indicators for the latest market row.",
        input_model=IndicatorsInput,
        output_model=IndicatorsOutput,
        handler=calculate_indicators,
        timeout_seconds=30,
    )
)
