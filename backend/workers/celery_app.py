"""Celery configuration with isolated Agent and compute queues."""

from __future__ import annotations

import os

from celery import Celery
from kombu import Queue


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "pro_trading_ds", broker=REDIS_URL, backend=REDIS_URL,
    include=["workers.agent_tasks", "workers.compute_tasks", "workers.rag_tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_protocol=2,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_queue="agent",
    task_queues=(Queue("agent"), Queue("compute")),
    task_routes={
        "backend.workers.agent_tasks.*": {"queue": "agent"},
        "backend.workers.compute_tasks.*": {"queue": "compute"},
    },
    task_soft_time_limit=int(os.getenv("AGENT_TASK_SOFT_TIMEOUT", "300")),
    task_time_limit=int(os.getenv("AGENT_TASK_HARD_TIMEOUT", "360")),
)


@celery_app.task(name="backend.workers.celery_app.health_check", queue="agent")
def health_check() -> dict[str, str]:
    """Small JSON-only task used by worker probes."""

    return {"status": "healthy", "queue": "agent"}
