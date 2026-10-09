"""W8 harness smoke tests exercise the persisted runtime with synthetic data only."""
import importlib.util
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("financial_mas_w8_eval", ROOT / "eval/run_financial_mas_w8.py")
w8 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w8)


def database(path):
    engine = create_engine("sqlite:///" + path.as_posix(), connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)


def test_w8_runner_exports_actual_persisted_market_and_portfolio_runs(tmp_path):
    market_cases, portfolio_cases = w8.fixtures.load_cases()
    engine, sessions = database(tmp_path / "w8.sqlite3")
    try:
        market = w8._run_one(market_cases[0], "market", "autonomous", sessions)
        portfolio = w8._run_one(portfolio_cases[0], "portfolio", "full", sessions)
    finally:
        engine.dispose()

    assert market["actual_workflow_executed"] is True
    assert market["run_status"] == "completed"
    assert market["counters"]["model_calls"] == market["counters"]["persisted_model_invocations"] == 5
    assert market["counters"]["tool_calls"] == market["counters"]["persisted_tool_invocations"]
    assert market["counters"]["token_usage"] is None
    assert len(market["persisted"]["artifacts"]) == 1
    assert market["metrics"]["eligible_event_count"]["correct"] is True

    assert portfolio["actual_workflow_executed"] is True
    assert portfolio["run_status"] == "completed"
    assert portfolio["counters"]["model_calls"] == portfolio["counters"]["persisted_model_invocations"] == 5
    assert portfolio["counters"]["tool_calls"] == portfolio["counters"]["persisted_tool_invocations"] == 6
    assert portfolio["counters"]["token_usage"] is None
    assert len(portfolio["persisted"]["artifacts"]) == 1
    assert portfolio["metrics"]["risk_calculation_accuracy"]["value"] == 1
    assert portfolio["metrics"]["simulation_net_value_consistency"]["value"] == 1


def test_builder_selects_explicit_baselines_and_keeps_defaults(tmp_path):
    market_cases, portfolio_cases = w8.fixtures.load_cases()
    engine, sessions = database(tmp_path / "modes.sqlite3")
    try:
        defaults = w8._new_dispatcher(sessions, market_cases[0], "market", "autonomous")
        defaults_portfolio = w8._new_dispatcher(sessions, portfolio_cases[0], "portfolio", "full")
        fixed_market = w8._new_dispatcher(sessions, market_cases[0], "market", "fixed")
        fixed_portfolio = w8._new_dispatcher(sessions, portfolio_cases[0], "portfolio", "fixed")
        single_portfolio = w8._new_dispatcher(sessions, portfolio_cases[0], "portfolio", "single")
        assert defaults.drivers.get("market_investigation").mode == "autonomous"
        assert defaults_portfolio.drivers.get("portfolio_rebalance").mode == "full"
        assert fixed_market.drivers.get("market_investigation").mode == "fixed"
        assert fixed_portfolio.drivers.get("portfolio_rebalance").mode == "fixed"
        assert single_portfolio.drivers.get("portfolio_rebalance").mode == "single"
    finally:
        engine.dispose()


def test_combined_smoke_exports_two_runs_and_persisted_relations(tmp_path):
    summary = w8.run_combined_smoke(tmp_path, verbose=False)
    row = w8.json.loads((tmp_path / "combined-synthetic-demo-v1.jsonl").read_text(encoding="utf-8"))
    assert summary["combined:synthetic-demo-v1"]["run_count"] == 2
    assert row["fixture_id"] == "combined-w7-synthetic-demo-v1"
    assert row["distinct_run_ids"] == 2
    assert row["combined_summary"]["both_terminal_completed"] is True
    assert row["combined_summary"]["combined_relation_present"] is True
    assert row["combined_summary"]["market_evidence_admitted"] is True
    assert row["combined_summary"]["artifacts_persisted"] == 2
    assert {entry["mas_kind"] for entry in row["run_rows"]} == {
        "market_investigation", "portfolio_rebalance"}
