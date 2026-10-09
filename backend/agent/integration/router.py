"""Route independent runs through the reviewed public admission authority.

No domain coordinator, provider, runtime table or process-local durable state.
Trusted adapters must be immutable, read-only and have their own I/O deadlines.
"""
from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import Field, model_validator

from agent.shared import (ArtifactRef, ArtifactStore, BudgetExhausted,
    CrossMASEnvelope, FinancialConflict, FinancialModel,
    MarketInvestigationArtifact, MarketInvestigationRequest,
    PortfolioReviewRequest, RunBudget)
from agent.tools.portfolio_snapshot import SnapshotRecord, SnapshotLoader

TERMINAL = frozenset({'completed', 'failed', 'cancelled', 'expired'})


class CrossMASRequest(FinancialModel):
    conversation_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1, max_length=100)
    mode: Literal['review', 'auto'] = 'review'
    market: MarketInvestigationRequest | None = None
    portfolio: PortfolioReviewRequest | None = None
    market_budget: RunBudget = Field(default_factory=RunBudget)
    portfolio_budget: RunBudget = Field(default_factory=RunBudget)

    @model_validator(mode='after')
    def independent_inputs(self):
        if self.market is None and self.portfolio is None:
            raise ValueError('At least one independent workflow is required')
        if self.market and self.portfolio and self.market.as_of != self.portfolio.as_of:
            raise ValueError('Combined workflows require the same as_of')
        if self.portfolio and self.portfolio.market_artifact_id is not None:
            raise ValueError('Router evidence requires admitted relations, not direct artifact IDs')
        return self


class CrossMASResponse(FinancialModel):
    conversation_id: str
    correlation_id: str
    market_run_id: str | None = None
    portfolio_run_id: str | None = None
    limitations: list[str] = Field(default_factory=list)


def _key(*parts):
    return 'cross:' + hashlib.sha256('\0'.join(parts).encode()).hexdigest()


def _message_id(key):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def _fresh_budget(snapshot):
    return RunBudget(**{k: v for k, v in snapshot['budget'].items() if k.startswith('max_')})


class CrossMASRouter:
    def __init__(self, dispatcher, artifact_store: ArtifactStore,
                 snapshot_loader: SnapshotLoader, *, execution_profile: str,
                 clock=None, ttl_seconds: float = 60):
        if dispatcher.execution_profile != execution_profile or not execution_profile:
            raise ValueError('Router requires the injected matching execution profile')
        if not 0 < ttl_seconds <= 120:
            raise ValueError('Cross TTL must be positive and at most 120 seconds')
        self.dispatcher = dispatcher
        self.artifacts = artifact_store
        self.snapshot_loader = snapshot_loader
        self.execution_profile = execution_profile
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.ttl_seconds = ttl_seconds

    def _snapshot(self, run_id):
        snapshot = self.dispatcher.snapshot(run_id)
        if snapshot['execution_profile'] != self.execution_profile:
            raise ValueError('Run execution profile differs from router assembly')
        return snapshot

    def _scope(self, request: PortfolioReviewRequest):
        raw = self.snapshot_loader(request.portfolio_snapshot_id)
        record = SnapshotRecord.model_validate(raw.model_dump() if isinstance(raw, SnapshotRecord) else raw)
        if (record.snapshot_id != request.portfolio_snapshot_id or not record.source
                or record.effective_at != request.as_of):
            raise ValueError('Trusted immutable holdings timepoint/snapshot mismatch')
        return {holding.symbol for holding in record.holdings}

    def create(self, request: CrossMASRequest) -> CrossMASResponse:
        request = CrossMASRequest.model_validate(request.model_dump())
        corr = _message_id(_key(request.conversation_id, request.idempotency_key, 'correlation'))
        result = CrossMASResponse(conversation_id=request.conversation_id, correlation_id=corr)
        for domain, value, budget in (('market', request.market, request.market_budget),
                                      ('portfolio', request.portfolio, request.portfolio_budget)):
            if value is None:
                continue
            try:
                run = self.dispatcher.create(request.conversation_id, value,
                    idempotency_key=_key(request.idempotency_key, domain), mode=request.mode,
                    budget=budget, correlation_id=corr)
            except KeyError:
                result.limitations.append(domain + '_peer_undeployed')
                continue
            setattr(result, domain + '_run_id', run.id)
        if result.market_run_id and result.portfolio_run_id:
            for attempt in range(3):
                source = self._snapshot(result.market_run_id)
                try:
                    self.dispatcher.link_runs(result.market_run_id, result.portfolio_run_id,
                        version=source['version'], relation_type='combined',
                        idempotency_key=_key(request.idempotency_key, 'combined'))
                    break
                except FinancialConflict:
                    if attempt == 2:
                        raise
        return result

    def restore(self, run_id: str) -> CrossMASResponse:
        """Recover normal paired identities without in-memory router bookkeeping."""
        own = self._snapshot(run_id)
        result = CrossMASResponse(conversation_id=own['conversation_id'], correlation_id=own['correlation_id'])
        field = 'market_run_id' if own['mas_kind'] == 'market_investigation' else 'portfolio_run_id'
        setattr(result, field, run_id)
        for relation in self.dispatcher.relations(run_id):
            if relation['relation_type'] == 'combined':
                result.market_run_id = relation['source_run_id']
                result.portfolio_run_id = relation['target_run_id']
            elif (own['mas_kind'] == 'market_investigation' and relation['relation_type'] == 'cross_admitted'
                  and relation['target_run_id'] == run_id
                  and relation['envelope'].get('message_type') == 'MARKET_EVIDENCE_REQUEST'):
                result.market_run_id = None
                result.portfolio_run_id = relation['source_run_id']
                for pair in self.dispatcher.relations(result.portfolio_run_id):
                    if pair['relation_type'] == 'combined':
                        result.market_run_id = pair['source_run_id']
        return result

    def _existing(self, run_id, key):
        return next((r for r in self.dispatcher.relations(run_id) if r['idempotency_key'] == key), None)

    def _envelope(self, source, target, key, message_type, *, ref=None, cause=None, deadline=None):
        now = self.clock()
        budget = _fresh_budget(source)
        budget.max_hops = min(budget.max_hops, target['budget']['max_hops'])
        budget.max_followups = min(budget.max_followups, target['budget']['max_followups'])
        return CrossMASEnvelope(message_id=_message_id(key), origin_mas=source['mas_kind'],
            target_mas=target['mas_kind'], run_id=source['run_id'], correlation_id=source['correlation_id'],
            message_type=message_type, payload_ref=ref, as_of=source['request']['as_of'],
            created_at=now, deadline_at=deadline or now + timedelta(seconds=self.ttl_seconds),
            idempotency_key=key, causation_id=cause, budget=budget)

    def admit(self, source_run_id: str, target_run_id: str, envelope: CrossMASEnvelope,
              *, expected_source_version: int, expected_target_version: int):
        """Scope guard plus the sole atomic executable admission seam."""
        source, target = self._snapshot(source_run_id), self._snapshot(target_run_id)
        portfolio = source if source['mas_kind'] == 'portfolio_rebalance' else target
        market = target if source['mas_kind'] == 'portfolio_rebalance' else source
        scope = self._scope(PortfolioReviewRequest.model_validate(portfolio['request']))
        if market['request']['symbol'] not in scope:
            raise ValueError('Market symbol is outside trusted saved holdings scope')
        if envelope.payload_ref:
            artifact = self.artifacts.get(envelope.payload_ref.artifact_id,
                conversation_id=portfolio['conversation_id'], as_of=envelope.as_of,
                symbols=[market['request']['symbol']], schema_version=envelope.payload_ref.schema_version)
            if not isinstance(artifact, MarketInvestigationArtifact) or artifact.symbol not in scope:
                raise ValueError('Not an authorized immutable Market artifact')
        return self.dispatcher.admit_cross_message(source_run_id, target_run_id,
            expected_source_version=expected_source_version, expected_target_version=expected_target_version,
            envelope=envelope)

    def transfer(self, market_run_id: str, portfolio_run_id: str, *, request_relation=None):
        source, target = self._snapshot(market_run_id), self._snapshot(portfolio_run_id)
        key = _key(market_run_id, portfolio_run_id, 'reply' if request_relation else 'initial')
        existing = self._existing(market_run_id, key)
        if existing:
            envelope = CrossMASEnvelope.model_validate(existing['envelope'])
        else:
            cause = None
            deadline = None
            if request_relation:
                request = CrossMASEnvelope.model_validate(request_relation['envelope'])
                cause, deadline = request.message_id, request.deadline_at
            if source['status'] == 'completed':
                refs = source['checkpoint']['artifact_ids']
                if len(refs) != 1:
                    raise ValueError('Expected one immutable final Market artifact')
                kind, ref = 'MARKET_EVIDENCE_READY', ArtifactRef(artifact_id=refs[0])
            else:
                kind, ref = 'SYSTEM_UNAVAILABLE', None
            envelope = self._envelope(source, target, key, kind, ref=ref, cause=cause, deadline=deadline)
        return self.admit(market_run_id, portfolio_run_id, envelope,
            expected_source_version=source['version'], expected_target_version=target['version'])

    def request_further_evidence(self, portfolio_run_id: str, market_request: MarketInvestigationRequest,
                                *, idempotency_key: str, mode: Literal['review', 'auto']='review'):
        """One bounded independent Market run, admitted before any delivery.

        The same key reconstructs creation and the original absolute envelope.
        This is fresh evidence work, never retry ancestry or history mutation.
        """
        source = self._snapshot(portfolio_run_id)
        key = _key(portfolio_run_id, idempotency_key, 'further')
        existing = self._existing(portfolio_run_id, key)
        if existing:
            target = self._snapshot(existing['target_run_id'])
            if target['request'] != market_request.model_dump(mode='json'):
                raise FinancialConflict('Follow-up key changes request')
            # Revalidate the full immutable creation identity, including mode,
            # even when replaying an already admitted historical request.
            self.dispatcher.create(source['conversation_id'], market_request,
                idempotency_key=_key(key, 'market'), mode=mode, budget=_fresh_budget(source),
                correlation_id=source['correlation_id'])
            envelope = CrossMASEnvelope.model_validate(existing['envelope'])
        else:
            if (source['status'] in TERMINAL or source['budget']['model_calls']
                    or self._existing(portfolio_run_id, _key(portfolio_run_id, 'selection'))):
                raise FinancialConflict('Further evidence must precede Portfolio role invocation')
            req = PortfolioReviewRequest.model_validate(source['request'])
            if market_request.as_of != req.as_of or market_request.symbol not in self._scope(req):
                raise ValueError('Further evidence timepoint/symbol outside authorized scope')
            budget = _fresh_budget(source)
            if (budget.max_hops == 0 or budget.max_followups == 0
                    or source['budget']['followups'] >= budget.max_followups):
                raise BudgetExhausted('Cross request disabled by user budget')
            run = self.dispatcher.create(source['conversation_id'], market_request,
                idempotency_key=_key(key, 'market'), mode=mode, budget=budget,
                correlation_id=source['correlation_id'])
            target = self._snapshot(run.id)
            envelope = self._envelope(source, target, key, 'MARKET_EVIDENCE_REQUEST')
        return self.admit(portfolio_run_id, target['run_id'], envelope,
            expected_source_version=source['version'], expected_target_version=target['version'])

    def artifact_resolver(self, run_id: str, conversation_id: str,
                          request: PortfolioReviewRequest) -> MarketInvestigationArtifact | None:
        """Consume admitted evidence once within TTL; replay accepted context.

        A durable selection is historical acceptance, not a new transfer. Scope
        is rechecked even on replay; unselected expired evidence returns None.
        """
        own = self._snapshot(run_id)
        if (own['conversation_id'] != conversation_id or own['mas_kind'] != 'portfolio_rebalance'
                or own['request'] != request.model_dump(mode='json')):
            raise ValueError('Resolver run/conversation/request mismatch')
        if own['status'] in {'failed', 'cancelled', 'expired'}:
            return None
        scope = self._scope(request)
        relations = self.dispatcher.relations(run_id)
        eligible = []
        for relation in relations:
            if relation['relation_type'] != 'cross_admitted' or relation['target_run_id'] != run_id:
                continue
            envelope = CrossMASEnvelope.model_validate(relation['envelope'])
            if (envelope.message_type == 'MARKET_EVIDENCE_READY' and envelope.payload_ref
                    and envelope.created_at <= self.clock()
                    and envelope.as_of == request.as_of and envelope.correlation_id == own['correlation_id']):
                eligible.append((envelope, relation))
        if not eligible:
            return None
        # All further evidence must arrive before role invocation. Preserve the
        # selected producer durably so duplicate/restored delivery cannot switch it.
        selection_key = _key(run_id, 'selection')
        selected = self._existing(run_id, selection_key)
        if selected:
            if selected['relation_type'] != 'artifact_selection' or selected['source_run_id'] != run_id:
                raise FinancialConflict('Selection key belongs to a different diagnostic relation')
            marker = CrossMASEnvelope.model_validate(selected['envelope'])
            candidates = [(e, r) for e, r in eligible if r['source_run_id'] == selected['target_run_id']
                          and e.message_id == marker.causation_id
                          and e.deadline_at == marker.deadline_at and e.as_of == marker.as_of]
            if not candidates:
                return None
            envelope, relation = candidates[0]
        else:
            eligible = [(e, r) for e, r in eligible if self.clock() < e.deadline_at]
            if not eligible:
                return None
            envelope, relation = max(eligible, key=lambda item: (item[0].causation_id is not None, item[0].created_at, item[0].message_id))
            producer = self._snapshot(relation['source_run_id'])
            artifact = self.artifacts.get(envelope.payload_ref.artifact_id, conversation_id=conversation_id,
                as_of=request.as_of, schema_version=envelope.payload_ref.schema_version)
            if (not isinstance(artifact, MarketInvestigationArtifact) or artifact.symbol not in scope
                    or artifact.producing_run_id != producer['run_id']
                    or artifact.symbol != producer['request']['symbol'] or artifact.as_of != request.as_of):
                raise ValueError('First consumption requires validated immutable authorized evidence')
            # Non-executable receipt metadata, owned/fenced by the receiver.
            # SYSTEM_UNAVAILABLE is the frozen non-work envelope variant; the
            # relation type distinguishes this selection receipt from a response.
            marker = self._envelope(own, producer, selection_key, 'SYSTEM_UNAVAILABLE',
                cause=envelope.message_id, deadline=envelope.deadline_at)
            try:
                self.dispatcher.link_runs(run_id, producer['run_id'], version=own['version'],
                    relation_type='artifact_selection', idempotency_key=selection_key, envelope=marker)
            except FinancialConflict:
                # A competing selector owns the durable marker; use its winner
                # without recursive retry or an unbounded version loop.
                winner = self._existing(run_id, selection_key)
                if winner:
                    if winner['relation_type'] != 'artifact_selection' or winner['source_run_id'] != run_id:
                        raise FinancialConflict('Invalid competing selection receipt')
                    marker = CrossMASEnvelope.model_validate(winner['envelope'])
                    matches = [(e, r) for e, r in eligible if r['source_run_id'] == winner['target_run_id']
                               and e.message_id == marker.causation_id
                               and e.deadline_at == marker.deadline_at and e.as_of == marker.as_of]
                    if not matches:
                        return None
                    envelope, relation = matches[0]
                else:
                    raise
        artifact = self.artifacts.get(envelope.payload_ref.artifact_id, conversation_id=conversation_id,
            as_of=request.as_of, schema_version=envelope.payload_ref.schema_version)
        producer = self._snapshot(relation['source_run_id'])
        if (not isinstance(artifact, MarketInvestigationArtifact) or artifact.symbol not in scope
                or artifact.producing_run_id != producer['run_id']
                or artifact.symbol != producer['request']['symbol'] or artifact.as_of != request.as_of):
            raise ValueError('Resolver immutable producer/scope mismatch')
        return artifact

    async def _deliver(self, run_id, max_deliveries, peer_timeout):
        for _ in range(max_deliveries):
            current = self._snapshot(run_id)
            if current['status'] in TERMINAL or current['status'] in {'waiting_user', 'paused'}:
                return current
            try:
                await asyncio.wait_for(self.dispatcher.start(run_id), timeout=peer_timeout)
            except (TimeoutError, KeyError):
                return self._snapshot(run_id)
            updated = self._snapshot(run_id)
            if updated['version'] == current['version']:
                return updated
        return self._snapshot(run_id)

    async def advance(self, response: CrossMASResponse, *, max_deliveries: int = 3,
                      peer_timeout: float = 30) -> CrossMASResponse:
        """Bounded scheduler; unfinished checkpoints can be delivered again later."""
        if not 1 <= max_deliveries <= 8 or not 0 < peer_timeout <= 120:
            raise ValueError('Invalid bounded delivery policy')
        result = response.model_copy(deep=True)
        for run_id, kind in ((result.market_run_id, 'market_investigation'),
                             (result.portfolio_run_id, 'portfolio_rebalance')):
            if run_id:
                own = self._snapshot(run_id)
                if (own['conversation_id'] != result.conversation_id or own['correlation_id'] != result.correlation_id
                        or own['mas_kind'] != kind):
                    raise ValueError('Response conversation/correlation/kind mismatch')
        if result.market_run_id:
            market = await self._deliver(result.market_run_id, max_deliveries, peer_timeout)
            if result.portfolio_run_id:
                portfolio = self._snapshot(result.portfolio_run_id)
                if portfolio['status'] not in TERMINAL and market['status'] != 'waiting_user':
                    try:
                        await asyncio.wait_for(asyncio.to_thread(self.transfer,
                            result.market_run_id, result.portfolio_run_id), timeout=peer_timeout)
                    except (ValueError, BudgetExhausted, FinancialConflict, TimeoutError):
                        result.limitations.append('Optional Market transfer unavailable; independent Portfolio continues')
        if result.portfolio_run_id:
            # Restore admitted follow-ups by reading relations; never wait on a
            # process-local future or create another request during advance.
            for relation in self.dispatcher.relations(result.portfolio_run_id):
                if (relation['relation_type'] == 'cross_admitted'
                        and relation['source_run_id'] == result.portfolio_run_id
                        and relation['envelope'].get('message_type') == 'MARKET_EVIDENCE_REQUEST'):
                    request = CrossMASEnvelope.model_validate(relation['envelope'])
                    if self.clock() < request.deadline_at:
                        await self._deliver(relation['target_run_id'], max_deliveries, peer_timeout)
                        try:
                            await asyncio.wait_for(asyncio.to_thread(self.transfer,
                                relation['target_run_id'], result.portfolio_run_id,
                                request_relation=relation), timeout=peer_timeout)
                        except (ValueError, BudgetExhausted, FinancialConflict, TimeoutError):
                            result.limitations.append('Further evidence unavailable; independent Portfolio continues')
            # Optional peer timeout must not replace the independent consumer's
            # own execution allowance. Its persisted active budget still bounds it.
            own_timeout = self._snapshot(result.portfolio_run_id)['budget']['max_active_seconds']
            await self._deliver(result.portfolio_run_id, max_deliveries, own_timeout)
        result.limitations = list(dict.fromkeys(result.limitations))
        return result
