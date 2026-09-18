"""Validated, bounded and non-leaky tool execution."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ValidationError

from ..schemas import ToolError, ToolResultEnvelope, ToolStatus
from .registry import ToolRegistry


class ToolExecutionError(Exception):
    """Expected, user-safe tool failure."""

    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class ToolBusinessError(ToolExecutionError):
    def __init__(self, message: str) -> None:
        super().__init__("business_error", message)


AuditWriter = Callable[[ToolResultEnvelope], Awaitable[None] | None]


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, audit_writer: AuditWriter | None = None) -> None:
        self.registry = registry
        self.audit_writer = audit_writer

    async def execute(
        self,
        name: str,
        payload: dict[str, Any],
        *,
        version: str = "1",
        call_id: str | None = None,
        confirmation_granted: bool = False,
    ) -> ToolResultEnvelope:
        call_id = call_id or str(uuid.uuid4())
        started = time.perf_counter()
        try:
            spec = self.registry.get(name, version)
            if spec.confirmation_policy == "always" and not confirmation_granted:
                raise ToolExecutionError("permission_denied", "Confirmation is required before this tool runs")
            validated = spec.input_model.model_validate(payload)
        except KeyError as exc:
            envelope = self._failure(call_id, name, version, "validation_error", str(exc), started)
            return await self._audit(envelope)
        except ValidationError:
            envelope = self._failure(
                call_id, name, version, "validation_error", "Tool input does not match the required schema", started
            )
            return await self._audit(envelope)
        except ToolExecutionError as exc:
            envelope = self._failure(call_id, name, version, exc.code, exc.message, started, exc.retryable)
            return await self._audit(envelope)

        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(spec.handler, validated), timeout=spec.timeout_seconds
            )
            output = spec.output_model.model_validate(raw)
            envelope = ToolResultEnvelope(
                call_id=call_id,
                tool_name=name,
                tool_version=version,
                status=ToolStatus.SUCCEEDED,
                data=output.model_dump(mode="json"),
                citations=output.model_dump().get("citations", []),
                duration_ms=round((time.perf_counter() - started) * 1000),
            )
        except asyncio.TimeoutError:
            envelope = self._failure(
                call_id, name, version, "dependency_timeout", "Tool execution timed out", started, True
            )
        except ToolExecutionError as exc:
            envelope = self._failure(call_id, name, version, exc.code, exc.message, started, exc.retryable)
        except ValidationError:
            envelope = self._failure(
                call_id, name, version, "internal_error", "Tool returned an invalid result", started
            )
        except Exception:
            envelope = self._failure(
                call_id, name, version, "internal_error", "Tool execution failed", started
            )
        return await self._audit(envelope)

    @staticmethod
    def _failure(
        call_id: str,
        name: str,
        version: str,
        code: str,
        message: str,
        started: float,
        retryable: bool = False,
    ) -> ToolResultEnvelope:
        return ToolResultEnvelope(
            call_id=call_id,
            tool_name=name,
            tool_version=version,
            status=ToolStatus.FAILED,
            error=ToolError(code=code, message=message, retryable=retryable),
            duration_ms=round((time.perf_counter() - started) * 1000),
        )

    async def _audit(self, envelope: ToolResultEnvelope) -> ToolResultEnvelope:
        if self.audit_writer:
            result = self.audit_writer(envelope)
            if asyncio.iscoroutine(result):
                await result
        return envelope
