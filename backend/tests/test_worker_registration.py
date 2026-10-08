"""The configured Celery entry point must register the dispatched tasks."""

import json
import os
import subprocess
import sys


def test_fresh_worker_loader_registers_all_queue_tasks():
    result = subprocess.run(
        [sys.executable, "-c",
         "import json; from workers.celery_app import celery_app; "
         "celery_app.loader.import_default_modules(); "
         "print(json.dumps(sorted(celery_app.tasks)))"],
        env=os.environ.copy(), capture_output=True, text=True, check=True,
    )
    tasks = json.loads(result.stdout.strip())
    for name in (
        "backend.workers.agent_tasks.run_agent",
        "backend.workers.agent_tasks.resume_agent_job",
        "backend.workers.compute_tasks.run_backtest_job",
    ):
        assert name in tasks
    assert any("rag_tasks" in name for name in tasks)
