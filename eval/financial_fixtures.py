"""Pure data loading for workflow-v1 preparation; no runtime or driver execution."""
from pathlib import Path
import hashlib
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict
from agent.shared.contracts import MarketInvestigationRequest, PortfolioReviewRequest
from agent.tools.market_history import HistorySeries, MarketDependencies, FixtureHistoryBackend
from agent.tools.market_events import EventRecord, EventDependencies, FixtureEventBackend
from agent.tools.portfolio_snapshot import SnapshotRecord, SnapshotInput, SnapshotOutput
from agent.tools.portfolio_risk import AssetHistory, RiskInput
from agent.tools.allocation import AssetClassification, AllocationInput, CandidateInput, SimulationInput

ROOT = Path(__file__).resolve().parents[1]

class FixtureCase(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal[1]
    case_id: str
    name: str
    synthetic: Literal[True]
    source_case_id: str | None
    source_file: str | None
    source_file_sha256: str | None
    source_case_sha256: str | None
    adapter_sha256: str
    gold: dict
    conformance: dict

class MarketCase(FixtureCase):
    request: MarketInvestigationRequest
    events: list[EventRecord]

class PortfolioCase(FixtureCase):
    original_tool_input: dict | None
    request: PortfolioReviewRequest
    snapshot: SnapshotRecord
    histories: tuple[AssetHistory, ...]
    classifications: dict[str, AssetClassification]
    # Proposal validation belongs to AllocationInput, not the request schema.
    proposals: list[dict[str, str]]

    def snapshot_input(self) -> SnapshotInput:
        return SnapshotInput(snapshot_id=self.request.portfolio_snapshot_id, as_of=self.request.as_of)

    def allocation_input(self, round_index: int = -1) -> AllocationInput:
        return AllocationInput(weights=self.proposals[round_index], constraints=self.request.user_constraints.model_dump(), classifications=self.classifications)

    def candidate_input(self) -> CandidateInput:
        return CandidateInput(symbols=[h.symbol for h in self.snapshot.holdings], constraints=self.request.user_constraints.model_dump(), classifications=self.classifications)

    def risk_input(self, snapshot: SnapshotOutput) -> RiskInput:
        return RiskInput(snapshot=snapshot, as_of=self.request.as_of, histories=self.histories)

    def simulation_input(self, initial_value, round_index: int = -1) -> SimulationInput:
        # Invalid negative targets are intentionally rejected by SimulationInput;
        # callers must check AllocationInput before constructing simulation.
        return SimulationInput(histories=self.histories, as_of=self.request.as_of, currency=self.snapshot.currency, target_weights=self.proposals[round_index], initial_value=initial_value, rebalance_every=1, fee_bps=0, slippage_bps=0)

def verify_manifest(root: Path = ROOT) -> dict:
    manifest = json.loads((root/'eval/fixtures/workflow_v1/manifest.json').read_text(encoding='utf-8'))
    for path, expected in (manifest['source_hashes'] | manifest['data_hashes']).items():
        if hashlib.sha256((root/path).read_bytes()).hexdigest() != expected:
            raise ValueError('Fixture hash mismatch: '+path)
    return manifest

def load_cases(root: Path = ROOT) -> tuple[list[MarketCase], list[PortfolioCase]]:
    verify_manifest(root)
    def load(name, model):
        return [model.model_validate_json(line) for line in (root/'eval'/name).read_text(encoding='utf-8').splitlines() if line]
    return load('market_cases.jsonl', MarketCase), load('portfolio_cases.jsonl', PortfolioCase)

def market_dependencies(case: MarketCase, root: Path = ROOT) -> tuple[MarketDependencies, EventDependencies]:
    verify_manifest(root)
    histories = [HistorySeries.model_validate(s) for s in json.loads((root/'eval/fixtures/workflow_v1/market_history.json').read_text(encoding='utf-8'))]
    return MarketDependencies(FixtureHistoryBackend(histories)), EventDependencies(FixtureEventBackend(case.events))
