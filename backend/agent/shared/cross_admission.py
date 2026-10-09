"""Atomic cross-message admission; conversation lock precedes every run CAS."""
import uuid
from sqlalchemy import select, update
from db.models.agent import AgentRun
from db.models.financial_mas import FinancialRelation, FinancialArtifact
from .contracts import (CrossMASEnvelope, RunBudget, MarketInvestigationRequest,
                        MarketInvestigationArtifact, PortfolioProposalArtifact)
from .dispatch import FinancialConflict, TERMINAL, aware


REQUEST = 'MARKET_EVIDENCE_REQUEST'
READY = 'MARKET_EVIDENCE_READY'
UNAVAILABLE = 'SYSTEM_UNAVAILABLE'


def _validate_endpoints(dispatcher, source, source_meta, target, target_meta, envelope):
    if source.id == target.id or source_meta.mas_kind == target_meta.mas_kind:
        raise ValueError('cross-MAS admission requires distinct opposite runs')
    if source.conversation_id != target.conversation_id:
        raise ValueError('cross-conversation admission denied')
    if source_meta.correlation_id != target_meta.correlation_id:
        raise ValueError('correlation mismatch')
    if dispatcher._request(source_meta).as_of != dispatcher._request(target_meta).as_of:
        raise ValueError('run timepoint mismatch')
    if (envelope.run_id != source.id or envelope.origin_mas != source_meta.mas_kind
            or envelope.target_mas != target_meta.mas_kind):
        raise ValueError('envelope ownership/direction mismatch')
    if envelope.correlation_id != source_meta.correlation_id:
        raise ValueError('envelope correlation mismatch')
    if envelope.as_of != dispatcher._request(source_meta).as_of:
        raise ValueError('envelope timepoint mismatch')
    if not envelope.idempotency_key or len(envelope.idempotency_key) > 128:
        raise ValueError('invalid idempotency key')


def _validate_payload(dispatcher, session, source, source_meta, target_meta, envelope):
    if envelope.deadline_at <= dispatcher.clock() or envelope.created_at > dispatcher.clock():
        raise ValueError('envelope expired or future-created')
    kind = envelope.message_type
    if kind == 'PORTFOLIO_IMPACT_REQUEST':
        raise ValueError('Portfolio impact requests are unsupported')
    if kind in {REQUEST, READY}:
        expected = 'portfolio_rebalance' if kind == REQUEST else 'market_investigation'
        if source_meta.mas_kind != expected:
            raise ValueError('message type direction mismatch')
    if kind == REQUEST:
        if source.status in TERMINAL:
            raise FinancialConflict('terminal sender cannot request work')
        if envelope.causation_id is not None:
            raise ValueError('request cannot resolve another request')
    if kind == UNAVAILABLE and envelope.payload_ref is not None:
        raise ValueError('unavailable cannot carry artifact')
    if kind == READY and source.status in TERMINAL and source.status != 'completed':
        raise FinancialConflict('only completed producers may transfer final evidence')
    if kind == READY and envelope.payload_ref is None:
        raise ValueError('READY requires Market artifact')
    if envelope.payload_ref is not None:
        artifact = session.get(FinancialArtifact, envelope.payload_ref.artifact_id)
        if (artifact is None or artifact.run_id != source.id
                or artifact.conversation_id != source.conversation_id):
            raise ValueError('artifact ownership mismatch')
        if artifact.schema_version != envelope.payload_ref.schema_version or aware(artifact.as_of) != envelope.as_of:
            raise ValueError('artifact version/timepoint mismatch')
        if artifact.mas_kind != source_meta.mas_kind:
            raise ValueError('artifact source kind mismatch')
        model = MarketInvestigationArtifact if artifact.mas_kind == 'market_investigation' else PortfolioProposalArtifact
        payload = model.model_validate(artifact.payload)
        if payload.producing_run_id != source.id or payload.as_of != envelope.as_of:
            raise ValueError('artifact payload ownership/timepoint mismatch')
        source_request = dispatcher._request(source_meta)
        if isinstance(payload, MarketInvestigationArtifact):
            if payload.symbol != source_request.symbol:
                raise ValueError('artifact source symbol mismatch')
        elif payload.snapshot_id != source_request.portfolio_snapshot_id:
            raise ValueError('artifact source holdings snapshot mismatch')
        target_request = dispatcher._request(target_meta)
        if isinstance(target_request, MarketInvestigationRequest) and target_request.symbol not in artifact.symbols:
            raise ValueError('artifact target symbol mismatch')
    if kind == UNAVAILABLE:
        return  # Non-work diagnostic has no envelope-budget authority.
    budget = envelope.budget
    if any(getattr(budget, counter) > getattr(budget, 'max_' + counter)
           for counter in ('model_calls', 'tool_calls', 'rounds', 'hops', 'followups')):
        raise ValueError('invalid envelope counters')
    for counter in ('hops', 'followups'):
        if getattr(budget, 'max_' + counter) > min(
                getattr(RunBudget.model_validate(meta.budget), 'max_' + counter)
                for meta in (source_meta, target_meta)):
            raise ValueError('envelope advertises excessive cross ceiling')


def _resolution(rows, source_id, target_id, envelope):
    if envelope.causation_id is None:
        return None
    matches = [row for row in rows if row.envelope.get('message_id') == envelope.causation_id]
    if len(matches) != 1:
        raise FinancialConflict('causation must identify one admitted request')
    row = matches[0]
    request = CrossMASEnvelope.model_validate(row.envelope)
    if (row.relation_type != 'cross_admitted' or request.message_type != REQUEST
            or row.correlation_id != envelope.correlation_id
            or row.source_run_id != target_id or row.target_run_id != source_id):
        raise ValueError('causation type/correlation/endpoints mismatch')
    if envelope.message_type not in {READY, UNAVAILABLE}:
        raise ValueError('only READY or UNAVAILABLE resolves request')
    if envelope.created_at < request.created_at or envelope.deadline_at > request.deadline_at:
        raise ValueError('response creation/deadline exceeds request')
    if any(other.relation_type == 'cross_admitted'
           and other.envelope.get('causation_id') == envelope.causation_id for other in rows):
        raise FinancialConflict('request already resolved')
    return row


def _check_wait_cycle(session, rows, source_id, target_id):
    # Inspect admitted requests only. Diagnostic legacy relations never authorize
    # execution or discharge a waiting edge.
    resolved = {row.envelope.get('causation_id') for row in rows
                if row.relation_type == 'cross_admitted'
                and row.envelope.get('message_type') in {READY, UNAVAILABLE}}
    graph = {}
    for row in rows:
        if (row.relation_type != 'cross_admitted'
                or not row.envelope.get('message_type', '').endswith('_REQUEST')
                or row.envelope.get('message_id') in resolved):
            continue
        if any(session.get(AgentRun, run_id).status in TERMINAL
               for run_id in (row.source_run_id, row.target_run_id)):
            continue
        graph.setdefault(row.source_run_id, set()).add(row.target_run_id)
    graph.setdefault(source_id, set()).add(target_id)
    visiting, visited = set(), set()

    def visit(node):
        if node in visiting:
            raise FinancialConflict('outstanding request wait cycle')
        if node in visited:
            return
        visiting.add(node)
        for child in graph.get(node, ()):
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def admit_cross_message(dispatcher, source_run_id, target_run_id, *,
                        expected_source_version, expected_target_version, envelope):
    envelope = CrossMASEnvelope.model_validate(envelope.model_dump())
    data = envelope.model_dump(mode='json')
    with dispatcher.sessions() as session:
        source, source_meta = dispatcher._load(session, source_run_id)
        target, target_meta = dispatcher._load(session, target_run_id)
        _validate_endpoints(dispatcher, source, source_meta, target, target_meta, envelope)
        dispatcher._lock_conversation(session, source.conversation_id)
        session.expire_all()
        source, source_meta = dispatcher._load(session, source_run_id)
        target, target_meta = dispatcher._load(session, target_run_id)
        _validate_endpoints(dispatcher, source, source_meta, target, target_meta, envelope)
        rows = session.scalars(select(FinancialRelation).where(
            FinancialRelation.conversation_id == source.conversation_id)).all()
        existing = next((row for row in rows if row.idempotency_key == envelope.idempotency_key), None)
        if existing is not None:
            if (existing.source_run_id, existing.target_run_id, existing.relation_type, existing.envelope) != (
                    source_run_id, target_run_id, 'cross_admitted', data):
                raise FinancialConflict('relation key has different payload or diagnostic type')
            return dispatcher._relation_snapshot(existing)
        dispatcher._unique_message_id(session, source.conversation_id, envelope.message_id)
        versions = {source_run_id: expected_source_version, target_run_id: expected_target_version}
        for run_id in sorted(versions):
            expected = versions[run_id]
            changed = session.execute(update(AgentRun).where(
                AgentRun.id == run_id, AgentRun.version == expected).values(version=expected + 1),
                execution_options={'synchronize_session': False}).rowcount
            if changed != 1:
                raise FinancialConflict('stale admission version')
        session.refresh(source)
        session.refresh(source_meta)
        session.refresh(target)
        session.refresh(target_meta)
        if target.status in TERMINAL:
            raise FinancialConflict('terminal recipient cannot admit work')
        _validate_payload(dispatcher, session, source, source_meta, target_meta, envelope)
        resolution = _resolution(rows, source_run_id, target_run_id, envelope)
        if envelope.message_type == REQUEST:
            correlation_rows = [row for row in rows if row.correlation_id == source_meta.correlation_id]
            _check_wait_cycle(session, correlation_rows, source_run_id, target_run_id)
        counters = []
        if envelope.message_type != UNAVAILABLE and resolution is None:
            counters.append('hops')
            if envelope.message_type == REQUEST:
                counters.append('followups')
        if counters:
            dispatcher._reserve_cross_budget(session, source_meta, counters)
        row = FinancialRelation(id=str(uuid.uuid4()), conversation_id=source.conversation_id,
            source_run_id=source_run_id, target_run_id=target_run_id,
            correlation_id=source_meta.correlation_id, relation_type='cross_admitted',
            idempotency_key=envelope.idempotency_key, envelope=data)
        session.add(row)
        audit = {'relation_id': row.id, 'message_id': envelope.message_id,
                 'source_run_id': source_run_id, 'target_run_id': target_run_id,
                 'reserved_counters': counters}
        dispatcher._event(session, source, source_meta, 'cross_mas.admitted', audit)
        dispatcher._event(session, target, target_meta, 'cross_mas.received', audit)
        session.commit()
        return dispatcher._relation_snapshot(row)
