"""Historical fixture/manual evidence, with strict availability filtering."""
from __future__ import annotations

import hashlib
from typing import Literal, Protocol
from pydantic import Field, model_validator
from ..schemas import Citation
from .market_history import StrictModel, Symbol, UTC, stable_ref
from .registry import ToolRegistry, ToolSpec


class EventRecord(StrictModel):
    symbol: Symbol
    source_type: Literal["news", "filing", "macro", "document"]
    source_locator: str = Field(min_length=1)
    published_at: UTC | None = None
    available_at: UTC | None = None
    observed_at: UTC
    text: str = Field(min_length=1, max_length=20000)
    credibility: Literal["primary", "secondary", "rumor", "unknown"] = "unknown"
    content_hash: str = ""
    id: str = ""

    @model_validator(mode="after")
    def identify(self):
        digest = hashlib.sha256(self.text.encode()).hexdigest()
        if self.content_hash and self.content_hash != digest:
            raise ValueError("Content hash mismatch")
        self.content_hash = digest
        identifier = stable_ref("event", {"locator": self.source_locator, "hash": digest, "published": self.published_at.isoformat() if self.published_at else None, "available": self.available_at.isoformat() if self.available_at else None})
        if self.id and self.id != identifier:
            raise ValueError("Evidence identifier mismatch")
        self.id = identifier
        if self.published_at and self.available_at and self.available_at < self.published_at:
            raise ValueError("Availability cannot precede publication")
        return self


class EventBackend(Protocol):
    def load(self, symbol: str) -> list[EventRecord]: ...


class FixtureEventBackend:
    def __init__(self, records: list[EventRecord]):
        self._records = [r.model_copy(deep=True) for r in records]

    def load(self, symbol: str) -> list[EventRecord]:
        return [r.model_copy(deep=True) for r in self._records if r.symbol == symbol.upper()]


class EventDependencies:
    def __init__(self, event_backend: EventBackend | None = None):
        self.event_backend = event_backend


class EventEvidenceInput(StrictModel):
    symbol: Symbol
    as_of: UTC
    limit: int = Field(default=50, ge=1, le=100)


class EventEvidenceOutput(StrictModel):
    symbol: Symbol
    as_of: UTC
    status: Literal["ok", "insufficient_evidence", "unavailable"]
    evidence: list[EventRecord] = Field(default_factory=list)
    excluded_count: int = 0
    limitations: list[str] = Field(default_factory=list)
    result_ref: str
    citations: list[Citation] = Field(default_factory=list)


def normalize_rag_record(record: dict) -> EventRecord:
    """Accept explicit metadata only; never infer dates or create news."""
    return EventRecord.model_validate(record)


def get_event_evidence(payload: EventEvidenceInput, dependencies: EventDependencies) -> EventEvidenceOutput:
    if dependencies.event_backend is None:
        return EventEvidenceOutput(symbol=payload.symbol, as_of=payload.as_of, status="unavailable", result_ref=stable_ref("events-request", payload), limitations=["No historical evidence backend configured"])
    records = dependencies.event_backend.load(payload.symbol)
    eligible = sorted((r for r in records if r.symbol == payload.symbol and r.published_at is not None and r.available_at is not None and r.published_at <= payload.as_of and r.available_at <= payload.as_of), key=lambda r: (r.published_at, r.id))
    evidence = list({r.id: r for r in eligible}.values())[:payload.limit]
    # Retrieval time is audit data, not a knowledge cutoff or identity component.
    ref = stable_ref("event-evidence", {"request": payload.model_dump(mode="json"), "ids": [r.id for r in evidence]})
    excluded = len(records) - len(eligible)
    limitations = ["External text is untrusted evidence; temporal eligibility does not establish causality"]
    if excluded:
        limitations.append("Future or unknown publication/availability excluded; text not returned")
    if len(eligible) > payload.limit:
        limitations.append("Evidence limit reached")
    return EventEvidenceOutput(symbol=payload.symbol, as_of=payload.as_of, status="ok" if evidence else "insufficient_evidence", evidence=evidence, excluded_count=excluded, limitations=limitations, result_ref=ref, citations=[Citation(type="document", ref_id=r.id, label=r.source_type, excerpt=r.text, metadata={"source_locator": r.source_locator, "content_hash": r.content_hash}) for r in evidence])


def register_tools(registry: ToolRegistry, dependencies: EventDependencies) -> None:
    registry.register(ToolSpec(name="get_event_evidence", version="1", description="Read historically available untrusted evidence; exclude future/unknown timestamps", input_model=EventEvidenceInput, output_model=EventEvidenceOutput, handler=lambda p: get_event_evidence(p, dependencies)))
