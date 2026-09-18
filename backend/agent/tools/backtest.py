"""Asynchronous backtest tools backed by the compute queue."""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from ..schemas import Citation
from .executor import ToolExecutionError
from .registry import ToolSpec, default_registry


class RunBacktestInput(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    years: int = Field(default=3, ge=1, le=10)
    holding_days: int = Field(default=20, ge=5, le=100)
    min_score: int = Field(default=60, ge=0, le=100)
    slippage: float = Field(default=0.001, ge=0, le=0.01)
    commission: float = Field(default=0.001, ge=0, le=0.01)
    confirmation_granted: bool = False


class RunBacktestOutput(BaseModel):
    job_id: str
    backtest_run_id: str
    status: str
    reused: bool = False
    citations: list[Citation] = Field(default_factory=list)


class GetBacktestResultInput(BaseModel):
    backtest_run_id: str = Field(min_length=1, max_length=64)


class GetBacktestResultOutput(BaseModel):
    backtest_run_id: str
    status: str
    result: dict[str, Any] | None = None
    error_code: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class CompareBacktestsInput(BaseModel):
    backtest_run_ids: list[str] = Field(min_length=2, max_length=10)


class CompareBacktestsOutput(BaseModel):
    results: list[dict[str, Any]]
    citations: list[Citation] = Field(default_factory=list)


def run_backtest(
    payload: RunBacktestInput,
    session_factory: Callable | None = None,
    dispatcher: Callable[[str], Any] | None = None,
) -> RunBacktestOutput:
    if payload.years > 5 and not payload.confirmation_granted:
        raise ToolExecutionError("confirmation_required", "Backtests covering more than five years require confirmation")
    if session_factory is None:
        from db.session import sync_session_factory

        session_factory = sync_session_factory
    if dispatcher is None:
        from workers.compute_tasks import run_backtest_job

        dispatcher = run_backtest_job.delay
    from services.jobs import create_backtest_job

    inputs = {
        "symbol": payload.symbol.upper(),
        "years": payload.years,
        "holding_days": payload.holding_days,
        "min_score": payload.min_score,
        "slippage": payload.slippage,
        "commission": payload.commission,
    }
    with session_factory() as session:
        handle = create_backtest_job(session, inputs)
    try:
        if not handle.reused:
            dispatcher(handle.job_id)
    except Exception as exc:
        raise ToolExecutionError("dependency_timeout", "Compute queue is unavailable", True) from exc
    return RunBacktestOutput(
        job_id=handle.job_id,
        backtest_run_id=handle.backtest_run_id,
        status=handle.status,
        reused=handle.reused,
        citations=[Citation(type="backtest_run", ref_id=handle.backtest_run_id, label="backtest job")],
    )


def get_backtest_result(payload: GetBacktestResultInput, session_factory: Callable | None = None) -> GetBacktestResultOutput:
    if session_factory is None:
        from db.session import sync_session_factory

        session_factory = sync_session_factory
    from services.jobs import get_backtest

    with session_factory() as session:
        record = get_backtest(session, payload.backtest_run_id)
        if record is None:
            raise ToolExecutionError("business_error", "Backtest run does not exist")
        return GetBacktestResultOutput(
            backtest_run_id=record.id,
            status=record.status,
            result=record.result_data,
            error_code=record.error_code,
            citations=[Citation(type="backtest_run", ref_id=record.id, label="backtest result")],
        )


def compare_backtests(payload: CompareBacktestsInput, session_factory: Callable | None = None) -> CompareBacktestsOutput:
    if session_factory is None:
        from db.session import sync_session_factory

        session_factory = sync_session_factory
    from services.jobs import get_backtest

    rows: list[dict[str, Any]] = []
    with session_factory() as session:
        for run_id in payload.backtest_run_ids:
            record = get_backtest(session, run_id)
            if record is None or record.status != "completed" or record.result_data is None:
                raise ToolExecutionError("business_error", "Only completed backtests can be compared")
            result = record.result_data
            rows.append(
                {
                    "backtest_run_id": record.id,
                    "symbol": record.symbol,
                    "cumulative_return": result.get("cumulative_return", 0),
                    "total_trades": result.get("total_trades", 0),
                    "sharpe_ratio": result.get("sharpe_ratio"),
                }
            )
    rows.sort(key=lambda row: (row["cumulative_return"], row["backtest_run_id"]), reverse=True)
    return CompareBacktestsOutput(
        results=rows,
        citations=[Citation(type="backtest_run", ref_id=row["backtest_run_id"], label="comparison") for row in rows],
    )


default_registry.register(
    ToolSpec(
        name="run_backtest",
        version="1",
        description="Queue an asynchronous backtest and return its stable job identifiers.",
        input_model=RunBacktestInput,
        output_model=RunBacktestOutput,
        handler=run_backtest,
        timeout_seconds=10,
    )
)
default_registry.register(
    ToolSpec(
        name="get_backtest_result",
        version="1",
        description="Read a persisted backtest result without polling a running job.",
        input_model=GetBacktestResultInput,
        output_model=GetBacktestResultOutput,
        handler=get_backtest_result,
        timeout_seconds=10,
    )
)
default_registry.register(
    ToolSpec(
        name="compare_backtests",
        version="1",
        description="Deterministically compare completed backtest runs.",
        input_model=CompareBacktestsInput,
        output_model=CompareBacktestsOutput,
        handler=compare_backtests,
        timeout_seconds=10,
    )
)
