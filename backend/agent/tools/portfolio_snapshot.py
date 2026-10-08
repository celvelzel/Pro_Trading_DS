"""Explicit immutable snapshot adapter. Never imports or constructs PortfolioStore."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from hashlib import sha256
from typing import Annotated, Callable, Literal, TypeVar
from collections.abc import Mapping
import json

from pydantic import BaseModel, ConfigDict, Field, AfterValidator, BeforeValidator, model_validator
from .registry import ToolSpec


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Aware timestamp required")
    return value.astimezone(timezone.utc)


def symbol(value: str) -> str:
    value = value.strip().upper()
    if not value or len(value) > 32:
        raise ValueError("Invalid symbol")
    return value


def currency(value: str) -> str:
    value = value.strip().upper()
    if len(value) != 3 or not value.isalpha():
        raise ValueError("Expected ISO currency code")
    return value


def nonblank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Nonblank metadata required")
    return value


def reject_symbol_collisions(value):
    if isinstance(value, Mapping):
        normalized = [symbol(key) for key in value if isinstance(key, str)]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Duplicate normalized symbol key")
    return value


Value = TypeVar("Value")
NonBlank = Annotated[str, AfterValidator(nonblank)]
UTCDateTime = Annotated[datetime, AfterValidator(utc)]
Symbol = Annotated[str, AfterValidator(symbol)]
SymbolMap = Annotated[dict[Symbol, Value], BeforeValidator(reject_symbol_collisions)]
Currency = Annotated[str, AfterValidator(currency)]
Amount = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]
PositiveAmount = Annotated[Decimal, Field(gt=0, allow_inf_nan=False)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Holding(StrictModel):
    symbol: Symbol
    quantity: Amount
    currency: Currency | None = None
    sector: NonBlank | None = None
    classification_source: NonBlank | None = None

    @model_validator(mode="after")
    def reserved(self):
        if self.symbol == "CASH":
            raise ValueError("CASH is reserved for explicit cash balance")
        return self


class ValuationQuote(StrictModel):
    symbol: Symbol
    price: PositiveAmount | None = None
    currency: Currency | None = None
    effective_at: UTCDateTime | None = None
    available_at: UTCDateTime | None = None
    source: NonBlank | None = None
    price_kind: Literal["market", "cost_basis"] = "market"


class SnapshotRecord(StrictModel):
    snapshot_id: str = Field(min_length=1)
    source: NonBlank | None = None
    effective_at: UTCDateTime | None = None
    holdings: tuple[Holding, ...] = Field(max_length=32)
    cash: Amount | None = None
    currency: Currency | None = None
    quotes: tuple[ValuationQuote, ...] = Field(default=(), max_length=32)
    snapshot_kind: Literal["saved", "demo"] = "saved"

    @model_validator(mode="after")
    def unique(self):
        for items in (self.holdings, self.quotes):
            names = [h.symbol for h in items]
            if len(names) != len(set(names)):
                raise ValueError("Duplicate symbol")
        return self


class SnapshotInput(StrictModel):
    snapshot_id: str = Field(min_length=1)
    as_of: UTCDateTime
    max_age_seconds: int = Field(default=86400, ge=0, le=604800)


class SnapshotOutput(StrictModel):
    status: Literal["ok", "insufficient_data"]
    snapshot: SnapshotRecord | None = None
    content_hash: str | None = None
    market_values: SymbolMap[Amount] = Field(default_factory=dict)
    total_value: Amount | None = None
    reasons: tuple[str, ...] = ()


SnapshotLoader = Callable[[str], SnapshotRecord | dict | None]


def get_portfolio_snapshot(payload: SnapshotInput, loader: SnapshotLoader) -> SnapshotOutput:
    raw = loader(payload.snapshot_id)
    if raw is None:
        return SnapshotOutput(status="insufficient_data", reasons=("snapshot_not_found",))
    record = SnapshotRecord.model_validate(raw.model_dump() if isinstance(raw, SnapshotRecord) else raw)
    reasons = []
    if record.snapshot_id != payload.snapshot_id:
        reasons.append("snapshot_id_mismatch")
    if not record.source:
        reasons.append("missing_snapshot_source")
    if record.cash is None:
        reasons.append("missing_explicit_cash")
    if record.currency is None:
        reasons.append("missing_currency")
    if record.effective_at is None:
        reasons.append("missing_snapshot_date")
    elif not 0 <= (payload.as_of-record.effective_at).total_seconds() <= payload.max_age_seconds:
        reasons.append("snapshot_future_or_stale")
    quotes = {q.symbol:q for q in record.quotes}
    values = {}
    for holding in record.holdings:
        if holding.currency is None:
            reasons.append("missing_holding_currency:" + holding.symbol)
        elif holding.currency != record.currency:
            reasons.append("mixed_currencies:" + holding.symbol)
        if holding.quantity == 0:
            values[holding.symbol] = Decimal(0)
            continue
        quote = quotes.get(holding.symbol)
        if quote is None or quote.price is None:
            reasons.append("missing_market_price:" + holding.symbol)
            continue
        if quote.price_kind != "market":
            reasons.append("cost_basis_not_market_price:" + holding.symbol)
        if not quote.source:
            reasons.append("missing_quote_source:" + holding.symbol)
        if quote.currency is None or quote.currency != record.currency:
            reasons.append("missing_or_mixed_quote_currency:" + holding.symbol)
        if quote.effective_at is None or quote.available_at is None:
            reasons.append("missing_quote_date:" + holding.symbol)
        elif quote.available_at > payload.as_of or quote.available_at < quote.effective_at or not 0 <= (payload.as_of-quote.effective_at).total_seconds() <= payload.max_age_seconds:
            reasons.append("quote_future_or_stale:" + holding.symbol)
        with localcontext() as ctx:
            ctx.prec = 28
            values[holding.symbol] = holding.quantity * quote.price
    canonical = json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    digest = sha256(canonical.encode()).hexdigest()
    with localcontext() as ctx:
        ctx.prec = 28
        total = sum(values.values(), record.cash or Decimal(0))
    if not reasons and total <= 0:
        reasons.append("zero_portfolio_value")
    return SnapshotOutput(status="insufficient_data" if reasons else "ok", snapshot=record,
                          content_hash=digest, market_values={} if reasons else values,
                          total_value=None if reasons else total, reasons=tuple(reasons))


def register_tools(registry, deps):
    loader = deps["snapshot_loader"] if isinstance(deps, dict) else deps.snapshot_loader
    registry.register(ToolSpec(name="get_portfolio_snapshot", version="1", description="Read an explicit immutable valued snapshot without defaults or writes.",
                              input_model=SnapshotInput, output_model=SnapshotOutput,
                              handler=lambda payload: get_portfolio_snapshot(payload, loader)))
