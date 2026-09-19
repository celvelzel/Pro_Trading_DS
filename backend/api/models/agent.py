"""REST DTOs for Agent conversations, runs, interventions and SSE."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class ConversationResponse(BaseModel):
    id: str
    title: str | None = None


class RunCreate(BaseModel):
    conversation_id: str
    goal: str = Field(min_length=1, max_length=4000)
    mode: Literal["review", "auto"] = "review"


class RunAction(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=2000)
    retry_of_step_id: str | None = None


class MemoryCreate(BaseModel):
    kind: Literal["user_preference", "research_constraint", "confirmed_fact"]
    content: str = Field(min_length=1, max_length=4000)
    source_message_id: str | None = None


class MemorySupersede(BaseModel):
    expected_version: int = Field(default=1, ge=1)
    content: str = Field(min_length=1, max_length=4000)


class AgentErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str
    retryable: bool = False
    details: dict[str, Any] | None = None
