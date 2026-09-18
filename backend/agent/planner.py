"""Bounded structured planner with one retained revision."""

from __future__ import annotations

from typing import Any

from .llm import ModelProvider
from .schemas import PlanSpec


class PlanValidationError(ValueError):
    pass


class Planner:
    def __init__(self, known_tools: set[str], max_replans: int = 1) -> None:
        self.known_tools = known_tools
        self.max_replans = max_replans

    async def create(self, provider: ModelProvider, context: list[dict[str, str]], *, revision: int = 1) -> PlanSpec:
        response = await provider.complete(context)
        if response.kind != "plan":
            raise PlanValidationError("Model did not return a structured plan")
        raw = dict(response.payload)
        raw["revision"] = revision
        plan = PlanSpec.model_validate(raw)
        self.validate(plan)
        return plan

    def validate(self, plan: PlanSpec) -> PlanSpec:
        plan.validate_dependencies()
        for step in plan.steps:
            if step.type in {"tool", "retrieve"} and step.tool_name not in self.known_tools:
                raise PlanValidationError(f"Unknown tool in plan: {step.tool_name}")
        return plan

    async def replan(
        self,
        provider: ModelProvider,
        context: list[dict[str, str]],
        previous_revision: int,
        replan_count: int,
    ) -> PlanSpec:
        if replan_count >= self.max_replans:
            raise PlanValidationError("Maximum replan count exceeded")
        return await self.create(provider, context, revision=previous_revision + 1)
