"""Pure Agent run state machine; persistence and side effects live elsewhere."""

from __future__ import annotations

from typing import Literal

from .schemas import RunStatus


class InvalidStateTransition(ValueError):
    pass


Transition = Literal[
    "queue",
    "begin_planning",
    "wait_user",
    "approve",
    "begin_execution",
    "wait_tool",
    "wait_job",
    "request_pause",
    "pause",
    "resume",
    "request_cancel",
    "cancel",
    "complete",
    "fail",
    "expire",
]


TERMINAL: set[str] = {"completed", "failed", "cancelled", "expired"}
_TRANSITIONS: dict[tuple[str, str], str] = {
    ("created", "queue"): "queued",
    ("queued", "begin_planning"): "planning",
    ("planning", "wait_user"): "waiting_user",
    ("planning", "begin_execution"): "executing",
    ("waiting_user", "approve"): "executing",
    ("executing", "wait_tool"): "waiting_tool",
    ("executing", "wait_job"): "waiting_job",
    ("waiting_tool", "begin_execution"): "executing",
    ("waiting_job", "begin_execution"): "executing",
    ("executing", "request_pause"): "pause_requested",
    ("pause_requested", "pause"): "paused",
    ("paused", "resume"): "executing",
    ("executing", "request_cancel"): "cancelling",
    ("waiting_tool", "request_cancel"): "cancelling",
    ("waiting_job", "request_cancel"): "cancelling",
    ("pause_requested", "cancel"): "cancelled",
    ("cancelling", "cancel"): "cancelled",
    ("planning", "fail"): "failed",
    ("executing", "complete"): "completed",
    ("executing", "fail"): "failed",
    ("waiting_user", "fail"): "failed",
    ("created", "expire"): "expired",
    ("queued", "expire"): "expired",
    ("planning", "expire"): "expired",
    ("executing", "expire"): "expired",
    ("waiting_job", "expire"): "expired",
    ("paused", "expire"): "expired",
}


def transition(current: RunStatus | str, event: Transition | str) -> RunStatus:
    try:
        return _TRANSITIONS[(current, event)]  # type: ignore[return-value]
    except KeyError as exc:
        raise InvalidStateTransition(f"Cannot apply {event!r} to {current!r}") from exc
