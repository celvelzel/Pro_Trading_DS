"""Deterministic allocation constraints, bounded candidates and simulation tools."""
from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import Field, field_validator
from lobster_quant.src.core.allocation_simulator import AllocationSimulator
from .portfolio_snapshot import StrictModel, Symbol, Amount, PositiveAmount, UTCDateTime, Currency
from .portfolio_risk import AssetHistory, checked_histories
from .registry import ToolSpec

Weight = Amount


class AllocationConstraints(StrictModel):
    max_weight_by_symbol: dict[Symbol, Amount] = Field(default_factory=dict)
    min_cash_weight: Amount = Decimal(0)
    max_equity_weight: Amount | None = None
    max_sector_weight: dict[str, Amount] = Field(default_factory=dict)
    weight_tolerance: Decimal = Field(default=Decimal("1e-8"), ge=0, le=Decimal("0.0001"), allow_inf_nan=False)

    @field_validator("max_weight_by_symbol", "max_sector_weight", "min_cash_weight", "max_equity_weight")
    @classmethod
    def unit_interval(cls, value):
        values = value.values() if isinstance(value, dict) else [value]
        if any(v is not None and v > 1 for v in values):
            raise ValueError("Constraint weights must be at most one")
        return value


class AssetClassification(StrictModel):
    asset_class: Literal["equity", "other"] | None = None
    sector: str | None = None
    source: str = Field(min_length=1)


class AllocationInput(StrictModel):
    weights: dict[Symbol, Decimal]  # negatives produce a deterministic failed check
    constraints: AllocationConstraints = Field(default_factory=AllocationConstraints)
    classifications: dict[Symbol, AssetClassification] = Field(default_factory=dict)


class CheckDetail(StrictModel):
    check: str
    status: Literal["pass", "fail", "unknown"]
    actual: Decimal | None = None
    limit: Decimal | None = None
    reason: str | None = None


class ConstraintCheck(StrictModel):
    status: Literal["pass", "fail", "unknown"]
    checks: tuple[CheckDetail, ...]
    violations: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()


def validate_allocation(payload: AllocationInput) -> ConstraintCheck:
    w, c, classes = payload.weights, payload.constraints, payload.classifications
    checks = []
    def add(name, ok, actual=None, limit=None, reason=None):
        checks.append(CheckDetail(check=name, status="unknown" if ok is None else "pass" if ok else "fail", actual=actual, limit=limit, reason=reason))
    add("explicit_cash", "CASH" in w, reason=None if "CASH" in w else "CASH weight required")
    add("nonnegative", all(v >= 0 for v in w.values()))
    total = sum(w.values(), Decimal(0))
    add("sum_to_one", abs(total-1) <= c.weight_tolerance, total, Decimal(1))
    cash = w.get("CASH", Decimal(0))
    add("min_cash", cash+c.weight_tolerance >= c.min_cash_weight, cash, c.min_cash_weight)
    for s, cap in sorted(c.max_weight_by_symbol.items()):
        actual = w.get(s, Decimal(0))
        add("max_symbol:"+s, actual <= cap+c.weight_tolerance, actual, cap)
    active = [s for s,v in w.items() if s != "CASH" and v > 0]
    if c.max_equity_weight is not None:
        known = all(s in classes and classes[s].asset_class is not None for s in active)
        equity = sum((w[s] for s in active if s in classes and classes[s].asset_class == "equity"), Decimal(0))
        add("max_equity", equity <= c.max_equity_weight+c.weight_tolerance if known else None,
            equity if known else None, c.max_equity_weight, None if known else "Trustworthy asset classification missing")
    for sector, cap in sorted(c.max_sector_weight.items()):
        # Every positive asset needs classification; unclassified exposure cannot be assigned elsewhere.
        known = all(s in classes and classes[s].sector is not None for s in active)
        actual = sum((w[s] for s in active if s in classes and classes[s].sector == sector), Decimal(0))
        add("max_sector:"+sector, actual <= cap+c.weight_tolerance if known else None,
            actual if known else None, cap, None if known else "Trustworthy sector classification missing")
    violations = tuple(ch.check for ch in checks if ch.status == "fail")
    unknowns = tuple(ch.check for ch in checks if ch.status == "unknown")
    return ConstraintCheck(status="fail" if violations else "unknown" if unknowns else "pass", checks=tuple(checks), violations=violations, unknowns=unknowns)


class CandidateInput(StrictModel):
    symbols: tuple[Symbol, ...] = Field(max_length=32)
    constraints: AllocationConstraints = Field(default_factory=AllocationConstraints)
    classifications: dict[Symbol, AssetClassification] = Field(default_factory=dict)
    max_candidates: int = Field(default=3, ge=1, le=8)


class Candidate(StrictModel):
    weights: dict[Symbol, Amount]
    constraint_check: ConstraintCheck


class CandidateOutput(StrictModel):
    status: Literal["feasible", "infeasible", "insufficient_data"]
    candidates: tuple[Candidate, ...] = ()
    reasons: tuple[str, ...] = ()
    method: Literal["bounded_greedy_upper_bound_constraints"] = "bounded_greedy_upper_bound_constraints"


def generate_feasible_candidates(payload: CandidateInput) -> CandidateOutput:
    symbols = sorted(set(payload.symbols)-{"CASH"})
    c = payload.constraints
    cash_cap = c.max_weight_by_symbol.get("CASH", Decimal(1))
    if c.min_cash_weight > cash_cap+c.weight_tolerance:
        return CandidateOutput(status="infeasible", reasons=("min_cash_exceeds_cash_cap",))
    # All-cash is a complete feasible witness when no equity exposure is required.
    allcash = {s:Decimal(0) for s in symbols} | {"CASH":Decimal(1)}
    cashcheck = validate_allocation(AllocationInput(weights=allcash, constraints=c, classifications=payload.classifications))
    results = [Candidate(weights=allcash, constraint_check=cashcheck)] if cashcheck.status == "pass" else []
    unknown = False
    for starting_cash, order in ((cash_cap, symbols), (c.min_cash_weight, symbols), (c.min_cash_weight, list(reversed(symbols)))):
        weights = {s:Decimal(0) for s in symbols} | {"CASH":starting_cash}
        remaining = Decimal(1)-starting_cash
        equity_used = Decimal(0)
        sectors = {}
        for s in order:
            if remaining <= c.weight_tolerance:
                break
            classification = payload.classifications.get(s)
            if (c.max_equity_weight is not None and (classification is None or classification.asset_class is None)) or (c.max_sector_weight and (classification is None or classification.sector is None)):
                unknown = True
                continue
            capacity = min(c.max_weight_by_symbol.get(s, Decimal(1)), remaining)
            if c.max_equity_weight is not None and classification.asset_class == "equity":
                capacity = min(capacity, max(Decimal(0), c.max_equity_weight-equity_used))
            if classification and classification.sector in c.max_sector_weight:
                sector = classification.sector
                capacity = min(capacity, max(Decimal(0), c.max_sector_weight[sector]-sectors.get(sector, Decimal(0))))
            weights[s] = capacity
            remaining -= capacity
            if classification:
                if classification.asset_class == "equity":
                    equity_used += capacity
                sectors[classification.sector] = sectors.get(classification.sector, Decimal(0))+capacity
        cash_add = min(remaining, cash_cap-weights["CASH"])
        weights["CASH"] += cash_add
        remaining -= cash_add
        check = validate_allocation(AllocationInput(weights=weights, constraints=c, classifications=payload.classifications))
        if check.status == "pass" and not any(candidate.weights == weights for candidate in results):
            results.append(Candidate(weights=weights, constraint_check=check))
    # Two orders may miss a witness for interacting equity/sector capacities. Never claim infeasible
    # from heuristic exhaustion in that case; unknown prevents an unproven conclusion.
    complex_caps = c.max_equity_weight is not None and bool(c.max_sector_weight)
    if results:
        return CandidateOutput(status="feasible", candidates=tuple(results[:payload.max_candidates]))
    if unknown or complex_caps:
        return CandidateOutput(status="insufficient_data", reasons=("classification_missing_or_bounded_search_inconclusive",))
    return CandidateOutput(status="infeasible", reasons=("insufficient_capacity_under_hard_caps",))


class SimulationInput(StrictModel):
    histories: tuple[AssetHistory, ...] = Field(max_length=32)
    as_of: UTCDateTime
    currency: Currency
    target_weights: dict[Symbol, Amount]
    initial_value: PositiveAmount
    rebalance_every: int = Field(default=1, ge=1, le=10000)
    fee_bps: Amount = Decimal(0)
    slippage_bps: Amount = Decimal(0)


class SimulationPoint(StrictModel):
    date: date
    net_value: PositiveAmount
    cost: Amount
    turnover: Amount


class SimulationOutput(StrictModel):
    status: Literal["ok", "insufficient_data"]
    path: tuple[SimulationPoint, ...] = ()
    total_cost: Amount | None = None
    total_turnover: Amount | None = None
    total_return: Decimal | None = None
    final_weights: dict[Symbol, Amount] = Field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    history_sources: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ("fixed_ex_ante_target", "fractional_units", "zero_cash_return", "same_close_rebalance_for_next_interval", "linear_traded_notional_fees_and_slippage", "initial_purchase_cost_included", "no_terminal_liquidation")


def simulate_allocation(payload: SimulationInput) -> SimulationOutput:
    try:
        active = [s for s,w in payload.target_weights.items() if s != "CASH" and w > 0]
        histories = checked_histories(payload.histories, payload.as_of, payload.currency, active)
        result = AllocationSimulator().simulate(histories, payload.target_weights, payload.initial_value,
                                                payload.rebalance_every, payload.fee_bps, payload.slippage_bps)
    except ValueError as exc:
        return SimulationOutput(status="insufficient_data", reasons=(str(exc),))
    return SimulationOutput(status="ok", history_sources=tuple(h.source for h in payload.histories), **result)


def register_tools(registry, deps=None):
    for name, inp, out, handler, desc in (
        ("validate_allocation", AllocationInput, ConstraintCheck, validate_allocation, "Check every requested hard constraint; unknown never passes."),
        ("generate_feasible_candidates", CandidateInput, CandidateOutput, generate_feasible_candidates, "Generate bounded candidates without relaxing constraints."),
        ("simulate_allocation", SimulationInput, SimulationOutput, simulate_allocation, "Simulate fixed allocations using common dates and explicit costs."),
    ):
        registry.register(ToolSpec(name=name, version="1", description=desc, input_model=inp, output_model=out, handler=handler))
