"""Agent conversations, runs, plans, events and tool audit models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from ..base import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


def new_id() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str | None] = mapped_column(String(255))
    user_id: Mapped[str | None] = mapped_column(String(255), index=True)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "sequence", name="uq_message_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    message_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Summary(Base):
    __tablename__ = "conversation_summaries"
    __table_args__ = (UniqueConstraint("conversation_id", "revision", name="uq_summary_revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    covered_through_message_id: Mapped[str | None] = mapped_column(String(36))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MemoryItem(TimestampMixin, Base):
    __tablename__ = "memory_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    source_message_id: Mapped[str | None] = mapped_column(String(36))
    superseded_by: Mapped[str | None] = mapped_column(String(36))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    parent_run_id: Mapped[str | None] = mapped_column(String(36), index=True)
    retry_of_step_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(32), index=True)
    mode: Mapped[str] = mapped_column(String(16), default="review")
    goal: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    replan_count: Mapped[int] = mapped_column(Integer, default=0)
    model_calls: Mapped[int] = mapped_column(Integer, default=0)
    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    checkpoint: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    final_answer: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(64))


class Plan(Base):
    __tablename__ = "agent_plans"
    __table_args__ = (UniqueConstraint("run_id", "revision", name="uq_plan_revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    goal: Mapped[str] = mapped_column(Text)
    assumptions: Mapped[list[Any]] = mapped_column(JsonType, default=list)
    completion_conditions: Mapped[list[Any]] = mapped_column(JsonType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Step(Base):
    __tablename__ = "agent_steps"
    __table_args__ = (UniqueConstraint("plan_id", "ordinal", name="uq_step_ordinal"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    plan_id: Mapped[str] = mapped_column(ForeignKey("agent_plans.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    tool_name: Mapped[str | None] = mapped_column(String(128))
    depends_on: Mapped[list[Any]] = mapped_column(JsonType, default=list)
    input_data: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=False)
    error_code: Mapped[str | None] = mapped_column(String(64))


class AgentEvent(Base):
    __tablename__ = "agent_events"
    __table_args__ = (UniqueConstraint("run_id", "seq", name="uq_event_seq"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    call_id: Mapped[str] = mapped_column(String(36), unique=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"), index=True)
    step_id: Mapped[str | None] = mapped_column(ForeignKey("agent_steps.id"))
    tool_name: Mapped[str] = mapped_column(String(128), index=True)
    tool_version: Mapped[str] = mapped_column(String(32), default="1")
    status: Mapped[str] = mapped_column(String(32))
    input_data: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ToolResult(Base):
    __tablename__ = "tool_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    result_id: Mapped[str] = mapped_column(String(36), unique=True, default=new_id)
    tool_call_id: Mapped[str] = mapped_column(ForeignKey("tool_calls.id"), unique=True)
    data: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    citations: Mapped[list[Any]] = mapped_column(JsonType, default=list)
    summary: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MessageCitation(Base):
    __tablename__ = "message_citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), index=True)
    citation_type: Mapped[str] = mapped_column(String(32))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    content_hash: Mapped[str | None] = mapped_column(String(128))
