"""Structured logging with request-scoped correlation IDs.

Identifiers stay in log context and are deliberately not used as metric
labels. Prompts, documents, secrets and exception tracebacks are not emitted.
"""

from __future__ import annotations

import contextvars
import json
import logging
import uuid
from contextlib import contextmanager
from typing import Iterator


_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def request_context() -> str:
    return _request_id.get() or str(uuid.uuid4())


@contextmanager
def request_scope(value: str | None = None) -> Iterator[str]:
    token = _request_id.set(value or str(uuid.uuid4()))
    try:
        yield _request_id.get()
    finally:
        _request_id.reset(token)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_context(),
        }
        if getattr(record, "route", None):
            payload["route"] = record.route
        if getattr(record, "status_code", None) is not None:
            payload["status_code"] = record.status_code
        return json.dumps(payload, ensure_ascii=False)
