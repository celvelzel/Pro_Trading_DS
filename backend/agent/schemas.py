"""Shared Pydantic contracts for tool calls and citations."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ToolStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PENDING = "pending"
    CANCELLED = "cancelled"


class ToolError(BaseModel):
    code: str
    message: str
    retryable: bool = False
    request_id: str | None = None


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["document", "tool_result", "backtest_run"]
    ref_id: str
    label: str
    field_path: str | None = None
    excerpt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResultEnvelope(BaseModel):
    call_id: str
    tool_name: str
    tool_version: str
    status: ToolStatus
    data: dict[str, Any] | None = None
    citations: list[Citation] = Field(default_factory=list)
    error: ToolError | None = None
    duration_ms: int = Field(default=0, ge=0)
    cached: bool = False


RunStatus = Literal[
    "created",
    "queued",
    "planning",
    "waiting_user",
    "executing",
    "waiting_tool",
    "waiting_job",
    "pause_requested",
    "paused",
    "cancelling",
    "completed",
    "failed",
    "cancelled",
    "expired",
]

StepType = Literal["clarify", "tool", "retrieve", "wait_job", "synthesize", "final"]
StepStatus = Literal["pending", "running", "waiting_user", "succeeded", "failed", "skipped", "cancelled"]


class PlanStepSpec(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    type: StepType
    name: str = Field(min_length=1, max_length=255)
    tool_name: str | None = None
    input_data: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    requires_confirmation: bool = False


class PlanSpec(BaseModel):
    goal: str = Field(min_length=1, max_length=4000)
    assumptions: list[str] = Field(default_factory=list)
    steps: list[PlanStepSpec] = Field(min_length=1, max_length=6)
    completion_conditions: list[str] = Field(default_factory=list)
    revision: int = Field(default=1, ge=1)

    def validate_dependencies(self) -> None:
        ids = {step.id for step in self.steps}
        if len(ids) != len(self.steps):
            raise ValueError("Plan step IDs must be unique")
        for step in self.steps:
            unknown = set(step.depends_on) - ids
            if unknown:
                raise ValueError(f"Unknown step dependency: {sorted(unknown)}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_id: str) -> None:
            if step_id in visiting:
                raise ValueError("Plan dependencies must be acyclic")
            if step_id in visited:
                return
            visiting.add(step_id)
            step = next(item for item in self.steps if item.id == step_id)
            for dependency in step.depends_on:
                visit(dependency)
            visiting.remove(step_id)
            visited.add(step_id)

        for step in self.steps:
            visit(step.id)
