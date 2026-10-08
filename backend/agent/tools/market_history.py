"""Explicit point-in-time history; no implicit provider suitability assumptions."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Annotated, Literal, Protocol
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, AfterValidator, model_validator

from ..schemas import Citation
from .registry import ToolRegistry, ToolSpec


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An aware timestamp is required")
    return value.astimezone(timezone.utc)


UTC = Annotated[datetime, AfterValidator(utc)]
Symbol = Annotated[str, Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9.\-]+$"), AfterValidator(str.upper)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


def stable_ref(prefix: str, value: BaseModel | dict) -> str:
    data = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return prefix + ":" + hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class HistoryBar(StrictModel):
    session_date: date
    close_at: UTC
    available_at: UTC
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)

    @model_validator(mode="after")
    def consistent(self):
        if self.available_at < self.close_at or not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("Invalid bar timing or OHLC range")
        return self


class HistorySeries(StrictModel):
    symbol: Symbol
    provider: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    currency: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    exchange_timezone: str = Field(min_length=1)
    adjustment: Literal["raw", "split", "total_return", "unknown"]
    point_in_time_safe: bool = False
    bars: list[HistoryBar]
    expected_sessions: list[date] = Field(default_factory=list)
    suspended_sessions: list[date] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique(self):
        ZoneInfo(self.exchange_timezone)
        if len({b.session_date for b in self.bars}) != len(self.bars):
            raise ValueError("Duplicate sessions")
        if any(b.close_at.astimezone(ZoneInfo(self.exchange_timezone)).date() != b.session_date for b in self.bars):
            raise ValueError("Session date must match exchange-local close date")
        return self


class MarketHistoryInput(StrictModel):
    symbol: Symbol
    as_of: UTC
    lookback: int = Field(default=21, ge=2, le=2520)
    adjustment: Literal["raw", "split", "total_return"] = "raw"


class MarketHistoryOutput(StrictModel):
    symbol: Symbol
    as_of: UTC
    status: Literal["ok", "insufficient_data", "unavailable"]
    series: HistorySeries | None = None
    data_last_bar_at: UTC | None = None
    gaps: list[date] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    result_ref: str
    citations: list[Citation] = Field(default_factory=list)


class HistoryBackend(Protocol):
    def load(self, symbol: str) -> HistorySeries | None: ...


class FixtureHistoryBackend:
    def __init__(self, series: list[HistorySeries]):
        self._series = {s.symbol: s.model_copy(deep=True) for s in series}

    def load(self, symbol: str) -> HistorySeries | None:
        value = self._series.get(symbol.upper())
        return value.model_copy(deep=True) if value else None


class MarketDependencies:
    def __init__(self, history_backend: HistoryBackend):
        self.history_backend = history_backend


class DataEngineHistoryBackend:
    """Opt-in adapter: caller supplies audited series metadata and per-session times.

    Metadata must include an empty bars list; session_times maps dates to explicit
    close/availability timestamps. Missing mappings fail rather than guess.
    """
    def __init__(self, engine, metadata: dict[str, HistorySeries], session_times: dict[str, dict[date, tuple[datetime, datetime]]]):
        self.engine, self.metadata, self.session_times = engine, metadata, session_times

    def load(self, symbol: str) -> HistorySeries | None:
        template = self.metadata.get(symbol)
        if template is None or template.adjustment == "unknown" or not template.point_in_time_safe:
            return None
        stock = self.engine.fetch_stock(symbol, years=10)
        if stock is None or stock.daily is None:
            return None
        bars = []
        for index, row in stock.daily.iterrows():
            session = index.date()
            times = self.session_times.get(symbol, {}).get(session)
            if times is None:
                return None
            bars.append(HistoryBar(session_date=session, close_at=times[0], available_at=times[1], **{key: float(row[key]) for key in ("open", "high", "low", "close", "volume")}))
        return HistorySeries.model_validate(template.model_copy(update={"bars": bars}).model_dump())


def get_market_history(payload: MarketHistoryInput, dependencies: MarketDependencies) -> MarketHistoryOutput:
    series = dependencies.history_backend.load(payload.symbol)
    ref = stable_ref("history-request", payload)
    if series is None or series.symbol != payload.symbol or series.adjustment != payload.adjustment or not series.point_in_time_safe:
        return MarketHistoryOutput(symbol=payload.symbol, as_of=payload.as_of, status="unavailable", result_ref=ref,
                                   limitations=["Missing data or unknown/incompatible point-in-time adjustment provenance"])
    bars = sorted((b for b in series.bars if b.close_at <= payload.as_of and b.available_at <= payload.as_of), key=lambda b: b.session_date)[-payload.lookback:]
    # Calendar bounds come from eligible bars, never from future data.
    cutoff_date = payload.as_of.astimezone(ZoneInfo(series.exchange_timezone)).date()
    calendar = [d for d in series.expected_sessions if (not bars or bars[0].session_date <= d) and d <= cutoff_date]
    gaps = sorted(set(calendar) - {b.session_date for b in bars})
    limitations = []
    if not series.expected_sessions:
        limitations.append("Trading calendar unavailable; gaps/nontrading days cannot be inferred")
    if gaps:
        limitations.append("Missing trading sessions (including declared suspensions)")
    if len(bars) < payload.lookback:
        limitations.append("Insufficient trading bars")
    trimmed = series.model_copy(update={"bars": bars, "expected_sessions": calendar, "suspended_sessions": [d for d in series.suspended_sessions if d in calendar]})
    ref = stable_ref("market-history", {"request": payload.model_dump(mode="json"), "series": trimmed.model_dump(mode="json")})
    return MarketHistoryOutput(symbol=payload.symbol, as_of=payload.as_of, status="insufficient_data" if gaps or len(bars) < payload.lookback else "ok", series=trimmed,
        data_last_bar_at=bars[-1].close_at if bars else None, gaps=gaps, limitations=limitations, result_ref=ref,
        citations=[Citation(type="tool_result", ref_id=ref, label="point-in-time OHLCV", field_path="series.bars", metadata={"source_locator": series.source_locator, "provider": series.provider})])


def register_tools(registry: ToolRegistry, dependencies: MarketDependencies) -> None:
    registry.register(ToolSpec(name="get_market_history", version="1", description="Read explicit point-in-time OHLCV history", input_model=MarketHistoryInput, output_model=MarketHistoryOutput, handler=lambda p: get_market_history(p, dependencies)))
