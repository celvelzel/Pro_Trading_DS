"""Token-budgeted context assembly with conversation isolation."""

from __future__ import annotations

from typing import Any


class ContextBuilder:
    def __init__(self, max_tokens: int = 4000) -> None:
        self.max_chars = max_tokens * 4

    def build(
        self,
        *,
        system_policy: str,
        memories: list[str],
        messages: list[dict[str, str]],
        summary: str | None = None,
        plan: dict[str, Any] | None = None,
        tool_summaries: list[str] | None = None,
        retrieval_chunks: list[str] | None = None,
    ) -> list[dict[str, str]]:
        result = [{"role": "system", "content": system_policy}]
        sections = [
            ("Explicit memory", memories),
            ("Summary", [summary] if summary else []),
            ("Current plan", [str(plan)] if plan else []),
            ("Tool results", tool_summaries or []),
            ("Retrieved sources", retrieval_chunks or []),
        ]
        for title, values in sections:
            if values:
                result.append({"role": "system", "content": f"{title}:\n" + "\n".join(values)})
        result.extend(messages[-20:])
        while self._size(result) > self.max_chars and len(result) > 1:
            # Preserve policy and the latest user/assistant turns; old messages
            # are replaced by the persisted summary in a later revision.
            result.pop(1)
        return result

    @staticmethod
    def _size(messages: list[dict[str, str]]) -> int:
        return sum(len(message.get("content", "")) for message in messages)
