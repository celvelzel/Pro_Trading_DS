"""Additive financial runtime persistence; legacy runs remain untouched."""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..base import Base
from .agent import JsonType, new_id


class FinancialRun(Base):
    __tablename__ = 'financial_runs'
    __table_args__ = (UniqueConstraint('conversation_id', 'idempotency_key', name='uq_financial_request'),)
    run_id: Mapped[str] = mapped_column(ForeignKey('agent_runs.id'), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('conversations.id'), index=True)
    mas_kind: Mapped[str] = mapped_column(String(32))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    request: Mapped[dict] = mapped_column(JsonType)
    creation_inputs: Mapped[dict] = mapped_column(JsonType)
    budget: Mapped[dict] = mapped_column(JsonType)
    checkpoint: Mapped[dict] = mapped_column(JsonType)
    active_seconds: Mapped[float] = mapped_column(Float, default=0)
    active_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resume_phase: Mapped[str | None] = mapped_column(String(32))
    claim_token: Mapped[str | None] = mapped_column(String(36))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_event_seq: Mapped[int] = mapped_column(Integer, default=1)


class FinancialInvocation(Base):
    __tablename__ = 'financial_invocations'
    __table_args__ = (UniqueConstraint('run_id', 'invocation_key', name='uq_financial_invocation'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey('financial_runs.run_id'), index=True)
    invocation_key: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))
    input_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    output: Mapped[dict | None] = mapped_column(JsonType)
    error_code: Mapped[str | None] = mapped_column(String(64))
    tool_call_id: Mapped[str | None] = mapped_column(ForeignKey('tool_calls.id'))


class FinancialArtifact(Base):
    __tablename__ = 'financial_artifacts'
    __table_args__ = (UniqueConstraint('run_id', 'artifact_key', name='uq_financial_artifact'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey('financial_runs.run_id'), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('conversations.id'), index=True)
    artifact_key: Mapped[str] = mapped_column(String(128))
    mas_kind: Mapped[str] = mapped_column(String(32))
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    symbols: Mapped[list] = mapped_column(JsonType, default=list)
    content_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JsonType)


class FinancialRelation(Base):
    __tablename__ = 'financial_relations'
    __table_args__ = (UniqueConstraint('conversation_id', 'idempotency_key', name='uq_financial_relation'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey('conversations.id'))
    source_run_id: Mapped[str] = mapped_column(ForeignKey('financial_runs.run_id'))
    target_run_id: Mapped[str] = mapped_column(ForeignKey('financial_runs.run_id'))
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    relation_type: Mapped[str] = mapped_column(String(32))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    envelope: Mapped[dict] = mapped_column(JsonType)
