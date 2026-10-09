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


def test_post_run_scoring_error_preserves_market_evidence_and_zero_credit_denominator(tmp_path, monkeypatch):
    market_cases, _ = w8.fixtures.load_cases()
    cases = market_cases[:2]
    original_metrics = w8._market_metrics

    def fail_first_case(case, artifact, persisted):
        if case.case_id == cases[0].case_id:
            raise ValueError("injected post-run scoring failure")
        return original_metrics(case, artifact, persisted)

    monkeypatch.setattr(w8, "_market_metrics", fail_first_case)
    output = tmp_path / "scoring-error"
    engine, _ = database(tmp_path / "scoring-error.sqlite3")
    try:
        summary = w8.run_domain("market", ("fixed",), cases, output, verbose=False)
    finally:
        engine.dispose()
    rows = [w8.json.loads(line) for line in (output / "market-fixed.jsonl").read_text().splitlines()]
    errored, scored = rows
    metrics = summary["market:fixed"]["metrics"]

    assert errored["evaluation_status"] == "evaluation_error"
    assert errored["evaluation_error"] == {
        "type": "ValueError", "message": "injected post-run scoring failure"}
    assert errored["failure_stage"] == "scoring"
    assert errored["actual_workflow_executed"] is True
    assert errored["run_status"] == "completed" and errored["run_id"]
    assert errored["run_budget"]["model_calls"] == 5
    assert errored["counters"]["model_calls"] == 5
    assert errored["counters"]["tool_calls"] > 0
    assert len(errored["persisted"]["artifacts"]) == 1
    assert len(errored["persisted"]["events"]) > 0
    assert scored["evaluation_status"] == "scored"
    assert metrics["counters_total"]["model_calls"] == 10
    assert metrics["metric_scoring_coverage"] == {
        "case_count": 2, "scored_case_count": 1, "unscored_case_count": 1,
        "scored_fraction": 0.5, "evaluation_error_count": 1, "harness_error_count": 0}
    numeric = metrics["numeric_fact_accuracy"]
    assert numeric["numerator"] == 6 and numeric["denominator"] == 12
    assert numeric["value"] == 0.5 and numeric["unscored_case_count"] == 1


def test_pre_execution_failure_remains_distinct_and_counts_zero_credit(tmp_path, monkeypatch):
    market_cases, _ = w8.fixtures.load_cases()
    cases = market_cases[:2]
    original_dispatcher = w8._new_dispatcher

    def fail_before_execution(session_factory, case, domain, mode):
        if case.case_id == cases[0].case_id:
            raise RuntimeError("injected pre-execution failure")
        return original_dispatcher(session_factory, case, domain, mode)

    monkeypatch.setattr(w8, "_new_dispatcher", fail_before_execution)
    output = tmp_path / "harness-error"
    engine, _ = database(tmp_path / "harness-error.sqlite3")
    try:
        summary = w8.run_domain("market", ("fixed",), cases, output, verbose=False)
    finally:
        engine.dispose()
    rows = [w8.json.loads(line) for line in (output / "market-fixed.jsonl").read_text().splitlines()]
    failed, completed = rows
    metrics = summary["market:fixed"]["metrics"]

    assert failed["run_status"] == "harness_error"
    assert failed["failure_stage"] == "pre_execution"
    assert failed["evaluation_status"] == "unscored"
    assert failed["actual_workflow_executed"] is False and failed["run_id"] is None
    assert completed["run_status"] == "completed" and completed["evaluation_status"] == "scored"
    assert metrics["terminal_completed"] == 1 and metrics["terminal_failed_or_other"] == 1
    assert metrics["counters_total"]["model_calls"] == 5
    assert metrics["metric_scoring_coverage"]["harness_error_count"] == 1
    assert metrics["numeric_fact_accuracy"]["numerator"] == 6
    assert metrics["numeric_fact_accuracy"]["denominator"] == 12
    assert metrics["numeric_fact_accuracy"]["value"] == 0.5


def test_capture_failure_retains_completed_run_context_and_persisted_evidence(tmp_path, monkeypatch):
    market_cases, _ = w8.fixtures.load_cases()
    cases = market_cases[:2]
    original_export = w8._persisted_run
    failed_once = False

    def fail_export_once(session_factory, run_id):
        nonlocal failed_once
        if not failed_once:
            failed_once = True
            raise RuntimeError("injected persisted export failure")
        return original_export(session_factory, run_id)

    monkeypatch.setattr(w8, "_persisted_run", fail_export_once)
    output = tmp_path / "capture-error"
    engine, _ = database(tmp_path / "capture-error.sqlite3")
    try:
        summary = w8.run_domain("market", ("fixed",), cases, output, verbose=False)
    finally:
        engine.dispose()
    rows = [w8.json.loads(line) for line in (output / "market-fixed.jsonl").read_text().splitlines()]
    captured_failure = rows[0]
    metrics = summary["market:fixed"]["metrics"]

    assert captured_failure["failure_stage"] == "execution_capture"
    assert captured_failure["evaluation_status"] == "unscored"
    assert captured_failure["actual_workflow_executed"] is True
    assert captured_failure["run_status"] == "completed"
    assert captured_failure["run_id"] and captured_failure["conversation_id"]
    assert captured_failure["run_budget"]["model_calls"] == 5
    assert captured_failure["counters"]["model_calls"] == 5
    assert captured_failure["counters"]["tool_calls"] > 0
    assert captured_failure["wall_ms"] is not None
    assert captured_failure["actual_artifact"] is not None
    assert len(captured_failure["persisted"]["artifacts"]) == 1
    assert len(captured_failure["persisted"]["events"]) > 0
    assert metrics["metric_scoring_coverage"]["unscored_case_count"] == 1
    assert metrics["metric_scoring_coverage"]["harness_error_count"] == 0


def test_snapshot_capture_failure_after_create_keeps_run_identity(tmp_path, monkeypatch):
    market_cases, _ = w8.fixtures.load_cases()
    original_factory = w8._new_dispatcher
    failed_once = False

    def fail_initial_snapshot(session_factory, case, domain, mode):
        dispatcher = original_factory(session_factory, case, domain, mode)
        original_snapshot = dispatcher.snapshot

        def snapshot_once(run_id):
            nonlocal failed_once
            if not failed_once:
                failed_once = True
                raise RuntimeError("injected initial snapshot failure")
            return original_snapshot(run_id)

        dispatcher.snapshot = snapshot_once
        return dispatcher

    monkeypatch.setattr(w8, "_new_dispatcher", fail_initial_snapshot)
    output = tmp_path / "initial-snapshot-error"
    engine, _ = database(tmp_path / "initial-snapshot-error.sqlite3")
    try:
        summary = w8.run_domain("market", ("fixed",), market_cases[:1], output, verbose=False)
    finally:
        engine.dispose()
    row = w8.json.loads((output / "market-fixed.jsonl").read_text().splitlines()[0])

    assert row["failure_stage"] == "execution_capture"
    assert row["evaluation_status"] == "unscored"
    assert row["actual_workflow_executed"] is True
    assert row["run_id"] and row["conversation_id"]
    assert row["run_status"] != "harness_error"
    assert row["run_budget"]["max_model_calls"] is not None
    assert row["counters"]["model_calls"] == 0
    assert summary["market:fixed"]["metrics"]["metric_scoring_coverage"]["unscored_case_count"] == 1


def test_portfolio_input_determined_denominators_come_from_fixture_after_scoring_error(tmp_path, monkeypatch):
    _, portfolio_cases = w8.fixtures.load_cases()
    selected = [case for case in portfolio_cases if case.case_id in {"P01", "P14", "P16"}]
    original_metrics = w8._portfolio_metrics

    def fail_missing_data_case(case, artifact, persisted):
        if case.case_id == "P16":
            raise ValueError("injected Portfolio scoring failure")
        return original_metrics(case, artifact, persisted)

    monkeypatch.setattr(w8, "_portfolio_metrics", fail_missing_data_case)
    output = tmp_path / "portfolio-scoring-error"
    engine, _ = database(tmp_path / "portfolio-scoring-error.sqlite3")
    try:
        summary = w8.run_domain("portfolio", ("full",), selected, output, verbose=False)
    finally:
        engine.dispose()
    rows = [w8.json.loads(line) for line in (output / "portfolio-full.jsonl").read_text().splitlines()]
    aggregate = summary["portfolio:full"]["metrics"]
    status = aggregate["status_accuracy_on_input_determined_cases"]
    expected_eligible = sum(w8._portfolio_gold_eligibility(case.gold)["status_metric_eligible"]
                            for case in selected)

    assert rows[2]["evaluation_status"] == "evaluation_error"
    assert rows[2]["run_status"] == "completed" and rows[2]["actual_workflow_executed"] is True
    assert status["denominator"] == expected_eligible == 2
    assert status["unscored_eligible_cases"] == 1
    assert status["failure_policy"].startswith("unscored eligible rows receive zero credit")
    assert aggregate["metric_scoring_coverage"]["scored_case_count"] == 2
    assert aggregate["metric_scoring_coverage"]["unscored_case_count"] == 1
