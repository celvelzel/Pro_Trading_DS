"""Compute queue tasks.  Agent workers never run these inline or poll them."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from db.models.jobs import BacktestRun, Job
from db.session import sync_session_factory
from workers.celery_app import celery_app


def _run_backtest(payload: dict):
    import pandas as pd

    from lobster_quant.src.analysis.backtest import BacktestEngine
    from lobster_quant.src.analysis.signals import SignalGenerator
    from lobster_quant.src.core.data_engine import get_data_engine
    from lobster_quant.src.core.indicator_engine import get_indicator_engine

    symbol = payload["symbol"]
    stock = get_data_engine().fetch_stock(symbol, years=payload.get("years", 3))
    if stock is None:
        raise ValueError(f"No market data available for {symbol}")
    frame = get_indicator_engine().compute_all(stock.daily)
    signal = SignalGenerator()
    score = pd.Series(
        [signal.calculate_score(frame.iloc[: index + 1]) for index in range(len(frame))],
        index=frame.index,
    )
    engine = BacktestEngine()
    for attribute in ("holding_days", "min_score", "slippage", "commission"):
        if attribute in payload:
            setattr(engine, attribute, payload[attribute])
    result = engine.run(frame, score, symbol=symbol)
    return result.model_dump(mode="json")


@celery_app.task(
    bind=True,
    name="backend.workers.compute_tasks.run_backtest_job",
    autoretry_for=(TimeoutError,),
    retry_backoff=True,
    max_retries=2,
    queue="compute",
)
def run_backtest_job(self, job_id: str) -> dict:
    """Run one pending job and persist a stable backtest result."""

    with sync_session_factory() as session:
        job = session.get(Job, job_id)
        if job is None:
            return {"status": "missing", "job_id": job_id}
        backtest = session.scalar(select(BacktestRun).where(BacktestRun.job_id == job.id))
        if backtest is None:
            job.status = "failed"
            job.error_code = "internal_error"
            session.commit()
            return {"status": "failed", "job_id": job.id, "error_code": job.error_code}
        if job.status == "completed" and backtest.status == "completed":
            _dispatch_agent_resumes(job.id)
            return {"status": "completed", "job_id": job.id, "backtest_run_id": backtest.id}

        job.status = "running"
        backtest.status = "running"
        job.attempts += 1
        session.commit()
        payload = dict(job.input_data)

    try:
        result = _run_backtest(payload)
    except TimeoutError as exc:
        raise self.retry(exc=exc) from exc
    except Exception:
        with sync_session_factory() as session:
            job = session.get(Job, job_id)
            backtest = session.scalar(select(BacktestRun).where(BacktestRun.job_id == job_id))
            if job and backtest:
                job.status = "failed"
                job.error_code = "business_error"
                backtest.status = "failed"
                backtest.error_code = "business_error"
                session.commit()
        _dispatch_agent_resumes(job_id)
        return {"status": "failed", "job_id": job_id, "error_code": "business_error"}

    with sync_session_factory() as session:
        job = session.get(Job, job_id)
        backtest = session.scalar(select(BacktestRun).where(BacktestRun.job_id == job_id))
        if job is None or backtest is None:
            return {"status": "missing", "job_id": job_id}
        backtest.status = "completed"
        backtest.result_data = result
        backtest.completed_at = datetime.now()
        job.status = "completed"
        job.result_ref = backtest.id
        session.commit()
        _dispatch_agent_resumes(job.id)
        return {"status": "completed", "job_id": job.id, "backtest_run_id": backtest.id}


def _dispatch_agent_resumes(job_id: str) -> None:
    """Queue one resume task per run waiting on this job.

    The task itself re-checks the checkpoint and run status, so duplicate
    delivery from Celery is harmless.
    """

    from db.models.agent import AgentRun
    from workers.agent_tasks import resume_agent_job

    with sync_session_factory() as session:
        waiting = [
            run
            for run in session.query(AgentRun).filter(AgentRun.status == "waiting_job").all()
            if run.checkpoint.get("job_id") == job_id
        ]
    for run in waiting:
        resume_agent_job.delay(run.id, job_id)
