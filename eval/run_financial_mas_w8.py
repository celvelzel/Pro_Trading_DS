"""Execute workflow-v1 fixtures through the persisted financial MAS runtime.

Only immutable synthetic fixtures and deterministic, no-network providers are
used. Results include the persisted run, invocation, tool, event, artifact and
relation records exported from an isolated SQLite database. This is runtime
conformance evidence, not an evaluation of real LLM or market-data quality.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from db.base import Base
from db.models import AgentEvent, AgentRun, Conversation, FinancialArtifact
from db.models.financial_mas import FinancialInvocation, FinancialRelation, FinancialRun
from db.models.agent import ToolCall, ToolResult
from agent.financial import build_financial_dispatcher
from agent.llm import ModelResponse
from agent.market_mas import SyntheticMarketModel
from agent.market_mas.driver import ROLES as MARKET_ROLES
from agent.portfolio_mas import PortfolioDependencies, SyntheticPortfolioModel
from agent.portfolio_mas.driver import PROMPTS as PORTFOLIO_PROMPTS
from agent.integration import CrossMASRequest, CrossMASRouter
from agent.shared import ArtifactStore, MarketInvestigationRequest, PortfolioReviewRequest, RunBudget
from agent.financial_demo import (DEMO_AS_OF, DEMO_SNAPSHOT_ID, demo_classifications,
    demo_histories, demo_market_dependencies, demo_snapshot_loader)

EVAL_DIR = Path(__file__).resolve().parent
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))
import financial_fixtures as fixtures


SCHEMA_VERSION = 1
PROFILE = "w8-fixture-v1"
MARKET_MODES = ("autonomous", "fixed", "single")
PORTFOLIO_MODES = ("full", "fixed", "single", "no_verifier", "no_independent_risk_critic")
PORTFOLIO_ROLES = tuple(PORTFOLIO_PROMPTS)
PORTFOLIO_COMPARATOR_LABELS = {
    "full": "full autonomous workflow",
    "fixed": "one-pass fixed specialist sequence with verifier",
    "single": "single coordinator model with deterministic tools",
    "no_verifier": "verifier ablation of the adaptive full workflow",
    "no_independent_risk_critic": "adaptive multi-agent ablation without model risk review or risk-critic verifier; deterministic risk and constraint gates retained",
}


class SyntheticSingleMarketModel(SyntheticMarketModel):
    """One-call evaluation policy that cites only evidence in its actual task."""

    async def complete(self, messages, *, request_id=None):
        response = await super().complete(messages, request_id=request_id)
        task = json.loads(messages[-1]["content"].removeprefix("<task_data>").removesuffix("</task_data>"))
        evidence = task["evidence"]
        event_evidence = [item for item in evidence if item["source_type"] != "market_tool"]
        challenged = [item for item in event_evidence if any(word in (item.get("excerpt") or "").lower()
            for word in ("rumor", "denied", "contradict", "unverified", "ignore", "instruction"))]
        # A single coordinator has no independent event specialist, but can cite
        # the exact immutable evidence it received. Keep the hypothesis explicitly
        # unverified; no fixture gold or expected score enters this response.
        cited = event_evidence or evidence
        payload = dict(response.payload)
        payload["hypotheses"] = ([{
            "explanation": "Company event association" if event_evidence else "Unknown factors",
            "support_ids": [item["id"] for item in cited if item not in challenged],
            "against_ids": [item["id"] for item in challenged],
            "disposition": "unverified",
        }] if cited else [])
        return ModelResponse.model_validate({**response.model_dump(), "payload": payload})
INDEPENDENT_STATUS_REASONS = {
    "classification_missing_or_bounded_search_inconclusive",
    "min_cash_exceeds_cash_cap",
    "insufficient_capacity_under_hard_caps",
    "missing_market_price:A",
    "missing_explicit_cash",
    "cost_basis_not_market_price:A",
    "mixed_currencies:A",
    "quote_future_or_stale:A",
    "missing_asset_history",
    "mixed_adjustment_conventions",
}
MARKET_COMPARATOR_LABELS = {
    "autonomous": "adaptive autonomous workflow",
    "fixed": "fixed specialist sequence without dynamic routing",
    "single": "single coordinator model with deterministic tools and citations from persisted task evidence",
}
MARKET_NUMERIC_FACT_GOLD_FIELDS = {
    "market.return_pct": "return_pct",
    "market.volume_ratio_20": "volume_ratio_20",
    "market.excess_return_pct": "market_excess_return_pct",
    "market.relative_strength": "market_relative_strength",
    "sector.excess_return_pct": "sector_excess_return_pct",
    "sector.relative_strength": "sector_relative_strength",
}
INFEASIBLE_STATUS_REASONS = {
    "min_cash_exceeds_cash_cap",
    "insufficient_capacity_under_hard_caps",
}
TERMINAL = {"completed", "failed", "cancelled", "expired"}


def _json(value):
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    return value


def _json_line(value):
    return json.dumps(_json(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value) -> str:
    return hashlib.sha256(_json_line(value).encode("utf-8")).hexdigest()


def _file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _number(value):
    text = str(value)
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        return float(Decimal(numerator) / Decimal(denominator))
    return float(Decimal(text))


def _model_row(row, names):
    return {name: _json(getattr(row, name)) for name in names}


def _persisted_run(session_factory, run_id):
    with session_factory() as session:
        run = session.get(AgentRun, run_id)
        meta = session.get(FinancialRun, run_id)
        calls = session.scalars(select(ToolCall).where(ToolCall.run_id == run_id)
                                .order_by(ToolCall.created_at, ToolCall.id)).all()
        call_ids = [call.id for call in calls]
        results = (session.scalars(select(ToolResult).where(ToolResult.tool_call_id.in_(call_ids))
                                   .order_by(ToolResult.created_at, ToolResult.id)).all()
                   if call_ids else [])
        invocations = session.scalars(select(FinancialInvocation).where(
            FinancialInvocation.run_id == run_id).order_by(FinancialInvocation.id)).all()
        events = session.scalars(select(AgentEvent).where(AgentEvent.run_id == run_id)
                                 .order_by(AgentEvent.seq)).all()
        artifacts = session.scalars(select(FinancialArtifact).where(
            FinancialArtifact.run_id == run_id).order_by(FinancialArtifact.id)).all()
        relations = session.scalars(select(FinancialRelation).where(
            (FinancialRelation.source_run_id == run_id) |
            (FinancialRelation.target_run_id == run_id)).order_by(FinancialRelation.id)).all()
        if run is None or meta is None:
            raise RuntimeError("created run was not persisted")
        return {
            "run": _model_row(run, ("id", "conversation_id", "parent_run_id", "status", "mode",
                "goal", "version", "model_calls", "tool_calls", "checkpoint", "final_answer", "error_code")),
            "financial_run": _model_row(meta, ("run_id", "conversation_id", "mas_kind", "correlation_id",
                "request", "creation_inputs", "budget", "checkpoint", "active_seconds")),
            "invocations": [_model_row(row, ("id", "run_id", "invocation_key", "role", "kind",
                "input_hash", "status", "attempts", "output", "error_code", "tool_call_id"))
                for row in invocations],
            "tool_calls": [_model_row(row, ("id", "call_id", "run_id", "tool_name", "tool_version",
                "status", "input_data", "error_code", "request_id")) for row in calls],
            "tool_results": [_model_row(row, ("id", "result_id", "tool_call_id", "data", "citations",
                "summary", "duration_ms", "cached")) for row in results],
            "events": [_model_row(row, ("id", "event_id", "run_id", "seq", "schema_version",
                "event_type", "payload")) for row in events],
            "artifacts": [_model_row(row, ("id", "run_id", "conversation_id", "artifact_key",
                "mas_kind", "schema_version", "as_of", "symbols", "content_hash", "payload"))
                for row in artifacts],
            "relations": [_model_row(row, ("id", "conversation_id", "source_run_id", "target_run_id",
                "correlation_id", "relation_type", "idempotency_key", "envelope")) for row in relations],
        }


def _tool_results_by_name(persisted):
    calls = {call["id"]: call for call in persisted["tool_calls"]}
    result = {}
    for row in persisted["tool_results"]:
        call = calls.get(row["tool_call_id"])
        if call:
            result.setdefault(call["tool_name"], []).append((call, row))
    return result


def _market_metrics(case, artifact, persisted):
    tools = _tool_results_by_name(persisted)
    event_outputs = [result["data"] for _, result in tools.get("get_event_evidence", [])
                     if isinstance(result.get("data"), dict)]
    observed_event_ids = {event.get("id") for output in event_outputs
                          for event in output.get("evidence", []) if event.get("id")}
    actual_event_count = len(observed_event_ids) if event_outputs else None
    event_count_correct = (actual_event_count == case.gold["eligible_count"]
                           if actual_event_count is not None else False)

    fact_values = {fact.get("name"): fact.get("value") for fact in (artifact or {}).get("numeric_facts", [])}
    numeric_matches = 0
    numeric_expected = 0
    for fact_name, gold_name in MARKET_NUMERIC_FACT_GOLD_FIELDS.items():
        if gold_name not in case.gold:
            continue
        numeric_expected += 1
        actual = fact_values.get(fact_name)
        if actual is not None and math.isclose(float(actual), _number(case.gold[gold_name]), rel_tol=0, abs_tol=1e-9):
            numeric_matches += 1

    persisted_valid_refs = set()
    for output in event_outputs:
        persisted_valid_refs.update(event.get("id") for event in output.get("evidence", []) if event.get("id"))
        if output.get("result_ref"):
            persisted_valid_refs.add(output["result_ref"])
    for tool_name in ("get_market_history", "calculate_market_anomaly"):
        for _, row in tools.get(tool_name, []):
            data = row.get("data") or {}
            if data.get("result_ref"):
                persisted_valid_refs.add(data["result_ref"])
    persisted_result_ids = {row.get("id") for row in persisted["tool_results"]}
    persisted_result_ids.update(row.get("result_id") for row in persisted["tool_results"])
    citation_ids = []
    for hypothesis in (artifact or {}).get("hypotheses", []):
        citation_ids.extend(hypothesis.get("support_ids", []))
        citation_ids.extend(hypothesis.get("against_ids", []))
    precision_numerator = sum(ref in persisted_valid_refs for ref in citation_ids)
    precision_denominator = len(citation_ids)
    evidence_refs = [evidence.get("id") for evidence in (artifact or {}).get("evidence", [])
                     if evidence.get("id")]
    evidence_ref_numerator = sum(ref in persisted_valid_refs for ref in evidence_refs)
    numeric_facts = (artifact or {}).get("numeric_facts", [])
    numeric_provenance_numerator = sum(fact.get("evidence_id") in persisted_valid_refs
        and fact.get("tool_result_id") in persisted_result_ids for fact in numeric_facts)

    source_events = {event.id: event for event in case.events}
    event_citations = set(ref for ref in citation_ids if ref in source_events)
    as_of = case.request.as_of
    timing_violations = sum(
        source_events[ref].published_at is None or source_events[ref].available_at is None
        or source_events[ref].published_at > as_of or source_events[ref].available_at > as_of
        for ref in event_citations)
    hypotheses = (artifact or {}).get("hypotheses", [])
    event_association_supported = sum(hypothesis.get("explanation") == "Company event association"
        and hypothesis.get("disposition") == "supported" for hypothesis in hypotheses)
    status = (artifact or {}).get("status")
    expected_status = case.gold.get("status")
    return {
        "artifact_status": status,
        "gold_status": expected_status,
        "status_correct": status == expected_status,
        "eligible_event_count": {"actual": actual_event_count, "expected": case.gold["eligible_count"],
                                  "correct": event_count_correct},
        "evidence_citation_precision": {"numerator": precision_numerator,
                                        "denominator": precision_denominator,
                                        "value": precision_numerator / precision_denominator
                                        if precision_denominator else None},
        "artifact_evidence_provenance": {"numerator": evidence_ref_numerator,
            "denominator": len(evidence_refs), "value": evidence_ref_numerator / len(evidence_refs)
            if evidence_refs else None},
        "numeric_fact_provenance": {"numerator": numeric_provenance_numerator,
            "denominator": len(numeric_facts), "value": numeric_provenance_numerator / len(numeric_facts)
            if numeric_facts else None},
        "timing_violation_count": timing_violations,
        "timing_violation_denominator": len(event_citations),
        "unsupported_causal_claims": {"scorable": False, "count": None, "denominator": 0,
            "reason": "Not applicable to MarketInvestigationArtifact v1 structured output: hypotheses are potential contributing factors, not causal assertions; retain historical unscored values."},
        "event_association_supported_disposition_count": event_association_supported,
        "numeric_fact_accuracy": {"numerator": numeric_matches, "denominator": numeric_expected,
                                  "value": numeric_matches / numeric_expected if numeric_expected else None},
        "partial_result_correct": status == expected_status,
        "causal_gold_requires_verified_claim": case.gold.get("causal_claim_verified", False),
    }


def _reference_risk(weights, histories):
    """Independent direct calculation for constant-weight fixture risk outputs."""
    normalized = {str(symbol).upper(): Decimal(str(weight)) for symbol, weight in weights.items()}
    total_weight = sum(normalized.values(), Decimal(0))
    if total_weight <= 0:
        return None
    normalized = {symbol: weight / total_weight for symbol, weight in normalized.items()}
    active = sorted(symbol for symbol, weight in normalized.items()
                    if symbol != "CASH" and weight > 0)
    if not active:
        return {"volatility": 0.0, "maximum_drawdown": 0.0,
                "concentration": 0.0, "cash_weight": float(normalized.get("CASH", 0))}
    by_symbol = {history["symbol"]: {bar["date"]: Decimal(str(bar["price"]))
                 for bar in history["bars"]} for history in histories}
    if any(symbol not in by_symbol for symbol in active):
        return None
    common = sorted(set.intersection(*(set(by_symbol[symbol]) for symbol in active)))
    if len(common) < 2:
        return None
    returns = []
    for index in range(1, len(common)):
        daily = Decimal(0)
        for symbol in active:
            daily += normalized[symbol] * (
                by_symbol[symbol][common[index]] / by_symbol[symbol][common[index - 1]] - 1)
        returns.append(float(daily))
    volatility = statistics.stdev(returns) * math.sqrt(252) if len(returns) >= 2 else None
    nav = peak = 1.0
    drawdown = 0.0
    for daily in returns:
        nav *= 1 + daily
        peak = max(peak, nav)
        drawdown = max(drawdown, 1 - nav / peak)
    return {"volatility": volatility, "maximum_drawdown": drawdown,
            "concentration": float(max(normalized[symbol] for symbol in active)),
            "cash_weight": float(normalized.get("CASH", 0))}


def _snapshot_weights(case):
    record = case.snapshot
    if record.cash is None or record.currency is None:
        return None
    quotes = {quote.symbol: quote for quote in record.quotes}
    market_values = {}
    for holding in record.holdings:
        quote = quotes.get(holding.symbol)
        if quote is None or quote.price is None:
            return None
        market_values[holding.symbol] = holding.quantity * quote.price
    total = sum(market_values.values(), Decimal(0)) + record.cash
    if total <= 0:
        return None
    return {symbol: float(value / total) for symbol, value in market_values.items()} | {
        "CASH": float(record.cash / total)}


def _risk_metrics(case, artifact):
    gold = case.gold
    histories = [history.model_dump(mode="json") for history in case.histories]
    actual_comparison = (artifact or {}).get("risk_comparison") or {}
    comparisons = {"before": _snapshot_weights(case),
                   "after": (artifact or {}).get("proposed_weights") or None}
    computable_fields = 0
    matched_fields = 0
    observed_fields = 0
    errors = []
    for side, weights in comparisons.items():
        gold_side = gold.get(side) or {}
        # Only score data-valid sides in the reviewed fixture. Missing-data
        # cases have a separate fail-closed metric and must not be penalized
        # for correctly omitting a risk calculation.
        if not gold_side:
            continue
        reference = _reference_risk(weights, histories) if weights else None
        observed = actual_comparison.get(side) or {}
        if reference is None:
            continue
        fields = {
            "volatility": "annualized_volatility",
            "maximum_drawdown": "max_drawdown",
            "concentration": "concentration",
            "cash_weight": "cash_weight",
        }
        for actual_name, gold_name in fields.items():
            # Report actual-vs-independent calculation; gold is included as an
            # additional fixture check only where a manually reviewed value exists.
            actual_value = observed.get(actual_name)
            expected_value = reference.get(actual_name)
            if expected_value is None:
                continue
            computable_fields += 1
            if actual_value is None:
                continue
            observed_fields += 1
            error = abs(float(actual_value) - float(expected_value))
            errors.append(error)
            if error <= 1e-10:
                matched_fields += 1
    return {"numerator": matched_fields, "denominator": observed_fields,
            "value": matched_fields / observed_fields if observed_fields else None,
            "computable_fields": computable_fields,
            "coverage": observed_fields / computable_fields if computable_fields else None,
            "max_absolute_error": max(errors) if errors else None}


def _simulation_consistency(persisted, artifact):
    tools = _tool_results_by_name(persisted).get("simulate_allocation", [])
    by_ref = {}
    for call, row in tools:
        data = row.get("data") or {}
        by_ref[row.get("id")] = (call, data)
        by_ref[row.get("result_id")] = (call, data)
    simulation = (artifact or {}).get("simulation") or {}
    final = by_ref.get(simulation.get("tool_result_id")) if simulation else None
    if final is None:
        return {"correct_points": 0, "total_points": 0, "value": None,
                "final_net_return_matches": False if simulation else None}
    call, output = final
    payload = call.get("input_data") or {}
    if Decimal(str(payload.get("fee_bps", 0))) != 0 or Decimal(str(payload.get("slippage_bps", 0))) != 0:
        return {"correct_points": 0, "total_points": 0, "value": None,
                "final_net_return_matches": None, "excluded_reason": "nonzero transaction cost"}
    weights = {str(symbol).upper(): Decimal(str(weight))
               for symbol, weight in (payload.get("target_weights") or {}).items()}
    weight_sum = sum(weights.values(), Decimal(0))
    if weight_sum <= 0:
        return {"correct_points": 0, "total_points": 0, "value": None,
                "final_net_return_matches": False}
    weights = {symbol: weight / weight_sum for symbol, weight in weights.items()}
    active = [symbol for symbol, weight in weights.items() if symbol != "CASH" and weight > 0]
    histories = payload.get("histories", [])
    by_symbol = {history["symbol"]: {bar["date"]: Decimal(str(bar["price"]))
                 for bar in history["bars"]} for history in histories}
    required = active or sorted(by_symbol)
    if any(symbol not in by_symbol for symbol in required):
        return {"correct_points": 0, "total_points": 0, "value": None,
                "final_net_return_matches": False}
    common = sorted(set.intersection(*(set(by_symbol[symbol]) for symbol in required)))
    if len(common) < 2:
        return {"correct_points": 0, "total_points": 0, "value": None,
                "final_net_return_matches": False}
    initial = Decimal(str(payload["initial_value"]))
    expected_values = [initial]
    with localcontext() as context:
        context.prec = 28
        for index in range(1, len(common)):
            daily_return = Decimal(0)
            for symbol in active:
                daily_return += weights[symbol] * (
                    by_symbol[symbol][common[index]] / by_symbol[symbol][common[index - 1]] - 1)
            expected_values.append(expected_values[-1] * (1 + daily_return))
    observed_path = output.get("path", [])
    paired = min(len(expected_values), len(observed_path))
    correct = sum(abs(expected_values[index] - Decimal(str(observed_path[index]["net_value"]))) <= Decimal("1e-16")
                  and common[index] == observed_path[index]["date"] for index in range(paired))
    expected_return = expected_values[-1] / initial - 1
    actual_return = output.get("total_return")
    artifact_return = simulation.get("net_return")
    return_matches = (actual_return is not None and artifact_return is not None
                      and abs(Decimal(str(actual_return)) - Decimal(str(artifact_return))) <= Decimal("1e-16")
                      and abs(Decimal(str(actual_return)) - expected_return) <= Decimal("1e-16"))
    return {"correct_points": correct, "total_points": len(expected_values),
            "value": correct / len(expected_values) if expected_values else None,
            "final_net_return_matches": return_matches,
            "expected_net_return": str(expected_return),
            "actual_tool_net_return": str(actual_return) if actual_return is not None else None,
            "artifact_net_return": str(artifact_return) if artifact_return is not None else None}


def _portfolio_gold_eligibility(gold):
    expected = gold.get("status")
    reason = gold.get("reason")
    expected_infeasible = reason in INFEASIBLE_STATUS_REASONS
    expected_feasible = expected == "feasible"
    expected_missing = reason in INDEPENDENT_STATUS_REASONS and not expected_infeasible
    return {
        "status_metric_eligible": expected_infeasible or expected_missing,
        "infeasibility_detection_eligible": expected_infeasible or expected_feasible,
        "gold_infeasible": expected_infeasible,
        "gold_feasible": expected_feasible,
        "missing_data_safety_eligible": expected_missing,
    }


def _portfolio_metrics(case, artifact, persisted):
    status = (artifact or {}).get("status")
    expected = case.gold.get("status")
    eligibility = _portfolio_gold_eligibility(case.gold)
    expected_infeasible = eligibility["gold_infeasible"]
    expected_feasible = eligibility["gold_feasible"]
    expected_missing = eligibility["missing_data_safety_eligible"]
    predicted_infeasible = status == "infeasible"
    predicted_safe_missing = status != "feasible"
    check = (artifact or {}).get("constraint_check") or {}
    unsafe_feasible = status == "feasible" and check.get("status") != "pass"
    return {
        "artifact_status": status,
        "gold_status": expected,
        "status_metric_eligible": eligibility["status_metric_eligible"],
        "status_correct": status == expected if eligibility["status_metric_eligible"] else None,
        "hard_constraint_violation": unsafe_feasible,
        "infeasibility_detection": {"true_positive": expected_infeasible and predicted_infeasible,
            "false_positive": expected_feasible and predicted_infeasible,
            "false_negative": expected_infeasible and not predicted_infeasible,
            "eligible": eligibility["infeasibility_detection_eligible"],
            "gold_positive": expected_infeasible,
            "gold_negative": expected_feasible},
        "missing_data_safety": {"safe": predicted_safe_missing,
            "unsafe_feasible_declaration": expected_missing and not predicted_safe_missing,
            "eligible": expected_missing},
        "risk_calculation_accuracy": _risk_metrics(case, artifact),
        "simulation_net_value_consistency": _simulation_consistency(persisted, artifact),
    }


def _new_dispatcher(session_factory, case, domain, mode):
    if domain == "market":
        history, events = fixtures.market_dependencies(case)
        models = {role: SyntheticMarketModel(role) for role in MARKET_ROLES}
        if mode == "single":
            models["coordinator"] = SyntheticSingleMarketModel("coordinator")
        kwargs = {
            "enabled": ("market_investigation",),
            "providers": {"market_investigation": models},
            "market_dependencies": history,
            "event_dependencies": events,
            "market_mode": mode,
            "portfolio_mode": "full",
        }
    else:
        if case.snapshot.snapshot_kind != "demo":
            raise ValueError("W8 portfolio runner accepts synthetic demo snapshots only")

        def snapshot_loader(snapshot_id):
            if snapshot_id != case.request.portfolio_snapshot_id:
                return None
            return case.snapshot.model_copy(deep=True)

        def history_loader(snapshot, as_of):
            if snapshot.snapshot_id != case.request.portfolio_snapshot_id or as_of != case.request.as_of:
                return ()
            return tuple(history.model_copy(deep=True) for history in case.histories)

        dependencies = PortfolioDependencies(snapshot_loader, history_loader, case.classifications)
        models = {role: SyntheticPortfolioModel(role) for role in PORTFOLIO_ROLES}
        kwargs = {
            "enabled": ("portfolio_rebalance",),
            "providers": {"portfolio_rebalance": models},
            "portfolio_dependencies": dependencies,
            "market_mode": "autonomous",
            "portfolio_mode": mode,
        }
    return build_financial_dispatcher(session_factory, demo=False,
        execution_profile=PROFILE, **kwargs)


def _budget_counters(budget):
    return {
        "model_calls": budget.get("model_calls", 0),
        "tool_calls": budget.get("tool_calls", 0),
        "rounds": budget.get("rounds", 0),
        "limits": {key: budget.get(key) for key in ("max_model_calls", "max_tool_calls",
            "max_rounds", "max_active_seconds", "max_hops", "max_followups")},
        "persisted_model_invocations": 0,
        "persisted_tool_invocations": 0,
        "persisted_tool_calls": 0,
        "persisted_tool_results": 0,
        "events": 0,
        "artifacts": 0,
        "relations": 0,
        "token_usage": None,
    }


def _run_one(case, domain, mode, session_factory, execution_context=None):
    context = execution_context if execution_context is not None else {}
    context.update({
        "actual_workflow_executed": False,
        "failure_stage": "pre_execution",
        "run_id": None,
        "conversation_id": None,
        "run_status": None,
        "run_error_code": None,
        "wall_ms": None,
        "run_budget": {},
        "counters": _budget_counters({}),
        "actual_artifact": None,
        "persisted": {},
    })
    dispatcher = _new_dispatcher(session_factory, case, domain, mode)
    context["_dispatcher"] = dispatcher
    if any(not tool.read_only or tool.side_effect for tool in dispatcher.tools.list()):
        raise RuntimeError("evaluation runner refuses a non-read-only financial tool")
    conversation_id = str(uuid.uuid4())
    with session_factory() as session:
        session.add(Conversation(id=conversation_id, title=f"W8 {domain} {case.case_id}"))
        session.commit()
    context["conversation_id"] = conversation_id
    request = case.request
    run = dispatcher.create(conversation_id, request, mode="auto",
        idempotency_key=f"w8:{domain}:{mode}:{case.case_id}",
        correlation_id=f"w8:{domain}:{mode}:{case.case_id}", budget=RunBudget())
    context.update({"actual_workflow_executed": True, "failure_stage": "execution_capture",
        "run_id": run.id, "conversation_id": conversation_id,
        "run_status": run.status, "run_error_code": run.error_code})
    initial_snapshot = dispatcher.snapshot(run.id)
    context.update({"failure_stage": "runtime",
        "run_budget": initial_snapshot.get("budget", {}),
        "counters": _budget_counters(initial_snapshot.get("budget", {}))})
    started = time.perf_counter_ns()
    completed = None
    try:
        for _ in range(8):
            try:
                completed = asyncio.run(dispatcher.start(run.id))
            except Exception:
                snapshot = dispatcher.snapshot(run.id)
                context["run_status"] = snapshot.get("status", context.get("run_status"))
                context["run_error_code"] = snapshot.get("error_code")
                context["run_budget"] = snapshot.get("budget", context.get("run_budget", {}))
                context["counters"] = _budget_counters(context["run_budget"])
                context["failure_stage"] = "runtime"
                raise
            context["run_status"] = completed.status
            context["run_error_code"] = completed.error_code
            context["failure_stage"] = "execution_capture"
            snapshot = dispatcher.snapshot(run.id)
            context["run_budget"] = snapshot.get("budget", {})
            context["counters"] = _budget_counters(context["run_budget"])
            context["failure_stage"] = "runtime"
            if completed.status in TERMINAL:
                break
    finally:
        wall_ms = (time.perf_counter_ns() - started) / 1_000_000
        context["wall_ms"] = wall_ms
    if completed is None or completed.status not in TERMINAL:
        raise RuntimeError("bounded runtime did not reach a terminal status")
    context["failure_stage"] = "execution_capture"
    persisted = _persisted_run(session_factory, run.id)
    answer = completed.final_answer
    try:
        artifact = json.loads(answer) if answer else None
    except (TypeError, json.JSONDecodeError):
        artifact = None
    budget = persisted["financial_run"]["budget"]
    invocations = persisted["invocations"]
    tools = persisted["tool_calls"]
    counters = _budget_counters(budget)
    counters.update({
        "persisted_model_invocations": sum(row["kind"] == "model" for row in invocations),
        "persisted_tool_invocations": sum(row["kind"] == "tool" for row in invocations),
        "persisted_tool_calls": len(tools),
        "persisted_tool_results": len(persisted["tool_results"]),
        "events": len(persisted["events"]),
        "artifacts": len(persisted["artifacts"]),
        "relations": len(persisted["relations"]),
    })
    raw = {
        "schema_version": SCHEMA_VERSION,
        "suite": "financial-mas-workflow-v1",
        "profile": PROFILE,
        "domain": domain,
        "strategy": mode,
        "comparator": (MARKET_COMPARATOR_LABELS if domain == "market" else PORTFOLIO_COMPARATOR_LABELS)[mode],
        "case_id": case.case_id,
        "case_name": case.name,
        "synthetic_fixture": True,
        "fixture_adapter_sha256": case.adapter_sha256,
        "source_case_sha256": case.source_case_sha256,
        "request": request.model_dump(mode="json"),
        "expected_gold": case.gold,
        "actual_workflow_executed": True,
        "run_status": completed.status,
        "run_error_code": completed.error_code,
        "run_id": run.id,
        "conversation_id": conversation_id,
        "run_budget": budget,
        "wall_ms": wall_ms,
        "counters": counters,
        "actual_artifact": artifact,
        "gold_metric_eligibility": (_portfolio_gold_eligibility(case.gold)
            if domain == "portfolio" else {}),
        "failure_stage": "scoring",
        "evaluation_status": "pending",
        "evaluation_error": None,
        "metrics": {},
        "persisted": persisted,
    }
    context.update(raw)
    context["failure_stage"] = "scoring"
    try:
        raw["metrics"] = (_market_metrics(case, artifact, persisted) if domain == "market"
                           else _portfolio_metrics(case, artifact, persisted))
        raw["evaluation_status"] = "scored"
        raw["failure_stage"] = None
        context["failure_stage"] = None
    except Exception as exc:  # Preserve completed execution evidence when scoring fails.
        raw["evaluation_status"] = "evaluation_error"
        raw["failure_stage"] = "scoring"
        raw["evaluation_error"] = {"type": type(exc).__name__, "message": str(exc)}
        context.update(raw)
    return raw


def _metric_scoring_coverage(rows):
    cases = len(rows)
    scored = sum(row.get("evaluation_status") == "scored" for row in rows)
    evaluation_errors = sum(row.get("evaluation_status") == "evaluation_error" for row in rows)
    harness_errors = sum(row.get("run_status") == "harness_error" for row in rows)
    return {
        "case_count": cases,
        "scored_case_count": scored,
        "unscored_case_count": cases - scored,
        "scored_fraction": scored / cases if cases else None,
        "evaluation_error_count": evaluation_errors,
        "harness_error_count": harness_errors,
    }


def _mark_metrics_unscorable(metrics, metric_names, coverage):
    if not coverage["unscored_case_count"]:
        return
    for name in metric_names:
        metric = metrics.get(name)
        if not isinstance(metric, dict) or metric.get("scorable") is False:
            continue
        if "value" in metric:
            metric["scored_subset_value"] = metric["value"]
            metric["value"] = None
        metric.update({
            "scorable": False,
            "scored_case_count": coverage["scored_case_count"],
            "unscored_case_count": coverage["unscored_case_count"],
            "reason": "One or more fixture rows have no complete metric scoring; see metric_scoring_coverage.",
        })


def _aggregate(rows, domain):
    cases = len(rows)
    scoring_coverage = _metric_scoring_coverage(rows)
    wall = [float(row["wall_ms"]) for row in rows if row.get("wall_ms") is not None]
    counter_names = ("model_calls", "tool_calls", "rounds", "persisted_model_invocations",
                     "persisted_tool_invocations", "persisted_tool_results")
    totals = {name: sum(int(row["counters"].get(name, 0)) for row in rows) for name in counter_names}
    base = {
        "case_count": cases,
        "terminal_completed": sum(row["run_status"] == "completed" for row in rows),
        "terminal_failed_or_other": sum(row["run_status"] != "completed" for row in rows),
        "counters_total": totals,
        "latency_ms": {"denominator": len(wall), "mean": statistics.mean(wall) if wall else None,
            "median": statistics.median(wall) if wall else None,
            "max": max(wall) if wall else None},
        "token_usage": {"available": False, "total": None},
        "metric_scoring_coverage": scoring_coverage,
    }
    if domain == "market":
        metric_rows = [row.get("metrics", {}) for row in rows]
        count_correct = sum(metric.get("eligible_event_count", {}).get("correct", False) for metric in metric_rows)
        status_correct = sum(metric.get("status_correct", False) for metric in metric_rows)
        citation_num = sum(metric.get("evidence_citation_precision", {}).get("numerator", 0) for metric in metric_rows)
        citation_den = sum(metric.get("evidence_citation_precision", {}).get("denominator", 0) for metric in metric_rows)
        artifact_ref_num = sum(metric.get("artifact_evidence_provenance", {}).get("numerator", 0) for metric in metric_rows)
        artifact_ref_den = sum(metric.get("artifact_evidence_provenance", {}).get("denominator", 0) for metric in metric_rows)
        fact_ref_num = sum(metric.get("numeric_fact_provenance", {}).get("numerator", 0) for metric in metric_rows)
        fact_ref_den = sum(metric.get("numeric_fact_provenance", {}).get("denominator", 0) for metric in metric_rows)
        numeric_num = sum(metric.get("numeric_fact_accuracy", {}).get("numerator", 0) for metric in metric_rows)
        numeric_den = sum(sum(gold_field in row.get("expected_gold", {})
            for gold_field in MARKET_NUMERIC_FACT_GOLD_FIELDS.values()) for row in rows)
        result = base | {"event_eligible_count_accuracy": {"numerator": count_correct,
                "denominator": cases, "value": count_correct / cases if cases else None},
            "artifact_status_accuracy": {"numerator": status_correct, "denominator": cases,
                "value": status_correct / cases if cases else None},
            "evidence_citation_precision": {"numerator": citation_num, "denominator": citation_den,
                "value": citation_num / citation_den if citation_den else None},
            "artifact_evidence_provenance": {"numerator": artifact_ref_num, "denominator": artifact_ref_den,
                "value": artifact_ref_num / artifact_ref_den if artifact_ref_den else None},
            "numeric_fact_provenance": {"numerator": fact_ref_num, "denominator": fact_ref_den,
                "value": fact_ref_num / fact_ref_den if fact_ref_den else None},
            "timing_violations": {"count": sum(metric.get("timing_violation_count", 0) for metric in metric_rows),
                "denominator": sum(metric.get("timing_violation_denominator", 0) for metric in metric_rows)},
            "unsupported_causal_claims": {"scorable": False, "count": None, "denominator": 0,
                "reason": "Not applicable to MarketInvestigationArtifact v1 structured output; do not infer causality from hypothesis disposition or report the unscored count as zero."},
            "event_association_supported_disposition_count": sum(metric.get("event_association_supported_disposition_count", 0)
                for metric in metric_rows),
            "numeric_fact_accuracy": {"numerator": numeric_num, "denominator": numeric_den,
                "value": numeric_num / numeric_den if numeric_den else None,
                "failure_policy": "unscored case facts receive zero credit against fixture-derived gold denominator",
                "scored_case_count": scoring_coverage["scored_case_count"],
                "unscored_case_count": scoring_coverage["unscored_case_count"]},
            "partial_result_correctness": {"numerator": status_correct, "denominator": cases,
                "value": status_correct / cases if cases else None}}
        result["event_eligible_count_accuracy"].update({
            "failure_policy": "unscored case rows receive zero credit against the full fixture denominator",
            "scored_case_count": scoring_coverage["scored_case_count"],
            "unscored_case_count": scoring_coverage["unscored_case_count"],
        })
        result["artifact_status_accuracy"].update({
            "failure_policy": "unscored case rows receive zero credit against the full fixture denominator",
            "scored_case_count": scoring_coverage["scored_case_count"],
            "unscored_case_count": scoring_coverage["unscored_case_count"],
        })
        result["partial_result_correctness"].update({
            "failure_policy": "unscored case rows receive zero credit against the full fixture denominator",
            "scored_case_count": scoring_coverage["scored_case_count"],
            "unscored_case_count": scoring_coverage["unscored_case_count"],
        })
        _mark_metrics_unscorable(result, (
            "evidence_citation_precision", "artifact_evidence_provenance",
            "numeric_fact_provenance", "timing_violations",
            "event_association_supported_disposition_count",
        ), scoring_coverage)
        return result

    metric_rows = [row.get("metrics", {}) for row in rows]
    status_rows = [row for row in rows
                   if row.get("gold_metric_eligibility", {}).get("status_metric_eligible")]
    status_correct = sum(row.get("metrics", {}).get("status_correct") is True for row in status_rows)
    infeasible_rows = [row for row in rows
                       if row.get("gold_metric_eligibility", {}).get("infeasibility_detection_eligible")]
    missing_rows = [row for row in rows
                    if row.get("gold_metric_eligibility", {}).get("missing_data_safety_eligible")]
    risk_num = sum(metric.get("risk_calculation_accuracy", {}).get("numerator", 0) for metric in metric_rows)
    risk_den = sum(metric.get("risk_calculation_accuracy", {}).get("denominator", 0) for metric in metric_rows)
    risk_computable = sum(metric.get("risk_calculation_accuracy", {}).get("computable_fields", 0) for metric in metric_rows)
    sim_num = sum(metric.get("simulation_net_value_consistency", {}).get("correct_points", 0) for metric in metric_rows)
    sim_den = sum(metric.get("simulation_net_value_consistency", {}).get("total_points", 0) for metric in metric_rows)
    result = base | {
        "status_accuracy_on_input_determined_cases": {"numerator": status_correct,
            "denominator": len(status_rows), "value": status_correct / len(status_rows) if status_rows else None,
            "failure_policy": "unscored eligible rows receive zero credit against the fixture-derived denominator",
            "unscored_eligible_cases": sum(row.get("evaluation_status") != "scored" for row in status_rows)},
        "hard_constraint_violation_safety": {"unsafe_feasible_declarations": sum(
            metric.get("hard_constraint_violation", False) for metric in metric_rows), "denominator": cases},
        "infeasibility_detection": {"true_positive": sum(metric.get("infeasibility_detection", {}).get("true_positive", False) for metric in metric_rows),
            "false_positive": sum(metric.get("infeasibility_detection", {}).get("false_positive", False) for metric in metric_rows),
            "false_negative": sum(metric.get("infeasibility_detection", {}).get("false_negative", False) for metric in metric_rows),
            "gold_positive_denominator": sum(row.get("gold_metric_eligibility", {}).get("gold_infeasible", False)
                for row in infeasible_rows),
            "gold_negative_denominator": sum(row.get("gold_metric_eligibility", {}).get("gold_feasible", False)
                for row in infeasible_rows)},
        "missing_data_safety": {"safe": sum(row.get("metrics", {}).get("missing_data_safety", {}).get("safe", False) for row in missing_rows),
            "unsafe_feasible_declarations": sum(row.get("metrics", {}).get("missing_data_safety", {}).get("unsafe_feasible_declaration", False) for row in rows),
            "denominator": len(missing_rows), "value": sum(row.get("metrics", {}).get("missing_data_safety", {}).get("safe", False)
                for row in missing_rows) / len(missing_rows) if missing_rows else None},
        "risk_calculation_accuracy": {"numerator": risk_num, "denominator": risk_den,
            "value": risk_num / risk_den if risk_den else None,
            "computable_fields": risk_computable,
            "coverage": risk_den / risk_computable if risk_computable else None,
            "max_absolute_error": max((metric.get("risk_calculation_accuracy", {}).get("max_absolute_error") or 0
                for metric in metric_rows), default=0)},
        "simulation_net_value_consistency": {"numerator": sim_num, "denominator": sim_den,
            "value": sim_num / sim_den if sim_den else None,
            "final_net_return_matches": sum(bool(metric.get("simulation_net_value_consistency", {}).get("final_net_return_matches"))
                for metric in metric_rows if metric.get("simulation_net_value_consistency", {}).get("final_net_return_matches") is not None),
            "runs_with_final_simulation": sum(metric.get("simulation_net_value_consistency", {}).get("final_net_return_matches") is not None
                for metric in metric_rows),
            "feasible_artifacts": sum((row.get("actual_artifact") or {}).get("status") == "feasible" for row in rows),
            "feasible_artifacts_with_simulation": sum((row.get("actual_artifact") or {}).get("status") == "feasible"
                and bool((row.get("actual_artifact") or {}).get("simulation")) for row in rows)},
    }
    result["status_accuracy_on_input_determined_cases"].update({
        "scored_eligible_cases": sum(row.get("evaluation_status") == "scored" for row in status_rows),
        "scorable": True,
    })
    result["missing_data_safety"].update({
        "failure_policy": "unscored eligible rows receive zero credit against the fixture-derived denominator",
        "unscored_eligible_cases": sum(row.get("evaluation_status") != "scored" for row in missing_rows),
        "scorable": True,
    })
    _mark_metrics_unscorable(result, (
        "hard_constraint_violation_safety", "infeasibility_detection",
        "risk_calculation_accuracy", "simulation_net_value_consistency",
    ), scoring_coverage)
    return result


def run_domain(domain, modes, cases, output_dir, verbose=True):
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = {}
    with tempfile.TemporaryDirectory(prefix=f"w8-{domain}-") as scratch:
        db_path = Path(scratch) / "financial-mas.sqlite3"
        engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        sessions = sessionmaker(engine, expire_on_commit=False)
        try:
            for mode in modes:
                rows = []
                for index, case in enumerate(cases, start=1):
                    execution_context = {}
                    try:
                        row = _run_one(case, domain, mode, sessions, execution_context)
                    except Exception as exc:  # Preserve the failure as an explicit row; never drop a case.
                        persisted = execution_context.get("persisted") or {}
                        run_id = execution_context.get("run_id")
                        dispatcher = execution_context.get("_dispatcher")
                        if run_id and dispatcher:
                            try:
                                snapshot = dispatcher.snapshot(run_id)
                                execution_context["run_status"] = snapshot.get("status",
                                    execution_context.get("run_status"))
                                execution_context["run_error_code"] = snapshot.get("error_code")
                                execution_context["run_budget"] = snapshot.get("budget",
                                    execution_context.get("run_budget", {}))
                                execution_context["counters"] = _budget_counters(
                                    execution_context["run_budget"])
                            except Exception:
                                pass
                        if run_id and not persisted:
                            try:
                                persisted = _persisted_run(sessions, run_id)
                            except Exception:
                                persisted = {}
                        counters = dict(execution_context.get("counters") or _budget_counters({}))
                        if persisted:
                            budget = (persisted.get("financial_run") or {}).get("budget") or {}
                            if budget:
                                execution_context["run_budget"] = budget
                                counters.update(_budget_counters(budget))
                            persisted_run = persisted.get("run") or {}
                            execution_context["run_status"] = persisted_run.get("status",
                                execution_context.get("run_status"))
                            execution_context["run_error_code"] = persisted_run.get("error_code")
                            counters.update({
                                "persisted_model_invocations": sum(row["kind"] == "model" for row in persisted["invocations"]),
                                "persisted_tool_invocations": sum(row["kind"] == "tool" for row in persisted["invocations"]),
                                "persisted_tool_calls": len(persisted["tool_calls"]),
                                "persisted_tool_results": len(persisted["tool_results"]),
                                "events": len(persisted["events"]),
                                "artifacts": len(persisted["artifacts"]),
                                "relations": len(persisted["relations"]),
                            })
                        actual_artifact = execution_context.get("actual_artifact")
                        if actual_artifact is None and persisted:
                            answer = (persisted.get("run") or {}).get("final_answer")
                            try:
                                actual_artifact = json.loads(answer) if answer else None
                            except (TypeError, json.JSONDecodeError):
                                actual_artifact = None
                        row_status = execution_context.get("run_status") or "harness_error"
                        failure_stage = (execution_context.get("failure_stage")
                            or ("execution_capture" if run_id else "pre_execution"))
                        runner_error = {"type": type(exc).__name__, "message": str(exc)}
                        row = {"schema_version": SCHEMA_VERSION, "suite": "financial-mas-workflow-v1",
                            "profile": PROFILE, "domain": domain, "strategy": mode,
                            "comparator": (MARKET_COMPARATOR_LABELS if domain == "market" else PORTFOLIO_COMPARATOR_LABELS)[mode],
                            "case_id": case.case_id, "case_name": case.name,
                            "synthetic_fixture": True, "fixture_adapter_sha256": case.adapter_sha256,
                            "source_case_sha256": case.source_case_sha256,
                            "request": case.request.model_dump(mode="json"), "expected_gold": case.gold,
                            "gold_metric_eligibility": (_portfolio_gold_eligibility(case.gold)
                                if domain == "portfolio" else {}),
                            "actual_workflow_executed": bool(execution_context.get("actual_workflow_executed")),
                            "run_status": row_status,
                            "failure_stage": failure_stage,
                            "evaluation_status": "unscored",
                            "evaluation_error": None,
                            "run_error_code": execution_context.get("run_error_code"),
                            "capture_error": runner_error if failure_stage == "execution_capture" else None,
                            "execution_error": runner_error if failure_stage != "execution_capture" else None,
                            "conversation_id": execution_context.get("conversation_id"),
                            "run_id": run_id, "run_budget": execution_context.get("run_budget", {}),
                            "wall_ms": execution_context.get("wall_ms"), "counters": counters,
                            "actual_artifact": actual_artifact, "metrics": {}, "persisted": persisted}
                    rows.append(row)
                    if verbose:
                        print(f"{domain}/{mode}: {index}/{len(cases)} {case.case_id} "
                              f"{row['run_status']} in {row['wall_ms'] if row['wall_ms'] is not None else 'n/a'} ms")
                raw_path = output_dir / f"{domain}-{mode}.jsonl"
                raw_path.write_text("\n".join(_json_line(row) for row in rows) + "\n", encoding="utf-8")
                summaries[f"{domain}:{mode}"] = {"comparator": (MARKET_COMPARATOR_LABELS if domain == "market" else PORTFOLIO_COMPARATOR_LABELS)[mode],
                    "raw_results": raw_path.name, "metrics": _aggregate(rows, domain)}
        finally:
            engine.dispose()
    return summaries


def run_combined_smoke(output_dir, verbose=True):
    """Run a separate W7 Combined smoke using only accepted synthetic adapters."""
    fixture_path = Path(__file__).parent / "fixtures" / "combined" / "synthetic_demo_v1.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("schema_version") != 1 or fixture.get("synthetic_only") is not True:
        raise ValueError("Unsupported Combined smoke fixture")
    if (fixture["portfolio"]["snapshot_id"] != DEMO_SNAPSHOT_ID
            or fixture["market"]["as_of"] != DEMO_AS_OF.isoformat().replace("+00:00", "Z")
            or fixture["portfolio"]["as_of"] != fixture["market"]["as_of"]
            or fixture["market"]["symbol"] != "MU"
            or fixture["market"]["sector_benchmark"] != "SOXX"):
        raise ValueError("Combined smoke fixture no longer matches the accepted W7 synthetic timepoint")
    output_dir.mkdir(parents=True, exist_ok=True)
    market_dependencies, event_dependencies = demo_market_dependencies()
    portfolio_dependencies = PortfolioDependencies(demo_snapshot_loader,
        lambda snapshot, as_of: demo_histories() if as_of == DEMO_AS_OF else (),
        demo_classifications())
    providers = {
        "market_investigation": {role: SyntheticMarketModel(role) for role in MARKET_ROLES},
        "portfolio_rebalance": {role: SyntheticPortfolioModel(role) for role in PORTFOLIO_ROLES},
    }
    with tempfile.TemporaryDirectory(prefix="w8-combined-") as scratch:
        db_path = Path(scratch) / "financial-mas.sqlite3"
        engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        sessions = sessionmaker(engine, expire_on_commit=False)
        router = None
        dispatcher = build_financial_dispatcher(sessions, demo=False, execution_profile=PROFILE,
            providers=providers, market_dependencies=market_dependencies,
            event_dependencies=event_dependencies, portfolio_dependencies=portfolio_dependencies,
            portfolio_artifact_resolver=lambda *args: router.artifact_resolver(*args))
        router = CrossMASRouter(dispatcher, ArtifactStore(sessions), demo_snapshot_loader,
            execution_profile=PROFILE)
        conversation_id = str(uuid.uuid4())
        with sessions() as session:
            session.add(Conversation(id=conversation_id, title="W8 Combined synthetic demo smoke"))
            session.commit()
        request = CrossMASRequest(conversation_id=conversation_id,
            idempotency_key="financial-mas-w8-combined-synthetic-demo-v1", mode="auto",
            market=MarketInvestigationRequest(symbol=fixture["market"]["symbol"],
                sector_benchmark=fixture["market"]["sector_benchmark"], as_of=DEMO_AS_OF),
            portfolio=PortfolioReviewRequest(portfolio_snapshot_id=DEMO_SNAPSHOT_ID,
                as_of=DEMO_AS_OF, user_constraints=fixture["portfolio"]["user_constraints"]),
            market_budget=RunBudget(), portfolio_budget=RunBudget())
        started = time.perf_counter_ns()
        pair = router.create(request)
        advanced = asyncio.run(router.advance(pair, peer_timeout=30))
        wall_ms = (time.perf_counter_ns() - started) / 1_000_000
        run_ids = [advanced.market_run_id, advanced.portfolio_run_id]
        if len(run_ids) != 2 or len(set(run_ids)) != 2:
            raise RuntimeError("Combined smoke did not create two independent MAS runs")
        persisted = {run_id: _persisted_run(sessions, run_id) for run_id in run_ids}
        snapshots = {run_id: dispatcher.snapshot(run_id) for run_id in run_ids}
        rows = []
        for kind, run_id in (("market_investigation", advanced.market_run_id),
                              ("portfolio_rebalance", advanced.portfolio_run_id)):
            details = persisted[run_id]
            budget = details["financial_run"]["budget"]
            rows.append({"mas_kind": kind, "run_id": run_id,
                "status": snapshots[run_id]["status"], "error_code": snapshots[run_id]["error_code"],
                "budget": budget,
                "model_calls_persisted": sum(row["kind"] == "model" for row in details["invocations"]),
                "tool_calls_persisted": sum(row["kind"] == "tool" for row in details["invocations"]),
                "artifact_count": len(details["artifacts"]), "relation_count": len(details["relations"]),
                "final_answer": json.loads(details["run"]["final_answer"])
                    if details["run"]["final_answer"] else None,
                "persisted": details})
        all_relations = {}
        for details in persisted.values():
            for relation in details["relations"]:
                all_relations[relation["id"]] = relation
        raw = {
            "schema_version": SCHEMA_VERSION,
            "fixture_id": fixture["fixture_id"],
            "fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
            "source_adapter_sha256": hashlib.sha256((Path(__file__).resolve().parents[1]
                / "backend/agent/financial_demo.py").read_bytes()).hexdigest(),
            "profile": PROFILE,
            "synthetic_only": True,
            "actual_workflow_executed": True,
            "public_api_used": False,
            "real_provider_used": False,
            "broker_or_order_calls": False,
            "holdings_write_calls": False,
            "conversation_id": advanced.conversation_id,
            "correlation_id": advanced.correlation_id,
            "limitations": advanced.limitations,
            "wall_ms": wall_ms,
            "run_count": len(rows),
            "distinct_run_ids": len({row["run_id"] for row in rows}),
            "run_rows": rows,
            "relations": list(all_relations.values()),
            "relation_type_counts": {relation_type: sum(relation["relation_type"] == relation_type
                for relation in all_relations.values())
                for relation_type in sorted({relation["relation_type"] for relation in all_relations.values()})},
            "combined_summary": {
                "both_terminal_completed": all(row["status"] == "completed" for row in rows),
                "combined_relation_present": any(relation["relation_type"] == "combined"
                    for relation in all_relations.values()),
                "market_evidence_admitted": any(relation["relation_type"] == "cross_admitted"
                    and relation["envelope"].get("message_type") == "MARKET_EVIDENCE_READY"
                    for relation in all_relations.values()),
                "artifacts_persisted": sum(row["artifact_count"] for row in rows),
                "independent_budget_records": len(rows),
                "token_usage": None,
            },
        }
        raw_path = output_dir / "combined-synthetic-demo-v1.jsonl"
        raw_path.write_text(_json_line(raw) + "\n", encoding="utf-8")
        engine.dispose()
    if verbose:
        print(f"combined/synthetic-demo-v1: 1/1 {raw['combined_summary']['both_terminal_completed']} "
              f"in {wall_ms:.2f} ms")
    return {"combined:synthetic-demo-v1": {
        "raw_results": raw_path.name,
        "case_count": 1,
        "run_count": raw["run_count"],
        "distinct_run_ids": raw["distinct_run_ids"],
        "relation_type_counts": raw["relation_type_counts"],
        "both_terminal_completed": raw["combined_summary"]["both_terminal_completed"],
        "artifacts_persisted": raw["combined_summary"]["artifacts_persisted"],
        "wall_ms": wall_ms,
    }}


def run(output_dir: Path, domain="all", verbose=True, invocation=None):
    manifest = fixtures.verify_manifest()
    market_cases, portfolio_cases = fixtures.load_cases()
    if len(market_cases) != 12 or len(portfolio_cases) != 30:
        raise RuntimeError("workflow-v1 fixture count changed; review before scoring")
    output_dir = output_dir.resolve()
    started_at = datetime.now(timezone.utc)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "suite": "financial-mas-workflow-v1",
        "profile": PROFILE,
        "synthetic_only": True,
        "actual_workflow_execution": True,
        "public_api_used": False,
        "real_provider_used": False,
        "broker_or_order_calls": False,
        "holdings_write_calls": False,
        "fixture_manifest_sha256": _sha256(manifest),
        "domain_summary": {},
    }
    if domain in ("all", "market"):
        summary["domain_summary"].update(run_domain("market", MARKET_MODES, market_cases, output_dir, verbose))
    if domain in ("all", "portfolio"):
        summary["domain_summary"].update(run_domain("portfolio", PORTFOLIO_MODES, portfolio_cases, output_dir, verbose))
    if domain == "all":
        summary["domain_summary"].update(run_combined_smoke(output_dir, verbose))
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(_json(summary), sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    source_root = Path(__file__).resolve().parents[1]
    source_paths = (
        Path(__file__).resolve(),
        source_root / "backend/agent/financial.py",
        source_root / "backend/agent/shared/dispatch.py",
        source_root / "backend/agent/shared/contracts.py",
        source_root / "backend/agent/shared/runtime.py",
        source_root / "backend/agent/market_mas/driver.py",
        source_root / "backend/agent/market_mas/synthetic.py",
        source_root / "backend/agent/portfolio_mas/driver.py",
        source_root / "backend/agent/tools/market_history.py",
        source_root / "backend/agent/tools/anomaly.py",
        source_root / "backend/agent/tools/market_events.py",
        source_root / "backend/agent/tools/portfolio_snapshot.py",
        source_root / "backend/agent/tools/portfolio_risk.py",
        source_root / "backend/agent/tools/allocation.py",
        source_root / "lobster_quant/src/core/portfolio_risk.py",
        source_root / "lobster_quant/src/core/allocation_simulator.py",
        source_root / "backend/db/models/agent.py",
        source_root / "backend/db/models/financial_mas.py",
        source_root / "backend/agent/financial_demo.py",
        source_root / "eval/financial_fixtures.py",
        source_root / "eval/market_cases.jsonl",
        source_root / "eval/portfolio_cases.jsonl",
        source_root / "eval/fixtures/combined/synthetic_demo_v1.json",
    )
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=source_root,
            capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    output_hashes = {path.name: _file_hash(path) for path in sorted(output_dir.iterdir()) if path.is_file()}
    run_manifest = {
        "schema_version": SCHEMA_VERSION,
        "suite": "financial-mas-workflow-v1",
        "profile": PROFILE,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "execution_command": invocation or f"python eval/run_financial_mas_w8.py --domain {domain} --output-dir {output_dir}",
        "base_git_revision": revision,
        "python_version": platform.python_version(),
        "domain": domain,
        "fixture_manifest_sha256": _sha256(manifest),
        "fixture_source_hashes": manifest["source_hashes"],
        "fixture_data_hashes": manifest["data_hashes"],
        "source_file_sha256": {str(path.relative_to(source_root)).replace("\\", "/"): _file_hash(path)
            for path in source_paths},
        "row_counts": {key: value.get("metrics", {}).get("case_count", value.get("case_count", 0))
            for key, value in summary["domain_summary"].items()},
        "completed_runs": {key: value.get("metrics", {}).get("terminal_completed",
            2 if value.get("both_terminal_completed") else 0) for key, value in summary["domain_summary"].items()},
        "outputs_sha256": output_hashes,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(_json(run_manifest), sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", choices=("all", "market", "portfolio"), default="all")
    parser.add_argument("--output-dir", type=Path, required=True,
        help="New or empty directory for raw JSONL and summary artifacts")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-case progress output")
    args = parser.parse_args()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("output directory must be empty to preserve previous evaluation artifacts")
    command = (f"$env:PYTHONPATH='backend;.;lobster_quant'; python eval/run_financial_mas_w8.py "
        f"--domain {args.domain} --output-dir {args.output_dir.as_posix()}"
        + (" --quiet" if args.quiet else ""))
    summary = run(args.output_dir, domain=args.domain, verbose=not args.quiet, invocation=command)
    print(f"W8 raw records and metrics written to {args.output_dir.resolve()}")
    for key, value in summary["domain_summary"].items():
        if "metrics" in value:
            metrics = value["metrics"]
            print(f"{key}: {metrics['terminal_completed']}/{metrics['case_count']} completed; "
                  f"model_calls={metrics['counters_total']['model_calls']}; "
                  f"tool_calls={metrics['counters_total']['tool_calls']}")
        else:
            completed = value.get("both_terminal_completed", False)
            print(f"{key}: {2 if completed else 0}/2 terminal runs completed; "
                  f"artifacts={value.get('artifacts_persisted', 0)}; "
                  f"relations={sum(value.get('relation_type_counts', {}).values())}")


if __name__ == "__main__":
    main()
