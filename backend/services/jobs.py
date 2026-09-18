"""Persistent compute job service used by Agent tools and workers."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models.jobs import BacktestRun, Job


@dataclass(frozen=True)
class BacktestJobHandle:
    job_id: str
    backtest_run_id: str
    status: str
    reused: bool = False


def make_idempotency_key(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def create_backtest_job(session: Session, payload: dict[str, Any]) -> BacktestJobHandle:
    """Create or reuse a compute job for one exact input payload."""

    key = make_idempotency_key(payload)
    existing = session.scalar(select(Job).where(Job.idempotency_key == key))
    if existing:
        backtest = session.scalar(select(BacktestRun).where(BacktestRun.job_id == existing.id))
        if backtest is None:  # defensive repair for a partially committed legacy row
            raise RuntimeError("Job exists without a backtest run")
        return BacktestJobHandle(existing.id, backtest.id, existing.status, reused=True)

    job = Job(
        idempotency_key=key,
        kind="backtest",
        status="pending",
        input_data=payload,
        attempts=0,
    )
    session.add(job)
    session.flush()
    backtest = BacktestRun(
        job_id=job.id,
        status="pending",
        symbol=payload.get("symbol"),
        strategy_id=payload.get("strategy_id"),
        input_data=payload,
        code_version=os.getenv("APP_COMMIT", "unknown"),
    )
    session.add(backtest)
    session.commit()
    return BacktestJobHandle(job.id, backtest.id, job.status)


def get_backtest(session: Session, backtest_run_id: str) -> BacktestRun | None:
    return session.get(BacktestRun, backtest_run_id)
