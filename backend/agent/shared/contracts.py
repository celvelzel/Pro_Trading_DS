"""Versioned financial contracts. External evidence is data, never instructions."""
from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Mapping
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MASKind = Literal['market_investigation', 'portfolio_rebalance']


def normalized_keys(value):
    if not isinstance(value, Mapping):
        raise ValueError('weights/caps must be a mapping')
    result = {}
    for key, weight in value.items():
        if not isinstance(key, str):
            raise ValueError('symbol/sector keys must be strings before coercion')
        normalized = key.strip().upper()
        if not normalized or normalized in result:
            raise ValueError('blank or duplicate normalized symbols/sector names')
        result[normalized] = weight
    return result


class FinancialModel(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, validate_assignment=True)

    @field_validator('*')
    @classmethod
    def aware_dates(cls, value):
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError('timestamps must be timezone aware')
            return value.astimezone(timezone.utc)
        return value


class FinancialExecutionAuthorization(FinancialModel):
    """Trusted immutable creation intent; cross intent alone grants no execution."""
    model_config = ConfigDict(extra='forbid', frozen=True)
    purpose: Literal['independent', 'cross_followup']
    source_run_id: str | None = None
    request_message_id: str | None = None

    @field_validator('purpose', 'source_run_id', 'request_message_id', mode='before')
    @classmethod
    def exact_strings(cls, value):
        if value is not None and (not isinstance(value, str) or not value or value != value.strip()):
            raise ValueError('authorization identifiers require exact nonblank strings')
        return value

    @model_validator(mode='after')
    def valid_origin(self):
        if self.purpose == 'cross_followup':
            if self.source_run_id is None or self.request_message_id is None:
                raise ValueError('cross_followup requires source and REQUEST message')
        elif self.source_run_id is not None or self.request_message_id is not None:
            raise ValueError('independent forbids source and REQUEST message')
        return self


class RunBudget(FinancialModel):
    max_model_calls: int = Field(default=16, ge=1, le=16)
    max_tool_calls: int = Field(default=20, ge=0, le=20)
    max_rounds: int = Field(default=3, ge=1, le=3)
    max_active_seconds: float = Field(default=120, gt=0, le=120)
    max_hops: int = Field(default=2, ge=0, le=2)
    max_followups: int = Field(default=1, ge=0, le=1)
    model_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    rounds: int = Field(default=0, ge=0)
    hops: int = Field(default=0, ge=0)
    followups: int = Field(default=0, ge=0)


class AllocationConstraints(FinancialModel):
    max_weight_by_symbol: dict[str, float] = Field(default_factory=dict)
    min_cash_weight: float = Field(default=0, ge=0, le=1)
    max_equity_weight: float = Field(default=1, ge=0, le=1)
    max_sector_weight: dict[str, float] = Field(default_factory=dict)
    weight_tolerance: float = Field(default=1e-6, gt=0, le=1e-4)

    @field_validator('max_weight_by_symbol', 'max_sector_weight', mode='before')
    @classmethod
    def cap_keys(cls, value):
        return normalized_keys(value)

    @field_validator('max_weight_by_symbol', 'max_sector_weight')
    @classmethod
    def caps(cls, value):
        import math
        if any(not math.isfinite(v) or v < 0 or v > 1 for v in value.values()):
            raise ValueError('caps must be finite weights')
        return value


class MarketInvestigationRequest(FinancialModel):
    symbol: str = Field(min_length=1, max_length=32)
    as_of: datetime
    lookback_trading_days: int = Field(default=20, ge=2, le=2520)
    sector_benchmark: str | None = None
    max_llm_calls: int = Field(default=16, ge=1, le=16)

    @field_validator('symbol', 'sector_benchmark', mode='before')
    @classmethod
    def symbols(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class PortfolioReviewRequest(FinancialModel):
    portfolio_snapshot_id: str = Field(min_length=1)
    as_of: datetime
    user_constraints: AllocationConstraints = Field(default_factory=AllocationConstraints)
    market_artifact_id: str | None = None


class EvidenceRef(FinancialModel):
    id: str
    source_type: Literal['market_tool', 'filing', 'news', 'macro', 'document']
    source_locator: str
    published_at: datetime | None = None
    available_at: datetime | None = None
    observed_at: datetime
    content_hash: str
    excerpt: str | None = None


class NumericFact(FinancialModel):
    name: str
    value: float
    unit: str
    evidence_id: str
    tool_result_id: str


class Hypothesis(FinancialModel):
    explanation: str
    support_ids: list[str] = Field(default_factory=list)
    against_ids: list[str] = Field(default_factory=list)
    disposition: Literal['supported', 'contradicted', 'unverified'] = 'unverified'


class MarketInvestigationArtifact(FinancialModel):
    schema_version: Literal[1] = 1
    producing_run_id: str
    symbol: str = Field(min_length=1, max_length=32)
    as_of: datetime
    numeric_facts: list[NumericFact] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    status: Literal['verified', 'partial', 'insufficient_evidence']

    @field_validator('symbol', mode='before')
    @classmethod
    def symbol_upper(cls, value):
        return value.strip().upper() if isinstance(value, str) else value


class ConstraintViolation(FinancialModel):
    constraint: str
    symbol: str | None = None
    actual: float | None = None
    limit: float | None = None
    reason: str


class ConstraintCheck(FinancialModel):
    status: Literal['pass', 'fail', 'unknown']
    violations: list[ConstraintViolation] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def valid_pass(self):
        if self.status == 'pass' and (self.violations or self.unknowns):
            raise ValueError('pass requires no violations or unknowns')
        return self


class RiskMetrics(FinancialModel):
    volatility: float | None = Field(default=None, ge=0)
    maximum_drawdown: float | None = None
    concentration: float | None = Field(default=None, ge=0, le=1)
    cash_weight: float | None = Field(default=None, ge=0, le=1)
    tool_result_id: str


class RiskComparison(FinancialModel):
    before: RiskMetrics
    after: RiskMetrics


class SimulationResult(FinancialModel):
    tool_result_id: str
    adjustment: str
    rebalance_cadence: str
    fees_bps: float = Field(ge=0)
    slippage_bps: float = Field(ge=0)
    net_return: float | None = None
    assumptions: list[str] = Field(default_factory=list)


class PortfolioProposalArtifact(FinancialModel):
    schema_version: Literal[1] = 1
    producing_run_id: str
    snapshot_id: str
    as_of: datetime
    current_weights: dict[str, float]
    proposed_weights: dict[str, float]
    constraint_check: ConstraintCheck
    risk_comparison: RiskComparison | None = None
    simulation: SimulationResult | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    status: Literal['feasible', 'infeasible', 'insufficient_data']

    @field_validator('current_weights', 'proposed_weights', mode='before')
    @classmethod
    def weight_keys(cls, value):
        return normalized_keys(value)

    @field_validator('current_weights', 'proposed_weights')
    @classmethod
    def weights(cls, value):
        import math
        if value and ('CASH' not in value or any(not math.isfinite(v) or v < 0 for v in value.values()) or abs(sum(value.values()) - 1) > 1e-6):
            raise ValueError('weights require CASH, nonnegative finite values, sum=1 within 1e-6')
        return value

    @model_validator(mode='after')
    def feasible(self):
        if self.status == 'feasible' and (self.constraint_check.status != 'pass' or not self.proposed_weights or not self.risk_comparison or not self.simulation):
            raise ValueError('feasible requires verified weights, deterministic risk and simulation')
        return self


class SpecialistResult(FinancialModel):
    role: str
    action: str
    summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    missing_checks: list[str] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    proposed_weights: dict[str, float] = Field(default_factory=dict)

    @field_validator('proposed_weights', mode='before')
    @classmethod
    def normalize_weights(cls, value):
        return normalized_keys(value)


class MarketState(FinancialModel):
    kind: Literal['market_investigation'] = 'market_investigation'
    phase: str = 'investigate'
    results: list[SpecialistResult] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    numeric_facts: list[NumericFact] = Field(default_factory=list)
    missing_checks: list[str] = Field(default_factory=list)


class PortfolioState(FinancialModel):
    kind: Literal['portfolio_rebalance'] = 'portfolio_rebalance'
    phase: str = 'propose'
    results: list[SpecialistResult] = Field(default_factory=list)
    proposed_weights: dict[str, float] = Field(default_factory=dict)
    constraint_check: ConstraintCheck | None = None
    risk_comparison: RiskComparison | None = None
    missing_checks: list[str] = Field(default_factory=list)

    @field_validator('proposed_weights', mode='before')
    @classmethod
    def normalize_weights(cls, value):
        return normalized_keys(value)


class Checkpoint(FinancialModel):
    schema_version: Literal[1] = 1
    state: MarketState | PortfolioState = Field(discriminator='kind')
    artifact_ids: list[str] = Field(default_factory=list)


class ArtifactRef(FinancialModel):
    artifact_id: str
    schema_version: Literal[1] = 1


class ToolResultRef(FinancialModel):
    """Persisted audit primary keys, not logical invocation keys."""
    run_id: str
    tool_call_id: str
    tool_result_id: str
    tool_name: str
    tool_version: str


class CrossMASEnvelope(FinancialModel):
    message_id: str
    schema_version: Literal[1] = 1
    origin_mas: MASKind
    target_mas: MASKind
    target_agent: str | None = None
    run_id: str
    correlation_id: str
    causation_id: str | None = None
    message_type: Literal['MARKET_EVIDENCE_REQUEST', 'MARKET_EVIDENCE_READY', 'PORTFOLIO_IMPACT_REQUEST', 'SYSTEM_UNAVAILABLE']
    payload_ref: ArtifactRef | None = None
    as_of: datetime
    created_at: datetime
    deadline_at: datetime
    idempotency_key: str
    budget: RunBudget

    @model_validator(mode='after')
    def deadline(self):
        if self.deadline_at <= self.created_at:
            raise ValueError('deadline must follow creation')
        return self
