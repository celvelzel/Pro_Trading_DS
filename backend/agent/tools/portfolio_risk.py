"""Typed portfolio risk tool with explicit point-in-time historical prices."""
from __future__ import annotations
from datetime import date
from typing import Literal
from pydantic import Field, model_validator, model_serializer
from lobster_quant.src.core.portfolio_risk import PortfolioRiskAnalyzer
from .portfolio_snapshot import (StrictModel, UTCDateTime, Symbol, Currency, PositiveAmount,
                                 Amount, SnapshotOutput, NonBlank, SymbolMap)
from .registry import ToolSpec


class HistoryBar(StrictModel):
    date: date
    price: PositiveAmount
    close_at: UTCDateTime
    available_at: UTCDateTime

    @model_validator(mode="after")
    def chronology(self):
        if self.close_at.date() != self.date or self.available_at < self.close_at:
            raise ValueError("Bar date must be UTC close date and availability cannot precede close")
        return self


class AssetHistory(StrictModel):
    symbol: Symbol
    currency: Currency
    source: NonBlank
    adjustment: Literal["total_return", "adjusted"]
    exchange_timezone: NonBlank
    bars: tuple[HistoryBar, ...] = Field(max_length=10000)

    @model_validator(mode="after")
    def unique(self):
        if len({bar.date for bar in self.bars}) != len(self.bars):
            raise ValueError("Duplicate history date")
        return self


class RiskInput(StrictModel):
    snapshot: SnapshotOutput
    as_of: UTCDateTime
    histories: tuple[AssetHistory, ...] = Field(default=(), max_length=32)
    max_history_age_seconds: int = Field(default=604800, ge=0, le=31536000)
    periods_per_year: int = Field(default=252, ge=1, le=366)
    max_quote_age_seconds: int | None = Field(default=None, ge=0, le=604800)

    @model_serializer(mode='wrap')
    def preserve_legacy_input(self, handler):
        data = handler(self)
        if self.max_quote_age_seconds is None:
            data.pop('max_quote_age_seconds', None)
        return data


class RiskOutput(StrictModel):
    status: Literal["ok", "insufficient_data"]
    snapshot_id: str | None = None
    content_hash: str | None = None
    weights: SymbolMap[Amount] = Field(default_factory=dict)
    total_value: Amount | None = None
    concentration: Amount | None = None
    cash_weight: Amount | None = None
    annualized_volatility: float | None = None
    max_drawdown: float | None = None
    correlations: dict[str, float | None] = Field(default_factory=dict)
    dates: tuple[date, ...] = ()
    observations: int = 0
    warnings: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    history_sources: tuple[str, ...] = ()
    method: Literal["constant_current_weights_sample_volatility"] = "constant_current_weights_sample_volatility"


def checked_histories(histories, as_of, currency, symbols):
    mapping = {}
    conventions = set()
    for history in histories:
        if history.symbol in mapping:
            raise ValueError("duplicate_history_symbol")
        if history.currency != currency:
            raise ValueError("mixed_history_currencies")
        conventions.add(history.adjustment)
        # Refuse future bars, instead of accidentally relying on a provider's filtering.
        if any(b.close_at > as_of or b.available_at > as_of for b in history.bars):
            raise ValueError("future_history_bar")
        mapping[history.symbol] = {b.date:b.price for b in history.bars}
    if len(conventions) > 1:
        raise ValueError("mixed_adjustment_conventions")
    if not set(symbols).issubset(mapping):
        raise ValueError("missing_asset_history")
    return mapping


def calculate_portfolio_risk(payload: RiskInput) -> RiskOutput:
    snapshot = payload.snapshot
    if snapshot.status != "ok" or snapshot.snapshot is None:
        return RiskOutput(status="insufficient_data", reasons=("snapshot_not_valued",))
    record = snapshot.snapshot
    # Revalue the record, so callers cannot forge market_values or use an old-valued wrapper.
    from .portfolio_snapshot import get_portfolio_snapshot, SnapshotInput
    checked = get_portfolio_snapshot(SnapshotInput(snapshot_id=record.snapshot_id, as_of=payload.as_of,
        max_age_seconds=payload.max_quote_age_seconds if payload.max_quote_age_seconds is not None else 86400), lambda _:record)
    if checked.status != "ok":
        return RiskOutput(status="insufficient_data", reasons=checked.reasons)
    try:
        active = [h.symbol for h in record.holdings if h.quantity > 0]
        histories = checked_histories(payload.histories, payload.as_of, record.currency, active)
        for h in payload.histories:
            if h.symbol in active and (not h.bars or (payload.as_of-max(b.close_at for b in h.bars)).total_seconds() > payload.max_history_age_seconds):
                raise ValueError("stale_history:"+h.symbol)
        result = PortfolioRiskAnalyzer().analyze(checked.market_values, record.cash, histories, payload.periods_per_year)
    except ValueError as exc:
        return RiskOutput(status="insufficient_data", reasons=(str(exc),))
    return RiskOutput(status="ok" if result["annualized_volatility"] is not None else "insufficient_data",
                      snapshot_id=record.snapshot_id, content_hash=checked.content_hash,
                      history_sources=tuple(h.source for h in payload.histories), **result)


def register_tools(registry, deps=None):
    registry.register(ToolSpec(name="calculate_portfolio_risk", version="1", description="Compute actual cash-inclusive weights and aligned historical risk proxy.",
                              input_model=RiskInput, output_model=RiskOutput, handler=calculate_portfolio_risk))
