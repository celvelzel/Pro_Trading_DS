"""T22/T23 async job and backtest tool tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import db.session as session_module

    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'jobs.db'}")
    session_module.get_database_url.cache_clear()
    session_module.async_engine.cache_clear()
    session_module.sync_engine.cache_clear()
    session_module.sync_session_factory.configure(bind=session_module.sync_engine())
    from db.base import Base
    from db.models import agent, jobs  # noqa: F401

    Base.metadata.create_all(session_module.sync_engine())
    yield session_module.sync_session_factory
    session_module.sync_engine().dispose()


def test_run_backtest_returns_pending_handle_and_reuses_idempotently(session_factory):
    from agent.tools.backtest import RunBacktestInput, run_backtest

    dispatched: list[str] = []
    first = run_backtest(
        RunBacktestInput(symbol="AAPL"),
        session_factory=session_factory,
        dispatcher=dispatched.append,
    )
    second = run_backtest(
        RunBacktestInput(symbol="AAPL"),
        session_factory=session_factory,
        dispatcher=dispatched.append,
    )
    assert first.job_id == second.job_id
    assert second.reused is True
    assert dispatched == [first.job_id]


def test_large_backtest_requires_confirmation(session_factory):
    from agent.tools.backtest import RunBacktestInput, run_backtest
    from agent.tools.executor import ToolExecutionError

    with pytest.raises(ToolExecutionError, match="more than five years"):
        run_backtest(
            RunBacktestInput(symbol="AAPL", years=6),
            session_factory=session_factory,
            dispatcher=lambda job_id: None,
        )


def test_compare_only_completed_runs_and_is_deterministic(session_factory):
    from agent.tools.backtest import CompareBacktestsInput, compare_backtests
    from db.models.jobs import BacktestRun, Job

    with session_factory() as session:
        rows = []
        for value in (0.1, 0.3):
            job = Job(idempotency_key=f"key-{value}", kind="backtest", status="completed")
            session.add(job)
            session.flush()
            run = BacktestRun(
                job_id=job.id,
                symbol="TEST",
                status="completed",
                result_data={"cumulative_return": value, "total_trades": 2},
            )
            session.add(run)
            session.flush()
            rows.append(run.id)
        session.commit()

    result = compare_backtests(CompareBacktestsInput(backtest_run_ids=rows), session_factory=session_factory)
    assert [row["cumulative_return"] for row in result.results] == [0.3, 0.1]
