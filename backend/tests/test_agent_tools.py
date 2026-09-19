"""T20/T21 contract tests for typed tools."""

from __future__ import annotations

import asyncio
import time

import pandas as pd
from pydantic import BaseModel

from agent.schemas import ToolStatus
from agent.tools.executor import ToolExecutor, ToolExecutionError
from agent.tools.registry import ToolRegistry, ToolSpec


class Input(BaseModel):
    value: int


class Output(BaseModel):
    result: int


def spec(name: str, handler, **kwargs):
    return ToolSpec(
        name=name,
        version="1",
        description="test",
        input_model=Input,
        output_model=Output,
        handler=handler,
        **kwargs,
    )


def test_registry_rejects_duplicate_name_and_exposes_schema():
    registry = ToolRegistry()
    registry.register(spec("demo", lambda payload: {"result": payload.value}))
    try:
        registry.register(spec("demo", lambda payload: {"result": payload.value}))
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:  # pragma: no cover - assertion branch
        raise AssertionError("duplicate tool was accepted")
    assert registry.schemas()[0]["input_schema"]["properties"]["value"]["type"] == "integer"


def test_executor_rejects_invalid_input_without_calling_handler():
    called = False

    def handler(payload):
        nonlocal called
        called = True
        return {"result": payload.value}

    registry = ToolRegistry()
    registry.register(spec("demo", handler))
    result = asyncio.run(ToolExecutor(registry).execute("demo", {"value": "bad"}))
    assert result.status == ToolStatus.FAILED
    assert result.error.code == "validation_error"
    assert called is False


def test_executor_maps_timeout_and_hides_exception_details():
    def slow(payload):
        time.sleep(0.05)
        return {"result": payload.value}

    registry = ToolRegistry()
    registry.register(spec("slow", slow, timeout_seconds=0.001))
    result = asyncio.run(ToolExecutor(registry).execute("slow", {"value": 1}))
    assert result.error.code == "dependency_timeout"
    assert "Traceback" not in result.error.message


def test_executor_maps_expected_business_error():
    def missing(payload):
        raise ToolExecutionError("business_error", "symbol does not exist")

    registry = ToolRegistry()
    registry.register(spec("missing", missing))
    result = asyncio.run(ToolExecutor(registry).execute("missing", {"value": 1}))
    assert result.error.code == "business_error"
    assert result.error.retryable is False


def test_builtin_registry_contains_first_three_tools():
    from agent.tools import default_registry

    assert {tool.name for tool in default_registry.list()} == {
        "get_market_snapshot",
        "calculate_indicators",
        "assess_risk",
        "run_backtest",
        "get_backtest_result",
        "compare_backtests",
        "search_knowledge_base",
    }


def test_market_adapter_returns_bounded_snapshot_from_fake_engine():
    from agent.tools.market import MarketSnapshotInput, get_market_snapshot
    from lobster_quant.src.data.models import StockData

    frame = pd.DataFrame(
        {
            "open": [10.0, 11.0],
            "high": [11.0, 12.0],
            "low": [9.0, 10.0],
            "close": [10.5, 11.5],
            "volume": [100, 120],
        },
        index=pd.date_range("2026-01-01", periods=2),
    )

    class FakeEngine:
        def fetch_stock(self, symbol, years):
            return StockData(symbol=symbol, daily=frame, source="fixture")

    result = get_market_snapshot(MarketSnapshotInput(symbol="TEST"), FakeEngine)
    assert result.price == 11.5
    assert result.rows == 2
    assert result.citations[0].type == "tool_result"
