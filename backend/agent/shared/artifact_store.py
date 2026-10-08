"""Immutable, conversation-scoped artifact reads and transactional inserts."""
import hashlib
import json
import uuid
from sqlalchemy import select
from db.models.financial_mas import FinancialArtifact
from .contracts import MarketInvestigationArtifact, PortfolioProposalArtifact


class ArtifactStore:
    def __init__(self, session_factory):
        self.sessions = session_factory

    @staticmethod
    def put_in_transaction(session, run, meta, artifact_key, artifact):
        payload = artifact.model_dump(mode='json')
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        existing = session.scalar(select(FinancialArtifact).where(FinancialArtifact.run_id == run.id, FinancialArtifact.artifact_key == artifact_key))
        if existing:
            if existing.content_hash != digest:
                raise ValueError('immutable artifact cannot be replaced')
            return existing
        if artifact.producing_run_id != run.id:
            raise ValueError('artifact run mismatch')
        symbols = [artifact.symbol] if isinstance(artifact, MarketInvestigationArtifact) else sorted(set(artifact.current_weights) | set(artifact.proposed_weights))
        row = FinancialArtifact(id=str(uuid.uuid4()), run_id=run.id, conversation_id=run.conversation_id, artifact_key=artifact_key, mas_kind=meta.mas_kind, schema_version=1, as_of=artifact.as_of, symbols=symbols, content_hash=digest, payload=payload)
        session.add(row)
        return row

    def get(self, artifact_id: str, *, conversation_id: str, as_of=None, symbols: list[str] | None = None, schema_version=1):
        from .dispatch import aware
        with self.sessions() as session:
            row = session.get(FinancialArtifact, artifact_id)
            if row is None or row.conversation_id != conversation_id:
                raise KeyError('artifact not found in conversation')
            if row.schema_version != schema_version:
                raise ValueError('artifact schema mismatch')
            if as_of is not None and aware(row.as_of) != as_of:
                raise ValueError('artifact timepoint mismatch')
            if symbols is not None and not set(symbols).issubset(row.symbols):
                raise ValueError('artifact symbols mismatch')
            model = MarketInvestigationArtifact if row.mas_kind == 'market_investigation' else PortfolioProposalArtifact
            return model.model_validate(row.payload)
