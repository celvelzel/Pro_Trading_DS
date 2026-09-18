"""Versioned registry for typed Agent tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Type

from pydantic import BaseModel


ToolHandler = Callable[[BaseModel], BaseModel | dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    version: str
    description: str
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]
    handler: ToolHandler
    read_only: bool = True
    side_effect: bool = False
    confirmation_policy: str = "never"
    timeout_seconds: float = 30.0
    max_retries: int = 0
    idempotent: bool = True
    allowed_error_codes: tuple[str, ...] = (
        "validation_error",
        "business_error",
        "dependency_timeout",
        "rate_limited",
        "permission_denied",
        "cancelled",
        "internal_error",
    )

    def public_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
            "output_schema": self.output_model.model_json_schema(),
            "read_only": self.read_only,
            "side_effect": self.side_effect,
            "confirmation_policy": self.confirmation_policy,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "idempotent": self.idempotent,
            "allowed_error_codes": list(self.allowed_error_codes),
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[tuple[str, str], ToolSpec] = {}

    def register(self, spec: ToolSpec) -> ToolSpec:
        key = (spec.name, spec.version)
        if key in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}@{spec.version}")
        if any(name == spec.name for name, _ in self._tools):
            raise ValueError(f"Tool name already registered with another version: {spec.name}")
        self._tools[key] = spec
        return spec

    def get(self, name: str, version: str = "1") -> ToolSpec:
        try:
            return self._tools[(name, version)]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}@{version}") from exc

    def list(self) -> list[ToolSpec]:
        return sorted(self._tools.values(), key=lambda item: (item.name, item.version))

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.public_schema() for tool in self.list()]


default_registry = ToolRegistry()
