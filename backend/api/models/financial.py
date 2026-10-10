"""Additive financial API DTOs; domain contracts remain the authority."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from agent.shared import (FinancialModel, ArtifactRef, MarketInvestigationArtifact,
    PortfolioProposalArtifact)


class FinancialRunSummary(FinancialModel):
    run_id: str
    mas_kind: Literal['market_investigation', 'portfolio_rebalance']
    status: Literal['queued', 'executing', 'waiting_user', 'paused', 'completed', 'failed', 'cancelled', 'expired']
    version: int


class FinancialCreateResponse(FinancialModel):
    schema_version: Literal[1] = 1
    conversation_id: str
    correlation_id: str
    market_run_id: str | None = None
    portfolio_run_id: str | None = None
    runs: list[FinancialRunSummary]


class FinancialRunResult(FinancialRunSummary):
    schema_version: Literal[1] = 1
    conversation_id: str
    correlation_id: str
    mode: Literal['review', 'auto']
    error_code: str | None = None
    artifact_ref: ArtifactRef | None = None
    artifact: MarketInvestigationArtifact | PortfolioProposalArtifact | None = None
    validation_outcome: Literal['verified', 'partial', 'insufficient_evidence', 'feasible', 'infeasible', 'insufficient_data', 'pending'] = 'pending'
    limitations: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def artifact_matches_kind(self):
        if self.artifact is not None:
            expected = MarketInvestigationArtifact if self.mas_kind == 'market_investigation' else PortfolioProposalArtifact
            if not isinstance(self.artifact, expected) or self.artifact.producing_run_id != self.run_id:
                raise ValueError('artifact producer/kind mismatch')
            if self.artifact_ref is None or self.validation_outcome != self.artifact.status:
                raise ValueError('artifact reference/outcome mismatch')
        elif self.artifact_ref is not None or self.validation_outcome != 'pending':
            raise ValueError('missing artifact must remain pending')
        return self


class FinancialRunAction(FinancialModel):
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=2000)


class MarketRunResult(FinancialRunResult):
    mas_kind: Literal['market_investigation']
    artifact: MarketInvestigationArtifact | None = None


class PortfolioRunResult(FinancialRunResult):
    mas_kind: Literal['portfolio_rebalance']
    artifact: PortfolioProposalArtifact | None = None


# The public result schema uses mas_kind to select its exact artifact shape.
FinancialRunResponse = Annotated[MarketRunResult | PortfolioRunResult,
    Field(discriminator='mas_kind')]
