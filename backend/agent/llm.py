"""Provider protocol plus deterministic fake and OpenAI-compatible adapter."""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, Field


class ModelProviderError(RuntimeError):
    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class ModelResponse(BaseModel):
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = 0
    token_usage: dict[str, Any] = Field(default_factory=dict)
    provider_request_id: str | None = None


class ModelProvider(Protocol):
    async def complete(self, messages: list[dict[str, str]], *, request_id: str | None = None) -> ModelResponse:
        ...


class ScriptedFakeModel:
    """No-network model used by unit and deterministic evaluation tests."""

    def __init__(self, responses: list[ModelResponse | dict[str, Any]]) -> None:
        self.responses = [response if isinstance(response, ModelResponse) else ModelResponse(**response) for response in responses]
        self.calls: list[list[dict[str, str]]] = []

    async def complete(self, messages: list[dict[str, str]], *, request_id: str | None = None) -> ModelResponse:
        self.calls.append(messages)
        if not self.responses:
            raise ModelProviderError("internal_error", "Fake model script is exhausted")
        response = self.responses.pop(0)
        return response.model_copy(update={"provider_request_id": request_id or str(uuid.uuid4())})


@dataclass
class OpenAICompatibleModel:
    """Minimal adapter; the response is normalized before entering the Agent."""

    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "OpenAICompatibleModel":
        return cls(
            base_url=os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            api_key=os.getenv("AI_API_KEY", ""),
            model=os.getenv("AI_MODEL", "gpt-4o-mini"),
        )

    async def complete(self, messages: list[dict[str, str]], *, request_id: str | None = None) -> ModelResponse:
        if not self.api_key:
            raise ModelProviderError("permission_denied", "AI provider is not configured")
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "X-Request-ID": request_id or str(uuid.uuid4())},
                    json={"model": self.model, "messages": messages, "response_format": {"type": "json_object"}},
                )
                response.raise_for_status()
                body = response.json()
        except httpx.TimeoutException as exc:
            raise ModelProviderError("dependency_timeout", "AI provider timed out", True) from exc
        except httpx.HTTPStatusError as exc:
            retryable = exc.response.status_code in {429, 500, 502, 503, 504}
            code = "rate_limited" if exc.response.status_code == 429 else "internal_error"
            raise ModelProviderError(code, "AI provider request failed", retryable) from exc
        except httpx.HTTPError as exc:
            raise ModelProviderError("internal_error", "AI provider request failed", True) from exc
        try:
            content = body["choices"][0]["message"]["content"]
            import json

            payload = json.loads(content) if isinstance(content, str) else content
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelProviderError("internal_error", "AI provider returned an invalid response") from exc
        return ModelResponse(
            kind=payload.get("kind", "final"),
            payload=payload.get("payload", payload),
            latency_ms=round((time.perf_counter() - started) * 1000),
            token_usage=body.get("usage", {}),
            provider_request_id=response.headers.get("x-request-id") or request_id,
        )
